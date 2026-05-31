
import os
import json
import pytest
import shutil
import math
from unittest.mock import MagicMock, patch

# Configuration for tests
TEST_DATA_DIR = "backend/data_test_integration"
TEST_SIM_ID = "integration_sim_1"
TEST_SIM_ID_2 = "integration_sim_2"

import uuid

@pytest.fixture
def test_dir():
    """Provides a unique directory for each test."""
    unique_dir = os.path.join(TEST_DATA_DIR, str(uuid.uuid4()))
    os.makedirs(unique_dir, exist_ok=True)
    yield unique_dir
    # On Windows, we might not be able to cleanup immediately if Chroma has locks
    try:
        shutil.rmtree(unique_dir, ignore_errors=True)
    except:
        pass

@pytest.fixture(autouse=True)
def setup_test_env(test_dir):
    """Setup and teardown for all tests."""
    # Mock Config
    with patch('app.config.Config') as mock_config:
        mock_config.DATA_DIR = test_dir
        mock_config.USE_EXPERIMENTAL_MEMORY = True
        mock_config.UPLOAD_FOLDER = os.path.join(test_dir, "uploads")
        mock_config.get_graph_search_embedder_config.return_value = {"base_url": "http://mock", "model": "mock-m"}
        yield mock_config

def test_strict_isolation_between_simulations():
    """Verify that data for one simulation does not leak into another."""
    from app.services.experimental_memory import ExperimentalMemoryService
    
    service1 = ExperimentalMemoryService(TEST_SIM_ID)
    service2 = ExperimentalMemoryService(TEST_SIM_ID_2)
    
    service1.add_memory("Memory for Sim 1", metadata={"sim": 1})
    service2.add_memory("Memory for Sim 2", metadata={"sim": 2})
    
    res1 = service1.retrieve("Memory", k=10)
    res2 = service2.retrieve("Memory", k=10)
    
    assert len(res1["archival_memory"]) == 1
    assert "Sim 1" in res1["archival_memory"][0]
    
    assert len(res2["archival_memory"]) == 1
    assert "Sim 2" in res2["archival_memory"][0]

def test_fallback_audit_mechanism():
    """Verify that fallback_count increments when embedding fails."""
    from app.services.experimental_memory import ExperimentalMemoryService
    
    # Initialize with a service that will fail embedding
    service = ExperimentalMemoryService(TEST_SIM_ID)
    service.add_memory("Test episode")
    
    # Force embedding failure by mocking the embedder to raise an exception
    service.embedder.embed_texts = MagicMock(side_effect=Exception("Embedding failed"))
    
    assert service.fallback_count == 0
    
    # This should trigger fallback
    service.retrieve("Test", k=1)
    
    assert service.fallback_count == 1
    stats = service.get_stats()
    assert stats["fallback_count"] == 1

def test_bypass_mode_logic_in_updater():
    """Verify that ZepGraphMemoryUpdater respects the bypass flag and stats reporting."""
    from app.services.zep_graph_memory_updater import ZepGraphMemoryUpdater
    
    os.environ["USE_EXPERIMENTAL_MEMORY"] = "true"
    
    # Mock the backend to ensure it's NOT initialized
    with patch('app.services.zep_graph_memory_updater.get_graph_backend') as mock_get_backend:
        updater = ZepGraphMemoryUpdater(graph_id="test_g", simulation_id=TEST_SIM_ID)
        
        assert updater.backend is None
        mock_get_backend.assert_not_called()
        
        stats = updater.get_stats()
        assert stats["mode"] == "bypass"
        assert stats["graph_id"] == "N/A (Experimental)"
        assert "experimental_stats" in stats

def test_core_memory_persistence():
    """Verify that core memory is correctly saved and loaded."""
    from app.services.experimental_memory import ExperimentalMemoryService
    
    service = ExperimentalMemoryService(TEST_SIM_ID)
    new_core = {"persona": "AI Assistant", "objectives": ["Help User"], "key_events": []}
    service.save_core_memory(new_core)
    
    # Reload service
    service_reloaded = ExperimentalMemoryService(TEST_SIM_ID)
    assert service_reloaded.core_memory["persona"] == "AI Assistant"
    assert "Help User" in service_reloaded.core_memory["objectives"]
