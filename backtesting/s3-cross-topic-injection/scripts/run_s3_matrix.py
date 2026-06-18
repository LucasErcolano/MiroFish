from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
S3_ROOT = Path(__file__).resolve().parents[1]
LEDGER = S3_ROOT / "RUN_LEDGER.csv"
HEADLESS = REPO_ROOT / "tools" / "mirofish_headless.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping in {path}")
    return data


def get_secret(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value if value else None
    except OSError:
        return None


def selected_csv(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {part.strip() for part in value.split(",") if part.strip()}


def iter_rows(matrix: dict, args: argparse.Namespace) -> list[dict]:
    topics_filter = selected_csv(args.topics)
    models_filter = selected_csv(args.models)
    conditions_filter = selected_csv(args.conditions)
    condition_ids = [item["id"] for item in matrix["conditions"]]
    if args.smoke:
        condition_ids = [item for item in condition_ids if item in matrix["smoke_conditions"]]
    if conditions_filter:
        condition_ids = [item for item in condition_ids if item in conditions_filter]

    rows: list[dict] = []
    for topic_key, topic in matrix["topics"].items():
        if topics_filter and topic_key not in topics_filter:
            continue
        for model_key, model in matrix["models"].items():
            if models_filter and model_key not in models_filter:
                continue
            for condition in condition_ids:
                output_dir = (
                    REPO_ROOT
                    / "runs"
                    / "s3_cross_topic"
                    / topic_key
                    / model_key
                    / f"{condition}-r{matrix['rounds']}"
                )
                rows.append(
                    {
                        "run_id": f"{topic_key}-{model_key}-{condition}-r{matrix['rounds']}",
                        "topic": topic_key,
                        "topic_spec": topic,
                        "model_key": model_key,
                        "model_spec": model,
                        "condition": condition,
                        "rounds": int(matrix["rounds"]),
                        "output_dir": output_dir,
                    }
                )
    if args.limit:
        rows = rows[: args.limit]
    return rows


def expected_events(matrix: dict, condition_id: str) -> int:
    for condition in matrix["conditions"]:
        if condition["id"] == condition_id:
            return int(condition["event_expected"])
    raise KeyError(condition_id)


def actual_events(output_dir: Path) -> int | None:
    manifest = output_dir / "run_manifest.json"
    if not manifest.exists():
        return None
    with manifest.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    value = data.get("scheduled_events_fired_count")
    return int(value) if value is not None else None


def append_ledger(row: dict, status: str, expected: int, actual: int | None, started: str, ended: str, notes: str) -> None:
    with LEDGER.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                row["run_id"],
                row["topic"],
                row["model_key"],
                row["model_spec"]["provider"],
                row["model_spec"]["model"],
                row["condition"],
                row["rounds"],
                status,
                expected,
                "" if actual is None else actual,
                str(row["output_dir"].relative_to(REPO_ROOT)),
                started,
                ended,
                notes,
            ]
        )


def build_env(model: dict) -> dict:
    env = os.environ.copy()
    key = get_secret(model["key_env"])
    if not key:
        raise RuntimeError(f"missing API key env {model['key_env']}")
    env["LLM_API_KEY"] = key
    env["OPENAI_API_KEY"] = key
    env["LLM_BASE_URL"] = model["base_url"]
    env["OPENAI_BASE_URL"] = model["base_url"]
    env["LLM_MODEL_NAME"] = model["model"]
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def build_command(row: dict, matrix: dict, base_url: str) -> list[str]:
    topic = row["topic_spec"]
    question = (S3_ROOT / topic["question"]).read_text(encoding="utf-8").strip()
    return [
        sys.executable,
        str(HEADLESS),
        "--base-url",
        base_url,
        "--file",
        str(S3_ROOT / topic["base_context"]),
        "--requirement",
        question,
        "--project-name",
        f"S3 {row['topic']} {row['model_key']} {row['condition']}",
        "--platform",
        matrix["platform"],
        "--max-rounds",
        str(row["rounds"]),
        "--accept-language",
        matrix.get("accept_language", "es"),
        "--output-dir",
        str(row["output_dir"]),
        "--poll-timeout",
        str(matrix.get("poll_timeout", 1800)),
        "--no-report",
        "--no-graph-memory-update",
        "--injection-plan",
        str(S3_ROOT / topic["injection_plan"]),
        "--condition",
        row["condition"],
        "--no-wait-after-run",
    ]


def wait_backend(base_url: str, timeout_s: int) -> None:
    deadline = time.time() + timeout_s
    url = base_url.rstrip("/") + "/api/graph/project/list"
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if 200 <= response.status < 500:
                    return
        except Exception as exc:  # noqa: BLE001 - startup probe
            last_error = exc
        time.sleep(2)
    raise RuntimeError(f"backend did not become reachable at {base_url}: {last_error}")


def backend_reachable(base_url: str) -> bool:
    url = base_url.rstrip("/") + "/api/graph/project/list"
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            return 200 <= response.status < 500
    except Exception:  # noqa: BLE001 - probe only
        return False


def start_backend(env: dict, model_key: str) -> subprocess.Popen:
    log_dir = REPO_ROOT / "runs" / "s3_cross_topic" / "_backend_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_time = utc_now().replace(":", "").replace("+", "Z")
    log_path = log_dir / f"backend-{model_key}-{safe_time}.log"
    log_handle = log_path.open("w", encoding="utf-8")
    return subprocess.Popen(
        ["npm", "run", "backend"],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )


def run_one(row: dict, matrix: dict, args: argparse.Namespace, env: dict) -> None:
    expected = expected_events(matrix, row["condition"])
    started = utc_now()

    existing_actual = actual_events(row["output_dir"])
    if existing_actual is not None and not args.force:
        status = "skipped_existing_valid" if existing_actual == expected else "skipped_existing_invalid"
        append_ledger(row, status, expected, existing_actual, started, utc_now(), "existing run_manifest.json")
        print(f"{status}: {row['run_id']} events={existing_actual}/{expected}")
        return

    command = build_command(row, matrix, args.base_url)
    if args.dry_run:
        print(json.dumps({"run_id": row["run_id"], "cmd": command}, indent=2))
        return

    row["output_dir"].mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, cwd=str(REPO_ROOT / "backend"), env=env, text=True)
    ended = utc_now()
    actual = actual_events(row["output_dir"])

    if completed.returncode != 0:
        append_ledger(row, "failed", expected, actual, started, ended, f"exit_code={completed.returncode}")
        print(f"failed: {row['run_id']} exit={completed.returncode}")
        return

    if actual != expected:
        append_ledger(row, "invalid_event_count", expected, actual, started, ended, "event audit mismatch")
        print(f"invalid_event_count: {row['run_id']} events={actual}/{expected}")
        return

    append_ledger(row, "completed", expected, actual, started, ended, "ok")
    print(f"completed: {row['run_id']} events={actual}/{expected}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run or list S3 cross-topic injection matrix rows.")
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--smoke", action="store_true", help="Use baseline-control and signal-mid only.")
    scope.add_argument("--full", action="store_true", help="Use all seven conditions.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true", help="Print planned commands only.")
    action.add_argument("--execute", action="store_true", help="Execute selected rows.")
    parser.add_argument("--start-backend", action="store_true", help="Start and stop backend per model group.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5001")
    parser.add_argument("--models", help="Comma-separated model keys.")
    parser.add_argument("--topics", help="Comma-separated topic keys.")
    parser.add_argument("--conditions", help="Comma-separated condition IDs.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true", help="Rerun rows even if a manifest exists.")
    parser.add_argument("--backend-timeout", type=int, default=180)
    args = parser.parse_args()

    matrix = read_yaml(S3_ROOT / "matrix.yaml")
    rows = iter_rows(matrix, args)
    print(f"selected_rows={len(rows)}")
    if not rows:
        return 0

    if args.dry_run:
        for row in rows:
            safe_env = {
                "LLM_BASE_URL": row["model_spec"]["base_url"],
                "LLM_MODEL_NAME": row["model_spec"]["model"],
                "key_env": row["model_spec"]["key_env"],
            }
            print(json.dumps({"run_id": row["run_id"], "env": safe_env, "output_dir": str(row["output_dir"].relative_to(REPO_ROOT))}, indent=2))
        return 0

    if args.start_backend:
        if backend_reachable(args.base_url):
            raise RuntimeError(
                f"{args.base_url} is already reachable. Stop the existing backend "
                "before using --start-backend, or rerun without --start-backend."
            )
        for model_key in sorted({row["model_key"] for row in rows}):
            model_rows = [row for row in rows if row["model_key"] == model_key]
            env = build_env(model_rows[0]["model_spec"])
            backend = start_backend(env, model_key)
            try:
                wait_backend(args.base_url, args.backend_timeout)
                for row in model_rows:
                    run_one(row, matrix, args, env)
            finally:
                backend.terminate()
                try:
                    backend.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    backend.kill()
        return 0

    for row in rows:
        env = build_env(row["model_spec"])
        run_one(row, matrix, args, env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
