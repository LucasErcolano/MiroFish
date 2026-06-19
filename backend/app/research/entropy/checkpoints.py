"""
Checkpoint-interview plumbing (pure, testable) for the intra-persona temporal
drift study.

The harness interviews every agent with a fixed question set at several points
in the simulation (start / mid / end). This module owns the parts that don't
need a live server:

- :func:`checkpoint_rounds` — evenly spaced round numbers + labels.
- :func:`parse_interview_result` — normalize the ``/api/simulation/interview``
  response (single- and dual-platform shapes) to ``{platform: text}``.
- the response record schema + :func:`save_responses` / :func:`load_responses`.
- :func:`responses_to_sequences` — group records into ordered per-(persona,
  question) text sequences for the temporal metrics.

The live HTTP orchestration lives in ``scripts/entropy_checkpoint_interview.py``.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Sequence

# Default fixed interview set. Same questions at every checkpoint so responses
# are comparable across time. Keep them tool-free / opinion-style.
DEFAULT_QUESTIONS = [
    {"id": "stance", "text": "What is your current position on the main issue, and why?"},
    {"id": "outlook", "text": "How do you expect things to unfold from here?"},
    {"id": "influence", "text": "Whose views have influenced you most so far?"},
]

CHECKPOINT_LABELS_3 = ("start", "mid", "end")


def checkpoint_rounds(total_rounds: int, n_checkpoints: int = 3) -> List[dict]:
    """Evenly spaced checkpoints over [0, total_rounds]. n=3 → start/mid/end."""
    if total_rounds < 0:
        raise ValueError("total_rounds must be >= 0")
    n = max(2, int(n_checkpoints))
    if n == 3:
        labels = list(CHECKPOINT_LABELS_3)
    else:
        labels = [f"c{i}" for i in range(n)]
    out = []
    for i in range(n):
        rnd = 0 if n == 1 else round(total_rounds * i / (n - 1))
        out.append({"label": labels[i], "round": int(rnd), "order": i})
    return out


def parse_interview_result(result: dict, platform: Optional[str] = None) -> Dict[str, str]:
    """
    Normalize the ``data.result`` object of an interview response to {platform: text}.

    Handles both shapes:
    - dual-platform: ``{"platforms": {"twitter": {"response": ...}, "reddit": {...}}}``
    - single-platform: ``{"response": ..., "platform": "twitter"}``
    """
    if not isinstance(result, dict):
        return {}
    if isinstance(result.get("platforms"), dict):
        out = {}
        for plat, obj in result["platforms"].items():
            if isinstance(obj, dict) and obj.get("response") is not None:
                out[plat] = obj["response"]
        return out
    if result.get("response") is not None:
        key = result.get("platform") or platform or "default"
        return {key: result["response"]}
    return {}


def parse_batch_response(resp: dict) -> List[dict]:
    """
    Normalize a ``/api/simulation/interview/batch`` response to a flat list of
    ``{agent_id, platform, response}``.

    The batch envelope is ``data.result.results`` — a dict keyed by
    ``"{platform}_{agent_id}"`` whose values are single-platform result objects
    (``{agent_id, response, platform}``). A list form is also tolerated.
    """
    data = resp.get("data", resp) if isinstance(resp, dict) else {}
    result = data.get("result", data) if isinstance(data, dict) else {}
    results = result.get("results", {}) if isinstance(result, dict) else {}
    if isinstance(results, dict):
        items = list(results.values())
    elif isinstance(results, list):
        items = results
    else:
        items = []
    out = []
    for obj in items:
        if not isinstance(obj, dict):
            continue
        aid = obj.get("agent_id")
        for plat, text in parse_interview_result(obj).items():
            out.append({"agent_id": aid, "platform": plat, "response": text})
    return out


def make_record(
    persona_id,
    checkpoint: dict,
    question: dict,
    platform: str,
    response: str,
    persona_name: Optional[str] = None,
) -> dict:
    """One normalized checkpoint response record."""
    return {
        "persona_id": persona_id,
        "persona_name": persona_name,
        "checkpoint": checkpoint["label"],
        "checkpoint_order": checkpoint.get("order"),
        "round": checkpoint.get("round"),
        "question_id": question["id"],
        "question": question["text"],
        "platform": platform,
        "response": response,
    }


def save_responses(records: Sequence[dict], path: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(records), f, ensure_ascii=False, indent=2)
    return path


def load_responses(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def responses_to_sequences(records: Sequence[dict], platform: Optional[str] = None) -> Dict[tuple, List[str]]:
    """
    Group records into ordered text sequences keyed by (persona_id, question_id, platform).

    Within each key, responses are ordered by ``checkpoint_order`` so the result
    is the persona's answer to one question across start → mid → end.
    """
    buckets: Dict[tuple, List[tuple]] = {}
    for r in records:
        if platform is not None and r.get("platform") != platform:
            continue
        key = (r.get("persona_id"), r.get("question_id"), r.get("platform"))
        buckets.setdefault(key, []).append((r.get("checkpoint_order", 0), r.get("response", "")))
    return {k: [resp for _, resp in sorted(v, key=lambda t: t[0])] for k, v in buckets.items()}
