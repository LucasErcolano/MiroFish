"""
Experiment Runner — Reproducible Harness for S2 (Spike S2)

Provides:
- Deterministic run_id generation from case_id + variant + seed
- Config YAML loading, validation, and snapshot
- SHA-256 hashing of seed documents and prompts
- Standardized output directory: runs/<case_id>/<variant>/<seed>/
- Automatic results.json export
- Baseline vs experimental comparison via YAML config switching

Usage from scripts/run_experiment.py:
    runner = ExperimentRunner.from_yaml("configs/experiments/example_case.yaml")
    result = runner.run()
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_RUNS_ROOT = "runs"
CONFIG_SNAPSHOT_FILENAME = "config_snapshot.yaml"
RESULTS_FILENAME = "results.json"
SEED_HASHES_FILENAME = "seed_hashes.json"
PROMPT_HASHES_FILENAME = "prompt_hashes.json"
RUN_MANIFEST_FILENAME = "run_manifest.json"

# Regex for valid case_id / variant directory names
_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file's contents."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_text(text: str) -> str:
    """Compute SHA-256 hex digest of a UTF-8 string."""
    return _sha256_bytes(text.encode("utf-8"))


def _validate_safe_name(name: str, field: str = "name") -> None:
    """Ensure a name is safe for use as a directory component."""
    if not _SAFE_NAME_RE.match(name):
        raise ValueError(
            f"Invalid {field} '{name}': must match {_SAFE_NAME_RE.pattern}"
        )


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SeedDocument:
    """A seed document to be hashed for provenance."""
    path: str  # Relative to project root or absolute
    alias: str = ""  # Short label (e.g. "T0", "noise_early")
    content_hash: str = ""  # Populated at run time


@dataclass
class PromptSpec:
    """A prompt/question to hash for provenance."""
    path: str  # Relative to project root or absolute
    alias: str = ""  # Short label
    content_hash: str = ""  # Populated at run time


@dataclass
class ExperimentResult:
    """Structured result of a single experiment run."""
    case_id: str
    variant: str
    seed: int
    run_id: str
    status: str  # "completed" | "failed" | "blocked"
    started_at: str = ""
    completed_at: str = ""
    error: str = ""
    # Populated by the actual simulation
    num_rounds_requested: Optional[int] = None
    num_rounds_completed: Optional[int] = None
    memory_mode: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    latency_sec: float = 0.0
    cost_usd_est: float = 0.0
    parse_errors: int = 0
    leak_flags: List[str] = field(default_factory=list)
    prediction: str = ""
    ground_truth: str = ""
    score: Optional[float] = None
    # Provenance
    config_snapshot_path: str = ""
    seed_hashes_path: str = ""
    prompt_hashes_path: str = ""
    output_dir: str = ""
    # Memory retrieval provenance
    memory_retrieval_log: List[Dict[str, Any]] = field(default_factory=list)
    memory_metrics: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Config schema validation
# ---------------------------------------------------------------------------

REQUIRED_KEYS = {
    "case_id", "variant", "seed",
}

OPTIONAL_KEYS = {
    "memory_mode", "max_rounds", "platform",
    "platforms", "parallel_profile_count",
    "model", "llm_base_url", "llm_api_key_env",
    "seed_documents", "prompts",
    "simulation_requirement", "project_name",
    "enable_graph_memory_update", "force",
    "use_llm_for_profiles", "generate_report",
    "poll_timeout_seconds", "extra_env",
    "runs_root", "project_root",
}

VALID_MEMORY_MODES = {"baseline", "experimental"}
VALID_VARIANTS = {"baseline", "experimental", "memory", "multimodel"}


def validate_config(cfg: Dict[str, Any]) -> List[str]:
    """Validate experiment config dict. Returns list of error strings."""
    errors: List[str] = []

    missing = REQUIRED_KEYS - set(cfg.keys())
    if missing:
        errors.append(f"Missing required keys: {sorted(missing)}")

    case_id = cfg.get("case_id", "")
    if case_id and not _SAFE_NAME_RE.match(str(case_id)):
        errors.append(f"Invalid case_id '{case_id}'")

    variant = cfg.get("variant", "")
    if variant and str(variant) not in VALID_VARIANTS:
        errors.append(
            f"Invalid variant '{variant}'. Must be one of {sorted(VALID_VARIANTS)}"
        )

    seed = cfg.get("seed")
    if seed is not None:
        try:
            int(seed)
        except (TypeError, ValueError):
            errors.append(f"seed must be an integer, got: {seed!r}")

    memory_mode = cfg.get("memory_mode", "")
    if memory_mode and str(memory_mode) not in VALID_MEMORY_MODES:
        errors.append(
            f"Invalid memory_mode '{memory_mode}'. Must be one of {sorted(VALID_MEMORY_MODES)}"
        )

    unknown = set(cfg.keys()) - REQUIRED_KEYS - OPTIONAL_KEYS
    if unknown:
        errors.append(f"Unknown config keys: {sorted(unknown)}")

    return errors


# ---------------------------------------------------------------------------
# Deterministic run_id
# ---------------------------------------------------------------------------


def compute_run_id(case_id: str, variant: str, seed: int) -> str:
    """Generate a deterministic run_id from case_id + variant + seed.

    The format is: <case_id>__<variant>__s<int-seed>
    Example: argentina_case_T0__baseline__s1
    """
    _validate_safe_name(case_id, "case_id")
    _validate_safe_name(variant, "variant")
    return f"{case_id}__{variant}__s{seed}"


# ---------------------------------------------------------------------------
# ExperimentRunner
# ---------------------------------------------------------------------------


class ExperimentRunner:
    """Orchestrates a reproducible experiment run.

    The runner:
    1. Loads config from YAML
    2. Validates it
    3. Computes a deterministic run_id
    4. Creates the output directory structure
    5. Snapshots the config
    6. Hashes seed documents and prompts
    7. Sets environment variables (e.g. MEMORY_MODE)
    8. Invokes the simulation (or a dry-run / smoke test)
    9. Writes results.json
    """

    def __init__(
        self,
        case_id: str,
        variant: str,
        seed: int,
        memory_mode: str = "baseline",
        max_rounds: Optional[int] = None,
        platform: str = "parallel",
        simulation_requirement: str = "",
        project_name: str = "",
        seed_documents: Optional[List[Dict[str, str]]] = None,
        prompts: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        llm_api_key_env: Optional[str] = None,
        enable_graph_memory_update: bool = True,
        force: bool = True,
        use_llm_for_profiles: bool = True,
        generate_report: bool = True,
        poll_timeout_seconds: int = 3600,
        parallel_profile_count: int = 5,
        extra_env: Optional[Dict[str, str]] = None,
        runs_root: str = DEFAULT_RUNS_ROOT,
        project_root: Optional[str] = None,
    ):
        self.case_id = case_id
        self.variant = variant
        self.seed = int(seed)
        self.memory_mode = memory_mode
        self.max_rounds = max_rounds
        self.platform = platform
        self.simulation_requirement = simulation_requirement
        self.project_name = project_name or case_id
        self.seed_documents = seed_documents or []
        self.prompts = prompts or []
        self.model = model
        self.llm_base_url = llm_base_url
        self.llm_api_key_env = llm_api_key_env
        self.enable_graph_memory_update = enable_graph_memory_update
        self.force = force
        self.use_llm_for_profiles = use_llm_for_profiles
        self.generate_report = generate_report
        self.poll_timeout_seconds = poll_timeout_seconds
        self.parallel_profile_count = parallel_profile_count
        self.extra_env = extra_env or {}
        self.runs_root = runs_root
        self.project_root = Path(project_root or os.getcwd())

        # Computed
        self.run_id = compute_run_id(self.case_id, self.variant, self.seed)
        self.output_dir = (
            self.project_root / self.runs_root
            / self.case_id / self.variant / f"s{self.seed}"
        )
        self._result = ExperimentResult(
            case_id=self.case_id,
            variant=self.variant,
            seed=self.seed,
            run_id=self.run_id,
            status="pending",
        )

    # ------------------------------------------------------------------
    # Factory from YAML
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, yaml_path: str, **overrides: Any) -> "ExperimentRunner":
        """Load config from a YAML file and create an ExperimentRunner."""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Config YAML not found: {yaml_path}")

        with path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        errors = validate_config(cfg)
        if errors:
            raise ValueError(f"Invalid config in {yaml_path}:\n" + "\n".join(errors))

        # Merge overrides
        cfg.update(overrides)

        # Build project_root from YAML location if not specified
        project_root = str(path.resolve().parent.parent.parent)

        return cls(
            case_id=cfg["case_id"],
            variant=cfg["variant"],
            seed=cfg["seed"],
            memory_mode=cfg.get("memory_mode", "baseline"),
            max_rounds=cfg.get("max_rounds"),
            platform=cfg.get("platform", "parallel"),
            simulation_requirement=cfg.get("simulation_requirement", ""),
            project_name=cfg.get("project_name", cfg["case_id"]),
            seed_documents=cfg.get("seed_documents", []),
            prompts=cfg.get("prompts", []),
            model=cfg.get("model"),
            llm_base_url=cfg.get("llm_base_url"),
            llm_api_key_env=cfg.get("llm_api_key_env"),
            enable_graph_memory_update=cfg.get("enable_graph_memory_update", True),
            force=cfg.get("force", True),
            use_llm_for_profiles=cfg.get("use_llm_for_profiles", True),
            generate_report=cfg.get("generate_report", True),
            poll_timeout_seconds=cfg.get("poll_timeout_seconds", 3600),
            parallel_profile_count=cfg.get("parallel_profile_count", 5),
            extra_env=cfg.get("extra_env", {}),
            runs_root=cfg.get("runs_root", DEFAULT_RUNS_ROOT),
            project_root=project_root,
        )

    # ------------------------------------------------------------------
    # Output directory
    # ------------------------------------------------------------------

    def ensure_output_dir(self) -> Path:
        """Create the output directory structure if it doesn't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir

    # ------------------------------------------------------------------
    # Config snapshot
    # ------------------------------------------------------------------

    def snapshot_config(self) -> Path:
        """Write a snapshot of the full config used for this run."""
        snap = {
            "case_id": self.case_id,
            "variant": self.variant,
            "seed": self.seed,
            "run_id": self.run_id,
            "memory_mode": self.memory_mode,
            "max_rounds": self.max_rounds,
            "platform": self.platform,
            "simulation_requirement": self.simulation_requirement,
            "project_name": self.project_name,
            "seed_documents": self.seed_documents,
            "prompts": self.prompts,
            "model": self.model,
            "llm_base_url": self.llm_base_url,
            "llm_api_key_env": self.llm_api_key_env,
            "enable_graph_memory_update": self.enable_graph_memory_update,
            "force": self.force,
            "use_llm_for_profiles": self.use_llm_for_profiles,
            "generate_report": self.generate_report,
            "poll_timeout_seconds": self.poll_timeout_seconds,
            "parallel_profile_count": self.parallel_profile_count,
            "extra_env": {k: "***" for k in self.extra_env} if self.extra_env else {},
            "runs_root": self.runs_root,
            "snapshot_at": _now_utc_iso(),
        }
        path = self.output_dir / CONFIG_SNAPSHOT_FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.dump(snap, default_flow_style=False, allow_unicode=True), encoding="utf-8")
        self._result.config_snapshot_path = str(path)
        return path

    # ------------------------------------------------------------------
    # Hash seed documents and prompts
    # ------------------------------------------------------------------

    def hash_seed_documents(self) -> Path:
        """Compute SHA-256 hashes of all declared seed documents."""
        hashes: List[Dict[str, str]] = []
        for doc in self.seed_documents:
            doc_path = self.project_root / doc.get("path", "")
            alias = doc.get("alias", doc.get("path", ""))
            content_hash = ""
            if doc_path.exists():
                content_hash = _sha256_file(doc_path)
            else:
                # If path is absolute, try it directly
                abs_path = Path(doc["path"])
                if abs_path.exists():
                    content_hash = _sha256_file(abs_path)
            hashes.append({
                "alias": alias,
                "path": doc.get("path", ""),
                "sha256": content_hash or "FILE_NOT_FOUND",
            })
        path = self.output_dir / SEED_HASHES_FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(hashes, indent=2, ensure_ascii=False), encoding="utf-8")
        self._result.seed_hashes_path = str(path)
        return path

    def hash_prompts(self) -> Path:
        """Compute SHA-256 hashes of all declared prompts/questions."""
        hashes: List[Dict[str, str]] = []
        for p in self.prompts:
            p_path = self.project_root / p.get("path", "")
            alias = p.get("alias", p.get("path", ""))
            content_hash = ""
            if p_path.exists():
                content_hash = _sha256_file(p_path)
            else:
                abs_path = Path(p["path"])
                if abs_path.exists():
                    content_hash = _sha256_file(abs_path)
            # Also hash inline content if provided
            if "content" in p:
                content_hash = content_hash or _sha256_text(p["content"])
            hashes.append({
                "alias": alias,
                "path": p.get("path", ""),
                "sha256": content_hash or "NOT_PROVIDED",
            })
        path = self.output_dir / PROMPT_HASHES_FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(hashes, indent=2, ensure_ascii=False), encoding="utf-8")
        self._result.prompt_hashes_path = str(path)
        return path

    # ------------------------------------------------------------------
    # Environment setup
    # ------------------------------------------------------------------

    def build_env_overrides(self) -> Dict[str, str]:
        """Build environment variable overrides for this run.

        This sets MEMORY_MODE and any extra_env variables.
        API keys are never written to files — they stay in the process env.
        """
        env = {}
        # Core memory mode
        env["MEMORY_MODE"] = self.memory_mode
        # Backward compat
        if self.memory_mode == "experimental":
            env["USE_EXPERIMENTAL_MEMORY"] = "true"
        else:
            env["USE_EXPERIMENTAL_MEMORY"] = "false"
        # LLM config
        if self.model:
            env["LLM_MODEL_NAME"] = self.model
        if self.llm_base_url:
            env["LLM_BASE_URL"] = self.llm_base_url
        if self.llm_api_key_env:
            # Read the API key from the specified env var name
            key_val = os.environ.get(self.llm_api_key_env, "")
            if key_val:
                env["LLM_API_KEY"] = key_val
        # Extra env (non-secret values only; secrets should use llm_api_key_env)
        env.update(self.extra_env)
        return env

    def apply_env_overrides(self) -> None:
        """Apply environment variable overrides to os.environ for this run."""
        env = self.build_env_overrides()
        os.environ.update(env)

    # ------------------------------------------------------------------
    # Run manifest
    # ------------------------------------------------------------------

    def write_run_manifest(self, status: str, **extra: Any) -> Path:
        """Write run_manifest.json with full provenance information."""
        manifest = {
            "run_id": self.run_id,
            "case_id": self.case_id,
            "variant": self.variant,
            "seed": self.seed,
            "status": status,
            "memory_mode": self.memory_mode,
            "started_at": self._result.started_at,
            "completed_at": self._result.completed_at or _now_utc_iso(),
            "output_dir": str(self.output_dir),
            "config_snapshot_path": self._result.config_snapshot_path,
            "seed_hashes_path": self._result.seed_hashes_path,
            "prompt_hashes_path": self._result.prompt_hashes_path,
            "num_rounds_requested": self.max_rounds,
            "num_rounds_completed": self._result.num_rounds_completed,
            **extra,
        }
        path = self.output_dir / RUN_MANIFEST_FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return path

    # ------------------------------------------------------------------
    # Results export
    # ------------------------------------------------------------------

    def write_results(self) -> Path:
        """Write results.json with the structured experiment result."""
        result_dict = asdict(self._result)
        result_dict["output_dir"] = str(self.output_dir)
        path = self.output_dir / RESULTS_FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(result_dict, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return path

    # ------------------------------------------------------------------
    # Memory data collection
    # ------------------------------------------------------------------

    def _collect_memory_data(self) -> None:
        """Collect memory metrics and retrieval log from the global
        MemoryMetrics singleton and store in the result.

        Safe to call even if no memory retrievals occurred — produces
        empty/logged data as appropriate.
        """
        from app.services.memory_mode import get_metrics
        metrics = get_metrics()
        self._result.memory_metrics = metrics.get_summary()
        self._result.memory_retrieval_log = metrics.get_recent_log()

    # ------------------------------------------------------------------
    # Dry run (no backend required)
    # ------------------------------------------------------------------

    def dry_run(self) -> ExperimentResult:
        """Execute a dry run: set up directories, snapshot config, hash files,
        write manifest, but do NOT invoke the backend simulation.

        This validates the harness plumbing without needing MiroFish backend.
        Memory metrics and retrieval log are set to empty defaults since no
        simulation runs.
        """
        self.ensure_output_dir()
        self._result.started_at = _now_utc_iso()

        try:
            self.snapshot_config()
            self.hash_seed_documents()
            self.hash_prompts()
            self._result.status = "dry_run_completed"
            self._result.memory_mode = self.memory_mode
            self._result.output_dir = str(self.output_dir)
            # Dry run: no simulation ran, so memory data is empty
            self._result.memory_retrieval_log = []
            self._result.memory_metrics = {}
            self.write_run_manifest(status="dry_run_completed")
            self.write_results()
        except Exception as exc:
            self._result.status = "failed"
            self._result.error = traceback.format_exc()
            self.write_run_manifest(status="failed", error=str(exc))
            self.write_results()
            raise

        self._result.completed_at = _now_utc_iso()
        return self._result

    # ------------------------------------------------------------------
    # Full run (using headless runner)
    # ------------------------------------------------------------------

    def run(self, base_url: str = "http://localhost:5001") -> ExperimentResult:
        """Execute a full experiment run using the headless runner.

        This requires the MiroFish backend to be running.
        """
        # Import here to avoid circular / heavy deps at module level
        sys.path.insert(0, str(self.project_root / "tools"))
        from mirofish_headless import MiroFishHeadlessRunner, file_sha256

        self.ensure_output_dir()
        self._result.started_at = _now_utc_iso()
        self.apply_env_overrides()

        try:
            # Snapshot and hash before simulation
            self.snapshot_config()
            self.hash_seed_documents()
            self.hash_prompts()

            # Collect seed document paths for the headless runner
            seed_files: List[Path] = []
            for doc in self.seed_documents:
                p = self.project_root / doc.get("path", "")
                if p.exists():
                    seed_files.append(p)
                elif Path(doc["path"]).exists():
                    seed_files.append(Path(doc["path"]))

            # Resolve prompt / simulation requirement
            requirement = self.simulation_requirement
            if not requirement and self.prompts:
                # Use first prompt file content as requirement
                p_path = self.project_root / self.prompts[0].get("path", "")
                if p_path.exists():
                    requirement = p_path.read_text(encoding="utf-8")

            if not requirement:
                raise ValueError(
                    "No simulation_requirement provided and no prompt files found"
                )

            if not seed_files:
                raise ValueError("No seed document files found")

            # Build the headless runner, pointing output to our standard dir
            runner = MiroFishHeadlessRunner(
                base_url=base_url,
                output_dir=str(self.output_dir),
                poll_interval=2.0,
                timeout_seconds=self.poll_timeout_seconds,
            )

            # Run the full flow
            manifest = runner.run_full_flow(
                files=seed_files,
                simulation_requirement=requirement,
                project_name=self.project_name,
                max_rounds=self.max_rounds,
                platform=self.platform,
                enable_graph_memory_update=self.enable_graph_memory_update,
                force=self.force,
                use_llm_for_profiles=self.use_llm_for_profiles,
                parallel_profile_count=self.parallel_profile_count,
                generate_report=self.generate_report,
                poll_timeout_seconds=self.poll_timeout_seconds,
            )

            self._result.status = manifest.get("status", "unknown")
            self._result.num_rounds_requested = self.max_rounds
            self._result.num_rounds_completed = manifest.get("num_rounds_or_epochs")
            self._result.memory_mode = self.memory_mode
            self._result.output_dir = str(self.output_dir)

            # Collect memory metrics and retrieval log from the simulation
            self._collect_memory_data()

            self.write_run_manifest(
                status=self._result.status,
                simulation_id=manifest.get("simulation_id", ""),
                project_id=manifest.get("project_id", ""),
                graph_id=manifest.get("graph_id", ""),
                report_id=manifest.get("report_id", ""),
            )
            self.write_results()

        except Exception as exc:
            self._result.status = "failed"
            self._result.error = traceback.format_exc()
            # Collect any partial memory metrics even on failure
            self._collect_memory_data()
            self.write_run_manifest(status="failed", error=str(exc))
            self.write_results()
            # Don't re-raise — result captures the error

        self._result.completed_at = _now_utc_iso()
        return self._result

    # ------------------------------------------------------------------
    # Compare results across variants
    # ------------------------------------------------------------------

    @staticmethod
    def compare_results(runs_root: str, case_id: str, seeds: Optional[List[int]] = None) -> Dict[str, Any]:
        """Load and compare results from baseline vs experimental variants.

        Returns a dict with per-variant, per-seed comparison.
        If seeds is None, discovers all seed directories automatically.
        """
        comparison: Dict[str, Any] = {"case_id": case_id, "variants": {}}
        root = Path(runs_root) / case_id

        if not root.exists():
            comparison["error"] = f"Case directory not found: {root}"
            return comparison

        for variant_dir in sorted(root.iterdir()):
            if not variant_dir.is_dir():
                continue
            variant_name = variant_dir.name
            variant_data: Dict[str, Any] = {"name": variant_name, "seeds": {}}

            for seed_dir in sorted(variant_dir.iterdir()):
                if not seed_dir.is_dir():
                    continue
                seed_name = seed_dir.name
                # Filter by seeds if provided
                if seeds is not None:
                    try:
                        seed_num = int(seed_name.lstrip("s"))
                        if seed_num not in seeds:
                            continue
                    except ValueError:
                        continue

                results_file = seed_dir / RESULTS_FILENAME
                if results_file.exists():
                    try:
                        data = json.loads(results_file.read_text(encoding="utf-8"))
                        variant_data["seeds"][seed_name] = data
                    except json.JSONDecodeError:
                        variant_data["seeds"][seed_name] = {"error": "invalid JSON"}
                else:
                    # Check for manifest if no results.json
                    manifest_file = seed_dir / RUN_MANIFEST_FILENAME
                    if manifest_file.exists():
                        try:
                            data = json.loads(manifest_file.read_text(encoding="utf-8"))
                            variant_data["seeds"][seed_name] = data
                        except json.JSONDecodeError:
                            variant_data["seeds"][seed_name] = {"error": "invalid JSON in manifest"}
                    else:
                        variant_data["seeds"][seed_name] = {"error": "no results found"}

            comparison["variants"][variant_name] = variant_data

        return comparison


# ---------------------------------------------------------------------------
# Convenience: load multiple configs for a case comparison
# ---------------------------------------------------------------------------


def load_case_variants(
    case_dir: str,
    seeds: Optional[List[int]] = None,
) -> List[ExperimentRunner]:
    """Load all variant YAMLs from a case directory.

    Expected structure:
        configs/experiments/<case_id>/
            baseline.yaml
            experimental.yaml
            ...

    Each YAML must have case_id + variant + seed set.
    If seeds is provided, override the seed in each config.
    """
    case_path = Path(case_dir)
    runners: List[ExperimentRunner] = []

    for yaml_file in sorted(case_path.glob("*.yaml")):
        with yaml_file.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        if seeds:
            for s in seeds:
                override_cfg = copy.deepcopy(cfg)
                override_cfg["seed"] = s
                runner = ExperimentRunner.from_yaml(str(yaml_file), **{"seed": s})
                runners.append(runner)
        else:
            runner = ExperimentRunner.from_yaml(str(yaml_file))
            runners.append(runner)

    return runners