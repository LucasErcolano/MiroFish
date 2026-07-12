"""
Embedding-based diversity metrics (optional: require numpy).

These operate on already-computed embedding vectors so the math stays pure and
unit-testable. Getting the vectors (real embedder vs offline fallback) is the
job of ``embedder.py``.

- ``vendi_score``: the *effective number of distinct items* — exp of the Shannon
  entropy of the eigenvalues of the normalized similarity (Gram) matrix
  (Friedman & Dieng, 2022). Ranges [1, n]: 1 = all identical, n = all orthogonal.
  This is the embedding analogue of categorical entropy and is the secondary
  across-persona metric.
- ``mean_pairwise_distance``: average cosine distance between all pairs.
- ``embedding_drift``: for an ordered sequence of vectors (e.g. one response per
  start/mid/end checkpoint), the step-by-step and endpoint distances — the basis
  of the intra-persona temporal drift metric.
"""

from __future__ import annotations

from typing import List, Sequence


def _np():
    try:
        import numpy as np
    except ImportError as e:  # pragma: no cover - exercised only without numpy
        raise RuntimeError(
            "Embedding metrics require numpy. Install it or use the stdlib metrics in metrics.py."
        ) from e
    return np


def _normalize_rows(matrix):
    np = _np()
    X = np.asarray(matrix, dtype=float)
    if X.ndim != 2:
        raise ValueError("embeddings must be a 2D array (n_items, dim)")
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return X / norms


def cosine_similarity_matrix(embeddings: Sequence[Sequence[float]]):
    """PSD Gram matrix of L2-normalized rows (unit diagonal)."""
    Xn = _normalize_rows(embeddings)
    return Xn @ Xn.T


def vendi_score(embeddings: Sequence[Sequence[float]]) -> float:
    """Effective number of distinct items via eigenvalue entropy of the cosine Gram matrix."""
    np = _np()
    n = len(embeddings)
    if n == 0:
        return 0.0
    if n == 1:
        return 1.0
    K = cosine_similarity_matrix(embeddings)
    # K is X X^T of normalized rows → PSD with unit diagonal, so eigvals(K/n) sum to 1.
    w = np.linalg.eigvalsh(K / n)
    w = np.clip(w, 0.0, None)
    w = w[w > 1e-12]
    s = w.sum()
    if s <= 0:
        return 0.0
    w = w / s
    H = float(-np.sum(w * np.log(w)))
    return float(np.exp(H))


def mean_pairwise_distance(embeddings: Sequence[Sequence[float]]) -> float:
    """Average cosine distance (1 - cosine similarity) over all distinct pairs. [0, 2]."""
    np = _np()
    n = len(embeddings)
    if n < 2:
        return 0.0
    S = cosine_similarity_matrix(embeddings)
    iu = np.triu_indices(n, k=1)
    return float(np.mean(1.0 - S[iu]))


def embedding_drift(sequence: Sequence[Sequence[float]]) -> dict:
    """
    Drift metrics for an ordered sequence of vectors (one per checkpoint).

    Returns step distances (consecutive checkpoints), the total path length, and
    the start→end distance. Distances are cosine distances in [0, 2].
    """
    np = _np()
    if len(sequence) < 2:
        return {"steps": [], "path_length": 0.0, "endpoint_distance": 0.0}
    Xn = _normalize_rows(sequence)
    steps = [float(1.0 - float(Xn[i] @ Xn[i + 1])) for i in range(len(Xn) - 1)]
    endpoint = float(1.0 - float(Xn[0] @ Xn[-1]))
    return {
        "steps": steps,
        "path_length": float(sum(steps)),
        "endpoint_distance": endpoint,
    }
