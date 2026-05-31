"""
Embedding client wrapper for OpenAI-compatible embedding APIs.
"""

import os
import json
import hashlib
from typing import List, Optional, Dict

from openai import OpenAI
from ..config import Config

class EmbeddingClient:
    """Thin wrapper around OpenAI-compatible embedding endpoints with local caching."""

    def __init__(
        self,
        api_key: Optional[str],
        base_url: str,
        model: str,
        batch_size: int = 32,
    ):
        if not base_url:
            raise ValueError("Embedding base_url 未配置")
        if not model:
            raise ValueError("Embedding model 未配置")

        self.api_key = api_key or 'ollama'
        self.base_url = base_url
        self.model = model
        self.batch_size = max(1, int(batch_size))
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        
        # Cache setup
        self.cache_dir = os.path.join(Config.DATA_DIR, 'cache', 'embeddings')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_file = os.path.join(self.cache_dir, f"{hashlib.md5(model.encode()).hexdigest()}.json")
        self._cache = self._load_cache()

    def _load_cache(self) -> Dict[str, List[float]]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False)
        except:
            pass

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed texts in batches while preserving input order and utilizing cache."""
        if not texts:
            return []

        results = [None] * len(texts)
        to_embed_indices = []
        to_embed_texts = []

        for i, text in enumerate(texts):
            clean_text = str(text or ' ').strip()
            if clean_text in self._cache:
                results[i] = self._cache[clean_text]
            else:
                to_embed_indices.append(i)
                to_embed_texts.append(clean_text or ' ')

        if to_embed_texts:
            for start in range(0, len(to_embed_texts), self.batch_size):
                batch = to_embed_texts[start:start + self.batch_size]
                batch_indices = to_embed_indices[start:start + self.batch_size]
                
                response = self.client.embeddings.create(model=self.model, input=batch)
                data = sorted(response.data, key=lambda item: item.index)
                
                for j, item in enumerate(data):
                    original_idx = batch_indices[j]
                    results[original_idx] = item.embedding
                    # Update cache
                    self._cache[batch[j]] = item.embedding
            
            self._save_cache()

        return results
