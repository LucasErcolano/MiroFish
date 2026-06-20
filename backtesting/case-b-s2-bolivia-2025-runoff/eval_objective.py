#!/usr/bin/env python3
"""Evaluate winner and vote-share predictions for Bolivia 2025 runoff."""

import argparse
import json
import re
from pathlib import Path


PAZ_WIN_RE = re.compile(
    r"(prediccion\s*(?:principal)?\s*[:：]\s*)?(paz|rodrigo paz).{0,80}(gana|ganara|vence|vencera|se impone|gana la eleccion|赢得|获胜|胜出|领先|最有可能)",
    re.IGNORECASE | re.DOTALL,
)
QUIROGA_WIN_RE = re.compile(
    r"(prediccion\s*(?:principal)?\s*[:：]\s*)?(quiroga|tuto|jorge quiroga).{0,80}(gana|ganara|vence|vencera|se impone|gana la eleccion|赢得|获胜|胜出|领先|最有可能)",
    re.IGNORECASE | re.DOTALL,
)
PREDICTION_LINE_RE = re.compile(r"prediccion(?:\s+principal)?\s*[:：]\s*([^\n]+)", re.IGNORECASE)

GROUND_TRUTH_VOTE_SHARES = {
    "paz": 54.53,
    "quiroga": 45.47,
    "otros": 0.00,
}
GROUND_TRUTH_MARGIN = 9.06

VOTE_SHARE_PATTERNS = {
    "paz": re.compile(
        r"(rodrigo paz|paz)[^\n0-9%]{0,40}([0-9]+(?:[.,][0-9]+)?)\s*%",
        re.IGNORECASE,
    ),
    "quiroga": re.compile(
        r"(jorge\s+quiroga|tuto\s+quiroga|quiroga|tuto)[^\n0-9%]{0,40}([0-9]+(?:[.,][0-9]+)?)\s*%",
        re.IGNORECASE,
    ),
    "otros": re.compile(
        r"(otros\s*/\s*blanco\s*/\s*nulo|otros|blanco|nulo|其他/空白/无效票|其他|空白|无效票)[^\n0-9%]{0,40}([0-9]+(?:[.,][0-9]+)?)\s*%",
        re.IGNORECASE,
    ),
}
MARGIN_RE = re.compile(
    r"(?:margen(?:\s+estimado)?|差距|领先)[^\n:：-]*[:：-]?\s*([+-]?[0-9]+(?:[.,][0-9]+)?)\s*(?:puntos|个百分点)?",
    re.IGNORECASE,
)


def infer_prediction(text: str) -> str | None:
    line_match = PREDICTION_LINE_RE.search(text)
    if line_match:
        line = line_match.group(1).strip().lower()
        if re.search(r"\b(paz|rodrigo paz)\b", line):
            return "paz_gana"
        if re.search(r"\b(quiroga|tuto)\b", line):
            return "quiroga_gana"

    if QUIROGA_WIN_RE.search(text):
        return "quiroga_gana"
    if PAZ_WIN_RE.search(text):
        return "paz_gana"
    return None


def parse_number(value: str) -> float:
    return float(value.replace(",", "."))


def infer_vote_shares(text: str) -> dict[str, float]:
    shares = {}
    for key, pattern in VOTE_SHARE_PATTERNS.items():
        match = pattern.search(text)
        if match:
            shares[key] = parse_number(match.group(2))
    return shares


def mean_absolute_error(predicted: dict[str, float]) -> float | None:
    if set(predicted) != set(GROUND_TRUTH_VOTE_SHARES):
        return None
    errors = [
        abs(predicted[key] - truth_value)
        for key, truth_value in GROUND_TRUTH_VOTE_SHARES.items()
    ]
    return round(sum(errors) / len(errors), 3)


def infer_margin(text: str, shares: dict[str, float], prediction: str | None) -> float | None:
    if "paz" in shares and "quiroga" in shares:
        return round(shares["paz"] - shares["quiroga"], 3)
    match = MARGIN_RE.search(text)
    if match:
        margin = parse_number(match.group(1))
        if prediction == "quiroga_gana":
            return -abs(margin)
        if prediction == "paz_gana":
            return abs(margin)
        return margin
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, help="Path to a MiroFish report markdown file")
    parser.add_argument("--case-id", default="bolivia_2025_runoff_s2")
    parser.add_argument("--variant", default="unknown")
    parser.add_argument("--model-policy", default="unknown")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    text = Path(args.report).read_text(encoding="utf-8")
    prediction = infer_prediction(text)
    winner_score = 1 if prediction == "paz_gana" else 0
    vote_shares = infer_vote_shares(text)
    mae_vote_share = mean_absolute_error(vote_shares)
    predicted_margin = infer_margin(text, vote_shares, prediction)
    margin_abs_error = (
        round(abs(predicted_margin - GROUND_TRUTH_MARGIN), 3)
        if predicted_margin is not None
        else None
    )

    parse_errors = 0
    if prediction is None:
        parse_errors += 1
    if mae_vote_share is None:
        parse_errors += 1
    if predicted_margin is None:
        parse_errors += 1

    result = {
        "case_id": args.case_id,
        "variant": args.variant,
        "model_policy": args.model_policy,
        "seed": args.seed,
        "prediction": prediction,
        "ground_truth": "paz_gana",
        "winner_score": winner_score,
        "score": winner_score,
        "parsed_vote_shares": vote_shares,
        "ground_truth_vote_shares": GROUND_TRUTH_VOTE_SHARES,
        "mae_vote_share": mae_vote_share,
        "predicted_margin": predicted_margin,
        "ground_truth_margin": GROUND_TRUTH_MARGIN,
        "margin_abs_error": margin_abs_error,
        "parse_errors": parse_errors,
        "leak_flags": [],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
