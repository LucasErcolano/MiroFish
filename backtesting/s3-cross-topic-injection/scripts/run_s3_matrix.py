from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import sqlite3
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


def set_if_missing(env: dict, name: str, value: str | None) -> None:
    if value and not env.get(name):
        env[name] = value


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


def write_sanitized_json(path: Path, payload: dict) -> None:
    sys.path.insert(0, str(REPO_ROOT))
    from tools.mirofish_headless import write_json

    write_json(path, payload)


def prepared_dir(row: dict) -> Path:
    return REPO_ROOT / "runs" / "s3_cross_topic" / "_prepared" / row["topic"] / row["model_key"]


def simulation_config_exists(simulation_id: str) -> bool:
    return (REPO_ROOT / "backend" / "uploads" / "simulations" / simulation_id / "simulation_config.json").exists()


def read_prepared_manifest(row: dict) -> dict:
    manifest = prepared_dir(row) / "prepared_manifest.json"
    if not manifest.exists():
        return {}
    try:
        return json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def copy_prepared_artifacts(simulation_id: str, output_dir: Path) -> None:
    sim_dir = REPO_ROOT / "backend" / "uploads" / "simulations" / simulation_id
    artifact_dir = output_dir / "simulation_artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    for name in ["simulation_config.json", "reddit_profiles.json", "twitter_profiles.json", "state.json"]:
        src = sim_dir / name
        if src.exists() and src.is_file():
            shutil.copy2(src, artifact_dir / name)


def discover_existing_prepared_simulation(row: dict) -> str | None:
    model_root = REPO_ROOT / "runs" / "s3_cross_topic" / row["topic"] / row["model_key"]
    if not model_root.exists():
        return None
    for manifest_path in sorted(model_root.glob("*/run_manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        simulation_id = manifest.get("simulation_id")
        if simulation_id and simulation_config_exists(str(simulation_id)):
            return str(simulation_id)
    return None


def prepare_topic_model(row: dict, args: argparse.Namespace) -> str:
    sys.path.insert(0, str(REPO_ROOT))
    from tools.mirofish_headless import MiroFishHeadlessRunner, file_sha256

    output_dir = prepared_dir(row)
    output_dir.mkdir(parents=True, exist_ok=True)
    topic = row["topic_spec"]
    base_context = S3_ROOT / topic["base_context"]
    question = (S3_ROOT / topic["question"]).read_text(encoding="utf-8").strip()
    started = utc_now()

    runner = MiroFishHeadlessRunner(
        base_url=args.base_url,
        output_dir=output_dir,
        repo_root=REPO_ROOT,
        accept_language=args.accept_language,
    )
    write_sanitized_json(
        output_dir / "prepare_config.json",
        {
            "flow_provenance": "s3_prepare_only_backend_api",
            "topic": row["topic"],
            "model_key": row["model_key"],
            "model": row["model_spec"]["model"],
            "project_name": f"S3 prepared {row['topic']} {row['model_key']}",
            "files": [{"path": str(base_context), "sha256": file_sha256(base_context), "bytes": base_context.stat().st_size}],
            "simulation_requirement": question,
            "parallel_profile_count": args.parallel_profile_count,
            "started_at": started,
        },
    )

    try:
        ontology = runner.client.post_multipart(
            "/api/graph/ontology/generate",
            fields={
                "simulation_requirement": question,
                "project_name": f"S3 prepared {row['topic']} {row['model_key']}",
            },
            files=[base_context],
            retry=True,
        )
        project_id = ontology.get("data", {}).get("project_id")
        if not project_id:
            raise RuntimeError("ontology/generate did not return project_id")

        graph_build = runner.client.request_json("POST", "/api/graph/build", {"project_id": project_id}, retry=True)
        runner._wait_graph_task(graph_build.get("data", {}).get("task_id"), args.poll_timeout)

        project = runner.client.request_json("GET", f"/api/graph/project/{project_id}")
        graph_id = project.get("data", {}).get("graph_id")
        if not graph_id:
            raise RuntimeError("graph build completed but project has no graph_id")
        runner.client.request_json("GET", f"/api/graph/data/{graph_id}")

        sim_create = runner.client.request_json(
            "POST",
            "/api/simulation/create",
            {"project_id": project_id, "graph_id": graph_id, "enable_twitter": True, "enable_reddit": True},
            retry=True,
        )
        simulation_id = sim_create.get("data", {}).get("simulation_id")
        if not simulation_id:
            raise RuntimeError("simulation/create did not return simulation_id")

        prepare = runner.client.request_json(
            "POST",
            "/api/simulation/prepare",
            {
                "simulation_id": simulation_id,
                "use_llm_for_profiles": True,
                "parallel_profile_count": args.parallel_profile_count,
            },
            retry=True,
        )
        prepare_status = runner._wait_prepare(simulation_id, prepare.get("data", {}).get("task_id"), args.poll_timeout)
        prepare_result = prepare_status.get("result") or {}
        if (
            prepare_result.get("status") == "failed"
            or prepare_result.get("config_generated") is False
            or not simulation_config_exists(str(simulation_id))
        ):
            raise RuntimeError(
                "simulation prepare did not produce simulation_config.json "
                f"for {row['topic']}/{row['model_key']}: {prepare_result.get('error') or prepare_result}"
            )
        copy_prepared_artifacts(simulation_id, output_dir)
        write_sanitized_json(
            output_dir / "prepared_manifest.json",
            {
                "status": "prepared",
                "flow_provenance": "s3_prepare_only_backend_api",
                "topic": row["topic"],
                "model_key": row["model_key"],
                "model": row["model_spec"]["model"],
                "project_id": project_id,
                "graph_id": graph_id,
                "simulation_id": simulation_id,
                "prepare_status": prepare_status,
                "started_at": started,
                "completed_at": utc_now(),
            },
        )
        return str(simulation_id)
    except Exception as exc:  # noqa: BLE001 - preserve prepare blocker
        write_sanitized_json(
            output_dir / "prepared_manifest.json",
            {
                "status": "BLOCKED",
                "flow_provenance": "s3_prepare_only_backend_api",
                "topic": row["topic"],
                "model_key": row["model_key"],
                "model": row["model_spec"]["model"],
                "reason": str(exc),
                "started_at": started,
                "completed_at": utc_now(),
            },
        )
        raise


def ensure_prepared_simulation(row: dict, args: argparse.Namespace) -> str | None:
    if args.full_flow_per_run:
        return None

    manifest = read_prepared_manifest(row)
    simulation_id = manifest.get("simulation_id")
    if simulation_id and simulation_config_exists(str(simulation_id)) and not args.force_prepare:
        return str(simulation_id)

    discovered = discover_existing_prepared_simulation(row)
    if discovered and not args.force_prepare:
        output_dir = prepared_dir(row)
        output_dir.mkdir(parents=True, exist_ok=True)
        write_sanitized_json(
            output_dir / "prepared_manifest.json",
            {
                "status": "prepared",
                "flow_provenance": "s3_discovered_existing_simulation",
                "topic": row["topic"],
                "model_key": row["model_key"],
                "model": row["model_spec"]["model"],
                "simulation_id": discovered,
                "completed_at": utc_now(),
            },
        )
        copy_prepared_artifacts(discovered, output_dir)
        return discovered

    return prepare_topic_model(row, args)


def expected_events(matrix: dict, condition_id: str) -> int:
    for condition in matrix["conditions"]:
        if condition["id"] == condition_id:
            return int(condition["event_expected"])
    raise KeyError(condition_id)


def read_manifest(output_dir: Path) -> dict:
    manifest = output_dir / "run_manifest.json"
    if not manifest.exists():
        return {}
    with manifest.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def count_jsonl(path: Path) -> int | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def actual_events(output_dir: Path, expected: int) -> int | None:
    has_artifact_context = (output_dir / "run_manifest.json").exists() or (output_dir / "simulation_artifacts").exists()
    data = read_manifest(output_dir)
    value = data.get("scheduled_events_fired_count")
    if value is not None:
        return int(value)

    fired_log = output_dir / "simulation_artifacts" / "scheduled_events_fired.jsonl"
    fired_count = count_jsonl(fired_log)
    if fired_count is not None:
        return fired_count

    if expected == 0 and has_artifact_context:
        return 0
    return None


def reddit_db_counts(output_dir: Path) -> dict[str, int]:
    db_path = output_dir / "simulation_artifacts" / "reddit_simulation.db"
    if not db_path.exists():
        return {}
    counts: dict[str, int] = {}
    with sqlite3.connect(db_path) as connection:
        for table in ["post", "comment", "trace", "user"]:
            try:
                counts[table] = int(connection.execute(f"select count(*) from {table}").fetchone()[0])
            except sqlite3.DatabaseError:
                counts[table] = 0
    return counts


def log_reached_requested_round(output_dir: Path, rounds: int) -> bool:
    log_path = output_dir / "simulation_artifacts" / "simulation.log"
    if not log_path.exists():
        return False
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return bool(re.search(rf"Round\s+{rounds}\s*/\s*{rounds}\b", text))


def has_real_run_evidence(output_dir: Path, rounds: int) -> tuple[bool, str]:
    manifest = read_manifest(output_dir)
    if manifest.get("status") == "completed" and manifest.get("is_real_mirofish_system"):
        return True, "manifest_real"

    counts = reddit_db_counts(output_dir)
    if counts.get("post", 0) > 0 and counts.get("trace", 0) > 0 and log_reached_requested_round(output_dir, rounds):
        return True, f"artifact_evidence posts={counts.get('post', 0)} traces={counts.get('trace', 0)}"

    return False, f"no_real_evidence manifest_rounds={manifest.get('num_rounds_or_epochs')} db={counts}"


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
    graphiti_key_env = model.get("graphiti_key_env") or model["key_env"]
    graphiti_key = get_secret(graphiti_key_env)
    if not graphiti_key:
        raise RuntimeError(f"missing API key env {graphiti_key_env}")
    graphiti_base_url = model.get("graphiti_base_url") or model["base_url"]
    env["LLM_API_KEY"] = key
    env["OPENAI_API_KEY"] = key
    env["LLM_BASE_URL"] = model["base_url"]
    env["OPENAI_BASE_URL"] = model["base_url"]
    env["LLM_MODEL_NAME"] = model["model"]
    env["PYTHONIOENCODING"] = "utf-8"
    set_if_missing(env, "FLASK_HOST", "127.0.0.1")
    set_if_missing(env, "FLASK_PORT", "5001")
    set_if_missing(env, "FLASK_DEBUG", "false")
    set_if_missing(env, "GRAPH_BACKEND", "graphiti")
    set_if_missing(env, "GRAPHITI_URI", "bolt://127.0.0.1:7687")
    set_if_missing(env, "GRAPHITI_USER", "neo4j")
    set_if_missing(env, "GRAPHITI_PASSWORD", "mirofishpassword")
    set_if_missing(env, "GRAPHITI_DATABASE", "neo4j")
    set_if_missing(env, "GRAPHITI_LLM_API_KEY", graphiti_key)
    set_if_missing(env, "GRAPHITI_LLM_BASE_URL", graphiti_base_url)
    set_if_missing(env, "GRAPHITI_LLM_MODEL", model.get("graphiti_llm_model") or model["model"])
    set_if_missing(env, "GRAPHITI_LLM_CLIENT_MODE", "generic")
    set_if_missing(env, "GRAPHITI_LLM_MAX_TOKENS", "4096")
    set_if_missing(env, "MIROFISH_INTERVIEW_AGENTS_TIMEOUT", "45")

    openrouter_key = get_secret("OPENROUTER_API_KEY")
    openrouter_base_url = get_secret("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"
    if openrouter_key:
        set_if_missing(env, "OPENROUTER_API_KEY", openrouter_key)
        set_if_missing(env, "OPENROUTER_BASE_URL", openrouter_base_url)
        set_if_missing(env, "GRAPHITI_EMBEDDER_API_KEY", openrouter_key)
        set_if_missing(env, "GRAPHITI_EMBEDDER_BASE_URL", openrouter_base_url)
        set_if_missing(env, "GRAPHITI_EMBEDDER_MODEL", "qwen/qwen3-embedding-8b")
        set_if_missing(env, "GRAPHITI_EMBEDDER_DIM", "4096")
        set_if_missing(env, "GRAPH_SEARCH_APP_EMBEDDER_API_KEY", openrouter_key)
        set_if_missing(env, "GRAPH_SEARCH_APP_EMBEDDER_BASE_URL", openrouter_base_url)
        set_if_missing(env, "GRAPH_SEARCH_APP_EMBEDDER_MODEL", "qwen/qwen3-embedding-8b")
    return env


def build_command(
    row: dict,
    matrix: dict,
    base_url: str,
    no_wait_after_run: bool,
    simulation_id: str | None,
) -> list[str]:
    topic = row["topic_spec"]
    question = (S3_ROOT / topic["question"]).read_text(encoding="utf-8").strip()
    command = [
        sys.executable,
        str(HEADLESS),
        "--base-url",
        base_url,
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
    ]
    if simulation_id:
        command.extend(["--existing-simulation-id", simulation_id])
    else:
        command.extend(
            [
                "--file",
                str(S3_ROOT / topic["base_context"]),
                "--requirement",
                question,
                "--project-name",
                f"S3 {row['topic']} {row['model_key']} {row['condition']}",
            ]
        )
    if no_wait_after_run:
        command.append("--no-wait-after-run")
    return command


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
    uv_exe = "uv.exe" if os.name == "nt" else "uv"
    process = subprocess.Popen(
        [uv_exe, "run", "--frozen", "--python", "3.11", "python", "run.py"],
        cwd=str(REPO_ROOT / "backend"),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    log_handle.close()
    return process


def stop_backend_process_tree(process: subprocess.Popen) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    process.terminate()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()


def run_one(row: dict, matrix: dict, args: argparse.Namespace, env: dict) -> None:
    expected = expected_events(matrix, row["condition"])
    started = utc_now()

    existing_actual = actual_events(row["output_dir"], expected)
    if existing_actual is not None and not args.force:
        real_ok, evidence_note = has_real_run_evidence(row["output_dir"], row["rounds"])
        status = "skipped_existing_valid" if existing_actual == expected and real_ok else "skipped_existing_invalid"
        append_ledger(row, status, expected, existing_actual, started, utc_now(), f"existing artifacts; {evidence_note}")
        print(f"{status}: {row['run_id']} events={existing_actual}/{expected}")
        return

    simulation_id = ensure_prepared_simulation(row, args)
    command = build_command(row, matrix, args.base_url, args.no_wait_after_run, simulation_id)
    if args.dry_run:
        print(json.dumps({"run_id": row["run_id"], "cmd": command}, indent=2))
        return

    row["output_dir"].mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, cwd=str(REPO_ROOT / "backend"), env=env, text=True)
    ended = utc_now()
    actual = actual_events(row["output_dir"], expected)
    real_ok, evidence_note = has_real_run_evidence(row["output_dir"], row["rounds"])

    if completed.returncode != 0:
        append_ledger(row, "failed", expected, actual, started, ended, f"exit_code={completed.returncode}")
        print(f"failed: {row['run_id']} exit={completed.returncode}")
        return

    if not real_ok:
        append_ledger(row, "invalid_real_system", expected, actual, started, ended, evidence_note)
        print(f"invalid_real_system: {row['run_id']} {evidence_note}")
        return

    if actual != expected:
        append_ledger(row, "invalid_event_count", expected, actual, started, ended, f"event audit mismatch; {evidence_note}")
        print(f"invalid_event_count: {row['run_id']} events={actual}/{expected}")
        return

    status = "completed" if evidence_note == "manifest_real" else "completed_artifact_evidence"
    append_ledger(row, status, expected, actual, started, ended, evidence_note)
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
    parser.add_argument(
        "--no-wait-after-run",
        dest="no_wait_after_run",
        action="store_true",
        default=True,
        help="Pass through to headless runner; default for S3 autonomous runs.",
    )
    parser.add_argument(
        "--wait-after-run",
        dest="no_wait_after_run",
        action="store_false",
        help="Disable --no-wait-after-run; useful only for manual IPC debugging.",
    )
    parser.add_argument("--full-flow-per-run", action="store_true", help="Do not reuse prepared simulations; mostly for debugging.")
    parser.add_argument("--force-prepare", action="store_true", help="Regenerate prepared simulations even when cached.")
    parser.add_argument("--parallel-profile-count", type=int, default=5)
    parser.add_argument("--poll-timeout", type=int, default=None)
    parser.add_argument("--accept-language", default=None)
    args = parser.parse_args()

    matrix = read_yaml(S3_ROOT / "matrix.yaml")
    if args.poll_timeout is None:
        args.poll_timeout = int(matrix.get("poll_timeout", 1800))
    if args.accept_language is None:
        args.accept_language = matrix.get("accept_language", "es")
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
                "GRAPHITI_LLM_BASE_URL": row["model_spec"].get("graphiti_base_url") or row["model_spec"]["base_url"],
                "GRAPHITI_LLM_MODEL": row["model_spec"].get("graphiti_llm_model") or row["model_spec"]["model"],
                "graphiti_key_env": row["model_spec"].get("graphiti_key_env") or row["model_spec"]["key_env"],
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
                stop_backend_process_tree(backend)
        return 0

    for row in rows:
        env = build_env(row["model_spec"])
        run_one(row, matrix, args, env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
