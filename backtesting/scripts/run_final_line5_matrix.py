#!/usr/bin/env python3
"""Run the final Bolivia Line 5 Gemma/Qwen slim variants."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
FINAL_ROOT = REPO_ROOT / "backtesting" / "final-multimodel"
EVAL_ROOT = FINAL_ROOT / "evaluation"
S3_MATRIX_PATH = REPO_ROOT / "backtesting" / "s3-cross-topic-injection" / "matrix.yaml"

sys.path.insert(0, str(REPO_ROOT / "backtesting" / "s3-cross-topic-injection" / "scripts"))
from run_s3_matrix import (  # noqa: E402
    backend_reachable,
    build_env,
    start_backend,
    stop_backend_process_tree,
    wait_backend,
)

sys.path.insert(0, str(REPO_ROOT / "backtesting" / "scripts"))
from run_line5_llama_matrix import load_yaml, run_variant as run_case_variant  # noqa: E402


MODEL_CONFIGS = {
    "gemma": "config_line5_gemma_slim.yaml",
    "qwen": "config_line5_qwen_slim.yaml",
}


def csv_filter(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {item.strip() for item in value.split(",") if item.strip()}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_s3_models() -> dict[str, Any]:
    return yaml.safe_load(S3_MATRIX_PATH.read_text(encoding="utf-8"))["models"]


def output_dir(case_dir: Path, config: dict[str, Any], variant_id: str) -> Path:
    return (case_dir / config["experiment_metadata"].get("output_dir", "output_line5") / variant_id).resolve()


def output_completed(path: Path) -> bool:
    eval_path = path / "eval_result.json"
    run_state_path = path / "run_state.json"
    if not eval_path.exists() or not run_state_path.exists():
        return False
    try:
        run_state = read_json(run_state_path)
    except json.JSONDecodeError:
        return False
    return (
        str(run_state.get("runner_status", "")).lower() == "completed"
        and run_state.get("current_round") == run_state.get("total_rounds")
    )


def committable_dir(model_key: str, variant_id: str) -> Path:
    return EVAL_ROOT / "line5_bolivia" / model_key / variant_id


def copy_committable_artifacts(model_key: str, variant_id: str, raw_dir: Path) -> None:
    dst = committable_dir(model_key, variant_id)
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for name in ["report.md", "eval_result.json", "run_notes.md", "simulation_config.json"]:
        src = raw_dir / name
        if src.exists():
            shutil.copy2(src, dst / name)


def summarize_variant(
    model_key: str,
    config: dict[str, Any],
    variant_id: str,
    raw_dir: Path,
    status: str,
    error: str = "",
) -> dict[str, Any]:
    eval_result = read_json(raw_dir / "eval_result.json") if (raw_dir / "eval_result.json").exists() else {}
    run_state = read_json(raw_dir / "run_state.json") if (raw_dir / "run_state.json").exists() else {}
    run_entry = next(item for item in config["run_matrix"] if item["id"] == variant_id)
    return {
        "line": "line5_bolivia",
        "topic": "bolivia",
        "model_key": model_key,
        "variant_id": variant_id,
        "status": status,
        "rounds": run_entry["rounds"],
        "density": run_entry["density"],
        "runner_status": run_state.get("runner_status"),
        "current_round": run_state.get("current_round"),
        "total_rounds": run_state.get("total_rounds"),
        "prediction": eval_result.get("prediction"),
        "winner_score": eval_result.get("winner_score"),
        "score": eval_result.get("score"),
        "max_score": eval_result.get("max_score"),
        "mae_vote_share": eval_result.get("mae_vote_share"),
        "predicted_margin": eval_result.get("predicted_margin"),
        "margin_abs_error": eval_result.get("margin_abs_error"),
        "parse_errors": eval_result.get("parse_errors"),
        "raw_output_dir": str(raw_dir.relative_to(REPO_ROOT)) if raw_dir.exists() else "",
        "committable_dir": str(committable_dir(model_key, variant_id).relative_to(REPO_ROOT)),
        "error": error.encode("ascii", "backslashreplace").decode("ascii"),
    }


def write_summary(rows: list[dict[str, Any]]) -> None:
    EVAL_ROOT.mkdir(parents=True, exist_ok=True)
    json_path = EVAL_ROOT / "line5_bolivia_summary.json"
    csv_path = EVAL_ROOT / "line5_bolivia_summary.csv"
    md_path = EVAL_ROOT / "line5_bolivia_summary.md"
    write_json(json_path, rows)
    fieldnames = sorted({key for row in rows for key in row})
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    completed = sum(1 for row in rows if row["status"] == "completed")
    lines = [
        "# Bolivia Line 5 Final Multimodel Summary",
        "",
        f"Rows completed: {completed}/{len(rows)}",
        "",
        "| model | variant | status | rounds | density | prediction | winner | mae | margin error | parse errors |",
        "|---|---|---:|---:|---:|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['model_key']} | {row['variant_id']} | {row['status']} | {row['rounds']} | "
            f"{row['density']} | {row.get('prediction')} | {row.get('winner_score')} | "
            f"{row.get('mae_vote_share')} | {row.get('margin_abs_error')} | {row.get('parse_errors')} |"
        )
    lines.extend(
        [
            "",
            "Notes:",
            "",
            "- Uses `seed_T3_line5_slim.md`, matching the slim Llama Line 5 setup.",
            "- Raw simulation artifacts are local under `runs/final_multimodel/raw_line5/`.",
            "- Committed evidence keeps report, eval result, run notes, and generated simulation config.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_model(case_dir: Path, model_key: str, variants_filter: set[str] | None, args: argparse.Namespace) -> list[dict[str, Any]]:
    config = load_yaml(case_dir / MODEL_CONFIGS[model_key])
    variants = [item["id"] for item in config["run_matrix"] if not variants_filter or item["id"] in variants_filter]
    if args.dry_run:
        return [
            {
                "model_key": model_key,
                "variant_id": variant_id,
                "raw_output_dir": str(output_dir(case_dir, config, variant_id).relative_to(REPO_ROOT)),
            }
            for variant_id in variants
        ]

    summaries: list[dict[str, Any]] = []
    runnable: list[str] = []
    for variant_id in variants:
        raw_dir = output_dir(case_dir, config, variant_id)
        if not args.force and output_completed(raw_dir):
            copy_committable_artifacts(model_key, variant_id, raw_dir)
            summaries.append(summarize_variant(model_key, config, variant_id, raw_dir, "completed"))
            print(f"skipped completed: {variant_id}")
        else:
            runnable.append(variant_id)

    if not runnable:
        return summaries

    s3_models = load_s3_models()
    process = None
    if args.start_backend:
        if backend_reachable(args.base_url):
            raise RuntimeError(f"backend already reachable at {args.base_url}; stop it before --start-backend")
        process = start_backend(build_env(s3_models[model_key]), f"final-line5-{model_key}")
        wait_backend(args.base_url, args.backend_timeout)

    try:
        project_cache: dict[str, dict[str, Any]] = {}
        for variant_id in runnable:
            raw_dir = output_dir(case_dir, config, variant_id)
            try:
                raw_dir = run_case_variant(args.base_url, case_dir, config, variant_id, args.force, project_cache)
                copy_committable_artifacts(model_key, variant_id, raw_dir)
                summaries.append(summarize_variant(model_key, config, variant_id, raw_dir, "completed"))
                print(f"completed: {variant_id}")
            except Exception as exc:  # noqa: BLE001 - preserve partial output
                summaries.append(summarize_variant(model_key, config, variant_id, raw_dir, "failed", str(exc)))
                safe_error = str(exc).encode("ascii", "backslashreplace").decode("ascii")
                print(f"failed: {variant_id}: {safe_error}")
    finally:
        if process is not None:
            stop_backend_process_tree(process)
    return summaries


def main() -> int:
    parser = argparse.ArgumentParser(description="Run final Bolivia Line 5 Gemma/Qwen variants.")
    parser.add_argument("--case-dir", required=True)
    parser.add_argument("--models", default="gemma,qwen")
    parser.add_argument("--variants", default=None)
    parser.add_argument("--base-url", default="http://127.0.0.1:5001")
    parser.add_argument("--backend-timeout", type=int, default=180)
    parser.add_argument("--start-backend", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    case_dir = Path(args.case_dir).resolve()
    model_filter = csv_filter(args.models) or set(MODEL_CONFIGS)
    variant_filter = csv_filter(args.variants)
    unknown = model_filter - set(MODEL_CONFIGS)
    if unknown:
        raise SystemExit(f"Unsupported models: {sorted(unknown)}")

    rows: list[dict[str, Any]] = []
    for model_key in ["gemma", "qwen"]:
        if model_key not in model_filter:
            continue
        rows.extend(run_model(case_dir, model_key, variant_filter, args))

    if args.dry_run:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    rows = sorted(rows, key=lambda row: (row.get("model_key", ""), row.get("rounds", 0), row.get("variant_id", "")))
    write_summary(rows)
    completed = sum(1 for row in rows if row["status"] == "completed")
    print(f"line5 summary written: completed={completed}/{len(rows)}")
    return 0 if completed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
