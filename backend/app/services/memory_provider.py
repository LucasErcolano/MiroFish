
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class MemoryProvider(ABC):
    """Base interface for memory storage and retrieval."""
    
    @abstractmethod
    def add_memories(self, activities: List[Dict[str, Any]]):
        """Batch add activities to memory."""
        pass

    @abstractmethod
    def retrieve(self, query: str, k: int = 5) -> Dict[str, Any]:
        """Retrieve relevant context for a query."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get operational statistics."""
        pass
