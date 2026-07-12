"""
Metrics over the OASIS simulation output (Issue #28, Phase 2).

OASIS writes the run to a sqlite DB (``<platform>_simulation.db``): the ``post``
and ``comment`` tables hold generated content with ``user_id`` + ``created_at``
(the round/timestep), and ``user`` maps ``user_id`` -> ``agent_id``/``name``.

This module turns that into two metric families:

- **Output diversity** — how varied is a model's generated social content
  (distinct-n, Self-BLEU, type-token ratio, and optional Vendi over post text).
- **Posts-based temporal drift** — how much each persona's content changes from
  early to late rounds. This replaces injected checkpoint interviews (whose env
  is timing-fragile) with content the run already produced: robust and free.
"""

from __future__ import annotations

import glob
import os
import sqlite3
from typing import List, Optional, Sequence

from . import metrics


def find_sim_db(sim_dir: str) -> Optional[str]:
    """Return the simulation sqlite db in a sim dir (twitter preferred)."""
    for name in ("twitter_simulation.db", "reddit_simulation.db", "*_simulation.db", "*.db"):
        matches = sorted(glob.glob(os.path.join(sim_dir, name)))
        if matches:
            return matches[0]
    return None


def load_posts(db_path: str, include_comments: bool = True) -> List[dict]:
    """
    Load generated content rows: {user_id, agent_id, name, content, created_at, kind}.

    ``created_at`` is the simulation timestep/round (OASIS stores it as the step).
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # user_id -> (agent_id, name)
    umap = {}
    try:
        for r in cur.execute("SELECT user_id, agent_id, name FROM user"):
            umap[r["user_id"]] = (r["agent_id"], r["name"])
    except sqlite3.Error:
        pass

    rows: List[dict] = []

    def _collect(table: str, kind: str):
        try:
            for r in cur.execute(f"SELECT user_id, content, created_at FROM {table}"):
                content = (r["content"] or "").strip()
                if not content:
                    continue
                aid, name = umap.get(r["user_id"], (None, None))
                rows.append({
                    "user_id": r["user_id"],
                    "agent_id": aid,
                    "name": name,
                    "content": content,
                    "created_at": r["created_at"],
                    "kind": kind,
                })
        except sqlite3.Error:
            pass

    _collect("post", "post")
    if include_comments:
        _collect("comment", "comment")
    conn.close()
    return rows


def output_diversity(posts: Sequence[dict], embedder=None, with_embeddings: bool = False) -> dict:
    """Diversity of all generated content for one run/model."""
    texts = [p["content"] for p in posts]
    n_authors = len({p["user_id"] for p in posts})
    report = {
        "n_posts": len(texts),
        "n_authors": n_authors,
        "type_token_ratio": metrics.type_token_ratio(texts),
        "distinct_1": metrics.distinct_n(texts, 1),
        "distinct_2": metrics.distinct_n(texts, 2),
        "self_bleu": metrics.self_bleu(texts),  # inverse diversity
    }
    if with_embeddings and texts:
        from . import embeddings as emb
        from .embedder import get_embedder

        e = embedder or get_embedder()
        vecs = e.embed_texts(list(texts))
        report["embedder"] = getattr(e, "name", "unknown")
        report["vendi_score"] = emb.vendi_score(vecs)
        report["mean_pairwise_distance"] = emb.mean_pairwise_distance(vecs)
    return report


def _rank_bucketer(posts, n_buckets):
    """
    Map each distinct created_at to an early..late bucket by rank quantile.

    Robust to both integer time-steps (twitter) and ISO datetime strings
    (reddit), since both sort correctly within a single run.
    """
    times = sorted({p["created_at"] for p in posts if p.get("created_at") is not None})
    n = len(times)
    rank = {t: i for i, t in enumerate(times)}

    def bucket(value):
        if n == 0:
            return 0
        return min(n_buckets - 1, int(rank[value] / n * n_buckets))

    return bucket, n


def temporal_drift_from_posts(
    posts: Sequence[dict],
    n_buckets: int = 3,
    embedder=None,
    with_embeddings: bool = True,
) -> dict:
    """
    Intra-persona drift from posts over time.

    Posts are bucketed by ``created_at`` into ``n_buckets`` (early..late). For each
    author present in >=2 buckets, concatenate their text per bucket and measure
    drift across buckets (Self-BLEU = repetition; embedding endpoint distance).
    Also reports population-level early-vs-late drift over the whole post sets.
    """
    bucket, n_times = _rank_bucketer(posts, n_buckets)
    if n_times == 0:
        return {"aggregate": {"n_personas_with_drift": 0}, "per_persona": {}}

    # author -> bucket -> [texts]
    by_author: dict = {}
    buckets_all: dict = {}
    for p in posts:
        t = p.get("created_at")
        if t is None:
            continue
        b = bucket(t)
        by_author.setdefault(p["user_id"], {}).setdefault(b, []).append(p["content"])
        buckets_all.setdefault(b, []).append(p["content"])

    e = None
    emb = None
    if with_embeddings:
        from . import embeddings as emb  # noqa: F811
        from .embedder import get_embedder

        e = embedder or get_embedder()

    per_persona: dict = {}
    self_bleus: List[float] = []
    endpoint_dists: List[float] = []
    for uid, buckets in by_author.items():
        if len(buckets) < 2:
            continue
        ordered = [" ".join(buckets[b]) for b in sorted(buckets)]
        sb = metrics.self_bleu(ordered)
        self_bleus.append(sb)
        entry = {"n_buckets": len(buckets), "self_bleu": sb}
        if with_embeddings:
            d = emb.embedding_drift(e.embed_texts(ordered))
            entry["embedding_drift"] = d
            endpoint_dists.append(d["endpoint_distance"])
        per_persona[str(uid)] = entry

    aggregate = {
        "n_personas_with_drift": len(per_persona),
        "mean_self_bleu": (sum(self_bleus) / len(self_bleus)) if self_bleus else None,
    }
    if endpoint_dists:
        aggregate["mean_endpoint_distance"] = sum(endpoint_dists) / len(endpoint_dists)

    # population early-vs-late
    if with_embeddings and 0 in buckets_all and (n_buckets - 1) in buckets_all:
        early = " ".join(buckets_all[0])
        late = " ".join(buckets_all[n_buckets - 1])
        d = emb.embedding_drift(e.embed_texts([early, late]))
        aggregate["population_early_late_distance"] = d["endpoint_distance"]

    return {"aggregate": aggregate, "per_persona": per_persona}
