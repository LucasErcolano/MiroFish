#!/usr/bin/env python3
"""
Línea 6 (PD) — export a run as a prompt -> plan -> completion dataset record (Issue #28).

Bundles a MiroFish run's question (seed), the planning the model generated, and
the resulting report into a normalized record for fine-tuning / distillation.

Usage
-----
    # from a headless run dir (resolves all IDs from run_manifest.json)
    python backend/scripts/export_run_bundle.py \
        --run-dir runs/headless/<run-id> \
        --out-bundle runs/headless/<run-id>/bundle.json \
        --dataset datasets/mirofish_runs.jsonl

    # from explicit IDs
    python backend/scripts/export_run_bundle.py \
        --simulation-id <sim_id> --report-id <report_id> --project-id <proj_id> \
        --dataset datasets/mirofish_runs.jsonl

The dataset is JSONL, one record per run, deduplicated on content hash (so
re-running is idempotent).
"""

import argparse
import json
import os
import sys

_THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS, "..", "app", "research"))

from dataset import run_bundle  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export a MiroFish run as a dataset record (Línea 6 PD).")
    ap.add_argument("--uploads-root", default=run_bundle.DEFAULT_UPLOADS, help="backend/uploads root.")
    ap.add_argument("--run-dir", help="Headless run dir; resolves IDs from run_manifest.json.")
    ap.add_argument("--project-id")
    ap.add_argument("--simulation-id")
    ap.add_argument("--report-id")
    ap.add_argument("--include-seed-text", action="store_true", help="Embed extracted_text.txt in the bundle.")
    ap.add_argument("--no-personas", action="store_true", help="Don't embed the full generated personas (smaller records).")
    ap.add_argument("--out-bundle", help="Write the full bundle JSON here.")
    ap.add_argument("--dataset", help="Append the flattened training record to this JSONL (deduped).")
    args = ap.parse_args(argv)

    if not (args.run_dir or args.simulation_id):
        ap.error("provide --run-dir or at least --simulation-id")

    bundle = run_bundle.build_bundle(
        uploads_root=args.uploads_root,
        project_id=args.project_id,
        simulation_id=args.simulation_id,
        report_id=args.report_id,
        run_dir=args.run_dir,
        include_seed_text=args.include_seed_text,
        include_personas=not args.no_personas,
    )

    ids = bundle["ids"]
    has_q = bool(bundle["input"]["question"])
    has_plan = bool(bundle["plan"]["reasoning"])
    has_result = bool(bundle["result"]["report_markdown"])
    print(f"bundle_id={bundle['bundle_id']} model={bundle['model']}")
    print(f"  ids: {json.dumps(ids, ensure_ascii=False)}")
    print(f"  question={has_q}  plan_reasoning={has_plan}  report={has_result}")
    if not (has_q and has_result):
        print("  WARNING: question and/or report missing — check the IDs / that the run completed.")

    if args.out_bundle:
        run_bundle.write_bundle(bundle, args.out_bundle)
        print(f"  wrote bundle: {args.out_bundle}")

    if args.dataset:
        record = run_bundle.to_training_record(bundle)
        appended = run_bundle.append_to_dataset(record, args.dataset)
        print(f"  dataset: {'appended' if appended else 'skipped (duplicate content_hash)'} -> {args.dataset}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
