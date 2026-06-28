#!/usr/bin/env python3
"""Plan and run the IPC tri-model multi-agent benchmark matrix.

Default usage before paid smoke:

    python backtesting/ipc-trimodel-multiagent/scripts/run_ipc_trimodel_matrix.py --all --dry-run

Execution is deliberately explicit: pass ``--execute`` to make model calls.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
BENCH_ROOT = REPO_ROOT / "backtesting" / "ipc-trimodel-multiagent"
MATRIX_PATH = BENCH_ROOT / "matrix.yaml"
HEADLESS = REPO_ROOT / "tools" / "mirofish_headless.py"
LEDGER = BENCH_ROOT / "RUN_LEDGER.csv"
REQUIRED_ROUTED_MODELS = {
    "qwen/qwen3-8b",
    "google/gemma-3-27b-it",
    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


@dataclass(frozen=True)
class MatrixRow:
    line: str
    row_id: str
    package: str
    input_file: Path
    requirement: str
    rounds: int
    density: int
    condition: str | None
    injection_plan: Path | None
    expected_events: int
    raw_dir: Path
    committed_dir: Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping in {path}")
    return data


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def csv_filter(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {part.strip() for part in value.split(",") if part.strip()}


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
            return value or None
    except OSError:
        return None


def set_if_missing(env: dict[str, str], name: str, value: str | None) -> None:
    if value and not env.get(name):
        env[name] = value


def build_env(matrix: dict[str, Any]) -> dict[str, str]:
    """Build the backend env for a trimodel run without serializing secrets."""
    env = os.environ.copy()
    deepinfra_key = get_secret("DEEPINFRA_API_KEY")
    openrouter_key = get_secret("OPENROUTER_API_KEY")
    deepinfra_base = env.get("DEEPINFRA_BASE_URL") or "https://api.deepinfra.com/v1/openai"
    openrouter_base = env.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"
    graph_model = matrix.get("graph", {}).get("extraction_model") or "google/gemma-3-27b-it"

    set_if_missing(env, "DEEPINFRA_BASE_URL", deepinfra_base)
    set_if_missing(env, "OPENROUTER_BASE_URL", openrouter_base)
    if deepinfra_key:
        set_if_missing(env, "DEEPINFRA_API_KEY", deepinfra_key)
        set_if_missing(env, "LLM_API_KEY", deepinfra_key)
        set_if_missing(env, "OPENAI_API_KEY", deepinfra_key)
        set_if_missing(env, "GRAPHITI_LLM_API_KEY", deepinfra_key)
    if openrouter_key:
        set_if_missing(env, "OPENROUTER_API_KEY", openrouter_key)
        set_if_missing(env, "GRAPHITI_EMBEDDER_API_KEY", openrouter_key)
        set_if_missing(env, "GRAPHITI_EMBEDDER_BASE_URL", openrouter_base)
        set_if_missing(env, "GRAPHITI_EMBEDDER_MODEL", "qwen/qwen3-embedding-8b")
        set_if_missing(env, "GRAPHITI_EMBEDDER_DIM", "4096")
        set_if_missing(env, "GRAPH_SEARCH_APP_EMBEDDER_API_KEY", openrouter_key)
        set_if_missing(env, "GRAPH_SEARCH_APP_EMBEDDER_BASE_URL", openrouter_base)
        set_if_missing(env, "GRAPH_SEARCH_APP_EMBEDDER_MODEL", "qwen/qwen3-embedding-8b")

    set_if_missing(env, "LLM_BASE_URL", deepinfra_base)
    set_if_missing(env, "OPENAI_BASE_URL", deepinfra_base)
    set_if_missing(env, "LLM_MODEL_NAME", graph_model)
    set_if_missing(env, "USE_EXPERIMENTAL_MEMORY", "true")
    set_if_missing(env, "GRAPH_BACKEND", "graphiti")
    set_if_missing(env, "GRAPHITI_URI", "bolt://127.0.0.1:7687")
    set_if_missing(env, "GRAPHITI_USER", "neo4j")
    set_if_missing(env, "GRAPHITI_PASSWORD", "mirofishpassword")
    set_if_missing(env, "GRAPHITI_DATABASE", "neo4j")
    set_if_missing(env, "GRAPHITI_LLM_BASE_URL", deepinfra_base)
    set_if_missing(env, "GRAPHITI_LLM_MODEL", graph_model)
    set_if_missing(env, "GRAPHITI_LLM_CLIENT_MODE", "generic")
    set_if_missing(env, "GRAPHITI_BYPASS_NODE_DEDUP", "true")
    set_if_missing(env, "SIMILARITY_THRESHOLD", "0")
    set_if_missing(env, "MIROFISH_ACCEPT_PARTIAL_GRAPH_AFTER_SECONDS", "600")
    set_if_missing(env, "MIROFISH_ACCEPT_PARTIAL_GRAPH_MIN_NODES", "5")
    set_if_missing(env, "MIROFISH_ACCEPT_PARTIAL_GRAPH_MIN_EDGES", "5")
    set_if_missing(env, "LLM_REQUEST_TIMEOUT", "60")
    set_if_missing(env, "OASIS_PROFILE_MAX_TOKENS", "2048")
    set_if_missing(env, "OASIS_PROFILE_MAX_ATTEMPTS", "2")
    set_if_missing(env, "MIROFISH_PREPARE_STALE_AFTER_SECONDS", "420")
    set_if_missing(env, "PYTHONIOENCODING", "utf-8")
    return env


def env_plan(matrix: dict[str, Any]) -> dict[str, Any]:
    graph_model = matrix.get("graph", {}).get("extraction_model") or "google/gemma-3-27b-it"
    return {
        "backend_base_model": graph_model,
        "backend_base_url_env": "DEEPINFRA_BASE_URL",
        "backend_key_env": "DEEPINFRA_API_KEY",
        "agent_model_map": matrix["model_map"],
        "required_key_envs": {
            "OPENROUTER_API_KEY": bool(get_secret("OPENROUTER_API_KEY")),
            "DEEPINFRA_API_KEY": bool(get_secret("DEEPINFRA_API_KEY")),
        },
        "required_non_secret_env": {
            "OPENROUTER_BASE_URL": os.environ.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1",
            "DEEPINFRA_BASE_URL": os.environ.get("DEEPINFRA_BASE_URL") or "https://api.deepinfra.com/v1/openai",
            "USE_EXPERIMENTAL_MEMORY": "true",
            "GRAPHITI_BYPASS_NODE_DEDUP": "true",
            "SIMILARITY_THRESHOLD": "0",
            "MIROFISH_ACCEPT_PARTIAL_GRAPH_AFTER_SECONDS": "600",
            "MIROFISH_ACCEPT_PARTIAL_GRAPH_MIN_NODES": "5",
            "MIROFISH_ACCEPT_PARTIAL_GRAPH_MIN_EDGES": "5",
            "LLM_REQUEST_TIMEOUT": "60",
            "OASIS_PROFILE_MAX_TOKENS": "2048",
            "OASIS_PROFILE_MAX_ATTEMPTS": "2",
            "MIROFISH_PREPARE_STALE_AFTER_SECONDS": "420",
            "GRAPHITI_EMBEDDER_BASE_URL": os.environ.get("GRAPHITI_EMBEDDER_BASE_URL")
            or os.environ.get("OPENROUTER_BASE_URL")
            or "https://openrouter.ai/api/v1",
            "GRAPHITI_EMBEDDER_MODEL": os.environ.get("GRAPHITI_EMBEDDER_MODEL") or "qwen/qwen3-embedding-8b",
            "GRAPHITI_EMBEDDER_DIM": os.environ.get("GRAPHITI_EMBEDDER_DIM") or "4096",
            "PYTHONIOENCODING": "utf-8",
        },
    }


def combined_requirement(question: Path, constraints: Path | None) -> str:
    pieces: list[str] = []
    if constraints and constraints.exists():
        pieces.append(constraints.read_text(encoding="utf-8").strip())
    pieces.append(question.read_text(encoding="utf-8").strip())
    return "\n\n".join(piece for piece in pieces if piece)


def expected_events_from_plan(plan_path: Path, condition: str) -> int:
    plan = read_yaml(plan_path)
    return len((plan.get("conditions", {}).get(condition, {}) or {}).get("injections", []))


def make_rows(matrix: dict[str, Any], args: argparse.Namespace) -> list[MatrixRow]:
    line_filter = {line for line in ["smoke", "temporal", "line5", "s3"] if getattr(args, line)}
    row_filter = csv_filter(args.rows)
    condition_filter = csv_filter(args.conditions)

    case_dir = REPO_ROOT / matrix["case_dir"]
    question = case_dir / matrix["question_file"]
    constraints = case_dir / matrix.get("system_constraints_file", "")
    requirement = combined_requirement(question, constraints)
    raw_root = REPO_ROOT / matrix["outputs"]["raw_root"]
    committed_root = REPO_ROOT / matrix["outputs"]["committed_root"]

    rows: list[MatrixRow] = []
    if "smoke" in line_filter:
        smoke_rounds = int(args.smoke_rounds)
        row_id = f"ipc_trimodel_smoke_T0_R{smoke_rounds}_D{matrix['temporal']['density']}"
        rows.append(
            MatrixRow(
                line="smoke",
                row_id=row_id,
                package="T0",
                input_file=case_dir / "seed_T0.md",
                requirement=requirement,
                rounds=smoke_rounds,
                density=int(matrix["temporal"]["density"]),
                condition=None,
                injection_plan=None,
                expected_events=0,
                raw_dir=raw_root / "smoke" / row_id,
                committed_dir=committed_root / "smoke" / row_id,
            )
        )

    if "temporal" in line_filter:
        temporal = matrix["temporal"]
        for item in temporal["rows"]:
            row_id = item["id"]
            row = MatrixRow(
                line="temporal",
                row_id=row_id,
                package=item["package"],
                input_file=case_dir / item["input_file"],
                requirement=requirement,
                rounds=int(temporal["rounds"]),
                density=int(temporal["density"]),
                condition=None,
                injection_plan=None,
                expected_events=0,
                raw_dir=raw_root / "temporal" / row_id,
                committed_dir=committed_root / "temporal" / row_id,
            )
            rows.append(row)

    if "line5" in line_filter:
        line5 = matrix["line5"]
        for item in line5["rows"]:
            row_id = item["id"]
            rows.append(
                MatrixRow(
                    line="line5",
                    row_id=row_id,
                    package=line5["package"],
                    input_file=case_dir / line5["input_file"],
                    requirement=requirement,
                    rounds=int(item["rounds"]),
                    density=int(line5["density"]),
                    condition=None,
                    injection_plan=None,
                    expected_events=0,
                    raw_dir=raw_root / "line5" / row_id,
                    committed_dir=committed_root / "line5" / row_id,
                )
            )

    if "s3" in line_filter:
        topic_dir = REPO_ROOT / matrix["s3"]["topic_config"]
        injection_plan = topic_dir / "injection_plan.yaml"
        s3_requirement = (topic_dir / "question.md").read_text(encoding="utf-8").strip()
        for condition in matrix["s3"]["conditions"]:
            if condition_filter and condition not in condition_filter:
                continue
            row_id = f"ipc_trimodel_s3_{condition}_R{matrix['s3']['rounds']}_D{matrix['s3']['density']}"
            rows.append(
                MatrixRow(
                    line="s3",
                    row_id=row_id,
                    package="s3-ipc-base-context",
                    input_file=topic_dir / "base_context.md",
                    requirement=s3_requirement,
                    rounds=int(matrix["s3"]["rounds"]),
                    density=int(matrix["s3"]["density"]),
                    condition=condition,
                    injection_plan=injection_plan,
                    expected_events=expected_events_from_plan(injection_plan, condition),
                    raw_dir=raw_root / "s3" / row_id,
                    committed_dir=committed_root / "s3" / row_id,
                )
            )

    if row_filter:
        rows = [row for row in rows if row.row_id in row_filter]
    if args.limit:
        rows = rows[: args.limit]
    return rows


def build_command(row: MatrixRow, matrix: dict[str, Any], args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(HEADLESS),
        "--base-url",
        args.base_url,
        "--platform",
        matrix.get("platform", "reddit"),
        "--max-rounds",
        str(row.rounds),
        "--accept-language",
        args.accept_language,
        "--output-dir",
        str(row.raw_dir),
        "--poll-timeout",
        str(args.poll_timeout),
        "--repo-root",
        str(REPO_ROOT),
        "--model-map",
        str(REPO_ROOT / matrix["model_map"]),
        "--file",
        str(row.input_file),
        "--requirement",
        row.requirement,
        "--project-name",
        f"IPC trimodel {row.row_id}",
    ]
    if args.no_wait_after_run:
        command.append("--no-wait-after-run")
    if matrix.get("eval_artifact") == "structured_answer_json":
        command.append("--no-report")
    if row.injection_plan and row.condition:
        command.extend(["--injection-plan", str(row.injection_plan), "--condition", row.condition])
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


def start_backend(env: dict[str, str]) -> subprocess.Popen:
    log_dir = REPO_ROOT / "runs" / "ipc_trimodel_multiagent" / "_backend_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_time = utc_now().replace(":", "").replace("+", "Z")
    log_path = log_dir / f"backend-{safe_time}.log"
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


def summarize_telemetry(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "llm_calls": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd_est": 0.0,
        "errors": 0,
        "parse_errors": 0,
        "models": [],
        "providers": [],
    }
    models: set[str] = set()
    providers: set[str] = set()
    if not path.exists():
        summary["missing"] = True
        return summary
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            summary["parse_errors"] += 1
            continue
        summary["llm_calls"] += 1
        summary["tokens_in"] += int(record.get("tokens_in") or 0)
        summary["tokens_out"] += int(record.get("tokens_out") or 0)
        summary["cost_usd_est"] += float(record.get("cost_usd_est") or 0.0)
        if record.get("error"):
            summary["errors"] += 1
        if record.get("output_valid_json") is False:
            summary["parse_errors"] += 1
        if record.get("model"):
            models.add(str(record["model"]))
        if record.get("provider"):
            providers.add(str(record["provider"]))
    summary["cost_usd_est"] = round(summary["cost_usd_est"], 8)
    summary["models"] = sorted(models)
    summary["providers"] = sorted(providers)
    return summary


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_row(row: MatrixRow, matrix: dict[str, Any]) -> dict[str, Any]:
    structured_path = row.raw_dir / "structured_answer.json"
    report_path = row.raw_dir / "mirofish_report_raw.md"
    use_structured = matrix.get("eval_artifact") == "structured_answer_json"
    if use_structured and not structured_path.exists():
        raise RuntimeError(f"structured answer not found for evaluation: {structured_path}")
    if not use_structured and not report_path.exists():
        raise RuntimeError(f"report markdown not found for evaluation: {report_path}")
    eval_script = REPO_ROOT / matrix["case_dir"] / matrix["eval_script"]
    artifact_args = ["--structured-answer", str(structured_path)] if use_structured else ["--report", str(report_path)]
    completed = subprocess.run(
        [
            sys.executable,
            str(eval_script),
            *artifact_args,
            "--case-id",
            matrix["case_id"],
            "--variant",
            row.row_id,
            "--model-policy",
            "trimodel_multiagent",
            "--seed",
            "1",
        ],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    result = json.loads(completed.stdout)
    write_json(row.raw_dir / "eval_result.json", result)
    return result


def extract_source_ids(text: str) -> list[str]:
    return sorted(set(re.findall(r"\b[A-Z][A-Z0-9_]*_[0-9]+\b", text)))


def structured_report_context(row: MatrixRow, matrix: dict[str, Any]) -> dict[str, Any]:
    case_dir = REPO_ROOT / matrix["case_dir"]
    constraints_path = case_dir / matrix.get("system_constraints_file", "")
    source_packet_text = row.input_file.read_text(encoding="utf-8")
    return {
        "cutoff_date": "2025-01-31",
        "temporal_package": row.package,
        "source_ids": extract_source_ids(source_packet_text),
        "source_packet_text": source_packet_text,
        "system_constraints_text": constraints_path.read_text(encoding="utf-8") if constraints_path.exists() else "",
        "primary_query": row.requirement,
        "row_id": row.row_id,
        "condition": row.condition,
        "expected_events": row.expected_events,
    }


def generate_structured_answer(row: MatrixRow, matrix: dict[str, Any], env: dict[str, str]) -> None:
    manifest = read_json(row.raw_dir / "run_manifest.json")
    simulation_id = manifest.get("simulation_id")
    graph_id = manifest.get("graph_id")
    if not simulation_id or not graph_id:
        raise RuntimeError("run_manifest.json missing simulation_id or graph_id for structured report")

    context_path = row.raw_dir / "structured_report_context.json"
    structured_path = row.raw_dir / "structured_answer.json"
    markdown_path = row.raw_dir / "structured_report.md"
    meta_path = row.raw_dir / "structured_report_meta.json"
    write_json(context_path, structured_report_context(row, matrix))

    code = r"""
import json
import sys
from pathlib import Path

repo_root = Path(sys.argv[1])
sys.path.insert(0, str(repo_root / "backend"))

from app.services.report_agent import ReportManager, ReportStatus
from app.services.structured_report_agent import StructuredReportAgent

simulation_id = sys.argv[2]
graph_id = sys.argv[3]
simulation_requirement_path = Path(sys.argv[4])
context_path = Path(sys.argv[5])
structured_path = Path(sys.argv[6])
markdown_path = Path(sys.argv[7])
meta_path = Path(sys.argv[8])
report_id = sys.argv[9]

context = json.loads(context_path.read_text(encoding="utf-8"))
simulation_requirement = simulation_requirement_path.read_text(encoding="utf-8")
agent = StructuredReportAgent(
    graph_id=graph_id,
    simulation_id=simulation_id,
    simulation_requirement=simulation_requirement,
    schema_id="arg_ipc_2025_v1",
    report_context=context,
)
report = agent.generate_report(report_id=report_id)
ReportManager.save_report(report)
status = getattr(report.status, "value", report.status)
meta = {
    "report_id": report.report_id,
    "simulation_id": simulation_id,
    "graph_id": graph_id,
    "status": status,
    "error": report.error,
    "output_mode": getattr(report, "output_mode", None),
    "schema_id": getattr(report, "schema_id", None),
}
meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if report.status != ReportStatus.COMPLETED:
    raise SystemExit(report.error or f"structured report failed with status={status}")
structured_path.write_text(json.dumps(report.structured_answer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
markdown_path.write_text(report.markdown_content or "", encoding="utf-8")
"""
    requirement_path = row.raw_dir / "structured_simulation_requirement.txt"
    requirement_path.write_text(row.requirement, encoding="utf-8")
    uv_exe = "uv.exe" if os.name == "nt" else "uv"
    completed = subprocess.run(
        [
            uv_exe,
            "run",
            "--frozen",
            "--python",
            "3.11",
            "python",
            "-c",
            code,
            str(REPO_ROOT),
            str(simulation_id),
            str(graph_id),
            str(requirement_path),
            str(context_path),
            str(structured_path),
            str(markdown_path),
            str(meta_path),
            f"structured_{row.row_id}",
        ],
        cwd=str(REPO_ROOT / "backend"),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())


def copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists() and src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def write_run_notes(row: MatrixRow, eval_result: dict[str, Any], telemetry: dict[str, Any]) -> None:
    manifest = read_json(row.raw_dir / "run_manifest.json")
    lines = [
        f"# {row.row_id}",
        "",
        f"- line: `{row.line}`",
        f"- package: `{row.package}`",
        f"- input_file: `{row.input_file.relative_to(REPO_ROOT)}`",
        f"- rounds: `{row.rounds}`",
        f"- density: `{row.density}`",
        f"- condition: `{row.condition or 'none'}`",
        f"- expected_events: `{row.expected_events}`",
        f"- raw_output: `{row.raw_dir.relative_to(REPO_ROOT)}`",
        f"- status: `{manifest.get('status', 'unknown')}`",
        f"- completed_rounds: `{manifest.get('num_rounds_or_epochs', '')}`",
        f"- eval_score: `{eval_result.get('score')}/{eval_result.get('max_score')}`",
        f"- parse_errors: `{eval_result.get('parse_errors')}`",
        f"- llm_calls: `{telemetry.get('llm_calls')}`",
        f"- tokens_in: `{telemetry.get('tokens_in')}`",
        f"- tokens_out: `{telemetry.get('tokens_out')}`",
        f"- estimated_cost_usd: `{telemetry.get('cost_usd_est')}`",
        "",
        "Routing evidence must be checked in `model_routing_audit.jsonl` before counting this as a valid tri-model row.",
    ]
    (row.raw_dir / "run_notes.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_committed_artifacts(row: MatrixRow, eval_result: dict[str, Any], telemetry: dict[str, Any]) -> None:
    if row.committed_dir.exists():
        shutil.rmtree(row.committed_dir)
    row.committed_dir.mkdir(parents=True, exist_ok=True)
    write_json(row.raw_dir / "llm_telemetry_summary.json", telemetry)
    write_run_notes(row, eval_result, telemetry)
    if (row.raw_dir / "mirofish_report_raw.md").exists():
        copy_if_exists(row.raw_dir / "mirofish_report_raw.md", row.committed_dir / "report.md")
    else:
        copy_if_exists(row.raw_dir / "structured_report.md", row.committed_dir / "report.md")
    copy_if_exists(row.raw_dir / "eval_result.json", row.committed_dir / "eval_result.json")
    copy_if_exists(row.raw_dir / "structured_answer.json", row.committed_dir / "structured_answer.json")
    copy_if_exists(row.raw_dir / "structured_report.md", row.committed_dir / "structured_report.md")
    copy_if_exists(row.raw_dir / "structured_report_meta.json", row.committed_dir / "structured_report_meta.json")
    copy_if_exists(row.raw_dir / "run_notes.md", row.committed_dir / "run_notes.md")
    copy_if_exists(row.raw_dir / "run_manifest.json", row.committed_dir / "run_manifest.json")
    copy_if_exists(row.raw_dir / "run_config.json", row.committed_dir / "run_config.json")
    copy_if_exists(
        row.raw_dir / "simulation_artifacts" / "model_routing_audit.jsonl",
        row.committed_dir / "model_routing_audit.jsonl",
    )
    copy_if_exists(row.raw_dir / "llm_telemetry_summary.json", row.committed_dir / "llm_telemetry_summary.json")
    copy_if_exists(
        row.raw_dir / "simulation_artifacts" / "experimental_memory_evidence.json",
        row.committed_dir / "experimental_memory_evidence.json",
    )
    copy_if_exists(
        row.raw_dir / "simulation_artifacts" / "experimental_memory" / "core_memory.json",
        row.committed_dir / "core_memory.json",
    )
    if row.condition:
        copy_if_exists(
            row.raw_dir / "simulation_artifacts" / "scheduled_events_fired.jsonl",
            row.committed_dir / "scheduled_events_fired.jsonl",
        )


def validate_committed_evidence(row: MatrixRow) -> list[str]:
    required = [
        "report.md",
        "eval_result.json",
        "structured_answer.json",
        "run_notes.md",
        "run_manifest.json",
        "model_routing_audit.jsonl",
        "llm_telemetry_summary.json",
        "experimental_memory_evidence.json",
    ]
    if row.condition and row.expected_events > 0:
        required.append("scheduled_events_fired.jsonl")

    missing = [name for name in required if not (row.committed_dir / name).exists()]

    manifest_path = row.committed_dir / "run_manifest.json"
    if manifest_path.exists():
        try:
            manifest = read_json(manifest_path)
        except json.JSONDecodeError:
            missing.append("run_manifest.json:invalid_json")
        else:
            completed_rounds = int(manifest.get("num_rounds_or_epochs") or 0)
            run_status = manifest.get("final_run_status") or {}
            current_round = int(run_status.get("current_round") or 0)
            simulated_hours = int(run_status.get("simulated_hours") or 0)
            total_actions = int(run_status.get("total_actions_count") or 0)
            reddit_actions = int(run_status.get("reddit_actions_count") or 0)
            reddit_db_summary = manifest.get("reddit_db_summary") or {}
            reddit_comments = int(reddit_db_summary.get("comment_count") or 0)
            if max(completed_rounds, current_round, simulated_hours, total_actions, reddit_actions, reddit_comments) <= 0:
                missing.append("run_manifest.json:no_completed_rounds")

    telemetry_path = row.committed_dir / "llm_telemetry_summary.json"
    if telemetry_path.exists():
        try:
            telemetry = read_json(telemetry_path)
        except json.JSONDecodeError:
            missing.append("llm_telemetry_summary.json:invalid_json")
        else:
            if int(telemetry.get("llm_calls") or 0) <= 0:
                missing.append("llm_telemetry_summary.json:no_llm_calls")
            telemetry_models = {str(model) for model in telemetry.get("models", [])}
            missing_telemetry_models = sorted(REQUIRED_ROUTED_MODELS - telemetry_models)
            if missing_telemetry_models:
                missing.append(
                    f"llm_telemetry_summary.json:missing_models={','.join(missing_telemetry_models)}"
                )

    memory_evidence_path = row.committed_dir / "experimental_memory_evidence.json"
    if memory_evidence_path.exists():
        try:
            memory_evidence = read_json(memory_evidence_path)
        except json.JSONDecodeError:
            missing.append("experimental_memory_evidence.json:invalid_json")
        else:
            if not (
                memory_evidence.get("core_memory_exists")
                or memory_evidence.get("chroma_db_exists")
                or memory_evidence.get("memory_dir_exists")
            ):
                missing.append("experimental_memory_evidence.json:no_memory_artifacts")
    audit_path = row.committed_dir / "model_routing_audit.jsonl"
    if audit_path.exists():
        models: set[str] = set()
        invalid_lines = 0
        for line in audit_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                invalid_lines += 1
                continue
            model = record.get("model")
            if model:
                models.add(str(model))
        missing_models = sorted(REQUIRED_ROUTED_MODELS - models)
        if invalid_lines:
            missing.append("model_routing_audit.jsonl:invalid_jsonl")
        if missing_models:
            missing.append(f"model_routing_audit.jsonl:missing_models={','.join(missing_models)}")
    scheduled_events_path = row.committed_dir / "scheduled_events_fired.jsonl"
    if row.expected_events > 0 and scheduled_events_path.exists():
        actual_events = sum(
            1 for line in scheduled_events_path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()
        )
        if actual_events != row.expected_events:
            missing.append(f"scheduled_events_fired.jsonl:event_count={actual_events},expected={row.expected_events}")
    return missing


def append_ledger(row: MatrixRow, status: str, eval_result: dict[str, Any], telemetry: dict[str, Any], notes: str) -> None:
    delta_1 = eval_result.get("delta_1", {}) or {}
    mae = delta_1.get("abs_error")
    with LEDGER.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                row.line,
                "ipc",
                row.row_id,
                row.package,
                row.condition or "",
                row.rounds,
                row.density,
                status,
                str(row.raw_dir.relative_to(REPO_ROOT)),
                str(row.committed_dir.relative_to(REPO_ROOT)),
                eval_result.get("score", ""),
                eval_result.get("max_score", ""),
                "" if mae is None else mae,
                eval_result.get("parse_errors", ""),
                int(telemetry.get("tokens_in", 0)) + int(telemetry.get("tokens_out", 0)),
                telemetry.get("cost_usd_est", ""),
                "",
                utc_now(),
                notes,
            ]
        )


def row_plan(row: MatrixRow, matrix: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    return {
        "line": row.line,
        "row_id": row.row_id,
        "package": row.package,
        "condition": row.condition,
        "rounds": row.rounds,
        "density": row.density,
        "expected_events": row.expected_events,
        "input_file": str(row.input_file.relative_to(REPO_ROOT)),
        "raw_output_dir": str(row.raw_dir.relative_to(REPO_ROOT)),
        "committed_output_dir": str(row.committed_dir.relative_to(REPO_ROOT)),
        "command": build_command(row, matrix, args),
    }


def plan_output_path(args: argparse.Namespace) -> Path:
    if args.smoke:
        return BENCH_ROOT / "evaluation" / "pre_smoke_plan.json"
    if args.all:
        return BENCH_ROOT / "evaluation" / "full_matrix_plan.json"
    for name in ["temporal", "line5", "s3"]:
        if getattr(args, name):
            return BENCH_ROOT / "evaluation" / f"{name}_plan.json"
    return BENCH_ROOT / "evaluation" / "last_dry_run_plan.json"


def run_one(row: MatrixRow, matrix: dict[str, Any], args: argparse.Namespace, env: dict[str, str]) -> dict[str, Any]:
    command = build_command(row, matrix, args)
    if row.raw_dir.exists():
        raw_root = REPO_ROOT / matrix["outputs"]["raw_root"]
        resolved_raw = row.raw_dir.resolve()
        resolved_root = raw_root.resolve()
        if resolved_raw == resolved_root or resolved_root not in resolved_raw.parents:
            raise RuntimeError(f"refusing to remove raw dir outside benchmark raw root: {resolved_raw}")
        shutil.rmtree(row.raw_dir)
    row.raw_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, cwd=str(REPO_ROOT), env=env, text=True, check=False)
    if completed.returncode != 0:
        append_ledger(row, "failed", {}, {}, f"headless_exit={completed.returncode}")
        raise RuntimeError(f"{row.row_id} failed with exit code {completed.returncode}")
    eval_result: dict[str, Any] = {}
    telemetry: dict[str, Any] = {}
    try:
        if matrix.get("eval_artifact") == "structured_answer_json":
            generate_structured_answer(row, matrix, env)
        eval_result = evaluate_row(row, matrix)
        telemetry = summarize_telemetry(row.raw_dir / "simulation_artifacts" / "llm_telemetry.jsonl")
        copy_committed_artifacts(row, eval_result, telemetry)
        missing_evidence = validate_committed_evidence(row)
        if missing_evidence:
            raise RuntimeError(f"missing required compact evidence: {', '.join(missing_evidence)}")
    except Exception as exc:
        if not telemetry:
            try:
                telemetry = summarize_telemetry(row.raw_dir / "simulation_artifacts" / "llm_telemetry.jsonl")
            except Exception:  # noqa: BLE001 - preserve original post-run failure
                telemetry = {}
        safe_error = str(exc).encode("ascii", "backslashreplace").decode("ascii")
        append_ledger(row, "failed_post_run", eval_result, telemetry, f"post_run_error={safe_error}")
        raise
    append_ledger(row, "completed", eval_result, telemetry, "compact_artifacts_copied")
    return {
        "row_id": row.row_id,
        "status": "completed",
        "score": eval_result.get("score"),
        "parse_errors": eval_result.get("parse_errors"),
        "committed_dir": str(row.committed_dir.relative_to(REPO_ROOT)),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan or run IPC tri-model multi-agent rows.")
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--temporal", action="store_true", help="Select temporal T0-T3 rows.")
    scope.add_argument("--line5", action="store_true", help="Select Line 5 depth rows.")
    scope.add_argument("--s3", action="store_true", help="Select S3 injection rows.")
    scope.add_argument("--smoke", action="store_true", help="Select one tiny T0 smoke row.")
    scope.add_argument("--all", action="store_true", help="Select all rows.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true", help="Print/write the planned rows only.")
    action.add_argument("--execute", action="store_true", help="Execute selected rows and evaluate reports.")
    parser.add_argument("--rows", help="Comma-separated row ids.")
    parser.add_argument("--conditions", help="Comma-separated S3 condition ids.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--base-url", default="http://127.0.0.1:5001")
    parser.add_argument("--start-backend", action="store_true", help="Start and stop a correctly configured backend.")
    parser.add_argument("--backend-timeout", type=int, default=180)
    parser.add_argument("--poll-timeout", type=int, default=3600)
    parser.add_argument("--accept-language", default="es")
    parser.add_argument("--smoke-rounds", type=int, default=2)
    parser.add_argument("--write-plan", action="store_true", help="Write evaluation/pre_smoke_plan.json.")
    parser.add_argument(
        "--no-wait-after-run",
        dest="no_wait_after_run",
        action="store_true",
        default=True,
        help="Pass --no-wait-after-run to headless. Default true for autonomous rows.",
    )
    parser.add_argument(
        "--wait-after-run",
        dest="no_wait_after_run",
        action="store_false",
        help="Do not pass --no-wait-after-run.",
    )
    args = parser.parse_args(argv)
    if args.all:
        args.temporal = True
        args.line5 = True
        args.s3 = True
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    matrix = read_yaml(MATRIX_PATH)
    rows = make_rows(matrix, args)
    plan = {
        "generated_at": utc_now(),
        "matrix": str(MATRIX_PATH.relative_to(REPO_ROOT)),
        "selected_rows": len(rows),
        "env_plan": env_plan(matrix),
        "rows": [row_plan(row, matrix, args) for row in rows],
    }
    if args.write_plan or args.dry_run:
        write_json(plan_output_path(args), plan)
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("selected_rows=0")
        return 0

    env = build_env(matrix)
    summaries: list[dict[str, Any]] = []
    backend = None
    if args.start_backend:
        if backend_reachable(args.base_url):
            raise RuntimeError(f"{args.base_url} is already reachable; stop it before --start-backend")
        backend = start_backend(env)
        wait_backend(args.base_url, args.backend_timeout)
    try:
        for row in rows:
            summaries.append(run_one(row, matrix, args, env))
    finally:
        if backend is not None:
            stop_backend_process_tree(backend)
    write_json(BENCH_ROOT / "evaluation" / "last_execution_summary.json", summaries)
    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
