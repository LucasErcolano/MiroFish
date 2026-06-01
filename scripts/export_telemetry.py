#!/usr/bin/env python3
"""Export LLM telemetry from a simulation run to CSV/JSONL (Issue #21).

Reads one or more ``llm_telemetry.jsonl`` files (written per simulation by the
telemetry wrapper) and produces:

  - a flat CSV of every call (one row per LLM call), and
  - a JSONL summary with totals and a per-model breakdown.

Standalone: depends only on the stdlib + the JSONL the runner already writes.
It does NOT require the #20 experiment harness.

Usage:
    python scripts/export_telemetry.py --input <sim_dir_or_jsonl> [...] \\
        --out-csv results/telemetry.csv --out-summary results/telemetry_summary.jsonl
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys
from collections import defaultdict
from typing import Any, Dict, Iterable, List

CSV_FIELDS = [
    "source_file",
    "timestamp",
    "round",
    "agent_id",
    "role",
    "provider",
    "model",
    "temperature",
    "prompt_hash",
    "response_hash",
    "tokens_in",
    "tokens_out",
    "latency_ms",
    "cost_usd_est",
    "output_valid_json",
    "error",
    "leak_flags",
]


def _resolve_jsonl_paths(inputs: List[str]) -> List[str]:
    """Expand each input (a JSONL file, a dir, or a glob) to JSONL file paths."""
    paths: List[str] = []
    for item in inputs:
        if os.path.isdir(item):
            paths.append(os.path.join(item, "llm_telemetry.jsonl"))
        elif any(ch in item for ch in "*?["):
            paths.extend(glob.glob(item))
        else:
            paths.append(item)
    existing = [p for p in paths if os.path.exists(p)]
    missing = [p for p in paths if not os.path.exists(p)]
    for p in missing:
        print(f"warning: telemetry file not found, skipping: {p}", file=sys.stderr)
    return existing


def _read_records(paths: List[str]) -> Iterable[Dict[str, Any]]:
    for path in paths:
        with open(path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    print(f"warning: {path}:{line_no} not valid JSON, skipping", file=sys.stderr)
                    continue
                rec["source_file"] = path
                yield rec


def write_csv(records: List[Dict[str, Any]], out_csv: str) -> None:
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            row = dict(rec)
            if isinstance(row.get("leak_flags"), list):
                row["leak_flags"] = ";".join(row["leak_flags"])
            writer.writerow(row)


def build_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_model: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd_est": 0.0, "latency_ms": 0.0}
    )
    total = {
        "calls": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd_est": 0.0,
        "latency_ms": 0.0,
        "errors": 0,
        "parse_errors": 0,
    }
    for rec in records:
        model = rec.get("model") or "unknown"
        m = by_model[model]
        m["calls"] += 1
        m["tokens_in"] += rec.get("tokens_in", 0) or 0
        m["tokens_out"] += rec.get("tokens_out", 0) or 0
        m["cost_usd_est"] += rec.get("cost_usd_est", 0.0) or 0.0
        m["latency_ms"] += rec.get("latency_ms", 0.0) or 0.0

        total["calls"] += 1
        total["tokens_in"] += rec.get("tokens_in", 0) or 0
        total["tokens_out"] += rec.get("tokens_out", 0) or 0
        total["cost_usd_est"] += rec.get("cost_usd_est", 0.0) or 0.0
        total["latency_ms"] += rec.get("latency_ms", 0.0) or 0.0
        if rec.get("error"):
            total["errors"] += 1
        if rec.get("output_valid_json") is False:
            total["parse_errors"] += 1

    total["cost_usd_est"] = round(total["cost_usd_est"], 8)
    total["latency_sec"] = round(total["latency_ms"] / 1000.0, 4)
    total["mean_latency_ms"] = round(total["latency_ms"] / total["calls"], 2) if total["calls"] else 0.0

    per_model = {}
    for model, m in sorted(by_model.items()):
        per_model[model] = {
            "calls": m["calls"],
            "tokens_in": int(m["tokens_in"]),
            "tokens_out": int(m["tokens_out"]),
            "cost_usd_est": round(m["cost_usd_est"], 8),
            "mean_latency_ms": round(m["latency_ms"] / m["calls"], 2) if m["calls"] else 0.0,
        }
    return {"total": total, "by_model": per_model}


def write_summary(summary: Dict[str, Any], out_summary: str) -> None:
    os.makedirs(os.path.dirname(out_summary) or ".", exist_ok=True)
    with open(out_summary, "w", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export LLM telemetry to CSV/JSONL")
    parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        help="One or more simulation dirs, llm_telemetry.jsonl files, or globs",
    )
    parser.add_argument("--out-csv", default="results/telemetry.csv")
    parser.add_argument("--out-summary", default="results/telemetry_summary.jsonl")
    args = parser.parse_args()

    paths = _resolve_jsonl_paths(args.input)
    if not paths:
        print("error: no telemetry files found", file=sys.stderr)
        return 1

    records = list(_read_records(paths))
    write_csv(records, args.out_csv)
    summary = build_summary(records)
    write_summary(summary, args.out_summary)

    print(f"Read {len(records)} calls from {len(paths)} file(s)")
    print(f"CSV:     {args.out_csv}")
    print(f"Summary: {args.out_summary}")
    print(json.dumps(summary["total"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
