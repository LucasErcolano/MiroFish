#!/usr/bin/env python3
"""Build market/proxy CSV aligned to the extracted prediction rows."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = ROOT / "backtesting" / "benchmarks" / "market_baseline"
SOURCE_JSON = OUT_DIR / "market_odds" / "temporal_market_proxies.json"

FIELDNAMES = [
    "case_id",
    "temporal_package",
    "target",
    "market_source_type",
    "source_id",
    "raw_value",
    "p_market",
    "market_value",
    "quality_flag",
    "notes",
]


def main() -> int:
    predictions_path = OUT_DIR / "mirofish_predictions.csv"
    with predictions_path.open(newline="", encoding="utf-8") as handle:
        prediction_keys = [
            (row["case_id"], row["temporal_package"], row["target"])
            for row in csv.DictReader(handle)
        ]

    configured = {
        (row["case_id"], row["temporal_package"], row["target"]): row
        for row in json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    }

    rows = []
    for case_id, package, target in prediction_keys:
        row = configured.get((case_id, package, target))
        if row is None:
            row = {
                "case_id": case_id,
                "temporal_package": package,
                "target": target,
                "market_source_type": "UNAVAILABLE",
                "source_id": "",
                "raw_value": "No numeric market/proxy configured for this target.",
                "p_market": None,
                "market_value": None,
                "quality_flag": "UNAVAILABLE",
                "notes": "Target remains MiroFish-only in this one-shot benchmark.",
            }
        rows.append({name: "" if row.get(name) is None else row.get(name, "") for name in FIELDNAMES})

    out_path = OUT_DIR / "market_odds.csv"
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

