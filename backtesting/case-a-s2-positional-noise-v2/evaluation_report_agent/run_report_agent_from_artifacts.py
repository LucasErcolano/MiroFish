"""Run ReportAgent from Issue 19 V2 artifacts without shared graph/tool state.

This script does not rerun simulations and does not read from graph memory. It
turns committed condition summaries, metrics, and narrative scores into one
condition-specific artifact context, then invokes ReportAgent in artifact-only
mode with unique report IDs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONDITIONS = [
    "v2-baseline-control",
    "v2-signal-strong-mid",
    "v2-signal-weak-mid",
    "v2-counter-colombia-mid",
    "v2-noise-near-mid",
    "v2-noise-off-mid",
]


@dataclass(frozen=True)
class ModelSpec:
    slug: str
    provider: str
    model: str
    base_url: str
    key_env: str
    summary_dir: Path
    metrics_csv: Path
    scores_csv: Path


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[3]


def ensure_backend_imports(repo_root: Path) -> None:
    backend_dir = repo_root / "backend"
    for path in (str(repo_root), str(backend_dir)):
        if path not in sys.path:
            sys.path.insert(0, path)


def read_csv_by_condition(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return {row["condition"]: dict(row) for row in rows}


def safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-").lower()


def get_env_secret(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value or None
    except OSError:
        return None


def model_specs(repo_root: Path) -> dict[str, ModelSpec]:
    base = repo_root / "backtesting" / "case-a-s2-positional-noise-v2"
    qwen_eval = base / "evaluation"
    deepinfra_eval = base / "evaluation_deepinfra"
    return {
        "qwen": ModelSpec(
            slug="qwen",
            provider="openrouter",
            model="qwen/qwen3-8b",
            base_url="https://openrouter.ai/api/v1",
            key_env="OPENROUTER_API_KEY",
            summary_dir=qwen_eval / "condition_summaries",
            metrics_csv=qwen_eval / "condition_summary_metrics.csv",
            scores_csv=qwen_eval / "narrative_scores.csv",
        ),
        "gemma": ModelSpec(
            slug="gemma",
            provider="deepinfra",
            model="google/gemma-3-27b-it",
            base_url="https://api.deepinfra.com/v1/openai",
            key_env="DEEPINFRA_API_KEY",
            summary_dir=deepinfra_eval / "gemma" / "condition_summaries",
            metrics_csv=deepinfra_eval / "gemma" / "condition_summary_metrics.csv",
            scores_csv=deepinfra_eval / "gemma" / "narrative_scores.csv",
        ),
        "llama": ModelSpec(
            slug="llama",
            provider="deepinfra",
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
            base_url="https://api.deepinfra.com/v1/openai",
            key_env="DEEPINFRA_API_KEY",
            summary_dir=deepinfra_eval / "llama" / "condition_summaries",
            metrics_csv=deepinfra_eval / "llama" / "condition_summary_metrics.csv",
            scores_csv=deepinfra_eval / "llama" / "narrative_scores.csv",
        ),
    }


def configure_model_env(spec: ModelSpec, max_tokens: int) -> None:
    key = get_env_secret(spec.key_env)
    if not key:
        raise RuntimeError(f"{spec.key_env} is not available in this process")
    os.environ["LLM_API_KEY"] = key
    os.environ["OPENAI_API_KEY"] = key
    os.environ["LLM_BASE_URL"] = spec.base_url
    os.environ["LLM_MODEL_NAME"] = spec.model
    os.environ["LLM_MAX_TOKENS"] = str(max_tokens)
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    from app.config import Config

    Config.LLM_API_KEY = key
    Config.LLM_BASE_URL = spec.base_url
    Config.LLM_MODEL_NAME = spec.model
    Config.LLM_MAX_TOKENS = max_tokens


def build_artifact_context(
    spec: ModelSpec,
    condition: str,
    summary: str,
    metrics: dict[str, str],
    score: dict[str, str],
) -> str:
    return "\n".join(
        [
            "# Issue 19 V2 Condition Artifact",
            "",
            f"- provider: {spec.provider}",
            f"- model_slug: {spec.slug}",
            f"- model: {spec.model}",
            f"- condition: {condition}",
            "",
            "## Technical Metrics",
            "```json",
            json.dumps(metrics, ensure_ascii=False, indent=2),
            "```",
            "",
            "## Narrative Score",
            "```json",
            json.dumps(score, ensure_ascii=False, indent=2),
            "```",
            "",
            "## Condition Summary",
            summary.strip(),
            "",
        ]
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_report_outputs(report_folder: Path, output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    keep = {"full_report.md", "meta.json", "outline.json"}
    copied: list[str] = []
    for path in sorted(report_folder.iterdir()):
        if path.is_file() and path.name in keep:
            shutil.copy2(path, output_dir / path.name)
            copied.append(path.name)
    return copied


def run_one(
    spec: ModelSpec,
    condition: str,
    output_root: Path,
    max_tokens: int,
    force: bool,
) -> dict[str, Any]:
    configure_model_env(spec, max_tokens=max_tokens)

    from app.config import Config
    from app.services.report_agent import ReportAgent, ReportManager, ReportStatus
    from app.utils.locale import set_locale

    set_locale("en")

    output_dir = output_root / spec.slug / condition
    report_id = f"issue19-ra-{safe_slug(spec.slug)}-{safe_slug(condition)}"
    if output_dir.exists() and not force:
        existing_status = "skipped_existing"
        existing_error = ""
        run_json = output_dir / "report_agent_run.json"
        if run_json.exists():
            try:
                run_data = json.loads(run_json.read_text(encoding="utf-8"))
                existing_status = str(run_data.get("status") or existing_status)
                existing_error = str(run_data.get("error") or "")
            except json.JSONDecodeError:
                existing_error = f"Could not parse {run_json}"
        return {
            "provider": spec.provider,
            "model_slug": spec.slug,
            "model": spec.model,
            "condition": condition,
            "report_id": report_id,
            "status": existing_status,
            "error": existing_error,
            "output_dir": str(output_dir),
            "duration_seconds": "0.00",
        }

    metrics = read_csv_by_condition(spec.metrics_csv)
    scores = read_csv_by_condition(spec.scores_csv)
    summary_path = spec.summary_dir / f"{condition}.md"
    if condition not in metrics:
        raise FileNotFoundError(f"Missing metrics row for {condition} in {spec.metrics_csv}")
    if condition not in scores:
        raise FileNotFoundError(f"Missing score row for {condition} in {spec.scores_csv}")
    if not summary_path.exists():
        raise FileNotFoundError(summary_path)

    summary = summary_path.read_text(encoding="utf-8")
    context = build_artifact_context(spec, condition, summary, metrics[condition], scores[condition])
    context_hash = hashlib.sha256(context.encode("utf-8")).hexdigest()

    if output_dir.exists():
        shutil.rmtree(output_dir)

    start = time.time()
    agent = ReportAgent(
        graph_id=f"artifact:{spec.slug}:{condition}",
        simulation_id=f"artifact-{spec.slug}-{condition}",
        simulation_requirement=(
            "S2 Issue 19 V2 Copa America 2024 final prediction benchmark: "
            "Argentina vs Colombia with scheduled condition-specific injection."
        ),
        artifact_context=context,
        artifact_only=True,
    )
    report = agent.generate_report(report_id=report_id)
    duration = time.time() - start

    report_folder = Path(ReportManager._get_report_folder(report_id))
    copied = copy_report_outputs(report_folder, output_dir)
    write_text(
        output_dir / "report_agent_run.json",
        json.dumps(
            {
                "provider": spec.provider,
                "model_slug": spec.slug,
                "model": spec.model,
                "condition": condition,
                "report_id": report_id,
                "status": report.status.value if isinstance(report.status, ReportStatus) else str(report.status),
                "error": report.error or "",
                "source_report_folder": str(report_folder),
                "copied_files": copied,
                "upload_folder": Config.UPLOAD_FOLDER,
                "artifact_only": True,
                "artifact_context_sha256": context_hash,
                "source_summary": str(summary_path),
                "source_metrics_csv": str(spec.metrics_csv),
                "source_scores_csv": str(spec.scores_csv),
            },
            ensure_ascii=False,
            indent=2,
        ),
    )

    return {
        "provider": spec.provider,
        "model_slug": spec.slug,
        "model": spec.model,
        "condition": condition,
        "report_id": report_id,
        "status": report.status.value if isinstance(report.status, ReportStatus) else str(report.status),
        "error": report.error or "",
        "output_dir": str(output_dir),
        "duration_seconds": f"{duration:.2f}",
    }


def write_manifest(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "provider",
        "model_slug",
        "model",
        "condition",
        "report_id",
        "status",
        "error",
        "output_dir",
        "duration_seconds",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default="qwen,gemma,llama")
    parser.add_argument("--conditions", default=",".join(CONDITIONS))
    parser.add_argument("--output-root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parent / "report_agent_manifest.csv")
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = repo_root_from_script()
    ensure_backend_imports(repo_root)

    specs = model_specs(repo_root)
    selected_models = [part.strip() for part in args.models.split(",") if part.strip()]
    selected_conditions = [part.strip() for part in args.conditions.split(",") if part.strip()]

    unknown_models = [model for model in selected_models if model not in specs]
    if unknown_models:
        raise ValueError(f"Unknown models: {unknown_models}. Valid models: {sorted(specs)}")
    unknown_conditions = [condition for condition in selected_conditions if condition not in CONDITIONS]
    if unknown_conditions:
        raise ValueError(f"Unknown conditions: {unknown_conditions}. Valid conditions: {CONDITIONS}")

    rows: list[dict[str, Any]] = []
    for model_slug in selected_models:
        spec = specs[model_slug]
        for condition in selected_conditions:
            print(f"Running ReportAgent artifact-only: {model_slug} / {condition}")
            try:
                row = run_one(
                    spec=spec,
                    condition=condition,
                    output_root=args.output_root,
                    max_tokens=args.max_tokens,
                    force=args.force,
                )
            except Exception as exc:
                row = {
                    "provider": spec.provider,
                    "model_slug": spec.slug,
                    "model": spec.model,
                    "condition": condition,
                    "report_id": f"issue19-ra-{safe_slug(spec.slug)}-{safe_slug(condition)}",
                    "status": "failed",
                    "error": str(exc),
                    "output_dir": str(args.output_root / spec.slug / condition),
                    "duration_seconds": "0.00",
                }
                print(f"FAILED {model_slug} / {condition}: {exc}")
            rows.append(row)
            write_manifest(rows, args.manifest)

    write_manifest(rows, args.manifest)
    print(f"Wrote manifest: {args.manifest}")
    return 0 if all(row["status"] in {"completed", "skipped_existing"} for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
