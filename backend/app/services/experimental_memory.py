"""
Experimental Memory Service (Spike S1)
Implements a dual-layer memory approach: Core Memory + Archival Memory.
Inspired by Karpathy's LLM-Wiki and MemGPT.
Now using ChromaDB for persistent archival memory.
"""

import os
import json
import time
import uuid
import math
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

from ..utils.embedding_client import EmbeddingClient
from ..config import Config
from ..utils.logger import get_logger

from .memory_provider import MemoryProvider

logger = get_logger('mirofish.experimental_memory')

class ExperimentalMemoryService(MemoryProvider):
    def __init__(self, simulation_id: str):
        self.simulation_id = simulation_id
        self.data_dir = os.path.join(Config.DATA_DIR, 'simulations', simulation_id)
        self.core_memory_path = os.path.join(self.data_dir, 'core_memory.json')
        self.chroma_path = os.path.join(self.data_dir, 'chroma_db')
        
        # Ensure directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.embedder = self._get_embedder()
        self.core_memory = self._load_core_memory()
        self.fallback_count = 0
        
        # Initialize ChromaDB
        try:
            self.chroma_client = chromadb.PersistentClient(path=self.chroma_path)
            self.collection = self.chroma_client.get_or_create_collection(name="archival_memory")
            logger.info(f"ChromaDB initialized for simulation {simulation_id}")
            
            # Migración desde JSON antiguo si existe
            self._migrate_from_json()
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.collection = None

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de uso de la memoria experimental."""
        total_episodes = 0
        if self.collection:
            total_episodes = self.collection.count()
            
        return {
            "total_episodes": total_episodes,
            "core_memory_populated": bool(self.core_memory.get("persona")),
            "fallback_count": self.fallback_count,
            "using_vector_search": self.embedder is not None,
            "storage_engine": "ChromaDB"
        }

    def _migrate_from_json(self):
        """Migra datos desde el antiguo experimental_memory.json a ChromaDB."""
        old_storage_path = os.path.join(self.data_dir, 'experimental_memory.json')
        if os.path.exists(old_storage_path) and self.collection:
            try:
                with open(old_storage_path, 'r', encoding='utf-8') as f:
                    memories = json.load(f)
                
                if memories:
                    logger.info(f"Migrating {len(memories)} episodes from JSON to ChromaDB...")
                    for m in memories:
                        self.add_memory(
                            text=m.get("text", ""),
                            metadata=m.get("metadata", {}),
                            _timestamp=m.get("timestamp")
                        )
                    # Renombrar archivo para evitar re-migración
                    os.rename(old_storage_path, old_storage_path + ".migrated")
                    logger.info("Migration completed.")
            except Exception as e:
                logger.error(f"Migration failed: {e}")

    def _get_embedder(self) -> Optional[EmbeddingClient]:
        embedder_config = Config.get_graph_search_embedder_config()
        base_url = embedder_config.get("base_url")
        model = embedder_config.get("model")
        if not base_url or not model:
            logger.warning("Embedding client not configured for experimental memory.")
            return None
        try:
            return EmbeddingClient(
                api_key=embedder_config.get("api_key") or "ollama",
                base_url=base_url,
                model=model
            )
        except Exception as e:
            logger.error(f"Failed to initialize embedding client: {e}")
            return None

    def _load_core_memory(self) -> Dict[str, Any]:
        if os.path.exists(self.core_memory_path):
            with open(self.core_memory_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        profiles = self._load_agent_profiles()
        if profiles:
            p = profiles[0]
            core = {
                "persona": p.get("persona", p.get("bio", "Standard MiroFish Agent")),
                "objectives": p.get("interested_topics", []),
                "key_events": []
            }
            self.save_core_memory(core)
            return core

        return {
            "persona": "Standard MiroFish Agent",
            "objectives": [],
            "key_events": []
        }

    def _load_agent_profiles(self) -> List[Dict[str, Any]]:
        import csv
        sim_dir = os.path.join(Config.UPLOAD_FOLDER, 'simulations', self.simulation_id)
        reddit_path = os.path.join(sim_dir, "reddit_profiles.json")
        if os.path.exists(reddit_path):
            try:
                with open(reddit_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        twitter_path = os.path.join(sim_dir, "twitter_profiles.csv")
        if os.path.exists(twitter_path):
            try:
                with open(twitter_path, 'r', encoding='utf-8') as f:
                    return list(csv.DictReader(f))
            except: pass
        return []

    def save_core_memory(self, core_data: Dict[str, Any]):
        self.core_memory.update(core_data)
        with open(self.core_memory_path, 'w', encoding='utf-8') as f:
            json.dump(self.core_memory, f, ensure_ascii=False, indent=2)

    def add_memories(self, activities: List[Dict[str, Any]]):
        """Add multiple episodes to archival memory (ChromaDB) with Entity Normalization."""
        if not activities or not self.collection:
            return

        ids = [str(uuid.uuid4()) for _ in activities]
        documents = []
        metadatas = [item.get("metadata", {}) for item in activities]
        
        # Entity Normalization: Aseguramos que el nombre del agente esté presente de forma canónica
        for item in activities:
            text = item.get("text", "")
            agent_name = item.get("metadata", {}).get("agent_name")
            # Si el texto no empieza por el nombre del agente, lo normalizamos
            if agent_name and not text.startswith(f"{agent_name}:"):
                normalized_text = f"Agent [{agent_name}]: {text}"
            else:
                normalized_text = text
            documents.append(normalized_text)
        
        # Inject timestamp into metadata
        now = time.time()
        for meta in metadatas:
            meta["timestamp"] = now

        embeddings = None
        if self.embedder:
            try:
                embeddings = self.embedder.embed_texts(documents)
            except Exception as e:
                logger.error(f"Failed to batch embed memory for ChromaDB: {e}")

        try:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
        except Exception as e:
            logger.error(f"Error adding to ChromaDB: {e}")

    def add_memory(self, text: str, metadata: Optional[Dict[str, Any]] = None, _timestamp: Optional[float] = None):
        """Add a single episode to archival memory."""
        meta = metadata or {}
        if _timestamp:
            meta["timestamp"] = _timestamp
        self.add_memories([{"text": text, "metadata": meta}])

    def retrieve(self, query: str, k: int = 5) -> Dict[str, Any]:
        """Retrieve context from both Core and Archival memory.

        Records a structured retrieval log and metrics entry via MemoryMetrics.
        """
        from .memory_mode import MemoryMode, get_metrics

        start = time.time()
        archival_results = self._retrieve_archival(query, k)
        latency_ms = (time.time() - start) * 1000.0

        result = {
            "core_memory": self.core_memory,
            "archival_memory": archival_results,
            "_meta": {
                "mode": "experimental",
                "results_count": len(archival_results) if archival_results else 0,
                "latency_ms": round(latency_ms, 2),
            },
        }

        # Record metrics
        get_metrics().record_retrieval(
            agent_name=None,
            round_num=None,
            mode=MemoryMode.EXPERIMENTAL,
            results_count=len(archival_results) if archival_results else 0,
            latency_ms=latency_ms,
            provider_class="ExperimentalMemoryService",
            query=query,
        )

        logger.info(
            "ExperimentalMemory.retrieve: query='%.80s' k=%d results=%d latency=%.1fms",
            query, k, len(archival_results) if archival_results else 0, latency_ms,
        )

        return result

    def _retrieve_archival(self, query: str, k: int) -> List[str]:
        if not self.collection:
            return []
        
        use_fallback = False
        query_embedding = None

        if self.embedder:
            try:
                query_embedding = self.embedder.embed_texts([query])[0]
            except Exception as e:
                logger.error(f"Embedding failed for query: {e}. Falling back to keyword search.")
                use_fallback = True
        else:
            use_fallback = True

        if not use_fallback:
            try:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=k
                )
                # ChromaDB query returns documents in results['documents']
                if results and 'documents' in results and results['documents']:
                    return results['documents'][0]
            except Exception as e:
                logger.error(f"ChromaDB query failed: {e}")
                use_fallback = True

        if use_fallback:
            self.fallback_count += 1
            logger.info(f"Using keyword search fallback (Total: {self.fallback_count})")
            # Fallback simple: obtener todos y filtrar (No eficiente para producción real, pero ok para spike)
            all_data = self.collection.get()
            if not all_data or not all_data['documents']:
                return []
            
            scored_results = []
            query_words = set(query.lower().split())
            for doc in all_data['documents']:
                doc_lower = doc.lower()
                score = 0
                if query.lower() in doc_lower: score += 10
                for word in query_words:
                    if word in doc_lower: score += 1
                if score > 0:
                    scored_results.append((score, doc))
            
            scored_results.sort(key=lambda x: x[0], reverse=True)
            return [s[1] for s in scored_results[:k]]
        
        return []
