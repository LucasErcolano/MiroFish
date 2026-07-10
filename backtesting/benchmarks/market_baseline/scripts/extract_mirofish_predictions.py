#!/usr/bin/env python3
"""Extract MiroFish predictions for Bolivia, IPC and Copa temporal packages."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from normalize import midpoint, relative_probability


ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = ROOT / "backtesting" / "benchmarks" / "market_baseline"
T_ORDER = ["T0", "T1", "T2", "T3"]


FIELDNAMES = [
    "case_id",
    "case_label",
    "temporal_package",
    "cutoff_date",
    "target",
    "target_label",
    "metric_family",
    "prediction_label",
    "p_mirofish",
    "point_estimate",
    "range_min",
    "range_max",
    "ground_truth_label",
    "ground_truth_value",
    "model",
    "variant",
    "parse_errors",
    "artifact_path",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_cutoffs() -> dict[tuple[str, str], str]:
    path = OUT_DIR / "temporal_cutoffs.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            (row["case_id"], row["temporal_package"]): row["cutoff_date"]
            for row in csv.DictReader(handle)
        }


def clean_float(value) -> str:
    if value is None:
        return ""
    return str(round(float(value), 6))


def bolivia_rows(cutoffs: dict[tuple[str, str], str]) -> list[dict[str, str]]:
    rows = []
    case_id = "bolivia_2025_runoff_s2"
    for package in T_ORDER:
        rel = Path(f"backtesting/case-b-s2-bolivia-2025-runoff/output/{package}_gemma_probe/eval_result.json")
        data = load_json(ROOT / rel)
        shares = data.get("parsed_vote_shares", {})
        p_paz = relative_probability(shares.get("paz"), shares.get("quiroga"))
        rows.append(
            {
                "case_id": case_id,
                "case_label": "Bolivia 2025 runoff",
                "temporal_package": package,
                "cutoff_date": cutoffs[(case_id, package)],
                "target": "paz_wins",
                "target_label": "Rodrigo Paz wins runoff",
                "metric_family": "binary",
                "prediction_label": data.get("prediction") or "",
                "p_mirofish": clean_float(p_paz),
                "point_estimate": "",
                "range_min": "",
                "range_max": "",
                "ground_truth_label": data.get("ground_truth", ""),
                "ground_truth_value": "1",
                "model": data.get("model_policy", ""),
                "variant": data.get("variant", ""),
                "parse_errors": str(data.get("parse_errors", "")),
                "artifact_path": str(rel),
            }
        )
    return rows


def ipc_rows(cutoffs: dict[tuple[str, str], str]) -> list[dict[str, str]]:
    rows = []
    case_id = "arg_ipc_2025_temporal"
    targets = [
        ("delta_1_feb", "February 2025 monthly IPC", "delta_1", "delta_1_feb"),
        ("delta_2_apr", "April 2025 monthly IPC", "delta_2", "delta_2_apr"),
        ("delta_3_jul", "July 2025 monthly IPC", "delta_3", "delta_3_jul"),
        ("delta_4_dec", "December 2025 monthly IPC", "delta_4", "delta_4_dec"),
        ("accumulated_2025", "Accumulated IPC 2025", "accumulated_2025", "accumulated_2025"),
    ]
    for package in T_ORDER:
        base = Path(f"backtesting/case-c-s2-arg-ipc-line5-gemma/output/gemma_{package}_R40_D2")
        structured = load_json(ROOT / base / "structured_answer.json")
        eval_data = load_json(ROOT / base / "eval_result.json")
        gt = eval_data.get("ground_truth", {})
        model = structured.get("metadata", {}).get("model", eval_data.get("model_policy", ""))
        for target, label, structured_key, gt_key in targets:
            if target == "accumulated_2025":
                low = structured["delta_4"].get("accumulated_2025_range_min")
                high = structured["delta_4"].get("accumulated_2025_range_max")
                point = midpoint(low, high)
            else:
                block = structured[structured_key]
                low = block.get("range_min")
                high = block.get("range_max")
                point = block.get("point_estimate")
                if point is None:
                    point = midpoint(low, high)
            rows.append(
                {
                    "case_id": case_id,
                    "case_label": "Argentina IPC 2025",
                    "temporal_package": package,
                    "cutoff_date": cutoffs[(case_id, package)],
                    "target": target,
                    "target_label": label,
                    "metric_family": "numeric_percent",
                    "prediction_label": "",
                    "p_mirofish": "",
                    "point_estimate": clean_float(point),
                    "range_min": clean_float(low),
                    "range_max": clean_float(high),
                    "ground_truth_label": "",
                    "ground_truth_value": clean_float(gt.get(gt_key)),
                    "model": model,
                    "variant": eval_data.get("variant", f"gemma_{package}_R40_D2"),
                    "parse_errors": str(eval_data.get("parse_errors", "")),
                    "artifact_path": str(base / "structured_answer.json"),
                }
            )
    return rows


def copa_rows(cutoffs: dict[tuple[str, str], str]) -> list[dict[str, str]]:
    rows = []
    case_id = "copa_america_2024_final"
    for package in T_ORDER:
        base = Path(f"backtesting/case-d-s2-copa-america-line5-gemma/output/gemma_{package}_R40_D2")
        structured = load_json(ROOT / base / "structured_answer.json")
        eval_data = load_json(ROOT / base / "eval_result.json")
        rows.append(
            {
                "case_id": case_id,
                "case_label": "Copa America 2024 final",
                "temporal_package": package,
                "cutoff_date": cutoffs[(case_id, package)],
                "target": "argentina_wins",
                "target_label": "Argentina wins final",
                "metric_family": "binary",
                "prediction_label": structured.get("predicted_winner", ""),
                "p_mirofish": clean_float(structured.get("winner_probability_point")),
                "point_estimate": "",
                "range_min": clean_float(structured.get("winner_probability_range", {}).get("winner_min")),
                "range_max": clean_float(structured.get("winner_probability_range", {}).get("winner_max")),
                "ground_truth_label": eval_data.get("ground_truth", {}).get("winner", ""),
                "ground_truth_value": "1",
                "model": structured.get("metadata", {}).get("model", eval_data.get("model_policy", "")),
                "variant": eval_data.get("variant", f"gemma_{package}_R40_D2"),
                "parse_errors": str(eval_data.get("parse_errors", "")),
                "artifact_path": str(base / "structured_answer.json"),
            }
        )
    return rows


def write_inventory(paths: list[str]) -> None:
    (OUT_DIR / "_inventory.txt").write_text("\n".join(paths) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cutoffs = load_cutoffs()
    rows = bolivia_rows(cutoffs) + ipc_rows(cutoffs) + copa_rows(cutoffs)
    out_path = OUT_DIR / "mirofish_predictions.csv"
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    write_inventory([row["artifact_path"] for row in rows])
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

