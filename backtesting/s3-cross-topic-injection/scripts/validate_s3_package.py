from __future__ import annotations

import csv
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
S3_ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_yaml(path: Path) -> dict:
    if not path.exists():
        fail(f"missing file: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        fail(f"expected mapping in {path}")
    return data


def rel_path(value: str) -> Path:
    return S3_ROOT / value


def validate_ledger() -> None:
    ledger = S3_ROOT / "RUN_LEDGER.csv"
    if not ledger.exists():
        fail("RUN_LEDGER.csv is missing")
    with ledger.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
    expected = [
        "run_id",
        "topic",
        "model_key",
        "provider",
        "model",
        "condition",
        "rounds",
        "status",
        "event_expected",
        "event_actual",
        "output_dir",
        "started_at",
        "ended_at",
        "notes",
    ]
    if header != expected:
        fail(f"unexpected RUN_LEDGER.csv header: {header}")


def validate_injection_plan(topic_key: str, topic: dict, conditions: list[dict]) -> None:
    plan_path = rel_path(topic["injection_plan"])
    plan = read_yaml(plan_path)
    plan_conditions = plan.get("conditions")
    if not isinstance(plan_conditions, dict):
        fail(f"{topic_key}: injection plan missing conditions map")

    matrix_condition_ids = [condition["id"] for condition in conditions]
    if sorted(plan_conditions) != sorted(matrix_condition_ids):
        fail(f"{topic_key}: injection plan conditions do not match matrix")

    for condition in conditions:
        condition_id = condition["id"]
        expected_events = int(condition["event_expected"])
        entry = plan_conditions[condition_id]
        injections = entry.get("injections", [])
        if len(injections) != expected_events:
            fail(
                f"{topic_key}/{condition_id}: expected {expected_events} injections, "
                f"found {len(injections)}"
            )
        for injection in injections:
            event_file = plan_path.parent / injection["file"]
            if not event_file.exists():
                fail(f"{topic_key}/{condition_id}: missing event file {event_file}")
            if injection.get("target_platform") != "reddit":
                fail(f"{topic_key}/{condition_id}: expected reddit target platform")
            if injection.get("action") != "create_post":
                fail(f"{topic_key}/{condition_id}: expected create_post action")
            timing = condition["timing"]
            pct = float(injection.get("round_pct"))
            expected_pct = {"early": 0.10, "mid": 0.50, "late": 0.90}.get(timing)
            if expected_pct is not None and abs(pct - expected_pct) > 0.0001:
                fail(f"{topic_key}/{condition_id}: round_pct {pct} != {expected_pct}")


def main() -> int:
    matrix = read_yaml(S3_ROOT / "matrix.yaml")
    conditions = matrix.get("conditions", [])
    models = matrix.get("models", {})
    topics = matrix.get("topics", {})
    smoke_conditions = set(matrix.get("smoke_conditions", []))

    if len(conditions) != 7:
        fail(f"expected 7 conditions, found {len(conditions)}")
    if set(condition["id"] for condition in conditions) != {
        "baseline-control",
        "signal-early",
        "signal-mid",
        "signal-late",
        "counter-signal-mid",
        "noise-near-mid",
        "noise-off-mid",
    }:
        fail("condition IDs do not match V3 canonical set")
    if set(smoke_conditions) != {"baseline-control", "signal-mid"}:
        fail("smoke_conditions must be baseline-control and signal-mid")
    if set(models) != {"gemma", "llama"}:
        fail("models must be gemma and llama")
    if set(topics) != {"football", "bolivia", "ipc"}:
        fail("topics must be football, bolivia, and ipc")

    for topic_key, topic in topics.items():
        for field in ["base_context", "question", "ground_truth", "injection_plan"]:
            path = rel_path(topic[field])
            if not path.exists():
                fail(f"{topic_key}: missing {field} at {path}")
        validate_injection_plan(topic_key, topic, conditions)

    validate_ledger()

    smoke_rows = len(topics) * len(models) * len(smoke_conditions)
    full_rows = len(topics) * len(models) * len(conditions)
    print("S3 package validation passed")
    print(f"topics={len(topics)} models={len(models)} conditions={len(conditions)}")
    print(f"smoke_rows={smoke_rows} full_rows={full_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
