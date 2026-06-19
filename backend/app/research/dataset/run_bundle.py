"""
Assemble a normalized prompt -> plan -> completion record from a MiroFish run's
on-disk artifacts. Pure stdlib; no app imports, so it runs anywhere.

Artifact layout (under ``backend/uploads/``):
- ``projects/<project_id>/project.json``        -> question / seed provenance
- ``simulations/<sim_id>/simulation_config.json`` -> planning (model-generated)
- ``simulations/<sim_id>/run_state.json``         -> run-result metadata
- ``simulations/<sim_id>/{twitter,reddit}/actions.jsonl`` -> action counts
- ``reports/<report_id>/{meta.json,full_report.md,outline.json}`` -> result
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from typing import Optional

SCHEMA_VERSION = 1

# backend/app/research/dataset/run_bundle.py -> backend/uploads
DEFAULT_UPLOADS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads")
)

# Identifier keys we look for when resolving IDs from a headless run manifest.
_ID_KEYS = ("project_id", "simulation_id", "report_id", "graph_id", "run_id")


# --------------------------------------------------------------------------- #
# IO helpers
# --------------------------------------------------------------------------- #
def _read_json(path: Optional[str]):
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
    return None


def _read_text(path: Optional[str]) -> Optional[str]:
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None
    return None


def sha256_text(s: Optional[str]) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def sha256_file(path: Optional[str]) -> Optional[str]:
    if not path or not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _count_jsonl_lines(path: str) -> int:
    if not os.path.exists(path):
        return 0
    n = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def _find_id(obj, key: str):
    """Recursively search a dict/list for the first value of ``key``."""
    if isinstance(obj, dict):
        if obj.get(key) not in (None, ""):
            return obj[key]
        for v in obj.values():
            found = _find_id(v, key)
            if found not in (None, ""):
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_id(v, key)
            if found not in (None, ""):
                return found
    return None


def resolve_ids_from_run_dir(run_dir: str) -> dict:
    """Pull project/simulation/report/graph IDs from a headless run_manifest.json."""
    manifest = _read_json(os.path.join(run_dir, "run_manifest.json")) or {}
    return {k: _find_id(manifest, k) for k in _ID_KEYS}


# --------------------------------------------------------------------------- #
# Bundle assembly
# --------------------------------------------------------------------------- #
def _agent_config_summary(sim_cfg: dict) -> dict:
    agents = (sim_cfg or {}).get("agent_configs") or []
    stance = Counter(a.get("stance") for a in agents if a.get("stance"))
    etype = Counter(a.get("entity_type") for a in agents if a.get("entity_type"))
    return {
        "n_agents": len(agents),
        "stance_distribution": dict(stance),
        "entity_type_distribution": dict(etype),
    }


def _run_state_summary(run_state: dict, sim_dir: str) -> dict:
    rs = run_state or {}
    return {
        "runner_status": rs.get("runner_status"),
        "current_round": rs.get("current_round"),
        "total_rounds": rs.get("total_rounds"),
        "twitter_actions_count": rs.get("twitter_actions_count"),
        "reddit_actions_count": rs.get("reddit_actions_count"),
        "twitter_completed": rs.get("twitter_completed"),
        "reddit_completed": rs.get("reddit_completed"),
        "twitter_actions_logged": _count_jsonl_lines(os.path.join(sim_dir, "twitter", "actions.jsonl")),
        "reddit_actions_logged": _count_jsonl_lines(os.path.join(sim_dir, "reddit", "actions.jsonl")),
    }


def _seed_provenance(project: dict, project_dir: str, include_seed_text: bool) -> dict:
    proj = project or {}
    files = []
    for fmeta in proj.get("files") or []:
        path = fmeta.get("path")
        files.append({
            "filename": fmeta.get("filename"),
            "size": fmeta.get("size"),
            "sha256": sha256_file(path) if path else None,
        })
    seed = {
        "files": files,
        "total_text_length": proj.get("total_text_length"),
        "ontology": proj.get("ontology"),
    }
    if include_seed_text:
        seed["extracted_text"] = _read_text(os.path.join(project_dir, "extracted_text.txt"))
    return seed


def build_bundle(
    uploads_root: str = DEFAULT_UPLOADS,
    project_id: Optional[str] = None,
    simulation_id: Optional[str] = None,
    report_id: Optional[str] = None,
    run_dir: Optional[str] = None,
    include_seed_text: bool = False,
) -> dict:
    """Assemble the full run bundle. IDs may be given explicitly or via a headless run_dir."""
    if run_dir:
        ids = resolve_ids_from_run_dir(run_dir)
        project_id = project_id or ids.get("project_id")
        simulation_id = simulation_id or ids.get("simulation_id")
        report_id = report_id or ids.get("report_id")
        graph_id = ids.get("graph_id")
        run_id = ids.get("run_id") or os.path.basename(os.path.normpath(run_dir))
    else:
        graph_id = None
        run_id = None

    project_dir = os.path.join(uploads_root, "projects", project_id) if project_id else None
    sim_dir = os.path.join(uploads_root, "simulations", simulation_id) if simulation_id else None
    report_dir = os.path.join(uploads_root, "reports", report_id) if report_id else None

    project = _read_json(os.path.join(project_dir, "project.json")) if project_dir else None
    sim_cfg = _read_json(os.path.join(sim_dir, "simulation_config.json")) if sim_dir else None
    run_state = _read_json(os.path.join(sim_dir, "run_state.json")) if sim_dir else None
    report_meta = _read_json(os.path.join(report_dir, "meta.json")) if report_dir else None
    report_md = _read_text(os.path.join(report_dir, "full_report.md")) if report_dir else None
    outline = _read_json(os.path.join(report_dir, "outline.json")) if report_dir else None

    graph_id = graph_id or (sim_cfg or {}).get("graph_id") or (report_meta or {}).get("graph_id")
    question = (project or {}).get("simulation_requirement") or (report_meta or {}).get("simulation_requirement")
    reasoning = (sim_cfg or {}).get("generation_reasoning")

    content_hash = sha256_text("\n".join([
        question or "", reasoning or "", report_md or "",
    ]))
    bundle_id = sha256_text("|".join([str(simulation_id), str(report_id)]))[:16]

    return {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": bundle_id,
        "content_hash": content_hash,
        "ids": {
            "project_id": project_id,
            "simulation_id": simulation_id,
            "report_id": report_id,
            "graph_id": graph_id,
            "run_id": run_id,
        },
        "model": (sim_cfg or {}).get("llm_model"),
        "input": {
            "question": question,
            "seed": _seed_provenance(project, project_dir, include_seed_text) if project_dir else None,
        },
        "plan": {
            "reasoning": reasoning,
            "generated_at": (sim_cfg or {}).get("generated_at"),
            "time_config": (sim_cfg or {}).get("time_config"),
            "event_config": (sim_cfg or {}).get("event_config"),
            "agents": _agent_config_summary(sim_cfg) if sim_cfg else None,
            "report_outline": outline,
        },
        "result": {
            "report_markdown": report_md,
            "report_status": (report_meta or {}).get("status"),
            "report_created_at": (report_meta or {}).get("created_at"),
            "report_completed_at": (report_meta or {}).get("completed_at"),
            "run_state": _run_state_summary(run_state, sim_dir) if sim_dir else None,
        },
    }


def to_training_record(bundle: dict) -> dict:
    """Flatten a bundle into one JSONL training record: prompt -> plan -> completion."""
    return {
        "schema_version": bundle.get("schema_version", SCHEMA_VERSION),
        "bundle_id": bundle.get("bundle_id"),
        "content_hash": bundle.get("content_hash"),
        "ids": bundle.get("ids"),
        "model": bundle.get("model"),
        "prompt": bundle.get("input", {}).get("question"),
        "plan": bundle.get("plan"),
        "completion": bundle.get("result", {}).get("report_markdown"),
        "result_meta": {
            "report_status": bundle.get("result", {}).get("report_status"),
            "run_state": bundle.get("result", {}).get("run_state"),
        },
        "seed": bundle.get("input", {}).get("seed"),
    }


def write_bundle(bundle: dict, out_path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)
    return out_path


def append_to_dataset(record: dict, dataset_path: str) -> bool:
    """
    Append a training record to a JSONL dataset, deduping on ``content_hash``.
    Returns True if appended, False if a record with the same content_hash exists.
    """
    os.makedirs(os.path.dirname(os.path.abspath(dataset_path)), exist_ok=True)
    seen = set()
    if os.path.exists(dataset_path):
        with open(dataset_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    seen.add(json.loads(line).get("content_hash"))
                except json.JSONDecodeError:
                    continue
    if record.get("content_hash") in seen:
        return False
    with open(dataset_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return True
