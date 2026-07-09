import json

from app.api import simulation as simulation_api
from app.config import Config


def test_paused_prepared_simulation_can_be_reused(tmp_path, monkeypatch):
    sim_id = "sim_paused_reusable"
    sim_dir = tmp_path / sim_id
    sim_dir.mkdir()

    (sim_dir / "state.json").write_text(
        json.dumps(
            {
                "simulation_id": sim_id,
                "project_id": "proj_test",
                "graph_id": "graph_test",
                "status": "paused",
                "config_generated": True,
                "entities_count": 1,
                "profiles_count": 1,
                "entity_types": ["NationalTeam"],
            }
        ),
        encoding="utf-8",
    )
    (sim_dir / "simulation_config.json").write_text("{}", encoding="utf-8")
    (sim_dir / "reddit_profiles.json").write_text("[]", encoding="utf-8")
    (sim_dir / "twitter_profiles.csv").write_text("agent_id,name\n0,test\n", encoding="utf-8")

    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))

    is_prepared, info = simulation_api._check_simulation_prepared(sim_id)

    assert is_prepared is True
    assert info["status"] == "paused"
