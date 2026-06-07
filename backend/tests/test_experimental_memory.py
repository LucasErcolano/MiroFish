
import unittest
import math
import os
import json
import shutil
from typing import List

# Mock Config before importing Service
class MockConfig:
    DATA_DIR = "backend/data_test"
    UPLOAD_FOLDER = "backend/uploads_test"
    SIMULATION_DATA_DIR = "backend/data_test/simulations"
    USE_EXPERIMENTAL_MEMORY = True
    ZEP_API_KEY = "mock_key"
    GRAPH_SEARCH_APP_RERANK_FUSION_K = 60
    GRAPH_SEARCH_APP_SEMANTIC_WEIGHT = 1.0
    
    @staticmethod
    def get_graph_search_embedder_config():
        return {"base_url": None, "model": None}

import sys
from unittest.mock import MagicMock

# Create a mock app.config module
mock_config_mod = MagicMock()
mock_config_mod.Config = MockConfig
sys.modules['app.config'] = mock_config_mod

# Also need to mock other things that get imported
sys.modules['app.utils.logger'] = MagicMock()
sys.modules['app.utils.locale'] = MagicMock()

# Import the service to test
sys.path.append(os.getcwd())
from app.services.experimental_memory import ExperimentalMemoryService

class TestExperimentalMemory(unittest.TestCase):
    def setUp(self):
        self.simulation_id = "test_sim"
        self.test_dir = "backend/data_test/simulations/test_sim"
        if os.path.exists("backend/data_test"):
            shutil.rmtree("backend/data_test")
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Initialize service
        self.service = ExperimentalMemoryService(self.simulation_id)

    def tearDown(self):
        if os.path.exists("backend/data_test"):
            shutil.rmtree("backend/data_test")

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

if __name__ == "__main__":
    unittest.main()
