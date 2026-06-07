
import os
from typing import Optional
from .memory_provider import MemoryProvider
from .experimental_memory import ExperimentalMemoryService
from .zep_memory_provider import ZepMemoryProvider
from ..config import Config

class MemoryFactory:
    """Factory to create memory providers based on configuration."""
    
    @staticmethod
    def create_provider(simulation_id: str, graph_id: str, api_key: Optional[str] = None) -> MemoryProvider:
        """Create a memory provider instance."""
        if os.getenv("USE_EXPERIMENTAL_MEMORY") == "true":
            return ExperimentalMemoryService(simulation_id)
        
        return ZepMemoryProvider(graph_id, api_key=api_key)
