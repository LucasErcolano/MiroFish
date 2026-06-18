from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
S3_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(S3_ROOT / "scripts"))
from run_s3_matrix import (  # noqa: E402
    actual_events,
    expected_events,
    has_real_run_evidence,
    read_manifest,
    read_prepared_manifest,
    reddit_db_counts,
)


def load_matrix() -> dict:
    with (S3_ROOT / "matrix.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def smoke_rows(matrix: dict) -> list[dict]:
    rows: list[dict] = []
    for topic_key, topic in matrix["topics"].items():
        for model_key, model in matrix["models"].items():
            for condition in matrix["smoke_conditions"]:
                rows.append(
                    {
                        "topic": topic_key,
                        "topic_spec": topic,
                        "model_key": model_key,
                        "model_spec": model,
                        "condition": condition,
                        "rounds": int(matrix["rounds"]),
                        "run_id": f"{topic_key}-{model_key}-{condition}-r{matrix['rounds']}",
                        "output_dir": REPO_ROOT
                        / "runs"
                        / "s3_cross_topic"
                        / topic_key
                        / model_key
                        / f"{condition}-r{matrix['rounds']}",
                    }
                )
    return rows


def summarize_row(matrix: dict, row: dict) -> dict:
    expected = expected_events(matrix, row["condition"])
    actual = actual_events(row["output_dir"], expected)
    real_ok, evidence_note = has_real_run_evidence(row["output_dir"], row["rounds"])
    manifest = read_manifest(row["output_dir"])
    prepared = read_prepared_manifest(row)
    db_summary = manifest.get("reddit_db_summary") or {}
    if not db_summary:
        raw_counts = reddit_db_counts(row["output_dir"])
        db_summary = {
            "post_count": raw_counts.get("post"),
            "comment_count": raw_counts.get("comment"),
            "trace_count": raw_counts.get("trace"),
            "user_count": raw_counts.get("user"),
        }
    valid = bool(real_ok and actual == expected and manifest.get("status") == "completed")
    return {
        "run_id": row["run_id"],
        "topic": row["topic"],
        "model_key": row["model_key"],
        "model": row["model_spec"]["model"],
        "condition": row["condition"],
        "valid": valid,
        "event_expected": expected,
        "event_actual": actual,
        "manifest_status": manifest.get("status"),
        "is_real_mirofish_system": manifest.get("is_real_mirofish_system"),
        "flow_provenance": manifest.get("flow_provenance"),
        "simulation_id": manifest.get("simulation_id"),
        "prepared_simulation_id": prepared.get("simulation_id"),
        "post_count": db_summary.get("post_count"),
        "comment_count": db_summary.get("comment_count"),
        "trace_count": db_summary.get("trace_count"),
        "user_count": db_summary.get("user_count"),
        "evidence_note": evidence_note,
        "output_dir": str(row["output_dir"].relative_to(REPO_ROOT)),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict]) -> None:
    valid_count = sum(1 for row in rows if row["valid"])
    total = len(rows)
    lines = [
        "# S3 Smoke Summary",
        "",
        f"Rows valid: {valid_count}/{total}",
        "",
        "Scope: 3 topics x 2 models x 2 conditions (`baseline-control`, `signal-mid`).",
        "",
        "Technical validity requires a completed manifest, real MiroFish/OASIS evidence, and scheduled event count matching the condition.",
        "",
        "| topic | model | condition | valid | events | posts | comments | traces | sim |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {topic} | {model_key} | {condition} | {valid} | {event_actual}/{event_expected} | "
            "{post_count} | {comment_count} | {trace_count} | {simulation_id} |".format(**row)
        )
    lines.extend(
        [
            "",
            "Notes:",
            "",
            "- `runs/` remains local and is not intended to be committed.",
            "- Backend round counters can remain zero for DeepInfra/OASIS runs; the audit uses manifest status, DB counts, and `scheduled_events_fired.jsonl`.",
            "- Llama rows use Llama for the simulation LLM and Gemma for Graphiti extraction, as declared in `matrix.yaml`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    matrix = load_matrix()
    rows = [summarize_row(matrix, row) for row in smoke_rows(matrix)]
    out_dir = S3_ROOT / "evaluation"
    write_csv(out_dir / "smoke_summary.csv", rows)
    (out_dir / "smoke_summary.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    write_markdown(out_dir / "smoke_summary.md", rows)
    valid_count = sum(1 for row in rows if row["valid"])
    print(f"S3 smoke summary written: valid={valid_count}/{len(rows)}")
    return 0 if valid_count == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
