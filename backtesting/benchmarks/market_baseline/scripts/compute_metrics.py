#!/usr/bin/env python3
"""Compute market-adjusted metrics for the temporal benchmark."""

from __future__ import annotations

import csv
from pathlib import Path

from normalize import abs_error, brier, log_loss, scaled_squared_error


ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = ROOT / "backtesting" / "benchmarks" / "market_baseline"

FIELDNAMES = [
    "case_id",
    "temporal_package",
    "target",
    "metric_family",
    "cutoff_date",
    "p_mirofish",
    "point_estimate",
    "ground_truth_value",
    "p_market",
    "market_value",
    "quality_flag",
    "comparable",
    "brier_mirofish",
    "brier_market",
    "delta_brier",
    "log_loss_mirofish",
    "log_loss_market",
    "abs_error_mirofish",
    "abs_error_market",
    "delta_abs_error",
    "directional_match_mirofish",
    "directional_match_market",
    "artifact_path",
    "notes",
]


def as_float(value: str) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def scale_for_target(target: str) -> float:
    if target == "accumulated_2025":
        return 100.0
    return 10.0


def compute_row(pred: dict[str, str], market: dict[str, str]) -> dict[str, str]:
    metric_family = pred["metric_family"]
    y = as_float(pred["ground_truth_value"])
    p_m = as_float(pred["p_mirofish"])
    point = as_float(pred["point_estimate"])
    p_market = as_float(market.get("p_market", ""))
    market_value = as_float(market.get("market_value", ""))
    comparable = False
    result = {name: "" for name in FIELDNAMES}
    result.update(
        {
            "case_id": pred["case_id"],
            "temporal_package": pred["temporal_package"],
            "target": pred["target"],
            "metric_family": metric_family,
            "cutoff_date": pred["cutoff_date"],
            "p_mirofish": pred["p_mirofish"],
            "point_estimate": pred["point_estimate"],
            "ground_truth_value": pred["ground_truth_value"],
            "p_market": market.get("p_market", ""),
            "market_value": market.get("market_value", ""),
            "quality_flag": market.get("quality_flag", "UNAVAILABLE"),
            "artifact_path": pred["artifact_path"],
            "notes": market.get("notes", ""),
        }
    )

    if metric_family == "binary" and y is not None and p_m is not None:
        result["brier_mirofish"] = str(brier(p_m, y))
        result["log_loss_mirofish"] = str(log_loss(p_m, y))
        result["directional_match_mirofish"] = str((p_m >= 0.5) == (y >= 0.5)).lower()
        if p_market is not None:
            comparable = True
            result["brier_market"] = str(brier(p_market, y))
            result["log_loss_market"] = str(log_loss(p_market, y))
            result["delta_brier"] = str(round(float(result["brier_mirofish"]) - float(result["brier_market"]), 6))
            result["directional_match_market"] = str((p_market >= 0.5) == (y >= 0.5)).lower()

    if metric_family == "numeric_percent" and y is not None and point is not None:
        scale = scale_for_target(pred["target"])
        result["abs_error_mirofish"] = str(abs_error(point, y))
        result["brier_mirofish"] = str(scaled_squared_error(point, y, scale))
        if market_value is not None:
            comparable = True
            result["abs_error_market"] = str(abs_error(market_value, y))
            result["brier_market"] = str(scaled_squared_error(market_value, y, scale))
            result["delta_abs_error"] = str(round(float(result["abs_error_mirofish"]) - float(result["abs_error_market"]), 6))
            result["delta_brier"] = str(round(float(result["brier_mirofish"]) - float(result["brier_market"]), 6))

    result["comparable"] = str(comparable).lower()
    return result


def main() -> int:
    predictions = read_csv(OUT_DIR / "mirofish_predictions.csv")
    markets = {
        (row["case_id"], row["temporal_package"], row["target"]): row
        for row in read_csv(OUT_DIR / "market_odds.csv")
    }
    rows = [
        compute_row(pred, markets[(pred["case_id"], pred["temporal_package"], pred["target"])])
        for pred in predictions
    ]
    out_path = OUT_DIR / "metrics_per_question.csv"
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

