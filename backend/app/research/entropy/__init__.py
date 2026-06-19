"""
Línea 6 — Diversity & entropy metrics for MiroFish (Issue #28).

Model-agnostic metrics to compare how much variety an LLM produces when it
populates and runs a simulated world. See ``docs/linea6_entropia.md``.

Public surface:
- Stdlib metrics (no deps): ``metrics`` module.
- Optional embedding metrics (numpy): ``embeddings`` module.
- Embedder adapter (real or offline): ``get_embedder``.
- Profile loaders: ``personas`` module.
"""

from .metrics import (
    CATEGORICAL_FIELDS,
    age_bucket,
    categorical_entropy,
    distinct_n,
    effective_number,
    jensen_shannon_divergence,
    kl_divergence,
    normalized_entropy,
    profile_categorical_report,
    self_bleu,
    shannon_entropy,
    tokenize,
    type_token_ratio,
)
from .embedder import HashingEmbedder, RealEmbedder, get_embedder
from .personas import (
    load_profiles,
    load_profiles_from_sim_dir,
    persona_texts,
)

__all__ = [
    "CATEGORICAL_FIELDS",
    "age_bucket",
    "categorical_entropy",
    "distinct_n",
    "effective_number",
    "jensen_shannon_divergence",
    "kl_divergence",
    "normalized_entropy",
    "profile_categorical_report",
    "self_bleu",
    "shannon_entropy",
    "tokenize",
    "type_token_ratio",
    "HashingEmbedder",
    "RealEmbedder",
    "get_embedder",
    "load_profiles",
    "load_profiles_from_sim_dir",
    "persona_texts",
]
