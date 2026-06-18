#!/usr/bin/env python3
"""Evaluate Argentina IPC 2025 predictions for the Gemma line 5 case."""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Tuple


GROUND_TRUTH = {
    "delta_1_feb": 2.4,
    "delta_2_apr": 3.7,
    "delta_3_jul": 3.0,
    "delta_4_dec": 2.8,
    "accumulated_2025": 31.5,
}

NUMBER_RE = re.compile(r"([0-9]+(?:[.,][0-9]+)?)\s*%")
RANGE_RE = re.compile(
    r"(?:entre\s+)?([0-9]+(?:[.,][0-9]+)?)\s*%?\s*(?:-|a|y|hasta)\s*([0-9]+(?:[.,][0-9]+)?)\s*%",
    re.IGNORECASE,
)
POST_CUTOFF_RE = re.compile(
    r"(enero\s+2026|enero\s+de\s+2026|publicado\s+en\s+enero\s+2026|dato\s+real|datos\s+reales|ground\s*truth)",
    re.IGNORECASE,
)


def parse_number(value: str) -> float:
    return float(value.replace(",", "."))


def window_for(text: str, keywords: list[str], radius: int = 650) -> str:
    lowered = text.lower()
    positions = [lowered.find(keyword.lower()) for keyword in keywords]
    positions = [position for position in positions if position >= 0]
    if not positions:
        return ""
    start = max(min(positions) - radius, 0)
    end = min(max(positions) + radius, len(text))
    return text[start:end]


def first_percent(text: str) -> float | None:
    match = NUMBER_RE.search(text)
    if not match:
        return None
    return parse_number(match.group(1))


def first_range(text: str) -> tuple[float, float] | None:
    match = RANGE_RE.search(text)
    if not match:
        return None
    low = parse_number(match.group(1))
    high = parse_number(match.group(2))
    if low > high:
        low, high = high, low
    return low, high


def range_contains(value: float, predicted_range: tuple[float, float] | None) -> bool | None:
    if predicted_range is None:
        return None
    low, high = predicted_range
    return low <= value <= high


def evaluate_text(text: str, case_id: str, variant: str, model_policy: str, seed: int) -> dict:
    delta_1_window = window_for(text, ["delta 1", "Δ1", "febrero"])
    delta_2_window = window_for(text, ["delta 2", "Δ2", "abril"])
    delta_3_window = window_for(text, ["delta 3", "Δ3", "julio"])
    delta_4_window = window_for(text, ["delta 4", "Δ4", "diciembre", "acumulada"])

    delta_1_prediction = first_percent(delta_1_window)
    delta_2_range = first_range(delta_2_window)
    delta_3_range = first_range(delta_3_window)
    delta_4_range = first_range(delta_4_window)

    accumulated_window = window_for(text, ["acumulada", "inflacion acumulada", "2025"], radius=900)
    accumulated_range = first_range(accumulated_window)

    delta_1_abs_error = (
        round(abs(delta_1_prediction - GROUND_TRUTH["delta_1_feb"]), 3)
        if delta_1_prediction is not None
        else None
    )
    delta_2_range_width = (
        round(delta_2_range[1] - delta_2_range[0], 3)
        if delta_2_range is not None
        else None
    )

    delta_1_pass = (
        delta_1_abs_error <= 1.5 if delta_1_abs_error is not None else None
    )
    delta_2_pass = (
        range_contains(GROUND_TRUTH["delta_2_apr"], delta_2_range)
        and delta_2_range_width <= 4
        if delta_2_range is not None
        else None
    )
    delta_3_range_width = (
        round(delta_3_range[1] - delta_3_range[0], 3)
        if delta_3_range is not None
        else None
    )
    delta_4_range_width = (
        round(delta_4_range[1] - delta_4_range[0], 3)
        if delta_4_range is not None
        else None
    )
    delta_3_pass = (
        range_contains(GROUND_TRUTH["delta_3_jul"], delta_3_range)
        and delta_3_range_width <= 4
        if delta_3_range is not None
        else None
    )
    delta_4_pass = (
        range_contains(GROUND_TRUTH["delta_4_dec"], delta_4_range)
        and delta_4_range_width <= 4
        if delta_4_range is not None
        else None
    )
    accumulated_pass = (
        range_contains(GROUND_TRUTH["accumulated_2025"], accumulated_range)
        if accumulated_range is not None
        else None
    )

    leak_flags = sorted(set(match.group(0) for match in POST_CUTOFF_RE.finditer(text)))
    parse_errors = sum(
        value is None
        for value in [delta_1_prediction, delta_2_range, delta_3_range, delta_4_range, accumulated_range]
    )

    score_parts = [delta_1_pass, delta_2_pass, delta_3_pass, delta_4_pass, accumulated_pass]
    score = sum(1 for part in score_parts if part is True)

    return {
        "case_id": case_id,
        "variant": variant,
        "model_policy": model_policy,
        "seed": seed,
        "ground_truth": GROUND_TRUTH,
        "delta_1": {
            "prediction": delta_1_prediction,
            "abs_error": delta_1_abs_error,
            "pass": delta_1_pass,
        },
        "delta_2": {
            "range": delta_2_range,
            "range_width": delta_2_range_width,
            "pass": delta_2_pass,
        },
        "delta_3": {
            "range": delta_3_range,
            "range_width": delta_3_range_width,
            "pass": delta_3_pass,
        },
        "delta_4": {
            "range": delta_4_range,
            "range_width": delta_4_range_width,
            "pass": delta_4_pass,
        },
        "accumulated_2025": {
            "range": accumulated_range,
            "pass": accumulated_pass,
        },
        "score": score,
        "max_score": 5,
        "parse_errors": parse_errors,
        "leak_flags": leak_flags,
        "artifact_kind": "report_markdown",
    }


def evaluate_structured_answer(payload: Dict[str, Any], case_id: str, variant: str, model_policy: str, seed: int) -> dict:
    delta_1 = payload.get("delta_1", {}) or {}
    delta_2 = payload.get("delta_2", {}) or {}
    delta_3 = payload.get("delta_3", {}) or {}
    delta_4 = payload.get("delta_4", {}) or {}

    delta_1_prediction = delta_1.get("point_estimate")
    delta_2_range = _range_tuple(delta_2.get("range_min"), delta_2.get("range_max"))
    delta_3_range = _range_tuple(delta_3.get("range_min"), delta_3.get("range_max"))
    delta_4_prediction = delta_4.get("point_estimate")
    delta_4_range = _range_tuple(delta_4.get("range_min"), delta_4.get("range_max"))
    accumulated_range = _range_tuple(
        delta_4.get("accumulated_2025_range_min"),
        delta_4.get("accumulated_2025_range_max"),
    )

    evidence_blob = json.dumps(payload.get("evidence", []), ensure_ascii=False)
    leak_flags = sorted(set(match.group(0) for match in POST_CUTOFF_RE.finditer(evidence_blob)))

    delta_1_abs_error = (
        round(abs(float(delta_1_prediction) - GROUND_TRUTH["delta_1_feb"]), 3)
        if delta_1_prediction is not None
        else None
    )
    delta_2_range_width = (
        round(delta_2_range[1] - delta_2_range[0], 3)
        if delta_2_range is not None
        else None
    )
    delta_3_range_width = (
        round(delta_3_range[1] - delta_3_range[0], 3)
        if delta_3_range is not None
        else None
    )
    delta_4_abs_error = (
        round(abs(float(delta_4_prediction) - GROUND_TRUTH["delta_4_dec"]), 3)
        if delta_4_prediction is not None
        else None
    )
    delta_4_range_width = (
        round(delta_4_range[1] - delta_4_range[0], 3)
        if delta_4_range is not None
        else None
    )

    delta_1_pass = delta_1_abs_error <= 1.5 if delta_1_abs_error is not None else None
    delta_2_pass = (
        range_contains(GROUND_TRUTH["delta_2_apr"], delta_2_range)
        and delta_2_range_width <= 4
        if delta_2_range is not None
        else None
    )
    delta_3_pass = (
        range_contains(GROUND_TRUTH["delta_3_jul"], delta_3_range)
        and delta_3_range_width <= 4
        if delta_3_range is not None
        else None
    )
    delta_4_pass = (
        range_contains(GROUND_TRUTH["delta_4_dec"], delta_4_range)
        and delta_4_range_width <= 4
        if delta_4_range is not None
        else None
    )
    accumulated_pass = (
        range_contains(GROUND_TRUTH["accumulated_2025"], accumulated_range)
        if accumulated_range is not None
        else None
    )

    parse_errors = sum(
        value is None
        for value in [delta_1_prediction, delta_2_range, delta_3_range, delta_4_prediction, delta_4_range, accumulated_range]
    )
    score_parts = [delta_1_pass, delta_2_pass, delta_3_pass, delta_4_pass, accumulated_pass]
    score = sum(1 for part in score_parts if part is True)

    return {
        "case_id": case_id,
        "variant": variant,
        "model_policy": model_policy,
        "seed": seed,
        "ground_truth": GROUND_TRUTH,
        "delta_1": {
            "prediction": delta_1_prediction,
            "abs_error": delta_1_abs_error,
            "pass": delta_1_pass,
        },
        "delta_2": {
            "range": delta_2_range,
            "range_width": delta_2_range_width,
            "pass": delta_2_pass,
        },
        "delta_3": {
            "range": delta_3_range,
            "range_width": delta_3_range_width,
            "pass": delta_3_pass,
        },
        "delta_4": {
            "prediction": delta_4_prediction,
            "abs_error": delta_4_abs_error,
            "range": delta_4_range,
            "range_width": delta_4_range_width,
            "pass": delta_4_pass,
        },
        "accumulated_2025": {
            "range": accumulated_range,
            "pass": accumulated_pass,
        },
        "score": score,
        "max_score": 5,
        "parse_errors": parse_errors,
        "leak_flags": leak_flags,
        "artifact_kind": "structured_answer_json",
    }


def _range_tuple(low: Any, high: Any) -> Tuple[float, float] | None:
    if low is None or high is None:
        return None
    low = float(str(low).replace(",", "."))
    high = float(str(high).replace(",", "."))
    if low > high:
        low, high = high, low
    return (low, high)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", help="Path to a MiroFish report markdown file")
    parser.add_argument("--structured-answer", help="Path to structured_answer.json")
    parser.add_argument("--case-id", default="case-c-s2-arg-ipc-line5-gemma")
    parser.add_argument("--variant", default="unknown")
    parser.add_argument("--model-policy", default="gemma_temporal_probe")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    if not args.report and not args.structured_answer:
        raise SystemExit("Provide --report or --structured-answer")

    if args.structured_answer:
        payload = json.loads(Path(args.structured_answer).read_text(encoding="utf-8"))
        result = evaluate_structured_answer(payload, args.case_id, args.variant, args.model_policy, args.seed)
    else:
        text = Path(args.report).read_text(encoding="utf-8")
        result = evaluate_text(text, args.case_id, args.variant, args.model_policy, args.seed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
