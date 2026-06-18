#!/usr/bin/env python3
"""Run the Copa America temporal matrix against a live MiroFish backend."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml


CASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = CASE_DIR.parent.parent
SIM_UPLOADS_DIR = REPO_ROOT / "backend" / "uploads" / "simulations"
REPORT_UPLOADS_DIR = REPO_ROOT / "backend" / "uploads" / "reports"


def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def json_request(base_url: str, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.loads(response.read().decode("utf-8"))


def multipart_request(base_url: str, path: str, fields: Dict[str, str], file_paths: Iterable[Path]) -> Dict[str, Any]:
    boundary = f"----MiroFishBoundary{uuid.uuid4().hex}"
    body = bytearray()

    for key, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    for file_path in file_paths:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        body.extend(
            f'Content-Disposition: form-data; name="files"; filename="{file_path.name}"\r\n'.encode("utf-8")
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(file_path.read_bytes())
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = urllib.request.Request(url, data=bytes(body), headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.loads(response.read().decode("utf-8"))


def poll_task(base_url: str, task_path: str, *, success_statuses: set[str], timeout_seconds: int = 3600) -> Dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_payload = None
    while time.time() < deadline:
        payload = json_request(base_url, "GET", task_path)
        if not payload.get("success", False):
            raise RuntimeError(f"Task polling failed: {payload}")
        data = payload["data"]
        last_payload = data
        status = str(data.get("status", "")).lower()
        if status in success_statuses:
            return data
        if status in {"failed", "error"}:
            raise RuntimeError(f"Task failed: {json.dumps(data, ensure_ascii=False)}")
        time.sleep(5)
    raise TimeoutError(f"Timed out while polling {task_path}: {last_payload}")


def poll_prepare(base_url: str, task_id: str, simulation_id: str, timeout_seconds: int = 3600) -> Dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_payload = None
    while time.time() < deadline:
        payload = json_request(
            base_url,
            "POST",
            "/api/simulation/prepare/status",
            {"task_id": task_id, "simulation_id": simulation_id},
        )
        if not payload.get("success", False):
            raise RuntimeError(f"Prepare polling failed: {payload}")
        data = payload["data"]
        last_payload = data
        status = str(data.get("status", "")).lower()
        if status in {"ready", "completed"}:
            return data
        if status in {"failed", "error"}:
            raise RuntimeError(f"Prepare failed: {json.dumps(data, ensure_ascii=False)}")
        time.sleep(5)
    raise TimeoutError(f"Timed out while polling prepare task {task_id}: {last_payload}")


def poll_run_status(base_url: str, simulation_id: str, timeout_seconds: int = 7200) -> Dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_payload = None
    while time.time() < deadline:
        payload = json_request(base_url, "GET", f"/api/simulation/{simulation_id}/run-status")
        if not payload.get("success", False):
            raise RuntimeError(f"Run-status polling failed: {payload}")
        data = payload["data"]
        last_payload = data
        status = str(data.get("runner_status", "")).lower()
        if status in {"completed", "stopped"}:
            return data
        if status in {"failed"}:
            raise RuntimeError(f"Simulation failed: {json.dumps(data, ensure_ascii=False)}")
        time.sleep(10)
    raise TimeoutError(f"Timed out while polling run status for {simulation_id}: {last_payload}")


def poll_report(base_url: str, task_id: str, simulation_id: str, timeout_seconds: int = 3600) -> Dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_payload = None
    while time.time() < deadline:
        payload = json_request(
            base_url,
            "POST",
            "/api/report/generate/status",
            {"task_id": task_id, "simulation_id": simulation_id},
        )
        if not payload.get("success", False):
            raise RuntimeError(f"Report polling failed: {payload}")
        data = payload["data"]
        last_payload = data
        status = str(data.get("status", "")).lower()
        if status in {"completed"}:
            return data
        if status in {"failed", "error"}:
            raise RuntimeError(f"Report failed: {json.dumps(data, ensure_ascii=False)}")
        time.sleep(5)
    raise TimeoutError(f"Timed out while polling report task {task_id}: {last_payload}")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    digest = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_variant(base_url: str, config: Dict[str, Any], variant_id: str, force: bool) -> Path:
    experiment = config["experiment_metadata"]
    temporal_packages = {item["id"]: item for item in config["temporal_packages"]}
    run_entry = next((item for item in config["run_matrix"] if item["id"] == variant_id), None)
    if not run_entry:
        raise ValueError(f"Variant not found: {variant_id}")

    package = temporal_packages[run_entry["package"]]
    seed_path = CASE_DIR / run_entry["input_file"]
    question_path = CASE_DIR / experiment["question_file"]
    system_constraints_path = CASE_DIR / experiment["system_constraints_file"]
    output_dir = CASE_DIR / "output" / variant_id

    if force and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    question_text = question_path.read_text(encoding="utf-8").strip()
    system_constraints_text = system_constraints_path.read_text(encoding="utf-8").strip()
    seed_text = seed_path.read_text(encoding="utf-8").strip()

    project_metadata = {
        "case_id": experiment["case_id"],
        "source_case": experiment["source_case"],
        "issue_source": experiment["issue_source"],
        "line_focus": experiment["line_focus"],
        "original_user_prompt": question_text,
        "normalized_task_prompt": question_text,
        "task_objective": "Predict the Argentina vs Colombia Copa America 2024 final winner under the allowed pre-cutoff evidence.",
        "system_constraints_text": system_constraints_text,
        "cutoff_date": package["max_document_date"],
        "temporal_package": package["id"],
        "source_ids": package.get("sources", []),
        "model": config["model_policy"]["provider_id"],
        "model_label": config["model_policy"]["label"],
        "seed": config["fixed_simulation_config"]["seed"],
        "rounds": run_entry["rounds"],
        "density": run_entry["density"],
        "excluded_files": [
            {
                "path": item,
                "reason": "excluded_by_case_config",
                "sha256": sha256_file(CASE_DIR / item) if (CASE_DIR / item).exists() else None,
            }
            for item in config.get("do_not_upload", [])
        ],
        "input_file": seed_path.name,
        "question_file": question_path.name,
        "system_constraints_file": system_constraints_path.name,
    }

    upload_response = multipart_request(
        base_url,
        "/api/graph/ontology/generate",
        fields={
            "project_name": variant_id,
            "simulation_requirement": question_text,
            "additional_context": system_constraints_text,
            "project_metadata_json": json.dumps(project_metadata, ensure_ascii=False),
        },
        file_paths=[seed_path],
    )
    if not upload_response.get("success", False):
        raise RuntimeError(f"Ontology generation failed: {upload_response}")
    project_id = upload_response["data"]["project_id"]

    build_response = json_request(
        base_url,
        "POST",
        "/api/graph/build",
        {
            "project_id": project_id,
            "graph_name": variant_id,
            "force": force,
        },
    )
    if not build_response.get("success", False):
        raise RuntimeError(f"Graph build start failed: {build_response}")
    build_task_id = build_response["data"]["task_id"]
    build_task = poll_task(
        base_url,
        f"/api/graph/task/{build_task_id}",
        success_statuses={"completed"},
        timeout_seconds=7200,
    )
    graph_id = build_task.get("result", {}).get("graph_id") or build_task.get("graph_id")

    create_sim_response = json_request(
        base_url,
        "POST",
        "/api/simulation/create",
        {
            "project_id": project_id,
            "graph_id": graph_id,
            "enable_twitter": True,
            "enable_reddit": True,
        },
    )
    if not create_sim_response.get("success", False):
        raise RuntimeError(f"Simulation creation failed: {create_sim_response}")
    simulation_id = create_sim_response["data"]["simulation_id"]

    prepare_response = json_request(
        base_url,
        "POST",
        "/api/simulation/prepare",
        {
            "simulation_id": simulation_id,
            "force_regenerate": force,
            "use_llm_for_profiles": True,
            "parallel_profile_count": 5,
        },
    )
    if not prepare_response.get("success", False):
        raise RuntimeError(f"Simulation prepare start failed: {prepare_response}")
    prepare_task_id = prepare_response["data"]["task_id"]
    poll_prepare(base_url, prepare_task_id, simulation_id, timeout_seconds=7200)

    start_response = json_request(
        base_url,
        "POST",
        "/api/simulation/start",
        {
            "simulation_id": simulation_id,
            "platform": "parallel",
            "max_rounds": run_entry["rounds"],
            "enable_graph_memory_update": False,
            "force": force,
        },
    )
    if not start_response.get("success", False):
        raise RuntimeError(f"Simulation start failed: {start_response}")
    run_state = poll_run_status(base_url, simulation_id, timeout_seconds=7200)

    report_response = json_request(
        base_url,
        "POST",
        "/api/report/generate",
        {
            "simulation_id": simulation_id,
            "force_regenerate": force,
            "output_mode": config["fixed_simulation_config"].get("output_mode", "structured_json"),
            "schema_id": config["fixed_simulation_config"].get("schema_id", "copa_america_winner_v1"),
            "report_context": {
                "case_id": experiment["case_id"],
                "temporal_package": package["id"],
                "cutoff_date": package["max_document_date"],
                "source_ids": package.get("sources", []),
                "primary_query": question_text,
                "system_constraints_text": system_constraints_text,
                "source_packet_file": seed_path.name,
                "source_packet_text": seed_text,
            },
        },
    )
    if not report_response.get("success", False):
        raise RuntimeError(f"Structured report start failed: {report_response}")
    report_task_id = report_response["data"].get("task_id")
    report_id = report_response["data"].get("report_id")
    if report_task_id:
        report_task = poll_report(base_url, report_task_id, simulation_id, timeout_seconds=3600)
        report_id = report_task.get("result", {}).get("report_id") or report_id

    report_payload = json_request(base_url, "GET", f"/api/report/{report_id}")
    if not report_payload.get("success", False):
        raise RuntimeError(f"Fetch report failed: {report_payload}")
    report_data = report_payload["data"]

    simulation_dir = SIM_UPLOADS_DIR / simulation_id
    report_dir = REPORT_UPLOADS_DIR / report_id
    structured_answer_path = report_dir / "structured_answer.json"
    eval_result = evaluate_structured_answer(structured_answer_path, variant_id)

    copy_if_exists(simulation_dir / "worldbuilding_trace.json", output_dir / "worldbuilding_trace.json")
    copy_if_exists(simulation_dir / "simulation_config.json", output_dir / "simulation_config.json")
    copy_if_exists(simulation_dir / "state.json", output_dir / "state.json")
    copy_if_exists(simulation_dir / "run_state.json", output_dir / "run_state.json")
    copy_tree_if_exists(simulation_dir / "worldbuilding_artifacts", output_dir / "worldbuilding_artifacts")
    copy_if_exists(report_dir / "full_report.md", output_dir / "report.md")
    copy_if_exists(report_dir / "meta.json", output_dir / "report_meta.json")
    copy_if_exists(report_dir / "structured_answer.json", output_dir / "structured_answer.json")
    write_json(output_dir / "eval_result.json", eval_result)

    simulation_config = read_json(simulation_dir / "simulation_config.json")
    run_notes = build_run_notes(
        variant_id=variant_id,
        package=package,
        project_id=project_id,
        graph_id=graph_id,
        simulation_id=simulation_id,
        report_id=report_id,
        run_state=run_state,
        report_data=report_data,
        simulation_config=simulation_config,
        eval_result=eval_result,
    )
    (output_dir / "run_notes.md").write_text(run_notes, encoding="utf-8")

    return output_dir


def copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def copy_tree_if_exists(src: Path, dst: Path) -> None:
    if src.exists() and src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)


def evaluate_structured_answer(structured_answer_path: Path, variant_id: str) -> Dict[str, Any]:
    command = [
        sys.executable,
        str(CASE_DIR / "eval_objective.py"),
        "--structured-answer",
        str(structured_answer_path),
        "--variant",
        variant_id,
        "--model-policy",
        "gemma_temporal_probe",
    ]
    import subprocess

    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def build_run_notes(
    *,
    variant_id: str,
    package: Dict[str, Any],
    project_id: str,
    graph_id: str,
    simulation_id: str,
    report_id: str,
    run_state: Dict[str, Any],
    report_data: Dict[str, Any],
    simulation_config: Dict[str, Any],
    eval_result: Dict[str, Any],
) -> str:
    lines = [
        f"# Run Notes - {variant_id}",
        "",
        f"- temporal_package: {package['id']}",
        f"- cutoff_date: {package['max_document_date']}",
        f"- project_id: {project_id}",
        f"- graph_id: {graph_id}",
        f"- simulation_id: {simulation_id}",
        f"- report_id: {report_id}",
        f"- llm_model: {simulation_config.get('llm_model')}",
        f"- runner_status: {run_state.get('runner_status')}",
        f"- total_rounds: {run_state.get('total_rounds')}",
        f"- current_round: {run_state.get('current_round')}",
        f"- output_mode: {report_data.get('output_mode')}",
        f"- schema_id: {report_data.get('schema_id')}",
        f"- eval_score: {eval_result.get('score')}/{eval_result.get('max_score')}",
        f"- parse_errors: {eval_result.get('parse_errors')}",
        "",
        "## Sources",
        *[f"- {source_id}" for source_id in package.get("sources", [])],
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5001")
    parser.add_argument("--variant", help="Run only one variant from config_matrix.yaml")
    parser.add_argument("--force", action="store_true", help="Delete local output folder and force backend regeneration")
    args = parser.parse_args()

    config = load_yaml(CASE_DIR / "config_matrix.yaml")
    variants = [args.variant] if args.variant else [item["id"] for item in config["run_matrix"]]

    for variant_id in variants:
        output_dir = run_variant(args.base_url, config, variant_id, args.force)
        print(f"[done] {variant_id} -> {output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
