import logging
from typing import Optional
from .memory_provider import MemoryProvider
from .memory_mode import MemoryMode, get_metrics, log_mode_switch
from ..config import Config

logger = logging.getLogger('mirofish.memory_factory')


class MemoryFactory:
    """Factory to create memory providers based on the active memory_mode.

    The memory mode is resolved from Config (MEMORY_MODE env var with
    backward-compat for USE_EXPERIMENTAL_MEMORY). This produces either
    a ZepMemoryProvider (baseline) or ExperimentalMemoryService
    (experimental), both conforming to the MemoryProvider interface.

    Rollback is clean: setting MEMORY_MODE=baseline (or removing the env
    var) immediately restores the Zep-based flow with no code changes.
    """

    _current_mode: Optional[MemoryMode] = None

    @staticmethod
    def create_provider(
        simulation_id: str,
        graph_id: str,
        api_key: Optional[str] = None,
    ) -> MemoryProvider:
        """Create a memory provider instance based on the active memory mode.

        Args:
            simulation_id: Simulation identifier for experimental memory isolation.
            graph_id: Zep graph identifier for baseline memory.
            api_key: Optional Zep API key override.

        Returns:
            A MemoryProvider instance (ZepMemoryProvider or ExperimentalMemoryService).
        """
        mode = Config.get_memory_mode()
        metrics = get_metrics()

        # Detect mode switches
        if MemoryFactory._current_mode is not None and MemoryFactory._current_mode != mode:
            log_mode_switch(MemoryFactory._current_mode, mode, source="MemoryFactory")
        MemoryFactory._current_mode = mode

        if mode == MemoryMode.EXPERIMENTAL:
            from .experimental_memory import ExperimentalMemoryService
            logger.info(
                "MemoryFactory: creating ExperimentalMemoryService "
                "(mode=experimental, simulation_id=%s)", simulation_id,
            )
            provider = ExperimentalMemoryService(simulation_id)
        else:
            from .zep_memory_provider import ZepMemoryProvider
            logger.info(
                "MemoryFactory: creating ZepMemoryProvider "
                "(mode=baseline, graph_id=%s)", graph_id,
            )
            provider = ZepMemoryProvider(graph_id, api_key=api_key)

        return provider

    @staticmethod
    def get_current_mode() -> Optional[MemoryMode]:
        """Return the last-resolved memory mode, or None if no provider has been created yet."""
        return MemoryFactory._current_mode