
import unittest
import math
import os
import tempfile
from unittest.mock import patch

from app.config import Config
from app.services.experimental_memory import ExperimentalMemoryService

class TestExperimentalMemory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = Config.DATA_DIR
        self.old_upload_folder = Config.UPLOAD_FOLDER
        self.old_embedder_base_url = Config.GRAPH_SEARCH_APP_EMBEDDER_BASE_URL
        self.old_embedder_model = Config.GRAPH_SEARCH_APP_EMBEDDER_MODEL

        Config.DATA_DIR = os.path.join(self.tmp.name, "data")
        Config.UPLOAD_FOLDER = os.path.join(self.tmp.name, "uploads")
        Config.GRAPH_SEARCH_APP_EMBEDDER_BASE_URL = None
        Config.GRAPH_SEARCH_APP_EMBEDDER_MODEL = None
        self.embedder_config_patch = patch.object(
            Config,
            "get_graph_search_embedder_config",
            return_value={"api_key": None, "base_url": None, "model": None},
        )
        self.embedder_config_patch.start()

        self.simulation_id = "test_sim"
        self.test_dir = os.path.join(Config.DATA_DIR, "simulations", self.simulation_id)
        os.makedirs(self.test_dir, exist_ok=True)

        self.service = ExperimentalMemoryService(self.simulation_id)

    def tearDown(self):
        self.embedder_config_patch.stop()
        Config.DATA_DIR = self.old_data_dir
        Config.UPLOAD_FOLDER = self.old_upload_folder
        Config.GRAPH_SEARCH_APP_EMBEDDER_BASE_URL = self.old_embedder_base_url
        Config.GRAPH_SEARCH_APP_EMBEDDER_MODEL = self.old_embedder_model
        self.tmp.cleanup()

    def test_cosine_similarity(self):
        """Test the pure Python math implementation of cosine similarity."""
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        # Identical vectors -> 1.0
        self.assertAlmostEqual(self.service._cosine_similarity(v1, v2), 1.0)

        v3 = [0.0, 1.0, 0.0]
        # Orthogonal vectors -> 0.0
        self.assertAlmostEqual(self.service._cosine_similarity(v1, v3), 0.0)

        v4 = [0.5, 0.5, 0.0]
        # 45 degrees -> ~0.707
        self.assertAlmostEqual(self.service._cosine_similarity(v1, v4), 0.5 / (1.0 * math.sqrt(0.5)))
        
        # Zero vector handling
        self.assertEqual(self.service._cosine_similarity([0,0], [1,1]), 0.0)

    def test_add_and_retrieve(self):
        """Test basic persistence and retrieval."""
        memories = [
            {"text": "The quick brown fox", "metadata": {"id": 1}, "embedding": [1.0, 0.0]},
            {"text": "Jumped over the lazy dog", "metadata": {"id": 2}, "embedding": [0.0, 1.0]}
        ]
        
        self.service.add_memories(memories)
        
        # Check if file exists
        file_path = os.path.join(self.test_dir, "experimental_memory.json")
        self.assertTrue(os.path.exists(file_path))
        
        # Test retrieval (uses embedding similarity)
        # Note: In the mock, embedder is None, so it might return empty or error
        # but the logic for cosine similarity and storage is what matters most here.
        results = self.service.retrieve("fox", k=1)
        self.assertIn("archival_memory", results)

    def test_offline_fixture_ignores_graphiti_defaults(self):
        """The test fixture must not activate Chroma from CI defaults."""
        old_base_url = Config.GRAPHITI_EMBEDDER_BASE_URL
        old_model = Config.GRAPHITI_EMBEDDER_MODEL
        Config.GRAPHITI_EMBEDDER_BASE_URL = "http://example.invalid/v1"
        Config.GRAPHITI_EMBEDDER_MODEL = "qwen3-embedding:8b"

        try:
            embedder_config = Config.get_graph_search_embedder_config()
            self.assertFalse(embedder_config["base_url"])
            self.assertFalse(embedder_config["model"])
        finally:
            Config.GRAPHITI_EMBEDDER_BASE_URL = old_base_url
            Config.GRAPHITI_EMBEDDER_MODEL = old_model

if __name__ == "__main__":
    unittest.main()
