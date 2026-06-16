#!/usr/bin/env python3
"""Evaluate Argentina IPC 2025 predictions for the Gemma line 5 case."""

import argparse
import json
import re
from pathlib import Path


GROUND_TRUTH = {
    "delta_1_feb": 2.4,
    "delta_2_apr": 3.7,
    "delta_3_bucket": "moderada",
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


def infer_bucket(text: str) -> str | None:
    lowered = text.lower()
    if "moderada" in lowered or "2-4" in lowered or "2 a 4" in lowered:
        return "moderada"
    if "desinflacion fuerte" in lowered or "<2" in lowered or "menor a 2" in lowered:
        return "desinflacion_fuerte"
    if "estancamiento" in lowered or "reversion" in lowered or ">4" in lowered or "mayor a 4" in lowered:
        return "estancamiento_reversion"
    return None


def evaluate(text: str, case_id: str, variant: str, model_policy: str, seed: int) -> dict:
    delta_1_window = window_for(text, ["delta 1", "Δ1", "febrero"])
    delta_2_window = window_for(text, ["delta 2", "Δ2", "abril"])
    delta_3_window = window_for(text, ["delta 3", "Δ3", "julio", "bucket"])
    delta_4_window = window_for(text, ["delta 4", "Δ4", "diciembre", "acumulada"])

    delta_1_prediction = first_percent(delta_1_window)
    delta_2_range = first_range(delta_2_window)
    delta_3_bucket = infer_bucket(delta_3_window)

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
    delta_3_pass = (
        delta_3_bucket == GROUND_TRUTH["delta_3_bucket"]
        if delta_3_bucket is not None
        else None
    )
    delta_4_pass = (
        range_contains(GROUND_TRUTH["accumulated_2025"], accumulated_range)
        if accumulated_range is not None
        else None
    )

    leak_flags = sorted(set(match.group(0) for match in POST_CUTOFF_RE.finditer(text)))
    parse_errors = sum(
        value is None
        for value in [delta_1_prediction, delta_2_range, delta_3_bucket, accumulated_range]
    )

    score_parts = [delta_1_pass, delta_2_pass, delta_3_pass, delta_4_pass]
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
            "bucket": delta_3_bucket,
            "pass": delta_3_pass,
        },
        "delta_4": {
            "accumulated_range": accumulated_range,
            "pass": delta_4_pass,
        },
        "score": score,
        "max_score": 4,
        "parse_errors": parse_errors,
        "leak_flags": leak_flags,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, help="Path to a MiroFish report markdown file")
    parser.add_argument("--case-id", default="case-c-s2-arg-ipc-line5-gemma")
    parser.add_argument("--variant", default="unknown")
    parser.add_argument("--model-policy", default="gemma_temporal_probe")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    text = Path(args.report).read_text(encoding="utf-8")
    result = evaluate(text, args.case_id, args.variant, args.model_policy, args.seed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
