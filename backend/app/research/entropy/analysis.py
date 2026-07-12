"""
High-level across-persona diversity reports (Phase-1 case selection).

``across_persona_report`` bundles the per-field categorical entropy, lexical
diversity and (optional) embedding diversity for one population of personas.
``rank_cases`` orders several such reports by the model-agnostic
``categorical_diversity_index`` — the key used to pick the comparison case.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from . import metrics
from .personas import persona_texts


def lexical_diversity(texts: Sequence[str]) -> dict:
    return {
        "type_token_ratio": metrics.type_token_ratio(texts),
        "distinct_1": metrics.distinct_n(texts, 1),
        "distinct_2": metrics.distinct_n(texts, 2),
        "self_bleu": metrics.self_bleu(texts),  # inverse diversity: higher = more repetitive
    }


def categorical_diversity_index(categorical_report: dict) -> float:
    """Mean normalized entropy across populated fields → [0, 1]. Model-agnostic ranking key."""
    vals = [v["normalized_entropy"] for v in categorical_report.values() if v.get("n", 0) > 0]
    return sum(vals) / len(vals) if vals else 0.0


def across_persona_report(
    profiles: Sequence[dict],
    embedder=None,
    with_embeddings: bool = False,
    label: Optional[str] = None,
) -> dict:
    """Diversity report for one persona population. Embeddings are opt-in."""
    texts = persona_texts(profiles)
    categorical = metrics.profile_categorical_report(profiles)
    report = {
        "label": label,
        "n_personas": len(profiles),
        "categorical": categorical,
        "categorical_diversity_index": categorical_diversity_index(categorical),
        "lexical": lexical_diversity(texts),
    }
    if with_embeddings:
        from . import embeddings as emb
        from .embedder import get_embedder

        e = embedder or get_embedder()
        vecs = e.embed_texts(list(texts))
        report["embeddings"] = {
            "embedder": getattr(e, "name", "unknown"),
            "vendi_score": emb.vendi_score(vecs),
            "mean_pairwise_distance": emb.mean_pairwise_distance(vecs),
        }
    return report


def rank_cases(reports: List[dict]) -> List[dict]:
    """Order reports by categorical diversity (descending). The first is the selected case."""
    return sorted(reports, key=lambda r: r.get("categorical_diversity_index", 0.0), reverse=True)
