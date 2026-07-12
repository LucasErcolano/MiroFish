#!/usr/bin/env python3
"""Run final temporal-optimum cross-model validation rows."""

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
MATRIX_PATH = FINAL_ROOT / "temporal_optimum_matrix.yaml"
S3_MATRIX_PATH = REPO_ROOT / "backtesting" / "s3-cross-topic-injection" / "matrix.yaml"
EVAL_ROOT = FINAL_ROOT / "evaluation"
RAW_OUTPUT_ROOT = "runs/final_multimodel/raw_temporal"

sys.path.insert(0, str(REPO_ROOT / "backtesting" / "s3-cross-topic-injection" / "scripts"))
from run_s3_matrix import (  # noqa: E402
    backend_reachable,
    build_env,
    start_backend,
    stop_backend_process_tree,
    wait_backend,
)

sys.path.insert(0, str(REPO_ROOT / "backtesting" / "scripts"))
from run_line5_llama_matrix import (  # noqa: E402
    build_run_notes as build_case_run_notes,
    evaluate as evaluate_case_output,
    run_variant as run_case_variant,
)


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def csv_filter(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {item.strip() for item in value.split(",") if item.strip()}


def selected_rows(matrix: dict[str, Any], topics: set[str] | None, models: set[str] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for topic_key, topic in matrix["topics"].items():
        if topics and topic_key not in topics:
            continue
        for model_key in matrix["models"]:
            if models and model_key not in models:
                continue
            package = topic["selected_package"]
            rows.append(
                {
                    "topic": topic_key,
                    "model_key": model_key,
                    "variant_id": f"{model_key}_{topic_key}_{package}_R{matrix['rounds']}_D{matrix['density']}",
                    "topic_spec": topic,
                    "rounds": int(matrix["rounds"]),
                    "density": int(matrix["density"]),
                }
            )
    return rows


def build_case_config(row: dict[str, Any], model_spec: dict[str, Any]) -> dict[str, Any]:
    topic = row["topic_spec"]
    model_key = row["model_key"]
    topic_key = row["topic"]
    package = topic["selected_package"]
    return {
        "experiment_metadata": {
            "phase": "final",
            "issue_source": topic["issue_source"],
            "source_pr": topic.get("source_pr"),
            "case_id": topic["case_id"],
            "source_case": topic["source_case"],
            "line_focus": topic["line_focus"],
            "question_file": topic["question_file"],
            "system_constraints_file": topic.get("system_constraints_file"),
            "primary_metric": "case objective evaluator",
            "output_dir": f"../../{RAW_OUTPUT_ROOT}/{topic_key}/{model_key}",
            "eval_script": topic["eval_script"],
            "eval_artifact": topic["eval_artifact"],
        },
        "model_policy": {
            "label": model_key,
            "provider_id": model_spec["model"],
            "model_policy": f"{model_key}_temporal_optimum_final",
            "required_backend_base_url": model_spec["base_url"],
            "note": "Backend is started by run_final_temporal_optimum.py for this model.",
        },
        "fixed_simulation_config": {
            "seed": topic["seed"],
            "temperature": 0,
            "output_mode": topic["output_mode"],
            "schema_id": topic.get("schema_id"),
            "platform": "parallel",
            "use_llm_for_profiles": True,
            "parallel_profile_count": 5,
            "enable_graph_memory_update": False,
        },
        "line5_package": {
            "id": package,
            "label": f"{topic_key} selected temporal optimum package",
            "max_document_date": topic["max_document_date"],
            "input_file": topic["input_file"],
            "reuse_graph_project": False,
            "reuse_existing_graph_from_run_notes": topic.get("reuse_existing_graph_from_run_notes"),
            "sources": topic.get("sources", []),
        },
        "run_matrix": [
            {
                "id": row["variant_id"],
                "package": package,
                "input_file": topic["input_file"],
                "rounds": row["rounds"],
                "density": row["density"],
                "label": "Temporal optimum",
            }
        ],
        "do_not_upload": [
            "ground_truth_private.md",
            "eval_objective.py",
            "README.md",
            "RESULTS.md",
            "ISSUE_RESPONSE.md",
            "rubric.md",
            "manifest.csv",
            "testing_protocol.md",
            "internal_notes.md",
            "output/",
            "output_llama_line5/",
            "output_llama_line5_slim/",
        ],
    }


def raw_output_dir(row: dict[str, Any]) -> Path:
    return (
        REPO_ROOT
        / RAW_OUTPUT_ROOT
        / row["topic"]
        / row["model_key"]
        / row["variant_id"]
    )


def committable_dir(row: dict[str, Any]) -> Path:
    return EVAL_ROOT / "temporal_optimum" / row["topic"] / row["model_key"]


def copy_committable_artifacts(row: dict[str, Any], output_dir: Path) -> None:
    dst = committable_dir(row)
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for name in ["report.md", "structured_answer.json", "eval_result.json", "run_notes.md"]:
        src = output_dir / name
        if src.exists():
            shutil.copy2(src, dst / name)


def output_completed(output_dir: Path) -> bool:
    eval_path = output_dir / "eval_result.json"
    run_state_path = output_dir / "run_state.json"
    if not eval_path.exists() or not run_state_path.exists():
        return False
    try:
        run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return (
        str(run_state.get("runner_status", "")).lower() == "completed"
        and run_state.get("current_round") == run_state.get("total_rounds")
    )


def output_run_finished(output_dir: Path) -> bool:
    run_state_path = output_dir / "run_state.json"
    report_path = output_dir / "report.md"
    if not run_state_path.exists() or not report_path.exists():
        return False
    try:
        run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return (
        str(run_state.get("runner_status", "")).lower() == "completed"
        and run_state.get("current_round") == run_state.get("total_rounds")
    )


def finalize_existing_output(row: dict[str, Any], model_spec: dict[str, Any], output_dir: Path) -> None:
    config = build_case_config(row, model_spec)
    case_dir = REPO_ROOT / row["topic_spec"]["case_dir"]
    eval_result = evaluate_case_output(case_dir, config, output_dir, row["variant_id"])
    write_json(output_dir / "eval_result.json", eval_result)

    simulation_config = (
        json.loads((output_dir / "simulation_config.json").read_text(encoding="utf-8"))
        if (output_dir / "simulation_config.json").exists()
        else {}
    )
    run_state = (
        json.loads((output_dir / "run_state.json").read_text(encoding="utf-8"))
        if (output_dir / "run_state.json").exists()
        else {}
    )
    report_meta = (
        json.loads((output_dir / "report_meta.json").read_text(encoding="utf-8"))
        if (output_dir / "report_meta.json").exists()
        else {}
    )
    package = config["line5_package"]
    run_entry = config["run_matrix"][0]
    run_notes = build_case_run_notes(
        config=config,
        variant_id=row["variant_id"],
        package=package,
        run_entry=run_entry,
        project_id=simulation_config.get("project_id", ""),
        graph_id=simulation_config.get("graph_id") or report_meta.get("graph_id", ""),
        simulation_id=simulation_config.get("simulation_id") or report_meta.get("simulation_id", ""),
        report_id=report_meta.get("report_id", ""),
        run_state=run_state,
        report_data=report_meta,
        simulation_config=simulation_config,
        eval_result=eval_result,
    )
    (output_dir / "run_notes.md").write_text(run_notes, encoding="utf-8")


def summarize_eval(row: dict[str, Any], output_dir: Path, status: str, error: str | None = None) -> dict[str, Any]:
    eval_path = output_dir / "eval_result.json"
    run_state_path = output_dir / "run_state.json"
    simulation_config_path = output_dir / "simulation_config.json"
    eval_result = json.loads(eval_path.read_text(encoding="utf-8")) if eval_path.exists() else {}
    run_state = json.loads(run_state_path.read_text(encoding="utf-8")) if run_state_path.exists() else {}
    simulation_config = (
        json.loads(simulation_config_path.read_text(encoding="utf-8"))
        if simulation_config_path.exists()
        else {}
    )
    summary = {
        "topic": row["topic"],
        "model_key": row["model_key"],
        "variant_id": row["variant_id"],
        "package": row["topic_spec"]["selected_package"],
        "status": status,
        "score": eval_result.get("score"),
        "max_score": eval_result.get("max_score"),
        "parse_errors": eval_result.get("parse_errors"),
        "runner_status": run_state.get("runner_status"),
        "current_round": run_state.get("current_round"),
        "total_rounds": run_state.get("total_rounds"),
        "backend_llm_model": simulation_config.get("llm_model"),
        "output_dir": str(output_dir.relative_to(REPO_ROOT)) if output_dir.exists() else "",
        "committable_dir": str(committable_dir(row).relative_to(REPO_ROOT)),
        "error": error.encode("ascii", "backslashreplace").decode("ascii") if error else "",
    }
    if row["topic"] == "bolivia":
        summary.update(
            {
                "prediction": eval_result.get("prediction"),
                "winner_score": eval_result.get("winner_score"),
                "mae_vote_share": eval_result.get("mae_vote_share"),
                "margin_abs_error": eval_result.get("margin_abs_error"),
            }
        )
    elif row["topic"] == "copa":
        summary.update(
            {
                "predicted_winner": eval_result.get("predicted_winner"),
                "confidence": eval_result.get("confidence"),
                "winner_probability_point": eval_result.get("winner_probability_point"),
            }
        )
    elif row["topic"] == "ipc":
        delta_1 = eval_result.get("delta_1", {}) or {}
        delta_4 = eval_result.get("delta_4", {}) or {}
        summary.update(
            {
                "delta_1_prediction": delta_1.get("prediction"),
                "delta_1_abs_error": delta_1.get("abs_error"),
                "delta_4_prediction": delta_4.get("prediction"),
                "delta_4_abs_error": delta_4.get("abs_error"),
            }
        )
    return summary


def merge_existing_summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    json_path = EVAL_ROOT / "temporal_optimum_summary.json"
    merged: dict[str, dict[str, Any]] = {}
    if json_path.exists():
        try:
            existing = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []
        for row in existing:
            if isinstance(row, dict) and row.get("variant_id"):
                merged[row["variant_id"]] = row
    for row in rows:
        merged[row["variant_id"]] = row
    return sorted(merged.values(), key=lambda item: (item.get("topic", ""), item.get("model_key", "")))


def write_summary(rows: list[dict[str, Any]]) -> None:
    EVAL_ROOT.mkdir(parents=True, exist_ok=True)
    json_path = EVAL_ROOT / "temporal_optimum_summary.json"
    csv_path = EVAL_ROOT / "temporal_optimum_summary.csv"
    md_path = EVAL_ROOT / "temporal_optimum_summary.md"
    write_json(json_path, rows)
    fieldnames = sorted({key for row in rows for key in row})
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    valid = sum(1 for row in rows if row["status"] == "completed")
    lines = [
        "# Temporal Optimum Cross-Model Summary",
        "",
        f"Rows completed: {valid}/{len(rows)}",
        "",
        "| topic | model | package | status | score | parse errors | rounds | key result |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        score = "" if row.get("score") is None else f"{row.get('score')}/{row.get('max_score')}"
        rounds = f"{row.get('current_round')}/{row.get('total_rounds')}"
        if row["topic"] == "bolivia":
            key = f"{row.get('prediction')} mae={row.get('mae_vote_share')}"
        elif row["topic"] == "copa":
            key = f"{row.get('predicted_winner')} p={row.get('winner_probability_point')}"
        elif row["topic"] == "ipc":
            key = f"d1={row.get('delta_1_prediction')} err={row.get('delta_1_abs_error')}"
        else:
            key = row.get("error", "")
        lines.append(
            f"| {row['topic']} | {row['model_key']} | {row['package']} | {row['status']} | "
            f"{score} | {row.get('parse_errors')} | {rounds} | {key} |"
        )
    lines.extend(
        [
            "",
            "Notes:",
            "",
            "- Raw simulation artifacts are local under `runs/final_multimodel/raw_temporal/`.",
            "- Committed evidence keeps only report, structured answer when present, eval result, and run notes.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_rows(rows: list[dict[str, Any]], model_specs: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for model_key in dict.fromkeys(row["model_key"] for row in rows):
        model_rows = [row for row in rows if row["model_key"] == model_key]
        runnable_rows: list[dict[str, Any]] = []
        for row in model_rows:
            output_dir = raw_output_dir(row)
            if not args.force and output_completed(output_dir):
                copy_committable_artifacts(row, output_dir)
                summaries.append(summarize_eval(row, output_dir, "completed"))
                print(f"skipped completed: {row['variant_id']}")
            elif not args.force and output_run_finished(output_dir):
                try:
                    finalize_existing_output(row, model_specs[row["model_key"]], output_dir)
                    copy_committable_artifacts(row, output_dir)
                    summaries.append(summarize_eval(row, output_dir, "completed"))
                    print(f"finalized existing: {row['variant_id']}")
                except Exception as exc:  # noqa: BLE001 - rerun if finalization cannot recover
                    runnable_rows.append(row)
                    safe_error = str(exc).encode("ascii", "backslashreplace").decode("ascii")
                    print(f"could not finalize existing {row['variant_id']}: {safe_error}")
            else:
                runnable_rows.append(row)
        if not runnable_rows:
            continue
        process = None
        if args.start_backend:
            if backend_reachable(args.base_url):
                raise RuntimeError(f"backend already reachable at {args.base_url}; stop it before --start-backend")
            process = start_backend(build_env(model_specs[model_key]), f"final-temporal-{model_key}")
            wait_backend(args.base_url, args.backend_timeout)
        try:
            project_cache: dict[str, dict[str, Any]] = {}
            for row in runnable_rows:
                case_dir = REPO_ROOT / row["topic_spec"]["case_dir"]
                config = build_case_config(row, model_specs[model_key])
                try:
                    output_dir = run_case_variant(args.base_url, case_dir, config, row["variant_id"], args.force, project_cache)
                    copy_committable_artifacts(row, output_dir)
                    summaries.append(summarize_eval(row, output_dir, "completed"))
                    print(f"completed: {row['variant_id']}")
                except Exception as exc:  # noqa: BLE001 - preserve partial rows
                    output_dir = raw_output_dir(row)
                    summaries.append(summarize_eval(row, output_dir, "failed", str(exc)))
                    safe_error = str(exc).encode("ascii", "backslashreplace").decode("ascii")
                    print(f"failed: {row['variant_id']}: {safe_error}")
        finally:
            if process is not None:
                stop_backend_process_tree(process)
    return summaries


def main() -> int:
    parser = argparse.ArgumentParser(description="Run final temporal optimum rows for Llama and Qwen.")
    parser.add_argument("--models", default=None, help="Comma-separated model keys.")
    parser.add_argument("--topics", default=None, help="Comma-separated topic keys.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5001")
    parser.add_argument("--start-backend", action="store_true")
    parser.add_argument("--backend-timeout", type=int, default=180)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    matrix = load_yaml(MATRIX_PATH)
    s3_matrix = load_yaml(S3_MATRIX_PATH)
    rows = selected_rows(matrix, csv_filter(args.topics), csv_filter(args.models))
    if args.dry_run:
        print(json.dumps([{k: v for k, v in row.items() if k != "topic_spec"} for row in rows], indent=2))
        return 0
    summaries = merge_existing_summaries(run_rows(rows, s3_matrix["models"], args))
    write_summary(summaries)
    completed = sum(1 for row in summaries if row["status"] == "completed")
    print(f"temporal optimum summary written: completed={completed}/{len(summaries)}")
    return 0 if completed == len(summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
