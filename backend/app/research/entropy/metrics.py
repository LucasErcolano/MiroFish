"""
Línea 6 — diversity / entropy metrics.

Pure-stdlib, model-agnostic metrics for comparing how much variety an LLM
produces when it populates and runs a MiroFish world. These functions take
plain Python data (label lists, text lists, probability dicts) and have **no
network or numpy dependency**, so they are the primary metrics for the cheap
Phase-1 case-selection step and run anywhere.

Embedding-based metrics (Vendi score, centroid drift) live in ``embeddings.py``
and require numpy + an embedder; they are optional.

Conventions
-----------
- Shannon entropy is reported in **bits** (base 2) unless ``base`` is changed.
- ``effective_n`` is the Hill number of order 1 (``base ** H``): the number of
  equally-likely categories that would yield the same entropy. Easier to read
  than raw bits when comparing fields with different cardinalities.
- ``self_bleu`` is an **inverse** diversity signal: higher Self-BLEU means the
  texts repeat each other, i.e. *less* diverse.
- Jensen-Shannon divergence is symmetric and, in base 2, bounded to [0, 1].
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable, List, Mapping, Sequence, Optional

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)

# Categorical persona fields worth measuring entropy over (from OasisAgentProfile).
CATEGORICAL_FIELDS = ("gender", "mbti", "country", "profession")


def tokenize(text: Optional[str]) -> List[str]:
    """Lowercase word-token list. Unicode-aware, punctuation stripped."""
    return _TOKEN_RE.findall((text or "").lower())


def _ngrams(tokens: Sequence[str], n: int) -> List[tuple]:
    if n <= 0 or len(tokens) < n:
        return []
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


# --------------------------------------------------------------------------- #
# Entropy over categorical distributions
# --------------------------------------------------------------------------- #
def shannon_entropy(distribution, base: float = 2.0) -> float:
    """Entropy of a distribution given as a count/prob mapping or an iterable of counts."""
    if isinstance(distribution, Mapping):
        counts = list(distribution.values())
    else:
        counts = list(distribution)
    total = float(sum(counts))
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts:
        if c <= 0:
            continue
        p = c / total
        h -= p * math.log(p, base)
    return h


def _clean_labels(values: Iterable) -> List:
    return [v for v in values if v is not None and v != ""]


def categorical_entropy(values: Iterable, base: float = 2.0) -> float:
    """Shannon entropy (bits) of the label distribution. None/empty are dropped."""
    return shannon_entropy(Counter(_clean_labels(values)), base)


def normalized_entropy(values: Iterable, base: float = 2.0) -> float:
    """Entropy divided by log(k) → [0, 1]; comparable across fields of different cardinality."""
    counts = Counter(_clean_labels(values))
    k = len(counts)
    if k <= 1:
        return 0.0
    return shannon_entropy(counts, base) / math.log(k, base)


def effective_number(values: Iterable, base: float = 2.0) -> float:
    """Hill number q=1 (``base ** H``): effective count of equally-likely categories."""
    return base ** categorical_entropy(values, base)


# --------------------------------------------------------------------------- #
# Lexical diversity over free text
# --------------------------------------------------------------------------- #
def distinct_n(texts: Iterable[str], n: int = 2) -> float:
    """Ratio of unique n-grams to total n-grams across all texts (Li et al. 2016). [0, 1]."""
    all_ngrams: List[tuple] = []
    for t in texts:
        all_ngrams.extend(_ngrams(tokenize(t), n))
    if not all_ngrams:
        return 0.0
    return len(set(all_ngrams)) / len(all_ngrams)


def type_token_ratio(texts: Iterable[str]) -> float:
    """Unique tokens / total tokens across all texts. [0, 1]."""
    tokens: List[str] = []
    for t in texts:
        tokens.extend(tokenize(t))
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def _modified_precision(candidate: Sequence[str], references: Sequence[Sequence[str]], n: int) -> Optional[float]:
    cand_ngrams = Counter(_ngrams(candidate, n))
    if not cand_ngrams:
        return None
    max_ref: Counter = Counter()
    for ref in references:
        for g, c in Counter(_ngrams(ref, n)).items():
            if c > max_ref[g]:
                max_ref[g] = c
    clipped = sum(min(c, max_ref[g]) for g, c in cand_ngrams.items())
    total = sum(cand_ngrams.values())
    return clipped / total if total else None


def _sentence_bleu(candidate: Sequence[str], references: Sequence[Sequence[str]], max_n: int = 4) -> float:
    precisions: List[float] = []
    for n in range(1, max_n + 1):
        p = _modified_precision(candidate, references, n)
        if p is None:
            continue
        precisions.append(p if p > 0 else 1e-9)  # epsilon-smooth zeros to avoid log(0)
    if not precisions:
        return 0.0
    log_p = sum(math.log(p) for p in precisions) / len(precisions)
    bleu = math.exp(log_p)
    c = len(candidate)
    if c == 0:
        return 0.0
    ref_lens = [len(r) for r in references] or [0]
    r = min(ref_lens, key=lambda rl: (abs(rl - c), rl))
    bp = 1.0 if c > r else (math.exp(1 - r / c) if c > 0 else 1.0)
    return bp * bleu


def self_bleu(texts: Iterable[str], max_n: int = 4) -> float:
    """Mean BLEU of each text against all the others. INVERSE diversity: higher = more repetitive. [0, 1]."""
    toks = [t for t in (tokenize(x) for x in texts) if t]
    if len(toks) < 2:
        return 0.0
    scores = []
    for i in range(len(toks)):
        refs = toks[:i] + toks[i + 1:]
        scores.append(_sentence_bleu(toks[i], refs, max_n))
    return sum(scores) / len(scores)


# --------------------------------------------------------------------------- #
# Divergence between distributions (temporal / cross-model comparison)
# --------------------------------------------------------------------------- #
def _to_prob(dist) -> dict:
    items = dist if isinstance(dist, Mapping) else Counter(_clean_labels(dist))
    total = float(sum(items.values()))
    if total <= 0:
        return {}
    return {k: v / total for k, v in items.items()}


def kl_divergence(p: Mapping, q: Mapping, base: float = 2.0) -> float:
    """KL(p || q). Terms where q==0 are skipped; use the JS mixture for a safe symmetric measure."""
    d = 0.0
    for k, pv in p.items():
        if pv <= 0:
            continue
        qv = q.get(k, 0.0)
        if qv <= 0:
            continue
        d += pv * math.log(pv / qv, base)
    return d


def jensen_shannon_divergence(p, q, base: float = 2.0) -> float:
    """Symmetric JS divergence between two distributions (prob dicts or label iterables). Base 2 → [0, 1]."""
    pp, qq = _to_prob(p), _to_prob(q)
    keys = set(pp) | set(qq)
    m = {k: 0.5 * (pp.get(k, 0.0) + qq.get(k, 0.0)) for k in keys}
    return 0.5 * kl_divergence(pp, m, base) + 0.5 * kl_divergence(qq, m, base)


# --------------------------------------------------------------------------- #
# Persona-level categorical report (Phase-1 across-persona diversity)
# --------------------------------------------------------------------------- #
def age_bucket(age, width: int = 10) -> Optional[str]:
    """Bucket a numeric age into a ``lo-hi`` band so it can be treated categorically."""
    if age is None or age == "":
        return None
    try:
        a = int(age)
    except (TypeError, ValueError):
        return None
    lo = (a // width) * width
    return f"{lo}-{lo + width - 1}"


def _coerce_topics(value) -> List[str]:
    """interested_topics may be a list (json) or a ';'-joined string (twitter csv)."""
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [x.strip() for x in re.split(r"[;,]", value) if x.strip()]
    if isinstance(value, (list, tuple)):
        return [str(x).strip() for x in value if str(x).strip()]
    return []


def _field_stats(values: Iterable, base: float = 2.0) -> dict:
    cleaned = _clean_labels(values)
    return {
        "entropy_bits": categorical_entropy(cleaned, base),
        "normalized_entropy": normalized_entropy(cleaned, base),
        "effective_n": effective_number(cleaned, base),
        "unique": len(set(cleaned)),
        "n": len(cleaned),
    }


def profile_categorical_report(
    profiles: Sequence[Mapping],
    fields: Sequence[str] = CATEGORICAL_FIELDS,
    base: float = 2.0,
) -> dict:
    """
    Per-field categorical entropy report over a list of persona dicts.

    Accepts dicts in OasisAgentProfile.to_dict()/reddit/twitter shapes. Adds
    derived ``age_bucket`` and flattened ``interested_topics`` fields.
    """
    report: dict = {}
    for f in fields:
        report[f] = _field_stats([p.get(f) for p in profiles], base)
    report["age_bucket"] = _field_stats([age_bucket(p.get("age")) for p in profiles], base)
    topics: List[str] = []
    for p in profiles:
        topics.extend(_coerce_topics(p.get("interested_topics")))
    report["interested_topics"] = _field_stats(topics, base)
    return report
