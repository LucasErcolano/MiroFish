#!/usr/bin/env python3
"""Extract effective temporal cutoffs for the three T0-T3 cases."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = ROOT / "backtesting" / "benchmarks" / "market_baseline"

T_ORDER = ["T0", "T1", "T2", "T3"]


CASES = {
    "bolivia_2025_runoff_s2": {
        "label": "Bolivia 2025 runoff",
        "manifest": "backtesting/case-b-s2-bolivia-2025-runoff/manifest.csv",
        "package_column": "package",
        "date_column": "published_at",
        "id_column": "doc_id",
        "type_column": "source_type",
    },
    "arg_ipc_2025_temporal": {
        "label": "Argentina IPC 2025",
        "manifest": "backtesting/case-c-s2-arg-ipc-line5-gemma/manifest.csv",
        "date_column": "fecha",
        "id_column": "id",
        "type_column": "categoria",
        "packages": {
            "T0": ["INST_01", "INST_02", "SOCIAL_01", "POLL_01", "MACRO_01"],
            "T1": ["INST_01", "INST_02", "SOCIAL_01", "POLL_01", "MACRO_01", "MACRO_03", "GEO_01"],
            "T2": ["INST_01", "INST_02", "SOCIAL_01", "POLL_01", "MACRO_01", "MACRO_03", "GEO_01", "MACRO_02", "POL_01"],
            "T3": ["INST_01", "INST_02", "SOCIAL_01", "POLL_01", "MACRO_01", "MACRO_03", "GEO_01", "MACRO_02", "POL_01", "MONETARY_01", "FISCAL_01", "MONETARY_02", "MACRO_04"],
        },
        "fallback_cutoffs": {
            "T0": "2024-12-31",
            "T1": "2025-01-10",
            "T2": "2025-01-14",
            "T3": "2025-01-31",
        },
    },
    "copa_america_2024_final": {
        "label": "Copa America 2024 final",
        "manifest": "backtesting/case-d-s2-copa-america-line5-gemma/manifest.csv",
        "package_column": "temporal_package",
        "date_column": "date",
        "id_column": "source_id",
        "type_column": "source_type",
    },
}


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def normalize_date(value: str) -> str:
    value = (value or "").strip()
    if len(value) == 7:
        return f"{value}-31"
    return value


def package_rank(package: str) -> int:
    return T_ORDER.index(package)


def rows_for_case(case_id: str, cfg: dict) -> list[dict[str, str]]:
    manifest_path = ROOT / cfg["manifest"]
    manifest = read_manifest(manifest_path)
    output = []
    for package in T_ORDER:
        if "packages" in cfg:
            source_ids = cfg["packages"][package]
            included = [row for row in manifest if row.get(cfg["id_column"]) in source_ids]
        else:
            included = [
                row
                for row in manifest
                if row.get(cfg["package_column"]) in T_ORDER
                and package_rank(row[cfg["package_column"]]) <= package_rank(package)
            ]
            source_ids = [row.get(cfg["id_column"], "") for row in included]

        dates = [normalize_date(row.get(cfg["date_column"], "")) for row in included if row.get(cfg["date_column"])]
        cutoff = max(dates) if dates else cfg.get("fallback_cutoffs", {}).get(package, "")
        if cfg.get("fallback_cutoffs", {}).get(package):
            cutoff = cfg["fallback_cutoffs"][package]

        just_added = []
        if "packages" in cfg:
            prev = set(cfg["packages"][T_ORDER[package_rank(package) - 1]]) if package != "T0" else set()
            just_added = [source_id for source_id in source_ids if source_id not in prev]
        else:
            just_added = [
                row.get(cfg["id_column"], "")
                for row in included
                if row.get(cfg["package_column"]) == package
            ]

        output.append(
            {
                "case_id": case_id,
                "case_label": cfg["label"],
                "temporal_package": package,
                "cutoff_date": cutoff,
                "source_count": str(len(source_ids)),
                "source_ids": ";".join(source_ids),
                "evidence_added": ";".join(just_added),
                "source_types": ";".join(sorted({row.get(cfg["type_column"], "") for row in included if row.get(cfg["type_column"])})),
                "manifest_path": cfg["manifest"],
            }
        )
    return output


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for case_id, cfg in CASES.items():
        rows.extend(rows_for_case(case_id, cfg))

    out_path = OUT_DIR / "temporal_cutoffs.csv"
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

