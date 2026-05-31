"""
Tests for the S2 Experiment Harness (experiment_runner.py).

Verifies:
- Deterministic run_id generation
- Config validation
- Config YAML loading and snapshot
- Seed document hashing
- Prompt hashing
- Output directory structure: runs/<case_id>/<variant>/<seed>/
- results.json export
- Dry run (no backend required)
- Baseline vs experimental switching via YAML
"""

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

# Ensure backend is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
import sys

sys.path.insert(0, str(PROJECT_ROOT / "backend"))

# Import directly from module to avoid Flask dependency in app.__init__
# The experiment_runner module only depends on stdlib + pyyaml
import importlib.util
import types

_mod_path = str(PROJECT_ROOT / "backend" / "app" / "services" / "experiment_runner.py")
_spec = importlib.util.spec_from_file_location("experiment_runner", _mod_path)
_mod = types.ModuleType("experiment_runner")
_mod.__file__ = _mod_path
_mod.__loader__ = _spec.loader
# Register the module so dataclass field() defaults resolve correctly
sys.modules["experiment_runner"] = _mod
_spec.loader.exec_module(_mod)

ExperimentRunner = _mod.ExperimentRunner
ExperimentResult = _mod.ExperimentResult
compute_run_id = _mod.compute_run_id
validate_config = _mod.validate_config
_sha256_text = _mod._sha256_text
_sha256_bytes = _mod._sha256_bytes
_sha256_file = _mod._sha256_file
CONFIG_SNAPSHOT_FILENAME = _mod.CONFIG_SNAPSHOT_FILENAME
RESULTS_FILENAME = _mod.RESULTS_FILENAME
SEED_HASHES_FILENAME = _mod.SEED_HASHES_FILENAME
PROMPT_HASHES_FILENAME = _mod.PROMPT_HASHES_FILENAME
RUN_MANIFEST_FILENAME = _mod.RUN_MANIFEST_FILENAME


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for test outputs."""
    d = tempfile.mkdtemp(prefix="test_experiment_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_config(tmp_dir):
    """Create a sample YAML config file."""
    cfg = {
        "case_id": "test_case",
        "variant": "baseline",
        "seed": 1,
        "memory_mode": "baseline",
        "max_rounds": 5,
        "platform": "parallel",
        "simulation_requirement": "Test simulation requirement",
        "seed_documents": [],
        "prompts": [],
    }
    path = tmp_dir / "test_config.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
    return str(path)


@pytest.fixture
def sample_config_with_files(tmp_dir):
    """Create a YAML config with seed documents and prompts."""
    # Create a seed document
    seed_dir = tmp_dir / "seeds"
    seed_dir.mkdir()
    seed_file = seed_dir / "doc_T0.md"
    seed_file.write_text("# Evidence document\n\nArgentina held elections in October 2023.", encoding="utf-8")

    # Create a prompt file
    prompt_file = seed_dir / "question.md"
    prompt_file.write_text("What happened in the Argentine election?", encoding="utf-8")

    cfg = {
        "case_id": "argentina_case",
        "variant": "baseline",
        "seed": 42,
        "memory_mode": "baseline",
        "max_rounds": 10,
        "seed_documents": [
            {"path": str(seed_file), "alias": "doc_T0"},
        ],
        "prompts": [
            {"path": str(prompt_file), "alias": "main_question"},
        ],
    }
    path = tmp_dir / "config_with_files.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
    return str(path)


# =============================================================================
# Test: Deterministic run_id
# =============================================================================

class TestRunId:
    def test_basic(self):
        rid = compute_run_id("my_case", "baseline", 1)
        assert rid == "my_case__baseline__s1"

    def test_different_seeds(self):
        r1 = compute_run_id("case", "baseline", 1)
        r2 = compute_run_id("case", "baseline", 2)
        assert r1 != r2

    def test_different_variants(self):
        r1 = compute_run_id("case", "baseline", 1)
        r2 = compute_run_id("case", "experimental", 1)
        assert r1 != r2

    def test_invalid_case_id(self):
        with pytest.raises(ValueError, match="Invalid case_id"):
            compute_run_id("bad case!", "baseline", 1)

    def test_invalid_variant(self):
        with pytest.raises(ValueError, match="Invalid variant"):
            compute_run_id("case", "b@d_v@riant", 1)


# =============================================================================
# Test: Config validation
# =============================================================================

class TestConfigValidation:
    def test_valid_minimal(self):
        cfg = {"case_id": "test", "variant": "baseline", "seed": 1}
        errors = validate_config(cfg)
        assert errors == []

    def test_missing_required(self):
        cfg = {"variant": "baseline"}
        errors = validate_config(cfg)
        assert any("case_id" in e or "seed" in e for e in errors)

    def test_invalid_memory_mode(self):
        cfg = {"case_id": "test", "variant": "baseline", "seed": 1, "memory_mode": "invalid"}
        errors = validate_config(cfg)
        assert any("memory_mode" in e for e in errors)

    def test_valid_memory_modes(self):
        for mode in ["baseline", "experimental"]:
            cfg = {"case_id": "test", "variant": "baseline", "seed": 1, "memory_mode": mode}
            errors = validate_config(cfg)
            assert not any("memory_mode" in e for e in errors)

    def test_invalid_variant(self):
        cfg = {"case_id": "test", "variant": "unknown_variant", "seed": 1}
        errors = validate_config(cfg)
        assert any("variant" in e for e in errors)

    def test_unknown_keys(self):
        cfg = {"case_id": "test", "variant": "baseline", "seed": 1, "totally_unknown": 42}
        errors = validate_config(cfg)
        assert any("unknown" in e.lower() for e in errors)


# =============================================================================
# Test: SHA-256 hashing
# =============================================================================

class TestHashing:
    def test_sha256_text_deterministic(self):
        text = "Hello, world!"
        h1 = _sha256_text(text)
        h2 = _sha256_text(text)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest

    def test_sha256_text_different(self):
        h1 = _sha256_text("foo")
        h2 = _sha256_text("bar")
        assert h1 != h2

    def test_sha256_bytes(self):
        h = _sha256_bytes(b"test data")
        assert len(h) == 64

    def test_sha256_file(self, tmp_dir):
        f = tmp_dir / "test_file.txt"
        f.write_text("file content", encoding="utf-8")
        h = _sha256_file(f)
        assert h == _sha256_text("file content")


# =============================================================================
# Test: ExperimentRunner init and from_yaml
# =============================================================================

class TestExperimentRunnerInit:
    def test_basic_init(self, tmp_dir):
        runner = ExperimentRunner(
            case_id="test_case",
            variant="baseline",
            seed=1,
            runs_root=str(tmp_dir / "runs"),
            project_root=str(tmp_dir),
        )
        assert runner.run_id == "test_case__baseline__s1"
        assert runner.memory_mode == "baseline"
        assert runner.output_dir == tmp_dir / "runs" / "test_case" / "baseline" / "s1"

    def test_from_yaml(self, sample_config, tmp_dir):
        runner = ExperimentRunner.from_yaml(sample_config, runs_root=str(tmp_dir / "runs"))
        assert runner.case_id == "test_case"
        assert runner.variant == "baseline"
        assert runner.seed == 1

    def test_yaml_override_seed(self, sample_config, tmp_dir):
        runner = ExperimentRunner.from_yaml(sample_config, seed=99, runs_root=str(tmp_dir / "runs"))
        assert runner.seed == 99
        assert "s99" in runner.run_id

    def test_yaml_override_memory_mode(self, sample_config, tmp_dir):
        runner = ExperimentRunner.from_yaml(
            sample_config, memory_mode="experimental", runs_root=str(tmp_dir / "runs")
        )
        assert runner.memory_mode == "experimental"

    def test_from_yaml_missing_file(self):
        with pytest.raises(FileNotFoundError):
            ExperimentRunner.from_yaml("/nonexistent/path.yaml")


# =============================================================================
# Test: Output directory structure
# =============================================================================

class TestOutputDirectory:
    def test_create_dirs(self, tmp_dir):
        runner = ExperimentRunner(
            case_id="my_case",
            variant="experimental",
            seed=7,
            runs_root=str(tmp_dir / "runs"),
            project_root=str(tmp_dir),
        )
        output = runner.ensure_output_dir()
        assert output.exists()
        assert output == tmp_dir / "runs" / "my_case" / "experimental" / "s7"


# =============================================================================
# Test: Config snapshot
# =============================================================================

class TestConfigSnapshot:
    def test_snapshot_created(self, tmp_dir):
        runner = ExperimentRunner(
            case_id="snap_test",
            variant="baseline",
            seed=1,
            runs_root=str(tmp_dir / "runs"),
            project_root=str(tmp_dir),
        )
        runner.ensure_output_dir()
        snap_path = runner.snapshot_config()
        assert snap_path.exists()

        with snap_path.open("r", encoding="utf-8") as f:
            snap = yaml.safe_load(f)
        assert snap["case_id"] == "snap_test"
        assert snap["memory_mode"] == "baseline"
        assert "snapshot_at" in snap

    def test_snapshot_redacts_env(self, tmp_dir):
        runner = ExperimentRunner(
            case_id="snap_test",
            variant="baseline",
            seed=1,
            extra_env={"SECRET_KEY": "super_secret_value"},
            runs_root=str(tmp_dir / "runs"),
            project_root=str(tmp_dir),
        )
        runner.ensure_output_dir()
        snap_path = runner.snapshot_config()
        with snap_path.open("r", encoding="utf-8") as f:
            snap = yaml.safe_load(f)
        # Extra env values should be redacted
        assert snap["extra_env"]["SECRET_KEY"] == "***"


# =============================================================================
# Test: Seed document hashing
# =============================================================================

class TestSeedDocumentHashing:
    def test_hash_real_file(self, sample_config_with_files, tmp_dir):
        runner = ExperimentRunner.from_yaml(
            sample_config_with_files, runs_root=str(tmp_dir / "runs")
        )
        runner.ensure_output_dir()
        hash_path = runner.hash_seed_documents()
        assert hash_path.exists()

        with hash_path.open("r", encoding="utf-8") as f:
            hashes = json.load(f)
        assert len(hashes) == 1
        assert hashes[0]["alias"] == "doc_T0"
        assert hashes[0]["sha256"] != "FILE_NOT_FOUND"
        assert len(hashes[0]["sha256"]) == 64

    def test_hash_missing_file(self, tmp_dir):
        runner = ExperimentRunner(
            case_id="hash_test",
            variant="baseline",
            seed=1,
            seed_documents=[{"path": "/nonexistent/file.md", "alias": "missing"}],
            runs_root=str(tmp_dir / "runs"),
            project_root=str(tmp_dir),
        )
        runner.ensure_output_dir()
        hash_path = runner.hash_seed_documents()
        with hash_path.open("r", encoding="utf-8") as f:
            hashes = json.load(f)
        assert hashes[0]["sha256"] == "FILE_NOT_FOUND"


# =============================================================================
# Test: Prompt hashing
# =============================================================================

class TestPromptHashing:
    def test_hash_real_prompt(self, sample_config_with_files, tmp_dir):
        runner = ExperimentRunner.from_yaml(
            sample_config_with_files, runs_root=str(tmp_dir / "runs")
        )
        runner.ensure_output_dir()
        prompt_path = runner.hash_prompts()
        assert prompt_path.exists()

        with prompt_path.open("r", encoding="utf-8") as f:
            hashes = json.load(f)
        assert len(hashes) == 1
        assert hashes[0]["alias"] == "main_question"


# =============================================================================
# Test: results.json export
# =============================================================================

class TestResultsJson:
    def test_dry_run_writes_results(self, tmp_dir):
        runner = ExperimentRunner(
            case_id="results_test",
            variant="baseline",
            seed=1,
            runs_root=str(tmp_dir / "runs"),
            project_root=str(tmp_dir),
        )
        result = runner.dry_run()
        assert result.status == "dry_run_completed"
        assert result.run_id == "results_test__baseline__s1"

        results_path = runner.output_dir / RESULTS_FILENAME
        assert results_path.exists()

        with results_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["case_id"] == "results_test"
        assert data["variant"] == "baseline"
        assert data["seed"] == 1
        assert data["memory_mode"] == "baseline"


# =============================================================================
# Test: Run manifest
# =============================================================================

class TestRunManifest:
    def test_manifest_written_on_dry_run(self, tmp_dir):
        runner = ExperimentRunner(
            case_id="manifest_test",
            variant="experimental",
            seed=3,
            runs_root=str(tmp_dir / "runs"),
            project_root=str(tmp_dir),
        )
        runner.dry_run()

        manifest_path = runner.output_dir / RUN_MANIFEST_FILENAME
        assert manifest_path.exists()

        with manifest_path.open("r", encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest["run_id"] == "manifest_test__experimental__s3"
        assert manifest["case_id"] == "manifest_test"
        assert manifest["variant"] == "experimental"
        assert manifest["seed"] == 3


# =============================================================================
# Test: Environment overrides
# =============================================================================

class TestEnvOverrides:
    def test_baseline_env(self, tmp_dir):
        runner = ExperimentRunner(
            case_id="env_test",
            variant="baseline",
            seed=1,
            memory_mode="baseline",
            runs_root=str(tmp_dir / "runs"),
        )
        env = runner.build_env_overrides()
        assert env["MEMORY_MODE"] == "baseline"
        assert env["USE_EXPERIMENTAL_MEMORY"] == "false"

    def test_experimental_env(self, tmp_dir):
        runner = ExperimentRunner(
            case_id="env_test",
            variant="experimental",
            seed=1,
            memory_mode="experimental",
            runs_root=str(tmp_dir / "runs"),
        )
        env = runner.build_env_overrides()
        assert env["MEMORY_MODE"] == "experimental"
        assert env["USE_EXPERIMENTAL_MEMORY"] == "true"

    def test_model_override(self, tmp_dir):
        runner = ExperimentRunner(
            case_id="env_test",
            variant="baseline",
            seed=1,
            model="gemini-2.5-flash-lite",
            runs_root=str(tmp_dir / "runs"),
        )
        env = runner.build_env_overrides()
        assert env["LLM_MODEL_NAME"] == "gemini-2.5-flash-lite"


# =============================================================================
# Test: Full output structure (runs/<case_id>/<variant>/<seed>/)
# =============================================================================

class TestOutputStructure:
    def test_path_components(self, tmp_dir):
        runner = ExperimentRunner(
            case_id="structure_test",
            variant="experimental",
            seed=5,
            runs_root=str(tmp_dir / "runs"),
            project_root=str(tmp_dir),
        )
        expected = tmp_dir / "runs" / "structure_test" / "experimental" / "s5"
        assert runner.output_dir == expected

    def test_dry_run_creates_all_artifacts(self, tmp_dir):
        # Create a seed doc for realism
        seeds = tmp_dir / "seeds"
        seeds.mkdir()
        doc = seeds / "doc.md"
        doc.write_text("Test evidence document", encoding="utf-8")

        runner = ExperimentRunner(
            case_id="all_artifacts",
            variant="baseline",
            seed=1,
            seed_documents=[{"path": str(doc), "alias": "test_doc"}],
            runs_root=str(tmp_dir / "runs"),
            project_root=str(tmp_dir),
        )
        runner.dry_run()

        out = runner.output_dir
        assert (out / CONFIG_SNAPSHOT_FILENAME).exists()
        assert (out / SEED_HASHES_FILENAME).exists()
        assert (out / PROMPT_HASHES_FILENAME).exists()
        assert (out / RESULTS_FILENAME).exists()
        assert (out / RUN_MANIFEST_FILENAME).exists()


# =============================================================================
# Test: Baseline vs experimental comparison setup
# =============================================================================

class TestBaselineVsExperimental:
    def test_compare_two_variants_same_case(self, tmp_dir):
        """Verify two runners with same case_id but different variants
        produce outputs in the correct directory structure for comparison."""
        for variant in ["baseline", "experimental"]:
            mode = "experimental" if variant == "experimental" else "baseline"
            runner = ExperimentRunner(
                case_id="compare_test",
                variant=variant,
                seed=1,
                memory_mode=mode,
                runs_root=str(tmp_dir / "runs"),
                project_root=str(tmp_dir),
            )
            runner.dry_run()

        # Both variants should exist under compare_test
        case_dir = tmp_dir / "runs" / "compare_test"
        assert (case_dir / "baseline" / "s1").exists()
        assert (case_dir / "experimental" / "s1").exists()