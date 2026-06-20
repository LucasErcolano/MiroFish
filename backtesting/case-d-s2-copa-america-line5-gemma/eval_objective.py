#!/usr/bin/env python3
"""Evaluate Copa America 2024 final winner forecasts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional


GROUND_TRUTH = {
    "winner": "Argentina",
    "event": "Argentina defeated Colombia 1-0 after extra time in the 2024 Copa America final.",
}

POST_CUTOFF_RE = re.compile(
    r"(extra\s*time|tiempo\s+extra|lautaro|martinez\s+111|resultado\s+real|gan[oó]\s+la\s+final|post[- ]?cutoff|despues\s+del\s+13)",
    re.IGNORECASE,
)


def normalize_winner(value: Any) -> Optional[str]:
    text = str(value or "").strip().lower()
    if "argentina" in text and "colombia" not in text:
        return "Argentina"
    if "colombia" in text and "argentina" not in text:
        return "Colombia"
    if text == "argentina":
        return "Argentina"
    if text == "colombia":
        return "Colombia"
    return None


def to_number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        match = re.search(r"[0-9]+(?:[.,][0-9]+)?", str(value))
        if not match:
            return None
        number = float(match.group(0).replace(",", "."))
    return round(number, 4)


def to_probability(value: Any) -> Optional[float]:
    number = to_number(value)
    if number is None:
        return None
    if number > 1:
        number = number / 100
    return round(min(max(number, 0.0), 1.0), 4)


def source_count(items: Any) -> int:
    source_ids = set()
    for item in items or []:
        if not isinstance(item, dict):
            continue
        values = item.get("source_id") or item.get("source_ids") or []
        if isinstance(values, str):
            values = [values]
        for value in values:
            if str(value).strip():
                source_ids.add(str(value).strip())
    return len(source_ids)


def evaluate_structured(payload: Dict[str, Any], variant: str, model_policy: str, seed: int) -> Dict[str, Any]:
    predicted_winner = normalize_winner(payload.get("predicted_winner"))
    confidence = to_probability(payload.get("confidence"))
    winner_probability_point = to_probability(payload.get("winner_probability_point"))
    probability = payload.get("winner_probability_range", {}) or {}
    goal_margin = payload.get("predicted_goal_margin", {}) or {}
    winner_min = to_probability(probability.get("winner_min"))
    winner_max = to_probability(probability.get("winner_max"))
    if winner_min is None or winner_max is None:
        if predicted_winner == "Argentina":
            winner_min = to_probability(probability.get("argentina_min"))
            winner_max = to_probability(probability.get("argentina_max"))
        elif predicted_winner == "Colombia":
            winner_min = to_probability(probability.get("colombia_min"))
            winner_max = to_probability(probability.get("colombia_max"))
    if winner_probability_point is None and winner_min is not None and winner_max is not None:
        winner_probability_point = round((winner_min + winner_max) / 2, 4)
    winner_margin_point = to_number(goal_margin.get("winner_goals_margin_point"))
    winner_margin_min = to_number(goal_margin.get("winner_goals_margin_min"))
    winner_margin_max = to_number(goal_margin.get("winner_goals_margin_max"))

    justification_sources = source_count(payload.get("justification"))
    uncertainty_sources = source_count(payload.get("uncertainty"))
    evidence_blob = json.dumps(payload, ensure_ascii=False)
    leak_flags = sorted(set(match.group(0) for match in POST_CUTOFF_RE.finditer(evidence_blob)))

    winner_correct = predicted_winner == GROUND_TRUTH["winner"]
    has_confidence = confidence is not None
    has_probability_point = winner_probability_point is not None
    has_probability_range = winner_min is not None and winner_max is not None
    probability_order_valid = (
        winner_min <= winner_max
        if has_probability_range
        else None
    )
    winner_range_width = (
        round(winner_max - winner_min, 4) if has_probability_range else None
    )
    winner_range_width_valid = (
        winner_range_width <= 0.05 if winner_range_width is not None else None
    )
    winner_point_inside_range = (
        winner_min <= winner_probability_point <= winner_max
        if has_probability_range and has_probability_point
        else None
    )
    evidence_disciplined = justification_sources >= 2 and uncertainty_sources >= 1
    no_leak = not leak_flags

    checks = [
        winner_correct,
        has_confidence,
        has_probability_point and has_probability_range and probability_order_valid,
        evidence_disciplined,
        no_leak,
    ]
    score = sum(1 for check in checks if check is True)
    parse_errors = sum(
        value is None
        for value in [predicted_winner, confidence, winner_probability_point, winner_min, winner_max]
    )

    return {
        "case_id": "case-d-s2-copa-america-line5-gemma",
        "variant": variant,
        "model_policy": model_policy,
        "seed": seed,
        "ground_truth": GROUND_TRUTH,
        "predicted_winner": predicted_winner,
        "confidence": confidence,
        "winner_probability_point": winner_probability_point,
        "winner_probability_range": {
            "winner_min": winner_min,
            "winner_max": winner_max,
            "order_valid": probability_order_valid,
            "winner_range_width": winner_range_width,
            "winner_range_width_valid": winner_range_width_valid,
            "winner_point_inside_range": winner_point_inside_range,
        },
        "predicted_goal_margin": {
            "winner_goals_margin_point": winner_margin_point,
            "winner_goals_margin_min": winner_margin_min,
            "winner_goals_margin_max": winner_margin_max,
        },
        "checks": {
            "winner_correct": winner_correct,
            "has_confidence": has_confidence,
            "has_probability_point": has_probability_point,
            "has_probability_range": has_probability_range,
            "evidence_disciplined": evidence_disciplined,
            "no_post_cutoff_leak": no_leak,
        },
        "source_counts": {
            "justification": justification_sources,
            "uncertainty": uncertainty_sources,
        },
        "score": score,
        "max_score": 5,
        "parse_errors": parse_errors,
        "leak_flags": leak_flags,
        "artifact_kind": "structured_answer_json",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--structured-answer", required=True)
    parser.add_argument("--variant", default="unknown")
    parser.add_argument("--model-policy", default="unknown")
    parser.add_argument("--seed", type=int, default=20240713)
    args = parser.parse_args()

    payload = json.loads(Path(args.structured_answer).read_text(encoding="utf-8"))
    result = evaluate_structured(payload, args.variant, args.model_policy, args.seed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
