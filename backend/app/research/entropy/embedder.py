"""
Embedder adapter for the entropy line.

Two backends, same interface (``embed_texts(list[str]) -> list[list[float]]``):

- ``RealEmbedder``: wraps the project's :class:`EmbeddingClient`, configured from
  ``Config.get_graph_search_embedder_config()`` (the same embedder the graph
  search uses), so we reuse existing infra and its on-disk cache.
- ``HashingEmbedder``: a deterministic, offline, dependency-free fallback (the
  hashing trick). Identical texts map to identical vectors and disjoint
  vocabularies map to near-orthogonal vectors, so Vendi / drift behave sensibly
  in tests and smoke runs with no network.

``get_embedder()`` returns the real one when configured and importable, else the
offline fallback. It never raises on a missing/broken embedder — embedding
metrics are optional, so degrading to offline is the right default.
"""

from __future__ import annotations

import hashlib
from typing import List

from .metrics import tokenize


class HashingEmbedder:
    """Deterministic offline embedder via the hashing trick. No network, no numpy."""

    name = "hashing-offline"

    def __init__(self, dim: int = 256):
        self.dim = max(8, int(dim))

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t or "") for t in texts]

    def _embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        toks = tokenize(text)
        if not toks:
            # Avoid a degenerate all-zero vector; seed from the raw string.
            h = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
            vec[h % self.dim] = 1.0
            return vec
        for tok in toks:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if ((h >> 8) & 1) else -1.0
            vec[idx] += sign
        return vec


class RealEmbedder:
    """Wraps the project EmbeddingClient (OpenAI-compatible, with local cache)."""

    def __init__(self, client, name: str):
        self._client = client
        self.name = name

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return self._client.embed_texts(list(texts))


def get_embedder(prefer_real: bool = True, dim: int = 256):
    """Return a configured RealEmbedder, or the offline HashingEmbedder fallback."""
    if prefer_real:
        try:
            from ...config import Config
            from ...utils.embedding_client import EmbeddingClient

            cfg = Config.get_graph_search_embedder_config()
            if cfg.get("base_url") and cfg.get("model"):
                client = EmbeddingClient(
                    api_key=cfg.get("api_key"),
                    base_url=cfg["base_url"],
                    model=cfg["model"],
                )
                return RealEmbedder(client, name=f"real:{cfg['model']}")
        except Exception:  # noqa: BLE001 - any failure degrades to offline, by design
            pass
    return HashingEmbedder(dim=dim)
