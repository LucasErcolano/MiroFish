"""Experimental memory service.

This implements a dual-layer memory path:

- Core memory: compact persona/objective/event JSON.
- Archival memory: ChromaDB when embeddings are configured, JSON fallback when
  running offline or in tests.

The JSON fallback is intentional. It keeps smoke tests deterministic and avoids
Windows file-lock cleanup issues from long-lived Chroma clients when no embedder
is configured.
"""

from __future__ import annotations

import csv
import json
import math
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import chromadb

from ..config import Config
from ..utils.embedding_client import EmbeddingClient
from ..utils.logger import get_logger
from .memory_provider import MemoryProvider

logger = get_logger("mirofish.experimental_memory")


class ExperimentalMemoryService(MemoryProvider):
    def __init__(self, simulation_id: str):
        self.simulation_id = simulation_id
        self.data_dir = os.path.join(Config.DATA_DIR, "simulations", simulation_id)
        self.core_memory_path = os.path.join(self.data_dir, "core_memory.json")
        self.json_memory_path = os.path.join(self.data_dir, "experimental_memory.json")
        self.chroma_path = os.path.join(self.data_dir, "chroma_db")

        os.makedirs(self.data_dir, exist_ok=True)

        self.embedder = self._get_embedder()
        self.core_memory = self._load_core_memory()
        self.fallback_count = 0
        self.chroma_client = None
        self.collection = None

        try:
            if self.embedder:
                self.chroma_client = chromadb.PersistentClient(path=self.chroma_path)
                self.collection = self.chroma_client.get_or_create_collection(
                    name="archival_memory"
                )
                logger.info(f"ChromaDB initialized for simulation {simulation_id}")
                self._migrate_from_json()
            else:
                logger.info(f"Using JSON archival memory fallback for simulation {simulation_id}")
        except Exception as exc:
            logger.error(f"Failed to initialize ChromaDB: {exc}")
            self.collection = None

    def get_stats(self) -> Dict[str, Any]:
        if self.collection:
            total_episodes = self.collection.count()
            storage_engine = "ChromaDB"
        else:
            total_episodes = len(self._load_json_memories())
            storage_engine = "JSON"

        return {
            "total_episodes": total_episodes,
            "core_memory_populated": bool(self.core_memory.get("persona")),
            "fallback_count": self.fallback_count,
            "using_vector_search": self.embedder is not None,
            "storage_engine": storage_engine,
        }

    def _migrate_from_json(self) -> None:
        old_storage_path = self.json_memory_path
        if os.path.exists(old_storage_path) and self.collection:
            try:
                with open(old_storage_path, "r", encoding="utf-8") as f:
                    memories = json.load(f)

                if memories:
                    logger.info(f"Migrating {len(memories)} episodes from JSON to ChromaDB")
                    for memory in memories:
                        self.add_memory(
                            text=memory.get("text", ""),
                            metadata=memory.get("metadata", {}),
                            _timestamp=memory.get("timestamp"),
                        )
                    os.rename(old_storage_path, old_storage_path + ".migrated")
            except Exception as exc:
                logger.error(f"Migration failed: {exc}")

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
                model=model,
            )
        except Exception as exc:
            logger.error(f"Failed to initialize embedding client: {exc}")
            return None

    def _load_core_memory(self) -> Dict[str, Any]:
        if os.path.exists(self.core_memory_path):
            with open(self.core_memory_path, "r", encoding="utf-8") as f:
                return json.load(f)

        profiles = self._load_agent_profiles()
        if profiles:
            profile = profiles[0]
            core = {
                "persona": profile.get("persona", profile.get("bio", "Standard MiroFish Agent")),
                "objectives": profile.get("interested_topics", []),
                "key_events": [],
            }
            self._write_core_memory(core)
            return core

        return {
            "persona": "Standard MiroFish Agent",
            "objectives": [],
            "key_events": [],
        }

    def _load_agent_profiles(self) -> List[Dict[str, Any]]:
        sim_dir = os.path.join(Config.UPLOAD_FOLDER, "simulations", self.simulation_id)
        reddit_path = os.path.join(sim_dir, "reddit_profiles.json")
        if os.path.exists(reddit_path):
            try:
                with open(reddit_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        twitter_path = os.path.join(sim_dir, "twitter_profiles.csv")
        if os.path.exists(twitter_path):
            try:
                with open(twitter_path, "r", encoding="utf-8") as f:
                    return list(csv.DictReader(f))
            except Exception:
                pass
        return []

    def _write_core_memory(self, core_data: Dict[str, Any]) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.core_memory_path, "w", encoding="utf-8") as f:
            json.dump(core_data, f, ensure_ascii=False, indent=2)

    def save_core_memory(self, core_data: Dict[str, Any]) -> None:
        current = getattr(
            self,
            "core_memory",
            {
                "persona": "Standard MiroFish Agent",
                "objectives": [],
                "key_events": [],
            },
        )
        current.update(core_data)
        self.core_memory = current
        self._write_core_memory(self.core_memory)

    def _load_json_memories(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.json_memory_path):
            return []
        try:
            with open(self.json_memory_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.error(f"Failed to load JSON archival memory: {exc}")
            return []

    def _write_json_memories(self, memories: List[Dict[str, Any]]) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.json_memory_path, "w", encoding="utf-8") as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def add_memories(self, activities: List[Dict[str, Any]]) -> None:
        if not activities:
            return

        if not self.collection:
            memories = self._load_json_memories()
            now = time.time()
            for item in activities:
                memories.append(
                    {
                        "text": item.get("text", ""),
                        "metadata": item.get("metadata", {}),
                        "embedding": item.get("embedding"),
                        "timestamp": item.get("timestamp", now),
                    }
                )
            self._write_json_memories(memories)
            return

        ids = [str(uuid.uuid4()) for _ in activities]
        documents = []
        metadatas = [item.get("metadata", {}) for item in activities]

        for item in activities:
            text = item.get("text", "")
            agent_name = item.get("metadata", {}).get("agent_name")
            if agent_name and not text.startswith(f"{agent_name}:"):
                documents.append(f"Agent [{agent_name}]: {text}")
            else:
                documents.append(text)

        now = time.time()
        for meta in metadatas:
            meta["timestamp"] = now

        embeddings = None
        if self.embedder:
            try:
                embeddings = self.embedder.embed_texts(documents)
            except Exception as exc:
                logger.error(f"Failed to batch embed memory for ChromaDB: {exc}")

        try:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )
        except Exception as exc:
            logger.error(f"Error adding to ChromaDB: {exc}")

    def add_memory(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        _timestamp: Optional[float] = None,
    ) -> None:
        meta = metadata or {}
        if _timestamp:
            meta["timestamp"] = _timestamp
        self.add_memories([{"text": text, "metadata": meta}])

    def retrieve(self, query: str, k: int = 5) -> Dict[str, Any]:
        return {
            "core_memory": self.core_memory,
            "archival_memory": self._retrieve_archival(query, k),
        }

    def _retrieve_archival(self, query: str, k: int) -> List[str]:
        if not self.collection:
            self.fallback_count += 1
            memories = self._load_json_memories()
            query_words = set(query.lower().split())
            scored_results = []
            for memory in memories:
                doc = str(memory.get("text", ""))
                doc_lower = doc.lower()
                score = 0
                if query.lower() in doc_lower:
                    score += 10
                for word in query_words:
                    if word in doc_lower:
                        score += 1
                if score > 0:
                    scored_results.append((score, doc))
            scored_results.sort(key=lambda item: item[0], reverse=True)
            return [doc for _, doc in scored_results[:k]]

        use_fallback = False
        query_embedding = None

        if self.embedder:
            try:
                query_embedding = self.embedder.embed_texts([query])[0]
            except Exception as exc:
                logger.error(f"Embedding failed for query: {exc}. Falling back to keyword search.")
                use_fallback = True
        else:
            use_fallback = True

        if not use_fallback:
            try:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=k,
                )
                if results and "documents" in results and results["documents"]:
                    return results["documents"][0]
            except Exception as exc:
                logger.error(f"ChromaDB query failed: {exc}")
                use_fallback = True

        if use_fallback:
            self.fallback_count += 1
            all_data = self.collection.get()
            if not all_data or not all_data["documents"]:
                return []

            scored_results = []
            query_words = set(query.lower().split())
            for doc in all_data["documents"]:
                doc_lower = doc.lower()
                score = 0
                if query.lower() in doc_lower:
                    score += 10
                for word in query_words:
                    if word in doc_lower:
                        score += 1
                if score > 0:
                    scored_results.append((score, doc))

            scored_results.sort(key=lambda item: item[0], reverse=True)
            return [doc for _, doc in scored_results[:k]]

        return []
