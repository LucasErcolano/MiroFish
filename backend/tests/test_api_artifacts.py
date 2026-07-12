import atexit
import json
from pathlib import Path

import pytest

from app import create_app
from app.config import Config
import app.api.simulation as simulation_api


@pytest.fixture()
def client(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    runs_dir = tmp_path / "runs"
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(upload_dir))
    monkeypatch.setattr(simulation_api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(simulation_api, "RUNS_ROOT", runs_dir)
    app = create_app()
    app.config.update(TESTING=True)
    try:
        atexit.unregister(simulation_api.SimulationRunner.cleanup_all_simulations)
    except ValueError:
        pass
    return app.test_client()


def _sim_dir(tmp_path: Path, simulation_id: str) -> Path:
    return tmp_path / "uploads" / "simulations" / simulation_id


def test_artifacts_manifest_returns_available_artifacts(client, tmp_path):
    simulation_id = "sim_test_123"
    sim_dir = _sim_dir(tmp_path, simulation_id)
    (sim_dir / "wiki").mkdir(parents=True)
    (sim_dir / "wiki" / "index.md").write_text("# Index", encoding="utf-8")
    (sim_dir / "llm_telemetry.jsonl").write_text("{}\n", encoding="utf-8")
    (sim_dir / "model_routing_audit.jsonl").write_text("{}\n", encoding="utf-8")
    (sim_dir / "deep_search_result.txt").write_text("Research trace", encoding="utf-8")
    (sim_dir / "deduplication_summary.json").write_text(
        json.dumps({"before_entities": 10, "after_entities": 7}),
        encoding="utf-8",
    )

    response = client.get(f"/api/simulation/{simulation_id}/artifacts")

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["wiki"] is True
    assert body["telemetry"] is True
    assert body["audit"] is True
    assert body["deep_search"] is True
    assert body["deduplication"] is True
    assert body["paths"]["deep_search"].endswith("deep_search_result.txt")
    assert body["paths"]["deduplication"].endswith("deduplication_summary.json")
    assert body["fusion_verdicts"] == []


def test_wiki_tree_and_page_endpoint(client, tmp_path):
    simulation_id = "sim_wiki"
    wiki_dir = _sim_dir(tmp_path, simulation_id) / "wiki"
    (wiki_dir / "entities").mkdir(parents=True)
    (wiki_dir / "claims").mkdir()
    (wiki_dir / "index.md").write_text("# Overview", encoding="utf-8")
    (wiki_dir / "entities" / "agent_1.md").write_text("# Agent 1", encoding="utf-8")
    (wiki_dir / "claims" / "claim_1.md").write_text("# Claim 1", encoding="utf-8")
    (wiki_dir / "wiki_meta.json").write_text('{"updated_at":"2026-06-20"}', encoding="utf-8")

    tree = client.get(f"/api/simulation/{simulation_id}/wiki").get_json()
    assert tree["success"] is True
    paths = {page["path"] for page in tree["pages"]}
    assert {"index.md", "entities/agent_1.md", "claims/claim_1.md", "wiki_meta.json"} <= paths

    page = client.get(f"/api/simulation/{simulation_id}/wiki/page?path=entities/agent_1.md")
    assert page.status_code == 200
    assert page.get_json()["content"] == "# Agent 1"


def test_wiki_page_rejects_path_traversal(client, tmp_path):
    simulation_id = "sim_wiki"
    (_sim_dir(tmp_path, simulation_id) / "wiki").mkdir(parents=True)

    response = client.get(f"/api/simulation/{simulation_id}/wiki/page?path=../../../../etc/passwd")

    assert response.status_code == 400


def test_telemetry_endpoint_aggregates_jsonl(client, tmp_path):
    simulation_id = "sim_telemetry"
    sim_dir = _sim_dir(tmp_path, simulation_id)
    sim_dir.mkdir(parents=True)
    records = [
        {
            "model": "model-a",
            "provider": "openai",
            "tokens_in": 10,
            "tokens_out": 5,
            "latency_ms": 100,
            "cost_usd_est": 0.01,
            "output_valid_json": True,
            "error": None,
        },
        {
            "model": "model-a",
            "provider": "openai",
            "tokens_in": 20,
            "tokens_out": 10,
            "latency_ms": 300,
            "cost_usd_est": 0.02,
            "output_valid_json": False,
            "error": None,
        },
        {
            "model": "model-b",
            "provider": "local",
            "tokens_in": 1,
            "tokens_out": 2,
            "latency_ms": 50,
            "cost_usd_est": 0,
            "error": "boom",
        },
    ]
    (sim_dir / "llm_telemetry.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    response = client.get(f"/api/simulation/{simulation_id}/telemetry")

    assert response.status_code == 200
    body = response.get_json()
    assert body["records_count"] == 3
    assert body["totals"]["calls"] == 3
    assert body["totals"]["errors"] == 1
    assert body["totals"]["parse_errors"] == 1
    assert body["totals"]["cost_estimation_status"] == "estimated"
    assert body["totals"]["usage_unavailable_calls"] == 0
    model_a = next(row for row in body["per_model"] if row["model"] == "model-a")
    assert model_a["calls"] == 2
    assert model_a["tokens_in"] == 30
    assert model_a["latency_p50_ms"] == 100.0
    assert model_a["latency_p95_ms"] == 300.0
    assert model_a["cost_estimation_status"] == "estimated"


def test_telemetry_endpoint_marks_unknown_cost_and_rate_limits(client, tmp_path):
    simulation_id = "sim_unknown_cost"
    sim_dir = _sim_dir(tmp_path, simulation_id)
    sim_dir.mkdir(parents=True)
    records = [
        {
            "model": "google/gemma-3-27b-it",
            "provider": "openrouter",
            "tokens_in": 1000,
            "tokens_out": 100,
            "latency_ms": 120,
            "cost_usd_est": 0,
            "error": None,
            "leak_flags": ["cost_unknown_model"],
        },
        {
            "model": "google/gemma-3-27b-it",
            "provider": "openrouter",
            "tokens_in": 0,
            "tokens_out": 0,
            "latency_ms": 75,
            "cost_usd_est": 0,
            "error": "RateLimitError: 429 Too Many Requests",
            "leak_flags": ["cost_unknown_model", "usage_unavailable"],
        },
    ]
    (sim_dir / "llm_telemetry.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    response = client.get(f"/api/simulation/{simulation_id}/telemetry")

    assert response.status_code == 200
    body = response.get_json()
    assert body["totals"]["cost_usd_est"] == 0
    assert body["totals"]["cost_unknown_model_calls"] == 2
    assert body["totals"]["usage_unavailable_calls"] == 1
    assert body["totals"]["rate_limited_calls"] == 1
    assert body["totals"]["cost_estimation_status"] == "unknown"
    model = body["per_model"][0]
    assert model["cost_estimation_status"] == "unknown"
    assert model["leak_flags"] == ["cost_unknown_model", "usage_unavailable"]


def test_routing_audit_endpoint_returns_jsonl_records(client, tmp_path):
    simulation_id = "sim_routing"
    sim_dir = _sim_dir(tmp_path, simulation_id)
    sim_dir.mkdir(parents=True)
    (sim_dir / "model_routing_audit.jsonl").write_text(
        json.dumps({"agent_id": 1, "role": "Analyst", "model": "model-a", "source": "by_role"}) + "\n",
        encoding="utf-8",
    )

    response = client.get(f"/api/simulation/{simulation_id}/routing-audit")

    assert response.status_code == 200
    body = response.get_json()
    assert body["records_count"] == 1
    assert body["records"][0]["source"] == "by_role"


def test_deduplication_endpoint_returns_summary(client, tmp_path):
    simulation_id = "sim_dedup"
    sim_dir = _sim_dir(tmp_path, simulation_id)
    sim_dir.mkdir(parents=True)
    summary = {
        "simulation_id": simulation_id,
        "status": "completed",
        "threshold": 0.85,
        "before_entities": 10,
        "after_entities": 7,
        "removed_entities": 3,
        "reduction_pct": 30.0,
    }
    (sim_dir / "deduplication_summary.json").write_text(json.dumps(summary), encoding="utf-8")

    response = client.get(f"/api/simulation/{simulation_id}/deduplication")

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["available"] is True
    assert body["summary"]["removed_entities"] == 3


def test_deduplication_endpoint_returns_empty_state_when_missing(client, tmp_path):
    simulation_id = "sim_no_dedup"
    _sim_dir(tmp_path, simulation_id).mkdir(parents=True)

    response = client.get(f"/api/simulation/{simulation_id}/deduplication")

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["available"] is False
    assert body["summary"] is None


def test_deep_search_endpoint_returns_trace(client, tmp_path):
    simulation_id = "sim_deep_search"
    sim_dir = _sim_dir(tmp_path, simulation_id)
    sim_dir.mkdir(parents=True)
    (sim_dir / "deep_search_result.txt").write_text("Research trace", encoding="utf-8")

    response = client.get(f"/api/simulation/{simulation_id}/deep-search")

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["available"] is True
    assert body["content"] == "Research trace"


def test_fusion_verdicts_list_and_fetch(client, tmp_path):
    simulation_id = "sim_fusion"
    verdict_dir = tmp_path / "runs" / "headless" / "fusion_001"
    verdict_dir.mkdir(parents=True)
    verdict = {
        "simulation_id": simulation_id,
        "judge": {"model": "judge-model"},
        "outcome": {"winner": "panel-a"},
    }
    (verdict_dir / "verdict_raw.json").write_text(json.dumps(verdict), encoding="utf-8")

    listing = client.get(f"/api/simulation/{simulation_id}/fusion-verdicts").get_json()
    assert listing["success"] is True
    assert len(listing["verdicts"]) == 1

    path = listing["verdicts"][0]["path"]
    response = client.get(f"/api/simulation/{simulation_id}/fusion-verdict", query_string={"path": path})
    assert response.status_code == 200
    assert response.get_json()["data"]["simulation_id"] == simulation_id


def test_start_simulation_forwards_reddit_model_map_and_no_wait(client, monkeypatch):
    captured = {}

    class FakeState:
        status = simulation_api.SimulationStatus.READY
        project_id = "project-1"
        graph_id = "graph-1"

    class FakeManager:
        def get_simulation(self, simulation_id):
            return FakeState()

        def _save_simulation_state(self, state):
            captured["saved_status"] = state.status

    class FakeRunState:
        def to_dict(self):
            return {"runner_status": "running", "process_pid": 123}

    def fake_start_simulation(**kwargs):
        captured.update(kwargs)
        return FakeRunState()

    monkeypatch.setattr(simulation_api, "SimulationManager", FakeManager)
    monkeypatch.setattr(
        simulation_api.SimulationRunner,
        "start_simulation",
        staticmethod(fake_start_simulation),
    )

    response = client.post(
        "/api/simulation/start",
        json={
            "simulation_id": "sim-model-map",
            "platform": "reddit",
            "max_rounds": 3,
            "no_wait": True,
            "model_map_path": "model_map.yaml",
        },
    )

    assert response.status_code == 200
    assert captured["simulation_id"] == "sim-model-map"
    assert captured["platform"] == "reddit"
    assert captured["max_rounds"] == 3
    assert captured["no_wait"] is True
    assert captured["model_map_path"] == "model_map.yaml"
    assert captured["saved_status"] == simulation_api.SimulationStatus.RUNNING


def test_start_simulation_rejects_model_map_for_non_reddit(client):
    response = client.post(
        "/api/simulation/start",
        json={
            "simulation_id": "sim-model-map",
            "platform": "parallel",
            "model_map_path": "model_map.yaml",
        },
    )

    assert response.status_code == 400
    assert "only supported for reddit" in response.get_json()["error"]
