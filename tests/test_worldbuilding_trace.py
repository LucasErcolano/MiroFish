import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import Config  # noqa: E402
from app.services.worldbuilding_trace import WorldbuildingTraceCapture  # noqa: E402


class DummyState:
    simulation_id = "sim_test"
    project_id = "proj_test"
    graph_id = "graph_test"
    enable_twitter = True
    enable_reddit = False

    def to_dict(self):
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "status": "ready",
            "config_generated": True,
            "entities_count": 1,
            "profiles_count": 1,
            "error": None,
        }


class DummyEntity:
    def to_dict(self):
        return {
            "uuid": "entity_1",
            "name": "Candidate A",
            "labels": ["Entity", "Candidate"],
            "summary": "A candidate",
            "attributes": {},
            "related_edges": [{"fact": "Candidate A competes in election"}],
            "related_nodes": [],
        }


class DummyFilteredEntities:
    entities = [DummyEntity()]
    entity_types = {"Candidate"}
    total_count = 3
    filtered_count = 1


class DummyProfile:
    def to_dict(self):
        return {
            "user_id": 1,
            "user_name": "candidate_a",
            "name": "Candidate A",
            "bio": "bio",
            "persona": "persona",
            "source_entity_uuid": "entity_1",
            "source_entity_type": "Candidate",
        }


class DummySimulationParams:
    def to_dict(self):
        return {
            "simulation_id": "sim_test",
            "project_id": "proj_test",
            "graph_id": "graph_test",
            "simulation_requirement": "predict the election",
            "agent_configs": [{"agent_id": 1, "entity_name": "Candidate A"}],
            "twitter_config": {"platform": "twitter"},
            "reddit_config": None,
            "generation_reasoning": "ok",
        }


class WorldbuildingTraceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_upload_folder = Config.UPLOAD_FOLDER
        self.old_enabled = Config.PLANNING_CAPTURE_ENABLED
        self.old_api_key = Config.LLM_API_KEY
        Config.UPLOAD_FOLDER = self.tmp.name
        Config.PLANNING_CAPTURE_ENABLED = True
        Config.LLM_API_KEY = "test-secret-key"

    def tearDown(self):
        Config.UPLOAD_FOLDER = self.old_upload_folder
        Config.PLANNING_CAPTURE_ENABLED = self.old_enabled
        Config.LLM_API_KEY = self.old_api_key
        self.tmp.cleanup()

    def test_saves_passive_trace_without_secret_values(self):
        simulation_dir = os.path.join(Config.UPLOAD_FOLDER, "simulations", "sim_test")
        os.makedirs(simulation_dir, exist_ok=True)
        with open(os.path.join(simulation_dir, "simulation_config.json"), "w", encoding="utf-8") as f:
            f.write("{}")

        trace_path = WorldbuildingTraceCapture.save_trace(
            simulation_dir=simulation_dir,
            state=DummyState(),
            filtered_entities=DummyFilteredEntities(),
            profiles=[DummyProfile()],
            simulation_params=DummySimulationParams(),
            simulation_requirement="predict the election",
            document_text="input document",
            defined_entity_types=["Candidate"],
            use_llm_for_profiles=True,
            parallel_profile_count=2,
        )

        self.assertTrue(os.path.exists(trace_path))
        data = json.loads(Path(trace_path).read_text(encoding="utf-8"))

        self.assertEqual(data["trace_version"], 1)
        self.assertEqual(data["simulation_id"], "sim_test")
        self.assertEqual(data["input_context"]["simulation_requirement"], "predict the election")
        self.assertEqual(data["entity_filtering_trace"]["filtered_count"], 1)
        self.assertEqual(data["agent_selection_trace"]["selected_agent_count"], 1)
        self.assertEqual(data["simulation_config_trace"]["generation_reasoning"], "ok")
        self.assertTrue(data["provenance"]["config_snapshot"]["llm_api_key_set"])

        artifact_paths = {item["path"] for item in data["artifact_manifest"]["artifacts"]}
        self.assertIn("simulation_config.json", artifact_paths)
        self.assertIn("worldbuilding_trace.json", artifact_paths)

        serialized = json.dumps(data)
        self.assertNotIn("test-secret-key", serialized)


if __name__ == "__main__":
    unittest.main()
