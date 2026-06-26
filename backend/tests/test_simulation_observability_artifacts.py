import json

from app.services.simulation_manager import SimulationManager


def test_write_deduplication_summary_persists_ui_ready_metrics(tmp_path, monkeypatch):
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(tmp_path / "simulations"))
    manager = SimulationManager()

    path = manager._write_deduplication_summary(
        simulation_id="sim_dedup",
        threshold=0.85,
        before_entities=10,
        after_entities=7,
        status="completed",
        warnings=[],
    )

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["simulation_id"] == "sim_dedup"
    assert data["threshold"] == 0.85
    assert data["before_entities"] == 10
    assert data["after_entities"] == 7
    assert data["removed_entities"] == 3
    assert data["reduction_pct"] == 30.0
    assert data["status"] == "completed"


def test_compile_wiki_artifacts_creates_wiki_files(tmp_path, monkeypatch):
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(tmp_path / "simulations"))
    manager = SimulationManager()

    result = manager._compile_wiki_artifacts(
        simulation_id="sim_wiki",
        case_metadata={"name": "Observability test"},
        documents=[{"name": "seed.md", "path": "/tmp/seed.md", "size": 123}],
        events=[
            {
                "actions": [
                    {
                        "agent_id": 1,
                        "agent_name": "Analyst A",
                        "round_num": 1,
                        "content": "The model should inspect evidence.",
                    }
                ],
                "round_num": 1,
                "timestamp": "2026-06-24T12:00:00",
            }
        ],
        retrieved_memories=[
            {
                "facts": ["Analyst A referenced the seed evidence."],
                "nodes": [{"uuid": "n1", "name": "Seed Evidence", "labels": ["Document"], "summary": "Input evidence"}],
            }
        ],
    )

    sim_dir = tmp_path / "simulations" / "sim_wiki"
    assert result["success"] is True
    assert (sim_dir / "wiki" / "index.md").is_file()
    assert (sim_dir / "wiki" / "agents.md").is_file()
    assert (sim_dir / "wiki_compile_log.jsonl").is_file()
    assert (sim_dir / "wiki_context.md").is_file()
