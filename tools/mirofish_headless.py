#!/usr/bin/env python3
"""MiroFish frontend-replay headless runner.

This is intentionally not a direct/adapted LLM runner. It replays the same
backend API contract used by the Vue frontend and records a sanitized trace for
benchmark provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

import yaml

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"
TERMINAL_TASK_STATUSES = {"completed", "failed", "cancelled", "error"}
TERMINAL_RUN_STATUSES = {"completed", "failed", "stopped"}
SECRET_KEY_RE = re.compile(r"(api[_-]?key|token|secret|password|authorization|backup)", re.I)
GEMINI_KEY_RE = re.compile(("AI" + "za") + r"[0-9A-Za-z_\-]{10,}")


class MiroFishRunnerError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed


def seconds_since_timestamp(value: Any) -> Optional[float]:
    parsed = parse_iso_timestamp(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        return max(0.0, time.time() - parsed.timestamp())
    return max(0.0, datetime.now(timezone.utc).timestamp() - parsed.timestamp())


def parse_key_list(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [part.strip() for part in re.split(r"[;,\n]", raw) if part.strip()]


def sanitize_for_artifact(value: Any, key_name: str = "") -> Any:
    """Recursively redact API keys/tokens before writing artifacts."""
    if isinstance(value, dict):
        return {
            k: sanitize_for_artifact(v, str(k))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [sanitize_for_artifact(v, key_name) for v in value]
    if isinstance(value, tuple):
        return [sanitize_for_artifact(v, key_name) for v in value]
    if isinstance(value, str):
        if SECRET_KEY_RE.search(key_name) or GEMINI_KEY_RE.search(value):
            return "<redacted>"
        return GEMINI_KEY_RE.sub("<redacted>", value)
    return value


def build_backend_env(
    base_env: Optional[Dict[str, str]] = None,
    gemini_api_keys: Optional[List[str]] = None,
    model: str = DEFAULT_GEMINI_MODEL,
) -> Dict[str, str]:
    """Return an env suitable for launching MiroFish backend with Gemini.

    Keys are returned in-memory only. Do not serialize this dict directly.
    """
    env = dict(base_env or os.environ)
    keys = list(gemini_api_keys or [])
    if keys:
        env["LLM_API_KEY"] = keys[0]
        env["OPENAI_API_KEY"] = keys[0]
        # run_parallel_simulation.py supports this acceleration key.
        if len(keys) > 1:
            env["LLM_BOOST_API_KEY"] = keys[1]
    env["LLM_BASE_URL"] = GEMINI_OPENAI_BASE_URL
    env["LLM_MODEL_NAME"] = model
    # Keep Graphiti aligned unless explicitly overridden by caller's env.
    env.setdefault("GRAPHITI_LLM_BASE_URL", GEMINI_OPENAI_BASE_URL)
    env.setdefault("GRAPHITI_LLM_MODEL", model)
    if keys:
        env.setdefault("GRAPHITI_LLM_API_KEY", keys[0])
    return env


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitize_for_artifact(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def apply_injection_plan_to_simulation_config(
    repo_root: Path,
    simulation_id: str,
    injection_plan: Path,
    condition: str,
) -> Dict[str, Any]:
    """Apply a condition's scheduled Reddit events to simulation_config.json."""
    injection_plan = Path(injection_plan)
    plan = yaml.safe_load(injection_plan.read_text(encoding="utf-8"))
    conditions = plan.get("conditions", {})
    if condition not in conditions:
        raise MiroFishRunnerError(f"unknown injection condition {condition!r}; available={sorted(conditions)}")

    sim_config_path = repo_root / "backend" / "uploads" / "simulations" / simulation_id / "simulation_config.json"
    if not sim_config_path.exists():
        raise MiroFishRunnerError(f"simulation config not found for injection: {sim_config_path}")

    plan_dir = injection_plan.parent
    scheduled_events = []
    for index, event in enumerate(conditions[condition].get("injections", [])):
        if event.get("target_platform", "reddit") != "reddit":
            raise MiroFishRunnerError(f"condition {condition} contains non-Reddit injection: {event}")
        if event.get("action", "create_post") != "create_post":
            raise MiroFishRunnerError(f"condition {condition} contains unsupported action: {event}")

        event_payload = dict(event)
        event_payload["id"] = str(event_payload.get("id") or f"{condition}-{index}")
        event_payload["condition"] = condition
        file_name = event_payload.get("file")
        if file_name:
            event_payload["content"] = (plan_dir / file_name).read_text(encoding="utf-8").strip()
        scheduled_events.append(event_payload)

    config = json.loads(sim_config_path.read_text(encoding="utf-8"))
    event_config = config.setdefault("event_config", {})
    event_config["scheduled_events"] = scheduled_events
    config["s2_condition"] = condition
    config["s2_injection_plan"] = str(injection_plan)
    write_json(sim_config_path, config)
    return {
        "condition": condition,
        "scheduled_events_count": len(scheduled_events),
        "simulation_config_path": str(sim_config_path),
        "scheduled_event_ids": [event["id"] for event in scheduled_events],
    }


def count_jsonl_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())


def summarize_reddit_db(repo_root: Path, simulation_id: str) -> Dict[str, Any]:
    db_path = repo_root / "backend" / "uploads" / "simulations" / simulation_id / "reddit_simulation.db"
    summary: Dict[str, Any] = {"path": str(db_path), "exists": db_path.exists()}
    if not db_path.exists():
        return summary

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        for table in ["post", "comment", "trace", "user"]:
            try:
                summary[f"{table}_count"] = cur.execute(f"select count(*) from {table}").fetchone()[0]
            except sqlite3.Error:
                summary[f"{table}_count"] = None
        try:
            summary["scheduled_signal_post_count"] = cur.execute(
                "select count(*) from post where content like '%Signal Document%'"
            ).fetchone()[0]
            summary["scheduled_noise_post_count"] = cur.execute(
                "select count(*) from post where content like '%Noise Document%'"
            ).fetchone()[0]
            summary["scheduled_counter_signal_post_count"] = cur.execute(
                "select count(*) from post where content like '%Counter-Signal Document%'"
            ).fetchone()[0]
            summary["scheduled_injection_post_count"] = cur.execute(
                "select count(*) from post where content like '# %Document%'"
            ).fetchone()[0]
        except sqlite3.Error:
            summary["scheduled_signal_post_count"] = None
            summary["scheduled_noise_post_count"] = None
            summary["scheduled_counter_signal_post_count"] = None
            summary["scheduled_injection_post_count"] = None
    finally:
        conn.close()
    return summary


@dataclass
class TraceEntry:
    ts: str
    method: str
    path: str
    status_code: Optional[int]
    request: Dict[str, Any] = field(default_factory=dict)
    response: Optional[Any] = None
    error: Optional[str] = None


class APIClient:
    def __init__(
        self,
        base_url: str,
        trace_path: Path,
        timeout_seconds: int = 300,
        accept_language: str = "zh",
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.trace_path = trace_path
        self.timeout_seconds = timeout_seconds
        self.accept_language = accept_language
        self.trace: List[Dict[str, Any]] = []

    def _record(self, entry: TraceEntry) -> None:
        self.trace.append(sanitize_for_artifact(entry.__dict__))
        write_json(self.trace_path, self.trace)

    def request_json(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry: bool = False,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> Dict[str, Any]:
        attempts = max_retries if retry else 1
        last_error: Optional[Exception] = None
        for attempt in range(attempts):
            try:
                return self._request_json_once(method, path, payload=payload, params=params)
            except Exception as exc:  # noqa: BLE001 - logged and retried like frontend
                last_error = exc
                if attempt == attempts - 1:
                    raise
                time.sleep(retry_delay * (2 ** attempt))
        raise MiroFishRunnerError(str(last_error))

    def _request_json_once(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = urljoin(self.base_url, path.lstrip("/"))
        if params:
            url = f"{url}?{urlencode(params)}"
        body = None
        headers = {"Accept-Language": self.accept_language}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = Request(url, data=body, headers=headers, method=method.upper())
        entry = TraceEntry(
            ts=utc_now(),
            method=method.upper(),
            path=path if not params else f"{path}?{urlencode(params)}",
            status_code=None,
            request={"json": payload or {}, "params": params or {}},
        )
        try:
            with urlopen(req, timeout=self.timeout_seconds) as resp:  # noqa: S310 - localhost/user-configured API
                raw = resp.read().decode("utf-8")
                data = json.loads(raw) if raw else {}
                entry.status_code = resp.status
                entry.response = data
        except HTTPError as exc:
            entry.status_code = exc.code
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                entry.response = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                entry.response = raw
            entry.error = str(exc)
            self._record(entry)
            raise MiroFishRunnerError(f"HTTP {exc.code} {path}: {entry.response}") from exc
        except URLError as exc:
            entry.error = str(exc)
            self._record(entry)
            raise MiroFishRunnerError(f"Request failed {path}: {exc}") from exc

        self._record(entry)
        if isinstance(data, dict) and data.get("success") is False:
            raise MiroFishRunnerError(f"API error {path}: {data.get('error') or data.get('message')}")
        return data

    def post_multipart(
        self,
        path: str,
        fields: Dict[str, str],
        files: List[Path],
        retry: bool = True,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        attempts = max_retries if retry else 1
        for attempt in range(attempts):
            try:
                return self._post_multipart_once(path, fields, files)
            except Exception:
                if attempt == attempts - 1:
                    raise
                time.sleep(1.0 * (2 ** attempt))
        raise MiroFishRunnerError("multipart request failed")

    def _post_multipart_once(self, path: str, fields: Dict[str, str], files: List[Path]) -> Dict[str, Any]:
        boundary = f"----MiroFishHeadless{uuid.uuid4().hex}"
        body_parts: List[bytes] = []
        for name, value in fields.items():
            body_parts.append(f"--{boundary}\r\n".encode())
            body_parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
            body_parts.append(str(value).encode("utf-8"))
            body_parts.append(b"\r\n")
        for file_path in files:
            filename = file_path.name
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            body_parts.append(f"--{boundary}\r\n".encode())
            body_parts.append(
                f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'.encode()
            )
            body_parts.append(f"Content-Type: {content_type}\r\n\r\n".encode())
            body_parts.append(file_path.read_bytes())
            body_parts.append(b"\r\n")
        body_parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(body_parts)

        headers = {
            "Accept-Language": self.accept_language,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        url = urljoin(self.base_url, path.lstrip("/"))
        req = Request(url, data=body, headers=headers, method="POST")
        entry = TraceEntry(
            ts=utc_now(),
            method="POST",
            path=path,
            status_code=None,
            request={
                "multipart_fields": fields,
                "files": [{"name": p.name, "sha256": file_sha256(p), "bytes": p.stat().st_size} for p in files],
            },
        )
        try:
            with urlopen(req, timeout=self.timeout_seconds) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8")
                data = json.loads(raw) if raw else {}
                entry.status_code = resp.status
                entry.response = data
        except HTTPError as exc:
            entry.status_code = exc.code
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                entry.response = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                entry.response = raw
            entry.error = str(exc)
            self._record(entry)
            raise MiroFishRunnerError(f"HTTP {exc.code} {path}: {entry.response}") from exc
        self._record(entry)
        if isinstance(data, dict) and data.get("success") is False:
            raise MiroFishRunnerError(f"API error {path}: {data.get('error') or data.get('message')}")
        return data


@dataclass
class MiroFishHeadlessRunner:
    base_url: str = "http://localhost:5001"
    output_dir: Path = Path("runs/headless")
    repo_root: Path = Path(__file__).resolve().parents[1]
    poll_interval: float = 2.0
    timeout_seconds: int = 300
    accept_language: str = "zh"

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        self.repo_root = Path(self.repo_root)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.client = APIClient(
            base_url=self.base_url,
            trace_path=self.output_dir / "request_trace.json",
            timeout_seconds=self.timeout_seconds,
            accept_language=self.accept_language,
        )

    def run_full_flow(
        self,
        files: List[Path],
        simulation_requirement: str,
        project_name: str = "MiroFish Headless Benchmark",
        max_rounds: Optional[int] = None,
        platform: str = "parallel",
        enable_graph_memory_update: bool = True,
        force: bool = True,
        use_llm_for_profiles: bool = True,
        parallel_profile_count: int = 5,
        generate_report: bool = True,
        poll_timeout_seconds: int = 60 * 60,
        injection_plan: Optional[Path] = None,
        condition: Optional[str] = None,
        no_wait: bool = False,
        model_map_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        files = [Path(p) for p in files]
        for p in files:
            if not p.exists():
                raise FileNotFoundError(p)

        started_at = utc_now()
        run_config = {
            "base_url": self.base_url,
            "flow_provenance": "frontend_replay_backend_api",
            "project_name": project_name,
            "files": [{"path": str(p), "sha256": file_sha256(p), "bytes": p.stat().st_size} for p in files],
            "simulation_requirement": simulation_requirement,
            "platform": platform,
            "max_rounds": max_rounds,
            "enable_graph_memory_update": enable_graph_memory_update,
            "force": force,
            "use_llm_for_profiles": use_llm_for_profiles,
            "parallel_profile_count": parallel_profile_count,
            "generate_report": generate_report,
            "injection_plan": str(injection_plan) if injection_plan else None,
            "condition": condition,
            "no_wait": no_wait,
            "model_map_path": str(model_map_path) if model_map_path else None,
            "started_at": started_at,
        }
        write_json(self.output_dir / "run_config.json", run_config)

        try:
            ontology = self.client.post_multipart(
                "/api/graph/ontology/generate",
                fields={
                    "simulation_requirement": simulation_requirement,
                    "project_name": project_name,
                },
                files=files,
                retry=True,
            )
            project_id = ontology.get("data", {}).get("project_id")
            if not project_id:
                raise MiroFishRunnerError("ontology/generate did not return project_id")

            graph_build = self.client.request_json(
                "POST",
                "/api/graph/build",
                {"project_id": project_id},
                retry=True,
            )
            graph_task_id = graph_build.get("data", {}).get("task_id")
            graph_task = self._wait_graph_task(graph_task_id, poll_timeout_seconds, project_id=project_id)
            project = self.client.request_json("GET", f"/api/graph/project/{project_id}")
            graph_id = project.get("data", {}).get("graph_id")
            if not graph_id:
                raise MiroFishRunnerError("graph build completed but project has no graph_id")
            # Frontend polls graph data while building; capture final graph too.
            graph_data_resp = self.client.request_json("GET", f"/api/graph/data/{graph_id}")
            graph_data_summary = self._summarize_graph_payload(graph_data_resp)

            create_payload = {
                "project_id": project_id,
                "graph_id": graph_id,
                "enable_twitter": True,
                "enable_reddit": True,
            }
            sim_create = self.client.request_json("POST", "/api/simulation/create", create_payload, retry=True)
            simulation_id = sim_create.get("data", {}).get("simulation_id")
            if not simulation_id:
                raise MiroFishRunnerError("simulation/create did not return simulation_id")

            prepare_payload = {
                "simulation_id": simulation_id,
                "use_llm_for_profiles": use_llm_for_profiles,
                "parallel_profile_count": parallel_profile_count,
            }
            prepare = self.client.request_json("POST", "/api/simulation/prepare", prepare_payload, retry=True)
            self._wait_prepare(simulation_id, prepare.get("data", {}).get("task_id"), poll_timeout_seconds)

            injection_metadata = None
            if injection_plan or condition:
                if not injection_plan or not condition:
                    raise MiroFishRunnerError("--injection-plan and --condition must be provided together")
                injection_metadata = apply_injection_plan_to_simulation_config(
                    repo_root=self.repo_root,
                    simulation_id=simulation_id,
                    injection_plan=Path(injection_plan),
                    condition=condition,
                )
                write_json(self.output_dir / "injection_applied.json", injection_metadata)

            start_payload: Dict[str, Any] = {
                "simulation_id": simulation_id,
                "platform": platform,
                "force": force,
                "enable_graph_memory_update": enable_graph_memory_update,
                "no_wait": no_wait,
            }
            if max_rounds:
                start_payload["max_rounds"] = max_rounds
            if model_map_path:
                start_payload["model_map_path"] = str(model_map_path)
            self.client.request_json("POST", "/api/simulation/start", start_payload, retry=True)
            final_run = self._wait_run(simulation_id, poll_timeout_seconds)
            self._capture_simulation_artifacts(simulation_id)

            report_id = None
            if generate_report:
                report_resp = self.client.request_json(
                    "POST",
                    "/api/report/generate",
                    {"simulation_id": simulation_id, "force_regenerate": True},
                    retry=True,
                )
                report_id = report_resp.get("data", {}).get("report_id")
                report_task_id = report_resp.get("data", {}).get("task_id")
                report_status = self._wait_report(simulation_id, report_task_id, poll_timeout_seconds)
                report_id = report_id or report_status.get("report_id")
                if report_id:
                    report_payload = self.client.request_json("GET", f"/api/report/{report_id}")
                    self._write_report_artifacts(report_payload)

            completed_rounds = self._extract_completed_rounds(final_run)
            manifest = {
                "status": "completed" if final_run.get("runner_status") == "completed" else final_run.get("runner_status"),
                "flow_provenance": "frontend_replay_backend_api",
                "is_model_output": True,
                "is_real_mirofish_system": bool(completed_rounds > 0 and final_run.get("runner_status") == "completed"),
                "real_mirofish_flow_invoked": True,
                "project_id": project_id,
                "graph_id": graph_id,
                "graph_build_task": graph_task,
                "graph_data_summary": graph_data_summary,
                "simulation_id": simulation_id,
                "report_id": report_id,
                "injection": injection_metadata,
                "scheduled_events_fired_count": count_jsonl_lines(
                    self.repo_root / "backend" / "uploads" / "simulations" / simulation_id / "scheduled_events_fired.jsonl"
                ),
                "reddit_db_summary": summarize_reddit_db(self.repo_root, simulation_id),
                "num_rounds_or_epochs_requested": max_rounds,
                "num_rounds_or_epochs": completed_rounds,
                "final_run_status": final_run,
                "started_at": started_at,
                "completed_at": utc_now(),
            }
            write_json(self.output_dir / "run_manifest.json", manifest)
            self._write_hashes()
            return manifest
        except Exception as exc:  # noqa: BLE001 - preserve artifacts for BLOCKED runs
            blocked = {
                "status": "BLOCKED",
                "reason": str(exc),
                "is_model_output": False,
                "is_real_mirofish_system": False,
                "real_mirofish_flow_invoked": True,
                "failure_stage": "frontend_replay_backend_api",
                "num_rounds_or_epochs_requested": max_rounds,
                "num_rounds_or_epochs": 0,
                "num_agents_configured": 0,
                "num_agents": 0,
                "started_at": started_at,
                "completed_at": utc_now(),
            }
            write_json(self.output_dir / "run_manifest.json", blocked)
            (self.output_dir / "mirofish_report_raw.md").write_text(
                "BLOCKED: no real MiroFish report was produced by this run.\n",
                encoding="utf-8",
            )
            write_json(self.output_dir / "verdict_raw.json", blocked)
            self._write_hashes()
            raise

    def run_existing_simulation(
        self,
        simulation_id: str,
        max_rounds: Optional[int] = None,
        platform: str = "reddit",
        enable_graph_memory_update: bool = False,
        force: bool = True,
        generate_report: bool = False,
        poll_timeout_seconds: int = 60 * 60,
        injection_plan: Optional[Path] = None,
        condition: Optional[str] = None,
        no_wait: bool = False,
        model_map_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        started_at = utc_now()
        run_config = {
            "base_url": self.base_url,
            "flow_provenance": "existing_prepared_simulation_backend_api",
            "simulation_id": simulation_id,
            "platform": platform,
            "max_rounds": max_rounds,
            "enable_graph_memory_update": enable_graph_memory_update,
            "force": force,
            "generate_report": generate_report,
            "injection_plan": str(injection_plan) if injection_plan else None,
            "condition": condition,
            "no_wait": no_wait,
            "model_map_path": str(model_map_path) if model_map_path else None,
            "started_at": started_at,
        }
        write_json(self.output_dir / "run_config.json", run_config)

        try:
            simulation = self.client.request_json("GET", f"/api/simulation/{simulation_id}", retry=True)
            simulation_data = simulation.get("data", {})
            injection_metadata = None
            if injection_plan or condition:
                if not injection_plan or not condition:
                    raise MiroFishRunnerError("--injection-plan and --condition must be provided together")
                injection_metadata = apply_injection_plan_to_simulation_config(
                    repo_root=self.repo_root,
                    simulation_id=simulation_id,
                    injection_plan=Path(injection_plan),
                    condition=condition,
                )
                write_json(self.output_dir / "injection_applied.json", injection_metadata)

            start_payload: Dict[str, Any] = {
                "simulation_id": simulation_id,
                "platform": platform,
                "force": force,
                "enable_graph_memory_update": enable_graph_memory_update,
                "no_wait": no_wait,
            }
            if max_rounds:
                start_payload["max_rounds"] = max_rounds
            if model_map_path:
                start_payload["model_map_path"] = str(model_map_path)
            self.client.request_json("POST", "/api/simulation/start", start_payload, retry=True)
            final_run = self._wait_run(simulation_id, poll_timeout_seconds)
            self._capture_simulation_artifacts(simulation_id)

            report_id = None
            if generate_report:
                report_resp = self.client.request_json(
                    "POST",
                    "/api/report/generate",
                    {"simulation_id": simulation_id, "force_regenerate": True},
                    retry=True,
                )
                report_id = report_resp.get("data", {}).get("report_id")
                report_task_id = report_resp.get("data", {}).get("task_id")
                report_status = self._wait_report(simulation_id, report_task_id, poll_timeout_seconds)
                report_id = report_id or report_status.get("report_id")
                if report_id:
                    report_payload = self.client.request_json("GET", f"/api/report/{report_id}")
                    self._write_report_artifacts(report_payload)

            sim_dir = self.repo_root / "backend" / "uploads" / "simulations" / simulation_id
            scheduled_log = sim_dir / "scheduled_events_fired.jsonl"
            reddit_summary = summarize_reddit_db(self.repo_root, simulation_id)
            completed_rounds = self._extract_completed_rounds(final_run)
            scheduled_events_fired_count = count_jsonl_lines(scheduled_log)
            manifest = {
                "status": "completed" if final_run.get("runner_status") == "completed" else final_run.get("runner_status"),
                "flow_provenance": "existing_prepared_simulation_backend_api",
                "is_model_output": True,
                "is_real_mirofish_system": bool(final_run.get("runner_status") == "completed"),
                "real_mirofish_flow_invoked": True,
                "project_id": simulation_data.get("project_id"),
                "graph_id": simulation_data.get("graph_id"),
                "simulation_id": simulation_id,
                "report_id": report_id,
                "injection": injection_metadata,
                "scheduled_events_fired_count": scheduled_events_fired_count,
                "reddit_db_summary": reddit_summary,
                "num_rounds_or_epochs_requested": max_rounds,
                "num_rounds_or_epochs": completed_rounds,
                "final_run_status": final_run,
                "started_at": started_at,
                "completed_at": utc_now(),
            }
            write_json(self.output_dir / "run_manifest.json", manifest)
            self._write_hashes()
            return manifest
        except Exception as exc:  # noqa: BLE001 - preserve artifacts for BLOCKED runs
            blocked = {
                "status": "BLOCKED",
                "reason": str(exc),
                "is_model_output": False,
                "is_real_mirofish_system": False,
                "real_mirofish_flow_invoked": True,
                "failure_stage": "existing_prepared_simulation_backend_api",
                "num_rounds_or_epochs_requested": max_rounds,
                "num_rounds_or_epochs": 0,
                "started_at": started_at,
                "completed_at": utc_now(),
            }
            write_json(self.output_dir / "run_manifest.json", blocked)
            (self.output_dir / "mirofish_report_raw.md").write_text(
                "BLOCKED: no real MiroFish report was produced by this run.\n",
                encoding="utf-8",
            )
            write_json(self.output_dir / "verdict_raw.json", blocked)
            self._capture_simulation_artifacts(simulation_id)
            self._write_hashes()
            raise

    def _summarize_graph_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        nodes = data.get("nodes") or []
        edges = data.get("edges") or []
        return {
            "node_count": int(data.get("node_count") or len(nodes) or 0),
            "edge_count": int(data.get("edge_count") or len(edges) or 0),
        }

    def _try_accept_stale_graph_task(self, task: Dict[str, Any], project_id: str) -> Optional[Dict[str, Any]]:
        stale_after = int(os.environ.get("MIROFISH_ACCEPT_PARTIAL_GRAPH_AFTER_SECONDS", "0") or "0")
        if stale_after <= 0:
            return None
        stale_seconds = seconds_since_timestamp(task.get("updated_at"))
        if stale_seconds is None or stale_seconds < stale_after:
            return None

        project = self.client.request_json("GET", f"/api/graph/project/{project_id}")
        graph_id = project.get("data", {}).get("graph_id")
        if not graph_id:
            return None

        graph_data = self.client.request_json("GET", f"/api/graph/data/{graph_id}")
        summary = self._summarize_graph_payload(graph_data)
        min_nodes = int(os.environ.get("MIROFISH_ACCEPT_PARTIAL_GRAPH_MIN_NODES", "5") or "5")
        min_edges = int(os.environ.get("MIROFISH_ACCEPT_PARTIAL_GRAPH_MIN_EDGES", "5") or "5")
        if summary["node_count"] < min_nodes or summary["edge_count"] < min_edges:
            return None

        accepted = dict(task)
        accepted["status"] = "completed"
        accepted["accepted_partial_graph"] = True
        accepted["partial_graph_reason"] = (
            f"graph task stale for {int(stale_seconds)}s but graph has "
            f"{summary['node_count']} nodes and {summary['edge_count']} edges"
        )
        accepted["graph_id"] = graph_id
        accepted["graph_data_summary"] = summary
        return accepted

    def _wait_graph_task(self, task_id: Optional[str], timeout: int, project_id: Optional[str] = None) -> Dict[str, Any]:
        if not task_id:
            raise MiroFishRunnerError("graph/build did not return task_id")
        deadline = time.time() + timeout
        last_partial_probe = 0.0
        while time.time() < deadline:
            resp = self.client.request_json("GET", f"/api/graph/task/{task_id}")
            task = resp.get("data", {})
            status = task.get("status")
            if status in TERMINAL_TASK_STATUSES:
                if status != "completed":
                    raise MiroFishRunnerError(f"graph task ended with status {status}: {task}")
                return task
            if project_id and time.time() - last_partial_probe >= 30:
                last_partial_probe = time.time()
                accepted = self._try_accept_stale_graph_task(task, project_id)
                if accepted:
                    return accepted
            time.sleep(self.poll_interval)
        raise TimeoutError("graph task polling timed out")

    def _wait_prepare(self, simulation_id: str, task_id: Optional[str], timeout: int) -> Dict[str, Any]:
        deadline = time.time() + timeout
        stale_after = int(os.environ.get("MIROFISH_PREPARE_STALE_AFTER_SECONDS", "0") or "0")
        while time.time() < deadline:
            payload = {"simulation_id": simulation_id}
            if task_id:
                payload["task_id"] = task_id
            resp = self.client.request_json("POST", "/api/simulation/prepare/status", payload)
            task = resp.get("data", {})
            status = task.get("status")
            if status in {"ready", "completed"}:
                return task
            if status in {"failed", "cancelled", "error"}:
                raise MiroFishRunnerError(f"prepare ended with status {status}: {task}")
            if stale_after > 0:
                stale_seconds = seconds_since_timestamp(task.get("updated_at"))
                if stale_seconds is not None and stale_seconds >= stale_after:
                    raise TimeoutError(
                        f"prepare task stale for {int(stale_seconds)}s; "
                        f"status={status}; message={task.get('message')!r}"
                    )
            time.sleep(self.poll_interval)
        raise TimeoutError("prepare polling timed out")

    def _wait_run(self, simulation_id: str, timeout: int) -> Dict[str, Any]:
        deadline = time.time() + timeout
        last: Dict[str, Any] = {}
        while time.time() < deadline:
            resp = self.client.request_json("GET", f"/api/simulation/{simulation_id}/run-status")
            last = resp.get("data", {})
            # Match frontend detail polling cadence by capturing details each loop.
            try:
                self.client.request_json("GET", f"/api/simulation/{simulation_id}/run-status/detail")
            except Exception:
                pass
            status = last.get("runner_status")
            if status in TERMINAL_RUN_STATUSES:
                if status == "failed":
                    raise MiroFishRunnerError(f"simulation failed: {last}")
                return last
            time.sleep(self.poll_interval)
        raise TimeoutError(f"simulation run polling timed out; last={last}")

    def _wait_report(self, simulation_id: str, task_id: Optional[str], timeout: int) -> Dict[str, Any]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            payload = {"simulation_id": simulation_id}
            if task_id:
                payload["task_id"] = task_id
            # Backend route is POST even though one frontend wrapper currently says GET.
            resp = self.client.request_json("POST", "/api/report/generate/status", payload)
            task = resp.get("data", {})
            status = task.get("status")
            if status == "completed":
                return task
            if status in {"failed", "cancelled", "error"}:
                raise MiroFishRunnerError(f"report ended with status {status}: {task}")
            time.sleep(self.poll_interval)
        raise TimeoutError("report polling timed out")

    def _capture_simulation_artifacts(self, simulation_id: str) -> None:
        for path in [
            f"/api/simulation/{simulation_id}/agent-stats",
            f"/api/simulation/{simulation_id}/actions",
            f"/api/simulation/{simulation_id}/timeline",
        ]:
            try:
                self.client.request_json("GET", path)
            except Exception:
                # These are post-run evidence endpoints; keep run valid if optional capture fails.
                pass
        sim_dir = self.repo_root / "backend" / "uploads" / "simulations" / simulation_id
        artifact_dir = self.output_dir / "simulation_artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        for name in [
            "simulation_config.json",
            "state.json",
            "run_state.json",
            "simulation.log",
            "scheduled_events_fired.jsonl",
            "model_routing_audit.jsonl",
            "llm_telemetry.jsonl",
            "reddit_profiles.json",
            "reddit_simulation.db",
        ]:
            src = sim_dir / name
            if src.exists() and src.is_file():
                shutil.copy2(src, artifact_dir / name)
        self._capture_experimental_memory_artifacts(simulation_id, artifact_dir)

    def _capture_experimental_memory_artifacts(self, simulation_id: str, artifact_dir: Path) -> None:
        memory_dir = self.repo_root / "backend" / "data" / "simulations" / simulation_id
        core_memory = memory_dir / "core_memory.json"
        chroma_dir = memory_dir / "chroma_db"
        memory_artifact_dir = artifact_dir / "experimental_memory"
        memory_artifact_dir.mkdir(parents=True, exist_ok=True)

        chroma_files = [path for path in chroma_dir.rglob("*") if path.is_file()] if chroma_dir.exists() else []
        evidence = {
            "simulation_id": simulation_id,
            "source_dir": str(memory_dir),
            "memory_dir_exists": memory_dir.exists(),
            "core_memory_exists": core_memory.exists(),
            "chroma_db_exists": chroma_dir.exists(),
            "chroma_file_count": len(chroma_files),
            "chroma_total_bytes": sum(path.stat().st_size for path in chroma_files),
            "copied_files": [],
        }
        if core_memory.exists() and core_memory.is_file():
            dst = memory_artifact_dir / "core_memory.json"
            shutil.copy2(core_memory, dst)
            evidence["copied_files"].append(str(dst.relative_to(artifact_dir)))
        legacy_memory = memory_dir / "experimental_memory.json"
        if legacy_memory.exists() and legacy_memory.is_file():
            dst = memory_artifact_dir / "experimental_memory.json"
            shutil.copy2(legacy_memory, dst)
            evidence["copied_files"].append(str(dst.relative_to(artifact_dir)))
        write_json(artifact_dir / "experimental_memory_evidence.json", evidence)

    def _write_report_artifacts(self, report_payload: Dict[str, Any]) -> None:
        data = report_payload.get("data", {}) if isinstance(report_payload, dict) else {}
        if not isinstance(data, dict):
            return
        write_json(self.output_dir / "report_meta.json", data)
        markdown = (
            data.get("markdown_content")
            or data.get("content")
            or data.get("report_markdown")
            or data.get("report")
        )
        if isinstance(markdown, str) and markdown.strip():
            (self.output_dir / "mirofish_report_raw.md").write_text(markdown, encoding="utf-8")

    @staticmethod
    def _extract_completed_rounds(run_status: Dict[str, Any]) -> int:
        candidates = [
            run_status.get("current_round"),
            run_status.get("twitter_current_round"),
            run_status.get("reddit_current_round"),
        ]
        ints = []
        for value in candidates:
            try:
                if value is not None:
                    ints.append(int(value))
            except (TypeError, ValueError):
                pass
        return max(ints) if ints else 0

    def _write_hashes(self) -> None:
        hashes: Dict[str, str] = {}
        for path in sorted(self.output_dir.rglob("*")):
            if path.is_file() and path.name != "run_hashes.json":
                hashes[str(path.relative_to(self.output_dir))] = file_sha256(path)
        write_json(self.output_dir / "run_hashes.json", hashes)


def start_backend_process(repo_root: Path, env: Dict[str, str]) -> subprocess.Popen:
    uv_exe = "uv.exe" if os.name == "nt" else "uv"
    return subprocess.Popen(  # noqa: S603 - explicit local project command
        [uv_exe, "run", "--frozen", "--python", "3.11", "python", "run.py"],
        cwd=repo_root / "backend",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def wait_for_backend(base_url: str, timeout: int = 60) -> None:
    client = APIClient(base_url, Path(os.devnull), timeout_seconds=5)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            client.request_json("GET", "/api/graph/project/list")
            return
        except Exception:
            time.sleep(1)
    raise TimeoutError(f"backend did not become ready at {base_url}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Replay the MiroFish frontend backend-API flow headlessly.")
    parser.add_argument("--base-url", default="http://localhost:5001")
    parser.add_argument("--file", action="append", dest="files", help="Seed PDF/MD/TXT file. Repeat for multiple files.")
    parser.add_argument("--requirement", default=None, help="Simulation requirement, same as frontend input.")
    parser.add_argument("--existing-simulation-id", default=None, help="Run an already prepared simulation, skipping ontology/graph/prepare.")
    parser.add_argument("--project-name", default="MiroFish Headless Benchmark")
    parser.add_argument("--max-rounds", type=int, default=None)
    parser.add_argument("--platform", default="parallel", choices=["twitter", "reddit", "parallel"])
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--poll-timeout", type=int, default=60 * 60)
    parser.add_argument("--no-report", action="store_true")
    parser.add_argument("--no-graph-memory-update", action="store_true")
    parser.add_argument("--no-force", action="store_true")
    parser.add_argument("--injection-plan", default=None, help="YAML injection plan for scheduled Reddit events.")
    parser.add_argument("--condition", default=None, help="Condition name from --injection-plan, e.g. signal-mid.")
    parser.add_argument("--no-wait-after-run", action="store_true", help="Pass --no-wait to the simulation process.")
    parser.add_argument("--model-map", default=None, help="Per-agent model routing YAML passed to reddit simulations.")
    parser.add_argument("--accept-language", default="zh")
    parser.add_argument("--start-backend", action="store_true", help="Start npm run backend with Gemini env before replaying.")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--gemini-model", default=os.environ.get("MIROFISH_GEMINI_MODEL", DEFAULT_GEMINI_MODEL))
    args = parser.parse_args(argv)

    out_dir = Path(args.output_dir) if args.output_dir else Path("runs/headless") / datetime.now().strftime("%Y%m%d-%H%M%S")
    backend_proc: Optional[subprocess.Popen] = None
    try:
        if args.start_backend:
            keys = parse_key_list(os.environ.get("MIROFISH_GEMINI_API_KEYS") or os.environ.get("LLM_API_KEYS") or os.environ.get("LLM_API_KEY"))
            env = build_backend_env(dict(os.environ), keys, model=args.gemini_model)
            # Persist only sanitized backend launch config.
            write_json(out_dir / "backend_env_sanitized.json", {
                "LLM_BASE_URL": env.get("LLM_BASE_URL"),
                "LLM_MODEL_NAME": env.get("LLM_MODEL_NAME"),
                "LLM_API_KEY": env.get("LLM_API_KEY"),
                "LLM_BOOST_API_KEY": env.get("LLM_BOOST_API_KEY"),
            })
            backend_proc = start_backend_process(Path(args.repo_root), env)
            wait_for_backend(args.base_url)

        runner = MiroFishHeadlessRunner(
            base_url=args.base_url,
            output_dir=out_dir,
            repo_root=Path(args.repo_root),
            poll_interval=args.poll_interval,
            accept_language=args.accept_language,
        )
        if args.existing_simulation_id:
            manifest = runner.run_existing_simulation(
                simulation_id=args.existing_simulation_id,
                max_rounds=args.max_rounds,
                platform=args.platform,
                enable_graph_memory_update=not args.no_graph_memory_update,
                force=not args.no_force,
                generate_report=not args.no_report,
                poll_timeout_seconds=args.poll_timeout,
                injection_plan=Path(args.injection_plan) if args.injection_plan else None,
                condition=args.condition,
                no_wait=args.no_wait_after_run,
                model_map_path=Path(args.model_map) if args.model_map else None,
            )
        else:
            if not args.files or not args.requirement:
                parser.error("--file and --requirement are required unless --existing-simulation-id is used")
            manifest = runner.run_full_flow(
                files=[Path(f) for f in args.files],
                simulation_requirement=args.requirement,
                project_name=args.project_name,
                max_rounds=args.max_rounds,
                platform=args.platform,
                enable_graph_memory_update=not args.no_graph_memory_update,
                force=not args.no_force,
                generate_report=not args.no_report,
                poll_timeout_seconds=args.poll_timeout,
                injection_plan=Path(args.injection_plan) if args.injection_plan else None,
                condition=args.condition,
                no_wait=args.no_wait_after_run,
                model_map_path=Path(args.model_map) if args.model_map else None,
            )
        print(json.dumps(sanitize_for_artifact(manifest), ensure_ascii=False, indent=2))
        print(f"Artifacts: {out_dir.resolve()}")
        return 0
    finally:
        if backend_proc is not None:
            backend_proc.terminate()
            try:
                backend_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                backend_proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
