
from typing import List, Dict, Any, Optional
import logging
from .memory_provider import MemoryProvider
from ..graph import get_graph_backend
from ..config import Config

logger = logging.getLogger('mirofish.zep_memory_provider')

class ZepMemoryProvider(MemoryProvider):
    """Memory provider implementation using Zep Knowledge Graph."""
    
    def __init__(self, graph_id: str, api_key: Optional[str] = None):
        self.graph_id = graph_id
        self.api_key = api_key or Config.ZEP_API_KEY
        self.backend = get_graph_backend(api_key=self.api_key)

    def add_memories(self, activities: List[Dict[str, Any]]):
        """Batch add activities to Zep."""
        # Note: ZepGraphMemoryUpdater handles the complex batching/threading, 
        # so this is a simplified view for the provider interface.
        # In a full refactor, the logic from updater would move here.
        if not activities:
            return
            
        combined_text = "\n".join([item.get("text", "") for item in activities])
        self.backend.add_text(
            graph_id=self.graph_id,
            data=combined_text
        )

    def retrieve(self, query: str, k: int = 5) -> Dict[str, Any]:
        """Retrieve from Zep (baseline).

        Records a structured retrieval log and metrics entry via MemoryMetrics.
        Note: The full Zep retrieval path goes through ZepToolsService.search_graph()
        which has its own logging; this method is a simplified interface stub.
        """
        import time as _time
        from .memory_mode import MemoryMode, get_metrics

        start = _time.time()
        # Simplified retrieval — full path is via ZepToolsService.search_graph()
        result = {
            "core_memory": {},
            "archival_memory": [],
            "_meta": {
                "mode": "baseline",
                "results_count": 0,
                "latency_ms": 0.0,
            },
        }
        latency_ms = (_time.time() - start) * 1000.0
        result["_meta"]["latency_ms"] = round(latency_ms, 2)

        # Record metrics
        get_metrics().record_retrieval(
            agent_name=None,
            round_num=None,
            mode=MemoryMode.BASELINE,
            results_count=0,
            latency_ms=latency_ms,
            provider_class="ZepMemoryProvider",
            query=query,
        )

        logger.info(
            "ZepMemoryProvider.retrieve: query='%.80s' k=%d (stub, full path via ZepToolsService)",
            query, k,
        )

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get Zep stats."""
        return {
            "engine": "Zep",
            "graph_id": self.graph_id
        }
