"""
Intra-persona temporal drift metrics (Issue #28, D4).

Given a persona's answers to the same question across checkpoints (start → mid →
end), measure how much the persona changed:

- ``self_bleu`` across the sequence — INVERSE drift: high = the persona repeats
  itself across time (little change), low = it changed a lot. Model-agnostic,
  no embedder.
- ``embedding_drift`` — step distances, total path length, and start→end
  distance in embedding space (optional; needs an embedder).
- ``stance_js_divergence`` — Jensen-Shannon divergence between the population's
  stance/sentiment label distribution at consecutive checkpoints (caller
  supplies the labels).

Input ``sequences`` is the output of ``checkpoints.responses_to_sequences``:
a dict mapping (persona_id, question_id, platform) → ordered list of responses.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from . import metrics


def _mean(values: Sequence[float]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def _mean_steps(step_lists: Sequence[Sequence[float]]) -> List[float]:
    """Mean of the i-th step distance across sequences that share the same length."""
    if not step_lists:
        return []
    width = max(len(s) for s in step_lists)
    out = []
    for i in range(width):
        col = [s[i] for s in step_lists if len(s) > i]
        out.append(_mean(col))
    return out


def temporal_drift_report(
    sequences: Dict[tuple, List[str]],
    embedder=None,
    with_embeddings: bool = True,
) -> dict:
    """Per-sequence and aggregate drift over checkpoint response sequences."""
    e = None
    emb_mod = None
    if with_embeddings:
        from . import embeddings as emb_mod  # noqa: F811
        from .embedder import get_embedder

        e = embedder or get_embedder()

    per_seq: Dict[str, dict] = {}
    self_bleus: List[float] = []
    drifts: List[dict] = []

    for key, seq in sequences.items():
        if len(seq) < 2:
            continue
        sb = metrics.self_bleu(seq)
        self_bleus.append(sb)
        entry = {"n_checkpoints": len(seq), "self_bleu": sb}
        if with_embeddings:
            d = emb_mod.embedding_drift(e.embed_texts(list(seq)))
            entry["embedding_drift"] = d
            drifts.append(d)
        per_seq[str(key)] = entry

    aggregate: dict = {
        "n_sequences": len(per_seq),
        "mean_self_bleu": _mean(self_bleus),  # high = low drift
    }
    if drifts:
        aggregate["embedder"] = getattr(e, "name", "unknown")
        aggregate["mean_path_length"] = _mean([d["path_length"] for d in drifts])
        aggregate["mean_endpoint_distance"] = _mean([d["endpoint_distance"] for d in drifts])
        aggregate["mean_step_distances"] = _mean_steps([d["steps"] for d in drifts])

    return {"aggregate": aggregate, "per_sequence": per_seq}


def stance_js_divergence(labels_by_checkpoint: Dict[str, Sequence]) -> dict:
    """
    JS divergence of a categorical label distribution across checkpoints.

    ``labels_by_checkpoint`` maps a checkpoint label (in temporal order) to the
    list of per-persona labels at that checkpoint (e.g. stance: supporting /
    opposing / neutral). Returns consecutive divergences and the start→end one.
    Base-2 JS → [0, 1].
    """
    keys = list(labels_by_checkpoint.keys())
    consecutive = []
    for i in range(len(keys) - 1):
        consecutive.append({
            "from": keys[i],
            "to": keys[i + 1],
            "js": metrics.jensen_shannon_divergence(
                labels_by_checkpoint[keys[i]], labels_by_checkpoint[keys[i + 1]]
            ),
        })
    endpoint = None
    if len(keys) >= 2:
        endpoint = metrics.jensen_shannon_divergence(
            labels_by_checkpoint[keys[0]], labels_by_checkpoint[keys[-1]]
        )
    return {"consecutive": consecutive, "endpoint": endpoint}
