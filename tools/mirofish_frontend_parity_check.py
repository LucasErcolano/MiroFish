#!/usr/bin/env python3
"""Static parity guard for MiroFish frontend-replay runner.

Run this periodically after frontend changes. It does not replace an occasional
real browser smoke test; it catches the common failure mode where Vue API wrapper
endpoints drift away from the headless runner's replay contract.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Set

CRITICAL_ENDPOINTS = [
    "/api/graph/ontology/generate",
    "/api/graph/build",
    "/api/graph/task/",
    "/api/graph/project/",
    "/api/graph/data/",
    "/api/simulation/create",
    "/api/simulation/prepare",
    "/api/simulation/prepare/status",
    "/api/simulation/start",
    "/api/simulation/stop",
    "/api/simulation/close-env",
    "/api/simulation/env-status",
    "/api/report/generate",
    "/api/report/generate/status",
]

RUNNER_REQUIRED_ENDPOINTS = [
    "/api/graph/ontology/generate",
    "/api/graph/build",
    "/api/graph/task/",
    "/api/graph/project/",
    "/api/graph/data/",
    "/api/simulation/create",
    "/api/simulation/prepare",
    "/api/simulation/prepare/status",
    "/api/simulation/start",
    "/api/simulation/{simulation_id}/run-status",
    "/api/simulation/{simulation_id}/run-status/detail",
    "/api/simulation/{simulation_id}/agent-stats",
    "/api/simulation/{simulation_id}/actions",
    "/api/simulation/{simulation_id}/timeline",
    "/api/report/generate",
    "/api/report/generate/status",
    "/api/report/{report_id}",
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _normalize_dynamic_endpoints(text: str) -> str:
    text = re.sub(r"`(/api/[^`$]*)\$\{simulationId\}([^`]*)`", r"'\1{simulation_id}\2'", text)
    text = re.sub(r"`(/api/[^`$]*)\$\{graphId\}([^`]*)`", r"'\1{graph_id}\2'", text)
    text = re.sub(r"`(/api/[^`$]*)\$\{taskId\}([^`]*)`", r"'\1{task_id}\2'", text)
    text = re.sub(r"`(/api/[^`$]*)\$\{reportId\}([^`]*)`", r"'\1{report_id}\2'", text)
    return text


def extract_api_endpoints_from_text(text: str) -> Set[str]:
    normalized = _normalize_dynamic_endpoints(text)
    endpoints = set(re.findall(r"['\"](/api/[^'\"]+)['\"]", normalized))
    # Also record prefix-style endpoints for dynamic paths.
    for endpoint in list(endpoints):
        for marker in ["{simulation_id}", "{graph_id}", "{task_id}", "{report_id}"]:
            if marker in endpoint:
                endpoints.add(endpoint.split(marker)[0])
    return endpoints


def _endpoint_present(endpoint: str, endpoints: Set[str], raw_text: str) -> bool:
    if endpoint in endpoints:
        return True
    if endpoint.endswith("/"):
        return endpoint in raw_text
    return endpoint in raw_text


def check_frontend_replay_parity(repo_root: Path) -> Dict[str, object]:
    repo_root = Path(repo_root)
    frontend_files = [
        repo_root / "frontend/src/api/graph.js",
        repo_root / "frontend/src/api/simulation.js",
        repo_root / "frontend/src/api/report.js",
    ]
    frontend_text = "\n".join(_read_text(p) for p in frontend_files)
    runner_path = repo_root / "tools/mirofish_headless.py"
    runner_text = _read_text(runner_path)

    frontend_endpoints = extract_api_endpoints_from_text(frontend_text)
    runner_endpoints = extract_api_endpoints_from_text(runner_text)

    missing_from_frontend = [
        endpoint for endpoint in CRITICAL_ENDPOINTS
        if not _endpoint_present(endpoint, frontend_endpoints, frontend_text)
    ]
    missing_from_runner = [
        endpoint for endpoint in RUNNER_REQUIRED_ENDPOINTS
        if not _endpoint_present(endpoint, runner_endpoints, runner_text)
    ]

    warnings: List[str] = []
    if "service.get(`/api/report/generate/status`" in frontend_text:
        warnings.append(
            "frontend/src/api/report.js declares getReportStatus as GET, but backend route is POST; runner uses backend POST to avoid a 405."
        )

    return {
        "ok": not missing_from_frontend and not missing_from_runner,
        "missing_from_frontend": missing_from_frontend,
        "missing_from_runner": missing_from_runner,
        "warnings": warnings,
        "frontend_endpoints": sorted(frontend_endpoints),
        "runner_endpoints": sorted(runner_endpoints),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check headless runner vs frontend API wrapper parity.")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = check_frontend_replay_parity(Path(args.repo_root))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("OK" if result["ok"] else "DRIFT DETECTED")
        if result["missing_from_frontend"]:
            print("Missing from frontend:", result["missing_from_frontend"])
        if result["missing_from_runner"]:
            print("Missing from runner:", result["missing_from_runner"])
        result_warnings = result.get("warnings", [])
        if isinstance(result_warnings, list):
            for warning in result_warnings:
                print("Warning:", warning)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
