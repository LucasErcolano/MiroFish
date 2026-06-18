from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
S3_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(S3_ROOT / "scripts"))
from run_s3_matrix import actual_events, expected_events, has_real_run_evidence, read_manifest  # noqa: E402


TOPIC_KEYWORDS = {
    "football": {
        "axis_a": "Argentina",
        "axis_b": "Colombia",
        "a_terms": [r"\bargentina\b", r"\balbiceleste\b", r"\bmessi\b"],
        "b_terms": [r"\bcolombia\b", r"\bcolombian\b", r"\bjames\b", r"\brodriguez\b"],
        "noise_terms": [r"ticket", r"celebrity", r"streaming", r"transfer", r"stadium food", r"watch part"],
    },
    "bolivia": {
        "axis_a": "Paz",
        "axis_b": "Quiroga",
        "a_terms": [r"\bpaz\b", r"\brodrigo paz\b"],
        "b_terms": [r"\bquiroga\b", r"\bjorge quiroga\b"],
        "noise_terms": [r"\bfootball\b", r"\bfutbol\b", r"\bus relations\b", r"\bdiplomatic\b"],
    },
    "ipc": {
        "axis_a": "Lower/disinflation",
        "axis_b": "Higher/rebound",
        "a_terms": [r"disinflation", r"desinflaci", r"lower inflation", r"fiscal discipline", r"crawling"],
        "b_terms": [r"rebound", r"pass-through", r"dollar shock", r"dolar", r"dólar", r"4-5%", r"higher inflation"],
        "noise_terms": [r"sports", r"concert", r"streaming", r"travel", r"social posts"],
    },
}


def load_matrix() -> dict:
    with (S3_ROOT / "matrix.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def full_rows(matrix: dict) -> list[dict]:
    rows: list[dict] = []
    for topic_key, topic in matrix["topics"].items():
        for model_key, model in matrix["models"].items():
            for condition in [item["id"] for item in matrix["conditions"]]:
                rows.append(
                    {
                        "run_id": f"{topic_key}-{model_key}-{condition}-r{matrix['rounds']}",
                        "topic": topic_key,
                        "model_key": model_key,
                        "model": model["model"],
                        "condition": condition,
                        "rounds": int(matrix["rounds"]),
                        "output_dir": REPO_ROOT
                        / "runs"
                        / "s3_cross_topic"
                        / topic_key
                        / model_key
                        / f"{condition}-r{matrix['rounds']}",
                    }
                )
    return rows


def read_db_texts(output_dir: Path) -> tuple[list[str], dict[str, int]]:
    db_path = output_dir / "simulation_artifacts" / "reddit_simulation.db"
    counts = {"posts": 0, "comments": 0, "traces": 0, "users": 0}
    texts: list[str] = []
    if not db_path.exists():
        return texts, counts
    with sqlite3.connect(db_path) as connection:
        for table, key in [("post", "posts"), ("comment", "comments"), ("trace", "traces"), ("user", "users")]:
            try:
                counts[key] = int(connection.execute(f"select count(*) from {table}").fetchone()[0])
            except sqlite3.DatabaseError:
                counts[key] = 0
        for table in ["post", "comment"]:
            try:
                for (content,) in connection.execute(f"select content from {table} where content is not null"):
                    texts.append(str(content))
            except sqlite3.DatabaseError:
                pass
    return texts, counts


def count_terms(text: str, patterns: list[str]) -> int:
    total = 0
    for pattern in patterns:
        total += len(re.findall(pattern, text, flags=re.IGNORECASE))
    return total


def classify(topic: str, a_count: int, b_count: int) -> str:
    spec = TOPIC_KEYWORDS[topic]
    if a_count > b_count:
        return spec["axis_a"]
    if b_count > a_count:
        return spec["axis_b"]
    return "Unclear"


def summarize_row(matrix: dict, row: dict) -> dict:
    expected = expected_events(matrix, row["condition"])
    actual = actual_events(row["output_dir"], expected)
    real_ok, evidence_note = has_real_run_evidence(row["output_dir"], row["rounds"])
    manifest = read_manifest(row["output_dir"])
    texts, db_counts = read_db_texts(row["output_dir"])
    joined = "\n\n".join(texts)
    spec = TOPIC_KEYWORDS[row["topic"]]
    a_count = count_terms(joined, spec["a_terms"])
    b_count = count_terms(joined, spec["b_terms"])
    noise_count = count_terms(joined, spec["noise_terms"])
    valid = bool(real_ok and actual == expected and manifest.get("status") == "completed")
    return {
        "run_id": row["run_id"],
        "topic": row["topic"],
        "model_key": row["model_key"],
        "model": row["model"],
        "condition": row["condition"],
        "valid": valid,
        "event_expected": expected,
        "event_actual": actual,
        "posts": db_counts["posts"],
        "comments": db_counts["comments"],
        "traces": db_counts["traces"],
        "users": db_counts["users"],
        "axis_a": spec["axis_a"],
        "axis_a_mentions": a_count,
        "axis_b": spec["axis_b"],
        "axis_b_mentions": b_count,
        "heuristic_prediction": classify(row["topic"], a_count, b_count),
        "noise_mentions": noise_count,
        "simulation_id": manifest.get("simulation_id"),
        "evidence_note": evidence_note,
    }


def write_outputs(rows: list[dict]) -> None:
    out_dir = S3_ROOT / "evaluation"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "condition_summary_metrics.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "condition_summary_metrics.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    lines = [
        "# S3 Condition Summary Metrics",
        "",
        "These deterministic metrics are extracted from local Reddit SQLite artifacts. They are not a ReportAgent/narrative judgment.",
        "",
        "| topic | model | condition | valid | events | axis A | A mentions | axis B | B mentions | heuristic | noise | posts | comments | traces |",
        "|---|---|---|---:|---:|---|---:|---|---:|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {topic} | {model_key} | {condition} | {valid} | {event_actual}/{event_expected} | "
            "{axis_a} | {axis_a_mentions} | {axis_b} | {axis_b_mentions} | {heuristic_prediction} | "
            "{noise_mentions} | {posts} | {comments} | {traces} |".format(**row)
        )
    lines.extend(
        [
            "",
            "Caveat: the heuristic counts injected documents themselves when they are posted. Use it to audit directional pressure and contamination, not as a final semantic evaluator.",
        ]
    )
    (out_dir / "condition_summary_metrics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    matrix = load_matrix()
    rows = [summarize_row(matrix, row) for row in full_rows(matrix)]
    write_outputs(rows)
    valid_count = sum(1 for row in rows if row["valid"])
    print(f"S3 condition metrics written: valid={valid_count}/{len(rows)}")
    return 0 if valid_count == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
