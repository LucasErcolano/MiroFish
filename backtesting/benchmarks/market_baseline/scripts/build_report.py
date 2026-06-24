#!/usr/bin/env python3
"""Build the markdown report for the temporal market baseline benchmark."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = ROOT / "backtesting" / "benchmarks" / "market_baseline"


CASE_LABELS = {
    "bolivia_2025_runoff_s2": "Bolivia 2025 Runoff",
    "arg_ipc_2025_temporal": "Argentina IPC 2025",
    "copa_america_2024_final": "Copa America 2024 Final",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fmt(value: str, fallback: str = "n/a") -> str:
    if value is None or value == "":
        return fallback
    try:
        return f"{float(value):.3f}"
    except ValueError:
        return value


def table_for_case(case_id: str, rows: list[dict[str, str]]) -> list[str]:
    lines = [f"## {CASE_LABELS.get(case_id, case_id)}", ""]
    if case_id == "arg_ipc_2025_temporal":
        lines.extend(
            [
                "| T | Target | Cutoff | MiroFish | Market/proxy | Quality | Abs err MF | Abs err market | Delta abs | Comparable |",
                "|---|---|---|---:|---:|---|---:|---:|---:|---|",
            ]
        )
        for row in rows:
            lines.append(
                "| {temporal_package} | {target} | {cutoff_date} | {mf} | {market} | {quality_flag} | {mf_err} | {mk_err} | {delta} | {comp} |".format(
                    temporal_package=row["temporal_package"],
                    target=row["target"],
                    cutoff_date=row["cutoff_date"],
                    mf=fmt(row["point_estimate"]),
                    market=fmt(row["market_value"]),
                    quality_flag=row["quality_flag"],
                    mf_err=fmt(row["abs_error_mirofish"]),
                    mk_err=fmt(row["abs_error_market"]),
                    delta=fmt(row["delta_abs_error"]),
                    comp=row["comparable"],
                )
            )
    else:
        lines.extend(
            [
                "| T | Target | Cutoff | p(MiroFish) | p(market/proxy) | Quality | Brier MF | Brier market | Delta Brier | Comparable |",
                "|---|---|---|---:|---:|---|---:|---:|---:|---|",
            ]
        )
        for row in rows:
            lines.append(
                "| {temporal_package} | {target} | {cutoff_date} | {pmf} | {pmk} | {quality_flag} | {bmf} | {bmk} | {delta} | {comp} |".format(
                    temporal_package=row["temporal_package"],
                    target=row["target"],
                    cutoff_date=row["cutoff_date"],
                    pmf=fmt(row["p_mirofish"]),
                    pmk=fmt(row["p_market"]),
                    quality_flag=row["quality_flag"],
                    bmf=fmt(row["brier_mirofish"]),
                    bmk=fmt(row["brier_market"]),
                    delta=fmt(row["delta_brier"]),
                    comp=row["comparable"],
                )
            )
    lines.append("")
    return lines


def summarize(rows: list[dict[str, str]]) -> list[str]:
    comparable = [row for row in rows if row["comparable"] == "true"]
    unavailable = [row for row in rows if row["quality_flag"] == "UNAVAILABLE"]
    deltas = [float(row["delta_brier"]) for row in comparable if row["delta_brier"]]
    improved = [delta for delta in deltas if delta < 0]
    avg_delta = sum(deltas) / len(deltas) if deltas else None
    lines = [
        "# Market Baseline Temporal Benchmark",
        "",
        "This report compares existing MiroFish T0-T3 predictions against market/proxy signals available at the same temporal package.",
        "",
        "No new MiroFish simulations were run for this benchmark.",
        "",
        "## Executive Summary",
        "",
        f"- Total rows: {len(rows)}",
        f"- Comparable rows with market/proxy: {len(comparable)}",
        f"- Unavailable market/proxy rows: {len(unavailable)}",
        f"- Rows where MiroFish beats market/proxy by delta Brier: {len(improved)}",
        f"- Average delta Brier over comparable rows: {fmt(str(avg_delta) if avg_delta is not None else '')}",
        "",
        "Negative delta means MiroFish has lower error than the market/proxy. Positive delta means the market/proxy is better.",
        "",
        "For IPC numeric targets, Brier is a scaled squared error over percentage values; absolute error is also reported.",
        "",
    ]
    return lines


def interpretation() -> list[str]:
    return [
        "## Interpretation",
        "",
        "- Bolivia shows the intended temporal behavior clearly: after T1, both MiroFish and the first-round proxy favor Paz, but the late T3 poll moves the market/proxy toward Quiroga and MiroFish also shifts toward Quiroga. The final ground truth favored Paz, so the late poll acted as a strong but misleading signal.",
        "- Copa has no explicit market proxy in T0/T1, then T2/T3 add market/model probabilities around Argentina. MiroFish remains close to that market anchor and predicts Argentina correctly.",
        "- IPC is only partly market-comparable in this one-shot because the available proxy is annual REM inflation, not monthly paths. The benchmark therefore treats monthly rows as MiroFish-only and compares accumulated 2025 where the REM anchor is available.",
        "",
        "## Caveats",
        "",
        "- Market/proxy rows use only signals already present in the temporal evidence packages; this is not an external odds-history research pass.",
        "- `UNAVAILABLE` rows are intentionally left out of market-adjusted aggregates.",
        "- Bolivia T1/T2 proxies are not direct runoff odds; they use first-round relative Paz/Quiroga information and are marked `LOW` quality.",
        "- IPC annual REM is a market-expectations proxy for accumulated inflation, not a direct monthly forecast.",
        "",
    ]


def main() -> int:
    rows = read_csv(OUT_DIR / "metrics_per_question.csv")
    by_case = defaultdict(list)
    for row in rows:
        by_case[row["case_id"]].append(row)

    lines = summarize(rows)
    for case_id in ["bolivia_2025_runoff_s2", "arg_ipc_2025_temporal", "copa_america_2024_final"]:
        lines.extend(table_for_case(case_id, by_case[case_id]))
    lines.extend(interpretation())

    out_path = OUT_DIR / "MARKET_BASELINE_REPORT.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

