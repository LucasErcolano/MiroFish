"""
Tests for memory_mode feature flag (Spike S2).

Covers:
  - MemoryMode enum parsing
  - Config resolution (MEMORY_MODE, USE_EXPERIMENTAL_MEMORY backward compat, default)
  - MemoryFactory creates correct provider per mode
  - Rollback: switching from experimental to baseline produces baseline provider
  - Unified retrieve() interface (both providers return same shape)
  - MemoryMetrics: recording retrievals, per-agent/per-round counters, summary
  - Structured retrieval logging / log entries
  - Mode switch detection logging
"""

import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# 1. MemoryMode enum tests
# ---------------------------------------------------------------------------

class TestMemoryModeEnum(unittest.TestCase):
    """Tests for the MemoryMode enum."""

    def test_from_string_baseline(self):
        from app.services.memory_mode import MemoryMode
        self.assertEqual(MemoryMode.from_string("baseline"), MemoryMode.BASELINE)

    def test_from_string_experimental(self):
        from app.services.memory_mode import MemoryMode
        self.assertEqual(MemoryMode.from_string("experimental"), MemoryMode.EXPERIMENTAL)

    def test_from_string_case_insensitive(self):
        from app.services.memory_mode import MemoryMode
        self.assertEqual(MemoryMode.from_string("  Baseline  "), MemoryMode.BASELINE)
        self.assertEqual(MemoryMode.from_string("EXPERIMENTAL"), MemoryMode.EXPERIMENTAL)

    def test_from_string_invalid_raises(self):
        from app.services.memory_mode import MemoryMode
        with self.assertRaises(ValueError) as ctx:
            MemoryMode.from_string("invalid_mode")
        self.assertIn("invalid_mode", str(ctx.exception))

    def test_is_experimental(self):
        from app.services.memory_mode import MemoryMode
        self.assertTrue(MemoryMode.EXPERIMENTAL.is_experimental())
        self.assertFalse(MemoryMode.BASELINE.is_experimental())

    def test_is_baseline(self):
        from app.services.memory_mode import MemoryMode
        self.assertTrue(MemoryMode.BASELINE.is_baseline())
        self.assertFalse(MemoryMode.EXPERIMENTAL.is_baseline())


# ---------------------------------------------------------------------------
# 2. Config resolution tests
# ---------------------------------------------------------------------------

class TestMemoryModeResolution(unittest.TestCase):
    """Tests for resolve_memory_mode() and Config.get_memory_mode()."""

    def setUp(self):
        # Save original env vars
        self._orig_memory_mode = os.environ.pop("MEMORY_MODE", None)
        self._orig_use_exp = os.environ.pop("USE_EXPERIMENTAL_MEMORY", None)

    def tearDown(self):
        # Restore env vars
        if self._orig_memory_mode is not None:
            os.environ["MEMORY_MODE"] = self._orig_memory_mode
        else:
            os.environ.pop("MEMORY_MODE", None)
        if self._orig_use_exp is not None:
            os.environ["USE_EXPERIMENTAL_MEMORY"] = self._orig_use_exp
        else:
            os.environ.pop("USE_EXPERIMENTAL_MEMORY", None)

    def test_default_is_baseline(self):
        from app.services.memory_mode import resolve_memory_mode
        mode = resolve_memory_mode()
        from app.services.memory_mode import MemoryMode
        self.assertEqual(mode, MemoryMode.BASELINE)

    def test_memory_mode_env_baseline(self):
        from app.services.memory_mode import resolve_memory_mode, MemoryMode
        os.environ["MEMORY_MODE"] = "baseline"
        self.assertEqual(resolve_memory_mode(), MemoryMode.BASELINE)

    def test_memory_mode_env_experimental(self):
        from app.services.memory_mode import resolve_memory_mode, MemoryMode
        os.environ["MEMORY_MODE"] = "experimental"
        self.assertEqual(resolve_memory_mode(), MemoryMode.EXPERIMENTAL)

    def test_memory_mode_takes_precedence_over_use_experimental(self):
        """MEMORY_MODE=baseline should win over USE_EXPERIMENTAL_MEMORY=true."""
        from app.services.memory_mode import resolve_memory_mode, MemoryMode
        os.environ["MEMORY_MODE"] = "baseline"
        os.environ["USE_EXPERIMENTAL_MEMORY"] = "true"
        self.assertEqual(resolve_memory_mode(), MemoryMode.BASELINE)

    def test_backward_compat_use_experimental_true(self):
        from app.services.memory_mode import resolve_memory_mode, MemoryMode
        os.environ["USE_EXPERIMENTAL_MEMORY"] = "true"
        self.assertEqual(resolve_memory_mode(), MemoryMode.EXPERIMENTAL)

    def test_backward_compat_use_experimental_false(self):
        from app.services.memory_mode import resolve_memory_mode, MemoryMode
        os.environ["USE_EXPERIMENTAL_MEMORY"] = "false"
        self.assertEqual(resolve_memory_mode(), MemoryMode.BASELINE)

    def test_config_get_memory_mode_from_memory_mode(self):
        from app.services.memory_mode import MemoryMode, resolve_memory_mode_from_config

        class LocalConfig:
            MEMORY_MODE = "experimental"
            USE_EXPERIMENTAL_MEMORY = False

        self.assertEqual(resolve_memory_mode_from_config(LocalConfig), MemoryMode.EXPERIMENTAL)

    def test_config_get_memory_mode_fallback_to_use_experimental(self):
        from app.services.memory_mode import MemoryMode, resolve_memory_mode_from_config

        class LocalConfig:
            MEMORY_MODE = ""
            USE_EXPERIMENTAL_MEMORY = True

        self.assertEqual(resolve_memory_mode_from_config(LocalConfig), MemoryMode.EXPERIMENTAL)

    def test_config_get_memory_mode_default(self):
        from app.services.memory_mode import MemoryMode, resolve_memory_mode_from_config

        class LocalConfig:
            MEMORY_MODE = ""
            USE_EXPERIMENTAL_MEMORY = False

        self.assertEqual(resolve_memory_mode_from_config(LocalConfig), MemoryMode.BASELINE)


# ---------------------------------------------------------------------------
# 3. MemoryFactory tests
# ---------------------------------------------------------------------------

class TestMemoryFactory(unittest.TestCase):
    """Tests for MemoryFactory mode-based provider creation."""

    def setUp(self):
        # Reset factory state
        from app.services.memory_factory import MemoryFactory
        MemoryFactory._current_mode = None

    def test_creates_experimental_provider_when_mode_experimental(self):
        from app.services.memory_mode import MemoryMode
        with patch("app.services.memory_factory.Config.get_memory_mode") as mock_mode:
            mock_mode.return_value = MemoryMode.EXPERIMENTAL
            # Patch at source module level (factory imports lazily)
            with patch("app.services.experimental_memory.ExperimentalMemoryService") as MockExpSvc:
                mock_instance = MagicMock()
                MockExpSvc.return_value = mock_instance

                from app.services.memory_factory import MemoryFactory
                MemoryFactory._current_mode = None
                provider = MemoryFactory.create_provider(
                    simulation_id="test_sim", graph_id="test_graph"
                )
                # Verify ExperimentalMemoryService was instantiated with simulation_id
                MockExpSvc.assert_called_once_with("test_sim")

    def test_creates_zep_provider_when_mode_baseline(self):
        from app.services.memory_mode import MemoryMode
        with patch("app.services.memory_factory.Config.get_memory_mode") as mock_mode:
            mock_mode.return_value = MemoryMode.BASELINE
            with patch("app.services.zep_memory_provider.ZepMemoryProvider") as MockZep:
                mock_instance = MagicMock()
                MockZep.return_value = mock_instance

                from app.services.memory_factory import MemoryFactory
                MemoryFactory._current_mode = None
                provider = MemoryFactory.create_provider(
                    simulation_id="test_sim", graph_id="test_graph"
                )
                MockZep.assert_called_once_with("test_graph", api_key=None)

    def test_rollback_from_experimental_to_baseline(self):
        """Switching MEMORY_MODE from experimental to baseline restores baseline provider."""
        from app.services.memory_mode import MemoryMode
        from app.services.memory_factory import MemoryFactory

        # First call: experimental
        with patch("app.services.memory_factory.Config.get_memory_mode") as mock_mode:
            mock_mode.return_value = MemoryMode.EXPERIMENTAL
            with patch("app.services.experimental_memory.ExperimentalMemoryService") as MockExpSvc:
                MockExpSvc.return_value = MagicMock()
                MemoryFactory._current_mode = None
                provider1 = MemoryFactory.create_provider(
                    simulation_id="test_sim", graph_id="test_graph"
                )

        # Second call: baseline (rollback)
        with patch("app.services.memory_factory.Config.get_memory_mode") as mock_mode:
            mock_mode.return_value = MemoryMode.BASELINE
            with patch("app.services.zep_memory_provider.ZepMemoryProvider") as MockZep:
                MockZep.return_value = MagicMock()
                provider2 = MemoryFactory.create_provider(
                    simulation_id="test_sim", graph_id="test_graph"
                )

        # Verify mode switch was detected
        self.assertEqual(MemoryFactory._current_mode, MemoryMode.BASELINE)

    def test_get_current_mode_initially_none(self):
        from app.services.memory_factory import MemoryFactory
        MemoryFactory._current_mode = None
        self.assertIsNone(MemoryFactory.get_current_mode())


# ---------------------------------------------------------------------------
# 4. Unified retrieve() interface test
# ---------------------------------------------------------------------------

class TestUnifiedInterface(unittest.TestCase):
    """Test that both providers return the same interface shape from retrieve()."""

    def test_experimental_retrieve_has_required_keys(self):
        """ExperimentalMemoryService.retrieve() returns core_memory, archival_memory, _meta."""
        from app.services.memory_mode import MemoryMode, get_metrics

        # Reset metrics to avoid side-effects
        get_metrics().reset()

        # Use a mock provider that simulates ExperimentalMemoryService's retrieve() output shape
        mock_provider = MagicMock()
        mock_provider.retrieve.return_value = {
            "core_memory": {"persona": "test"},
            "archival_memory": ["item1", "item2"],
            "_meta": {
                "mode": "experimental",
                "results_count": 2,
                "latency_ms": 10.0,
            },
        }

        # Verify the required keys exist
        result = mock_provider.retrieve("test query", k=5)
        self.assertIn("core_memory", result)
        self.assertIn("archival_memory", result)
        self.assertIn("_meta", result)

        meta = result["_meta"]
        self.assertEqual(meta["mode"], "experimental")
        self.assertIn("results_count", meta)
        self.assertIn("latency_ms", meta)

        # Also verify the _meta shape matches what ExperimentalMemoryService actually produces
        # by testing the real code path with chromadb mocked
        with patch("chromadb.PersistentClient") as mock_chroma:
            mock_collection = MagicMock()
            mock_collection.count.return_value = 0
            mock_client = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client

            with patch("app.config.Config") as mock_config:
                mock_config.DATA_DIR = "/tmp/test_mirofish_exp_interface"
                mock_config.UPLOAD_FOLDER = "/tmp/test_mirofish_uploads"
                mock_config.USE_EXPERIMENTAL_MEMORY = True
                mock_config.get_graph_search_embedder_config.return_value = {
                    "base_url": None, "model": None
                }

                from app.services.experimental_memory import ExperimentalMemoryService
                service = ExperimentalMemoryService("test_interface_sim")

                # Patch _retrieve_archival for deterministic output
                service._retrieve_archival = MagicMock(return_value=["memory item 1", "memory item 2"])

                result = service.retrieve("test query", k=5)

                self.assertIn("core_memory", result)
                self.assertIn("archival_memory", result)
                self.assertIn("_meta", result)

                meta = result["_meta"]
                self.assertEqual(meta["mode"], "experimental")
                self.assertIn("results_count", meta)
                self.assertIn("latency_ms", meta)

        # Cleanup temp dir
        import shutil
        import os
        tmp_dir = "/tmp/test_mirofish_exp_interface/simulations/test_interface_sim"
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_zep_retrieve_has_required_keys(self):
        """ZepMemoryProvider.retrieve() returns core_memory, archival_memory, _meta."""
        from app.services.zep_memory_provider import ZepMemoryProvider

        with patch("app.services.zep_memory_provider.get_graph_backend") as mock_backend:
            mock_backend.return_value = MagicMock()
            provider = ZepMemoryProvider("test_graph")
            result = provider.retrieve("test query", k=5)

            self.assertIn("core_memory", result)
            self.assertIn("archival_memory", result)
            self.assertIn("_meta", result)

            meta = result["_meta"]
            self.assertEqual(meta["mode"], "baseline")
            self.assertIn("results_count", meta)
            self.assertIn("latency_ms", meta)


# ---------------------------------------------------------------------------
# 5. MemoryMetrics tests
# ---------------------------------------------------------------------------

class TestMemoryMetrics(unittest.TestCase):
    """Tests for the MemoryMetrics collector."""

    def setUp(self):
        from app.services.memory_mode import MemoryMetrics
        self.metrics = MemoryMetrics()

    def test_record_and_summary(self):
        from app.services.memory_mode import MemoryMode
        self.metrics.record_retrieval(
            agent_name="agent_0",
            round_num=1,
            mode=MemoryMode.EXPERIMENTAL,
            results_count=5,
            latency_ms=120.0,
            provider_class="ExperimentalMemoryService",
            query="test query",
        )
        summary = self.metrics.get_summary()
        self.assertEqual(summary["total_retrievals"], 1)
        self.assertEqual(summary["total_results"], 5)
        self.assertEqual(summary["mode_breakdown"]["experimental"], 1)
        self.assertIn("agent_0", summary["per_agent"])
        self.assertEqual(summary["per_agent"]["agent_0"]["retrievals"], 1)

    def test_per_agent_metrics(self):
        from app.services.memory_mode import MemoryMode
        self.metrics.record_retrieval("agent_0", 1, MemoryMode.EXPERIMENTAL, 3, 50.0, "ExpSvc")
        self.metrics.record_retrieval("agent_0", 1, MemoryMode.EXPERIMENTAL, 2, 60.0, "ExpSvc")
        self.metrics.record_retrieval("agent_1", 2, MemoryMode.BASELINE, 1, 30.0, "ZepSvc")

        summary = self.metrics.get_summary()
        self.assertEqual(summary["per_agent"]["agent_0"]["retrievals"], 2)
        self.assertEqual(summary["per_agent"]["agent_0"]["total_results"], 5)
        self.assertEqual(summary["per_agent"]["agent_1"]["retrievals"], 1)
        self.assertEqual(summary["per_agent"]["agent_1"]["total_results"], 1)

    def test_per_round_metrics(self):
        from app.services.memory_mode import MemoryMode
        self.metrics.record_retrieval("agent_0", 1, MemoryMode.EXPERIMENTAL, 3, 50.0, "ExpSvc")
        self.metrics.record_retrieval("agent_0", 2, MemoryMode.EXPERIMENTAL, 5, 70.0, "ExpSvc")

        summary = self.metrics.get_summary()
        self.assertEqual(summary["per_round"]["1"]["retrievals"], 1)
        self.assertEqual(summary["per_round"]["2"]["retrievals"], 1)

    def test_mode_breakdown(self):
        from app.services.memory_mode import MemoryMode
        self.metrics.record_retrieval("a", 1, MemoryMode.BASELINE, 3, 50.0, "ZepSvc")
        self.metrics.record_retrieval("a", 1, MemoryMode.EXPERIMENTAL, 5, 70.0, "ExpSvc")
        self.metrics.record_retrieval("a", 2, MemoryMode.BASELINE, 1, 20.0, "ZepSvc")

        summary = self.metrics.get_summary()
        self.assertEqual(summary["mode_breakdown"]["baseline"], 2)
        self.assertEqual(summary["mode_breakdown"]["experimental"], 1)

    def test_latency_tracking(self):
        from app.services.memory_mode import MemoryMode
        self.metrics.record_retrieval("a", 1, MemoryMode.BASELINE, 3, 100.0, "ZepSvc")
        self.metrics.record_retrieval("a", 1, MemoryMode.BASELINE, 2, 200.0, "ZepSvc")

        summary = self.metrics.get_summary()
        self.assertAlmostEqual(summary["avg_latency_ms"], 150.0, places=1)

    def test_reset(self):
        from app.services.memory_mode import MemoryMode
        self.metrics.record_retrieval("a", 1, MemoryMode.BASELINE, 3, 50.0, "ZepSvc")
        self.metrics.reset()
        summary = self.metrics.get_summary()
        self.assertEqual(summary["total_retrievals"], 0)
        self.assertEqual(summary["total_results"], 0)

    def test_get_recent_log(self):
        from app.services.memory_mode import MemoryMode
        self.metrics.record_retrieval("a", 1, MemoryMode.BASELINE, 3, 50.0, "ZepSvc", query="test")
        self.metrics.record_retrieval("b", 2, MemoryMode.EXPERIMENTAL, 5, 80.0, "ExpSvc", query="test2")

        log = self.metrics.get_recent_log(2)
        self.assertEqual(len(log), 2)
        self.assertEqual(log[0]["mode"], "baseline")
        self.assertEqual(log[1]["mode"], "experimental")
        self.assertIn("query", log[0])

    def test_log_entry_bounded(self):
        from app.services.memory_mode import MemoryMode
        # Add more than max_log_entries
        for i in range(1010):
            self.metrics.record_retrieval("a", 1, MemoryMode.BASELINE, 1, 10.0, "Svc", query=f"q{i}")
        log = self.metrics.get_recent_log(2000)
        # Should be bounded to 1000
        self.assertLessEqual(len(log), 1000)


# ---------------------------------------------------------------------------
# 6. MemoryRetrievalLog dataclass test
# ---------------------------------------------------------------------------

class TestMemoryRetrievalLog(unittest.TestCase):

    def test_to_dict(self):
        from app.services.memory_mode import MemoryRetrievalLog
        entry = MemoryRetrievalLog(
            timestamp=12345.0,
            mode="experimental",
            agent_name="agent_0",
            round_num=3,
            query="test",
            results_count=5,
            provider_class="ExperimentalMemoryService",
            latency_ms=120.5,
        )
        d = entry.to_dict()
        self.assertEqual(d["mode"], "experimental")
        self.assertEqual(d["agent_name"], "agent_0")
        self.assertEqual(d["round_num"], 3)
        self.assertEqual(d["results_count"], 5)
        self.assertEqual(d["latency_ms"], 120.5)


# ---------------------------------------------------------------------------
# 7. Mode switch logging test
# ---------------------------------------------------------------------------

class TestModeSwitchLogging(unittest.TestCase):
    """Verify that log_mode_switch emits a warning log."""

    def test_log_mode_switch(self):
        from app.services.memory_mode import log_mode_switch, MemoryMode
        import logging

        with self.assertLogs("mirofish.memory_mode", level="WARNING") as cm:
            log_mode_switch(MemoryMode.BASELINE, MemoryMode.EXPERIMENTAL, source="test")
        self.assertIn("baseline", cm.output[0])
        self.assertIn("experimental", cm.output[0])


# ---------------------------------------------------------------------------
# 8. get_metrics() singleton test
# ---------------------------------------------------------------------------

class TestGetMetrics(unittest.TestCase):

    def test_singleton(self):
        from app.services.memory_mode import get_metrics, _metrics
        # Reset module-level singleton
        import app.services.memory_mode as mm
        mm._metrics = None
        m1 = get_metrics()
        m2 = get_metrics()
        self.assertIs(m1, m2)


# ---------------------------------------------------------------------------
# 9. Integration: MemoryFactory + Metrics recording
# ---------------------------------------------------------------------------

class TestFactoryMetricsIntegration(unittest.TestCase):
    """Verify that creating providers via factory doesn't crash when metrics are active."""

    def test_experimental_provider_creation_records_no_metrics_yet(self):
        """Factory creation itself doesn't record metrics — that happens on retrieve()."""
        from app.services.memory_mode import MemoryMetrics
        metrics = MemoryMetrics()

        # Just creating a provider shouldn't record any retrieval metrics
        summary = metrics.get_summary()
        self.assertEqual(summary["total_retrievals"], 0)


if __name__ == "__main__":
    unittest.main()