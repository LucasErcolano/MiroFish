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

from app.services.memory_mode import MemoryMode

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
    # Mock Config - patch at the module level where it's imported from
    with patch('app.services.experimental_memory.Config') as mock_config, \
         patch('app.services.memory_factory.Config') as mock_factory_config, \
         patch('app.services.zep_graph_memory_updater.Config') as mock_updater_config:
        mock_config.DATA_DIR = test_dir
        mock_config.USE_EXPERIMENTAL_MEMORY = True
        mock_config.MEMORY_MODE = "experimental"
        mock_config.UPLOAD_FOLDER = os.path.join(test_dir, "uploads")
        mock_config.get_graph_search_embedder_config.return_value = {"base_url": None, "model": None}
        mock_config.get_memory_mode.return_value = MemoryMode.EXPERIMENTAL
        mock_config.ZEP_API_KEY = "mock_key"
        mock_config.GRAPH_SEARCH_APP_RERANK_FUSION_K = 60
        mock_config.GRAPH_SEARCH_APP_SEMANTIC_WEIGHT = 1.0
        mock_config.GRAPH_BACKEND = None

        # Copy same config to factory and updater mocks
        for mc in [mock_factory_config, mock_updater_config]:
            mc.DATA_DIR = test_dir
            mc.USE_EXPERIMENTAL_MEMORY = True
            mc.MEMORY_MODE = "experimental"
            mc.UPLOAD_FOLDER = os.path.join(test_dir, "uploads")
            mc.get_graph_search_embedder_config.return_value = {"base_url": None, "model": None}
            mc.get_memory_mode.return_value = MemoryMode.EXPERIMENTAL
            mc.ZEP_API_KEY = "mock_key"
            mc.GRAPH_SEARCH_APP_RERANK_FUSION_K = 60
            mc.GRAPH_SEARCH_APP_SEMANTIC_WEIGHT = 1.0
            mc.GRAPH_BACKEND = None

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
    
    # Initialize with a service
    service = ExperimentalMemoryService(TEST_SIM_ID)
    service.add_memory("Test episode")
    
    # Force embedder to not be None so we can mock its embed_texts
    mock_embedder = MagicMock()
    service.embedder = mock_embedder
    
    # Save the original fallback count
    original_fallback = service.fallback_count
    
    # Make embedding fail
    mock_embedder.embed_texts.side_effect = Exception("Embedding failed")
    
    # This should trigger fallback
    result = service.retrieve("Test", k=1)
    
    assert service.fallback_count == original_fallback + 1
    stats = service.get_stats()
    assert stats["fallback_count"] == original_fallback + 1

def test_bypass_mode_logic_in_updater():
    """Verify that ZepGraphMemoryUpdater uses experimental memory and reports mode/stats correctly."""
    from app.services.zep_graph_memory_updater import ZepGraphMemoryUpdater
    
    # Patch get_graph_backend everywhere it might be imported to ensure it's NOT called.
    with patch('app.services.zep_graph_memory_updater.get_graph_backend') as mock_get_backend_gw, \
         patch('app.graph.factory.get_graph_backend') as mock_get_backend_factory:
        updater = ZepGraphMemoryUpdater(graph_id="test_g", simulation_id=TEST_SIM_ID)
        
        # In experimental mode, no Zep backend should be initialized
        assert updater.backend is None
        mock_get_backend_gw.assert_not_called()
        mock_get_backend_factory.assert_not_called()
        
        stats = updater.get_stats()
        assert stats["mode"] == "experimental"
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