import unittest
import os
import shutil
from unittest.mock import MagicMock, patch

from app.services.memory_mode import MemoryMode


class TestExperimentalMemory(unittest.TestCase):
    def setUp(self):
        self.simulation_id = "test_sim"
        self.test_dir = "backend/data_test/simulations/test_sim"

        # Create mock config
        self.mock_config = MagicMock()
        self.mock_config.DATA_DIR = "backend/data_test"
        self.mock_config.UPLOAD_FOLDER = "backend/uploads_test"
        self.mock_config.SIMULATION_DATA_DIR = "backend/data_test/simulations"
        self.mock_config.USE_EXPERIMENTAL_MEMORY = True
        self.mock_config.MEMORY_MODE = "experimental"
        self.mock_config.ZEP_API_KEY = "mock_key"
        self.mock_config.GRAPH_SEARCH_APP_RERANK_FUSION_K = 60
        self.mock_config.GRAPH_SEARCH_APP_SEMANTIC_WEIGHT = 1.0
        self.mock_config.get_graph_search_embedder_config.return_value = {"base_url": None, "model": None}
        self.mock_config.get_memory_mode.return_value = MemoryMode.EXPERIMENTAL

        # Start patchers
        self.config_patcher = patch('app.services.experimental_memory.Config', self.mock_config)
        self.config_patcher.start()

        if os.path.exists("backend/data_test"):
            shutil.rmtree("backend/data_test")
        os.makedirs(self.test_dir, exist_ok=True)

        # Import and initialize service
        from app.services.experimental_memory import ExperimentalMemoryService
        self.service = ExperimentalMemoryService(self.simulation_id)

    def tearDown(self):
        self.config_patcher.stop()
        if os.path.exists("backend/data_test"):
            shutil.rmtree("backend/data_test")

    def test_add_and_retrieve(self):
        """Test basic persistence and retrieval via ChromaDB."""
        # Add a memory item (without embeddings since embedder is None in mock)
        self.service.add_memory("The quick brown fox", metadata={"id": 1})
        self.service.add_memory("Jumped over the lazy dog", metadata={"id": 2})

        # Retrieve (will use keyword fallback since embedder is None)
        results = self.service.retrieve("fox", k=1)
        self.assertIn("archival_memory", results)
        self.assertIn("_meta", results)
        self.assertEqual(results["_meta"]["mode"], "experimental")

    def test_fallback_to_keyword_search(self):
        """Verify that when embedder is None, keyword search fallback works."""
        self.service.add_memory("The quick brown fox jumped over the lazy dog")
        self.service.add_memory("A completely different topic about economy")

        # With no embedder, should fall back to keyword search
        results = self.service.retrieve("fox", k=5)
        self.assertIn("archival_memory", results)
        # Fallback count should increment
        self.assertGreaterEqual(self.service.fallback_count, 1)

    def test_core_memory_persistence(self):
        """Test that core_memory is saved and loaded correctly."""
        self.service.core_memory["persona"] = "Test Agent"
        self.service.core_memory["objectives"] = ["objective1"]
        self.service.save_core_memory(self.service.core_memory)

        # Reload by creating a new service instance
        from app.services.experimental_memory import ExperimentalMemoryService
        service2 = ExperimentalMemoryService(self.simulation_id)
        self.assertEqual(service2.core_memory.get("persona"), "Test Agent")

    def test_get_stats(self):
        """Verify get_stats returns expected structure."""
        stats = self.service.get_stats()
        self.assertIn("total_episodes", stats)
        self.assertIn("core_memory_populated", stats)
        self.assertIn("fallback_count", stats)
        self.assertIn("using_vector_search", stats)
        self.assertIn("storage_engine", stats)
        self.assertEqual(stats["storage_engine"], "ChromaDB")

if __name__ == "__main__":
    unittest.main()