#!/usr/bin/env python3
"""
scripts/run_experiment.py — CLI entry point for the S2 experiment harness.

Usage:
    # Dry run (validate config, create dirs, hash files, no backend)
    python scripts/run_experiment.py --config configs/experiments/example_case.yaml --dry-run

    # Full run (requires MiroFish backend running)
    python scripts/run_experiment.py --config configs/experiments/example_case.yaml

    # Compare results across variants
    python scripts/run_experiment.py --compare --case example_case --runs-root runs

    # Override seed from CLI
    python scripts/run_experiment.py --config configs/experiments/example_case.yaml --seed 42

    # Override memory mode
    python scripts/run_experiment.py --config configs/experiments/example_case.yaml --memory-mode experimental
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure backend is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

# Import directly from the module file to avoid Flask dependency chain
# (app.__init__ imports Flask which may not be installed in lightweight envs)
import importlib.util
import types

_mod_path = str(PROJECT_ROOT / "backend" / "app" / "services" / "experiment_runner.py")
_spec = importlib.util.spec_from_file_location("experiment_runner", _mod_path)
if _spec is None or _spec.loader is None:
    print(f"ERROR: Cannot load experiment_runner from {_mod_path}", file=sys.stderr)
    sys.exit(1)
_mod = types.ModuleType("experiment_runner")
_mod.__file__ = _mod_path
_mod.__loader__ = _spec.loader
sys.modules["experiment_runner"] = _mod
_spec.loader.exec_module(_mod)

ExperimentRunner = _mod.ExperimentRunner
validate_config = _mod.validate_config
compute_run_id = _mod.compute_run_id


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MiroFish S2 Experiment Harness — reproducible baseline vs experimental runs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config", "-c",
        help="Path to experiment YAML config file",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Validate config, create dirs, hash files — but do NOT invoke backend",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare results across variants for a given case_id",
    )
    parser.add_argument(
        "--case",
        help="Case ID for --compare mode",
    )
    parser.add_argument(
        "--runs-root",
        default="runs",
        help="Root directory for run outputs (default: runs/)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override seed from config",
    )
    parser.add_argument(
        "--memory-mode",
        choices=["baseline", "experimental"],
        default=None,
        help="Override memory_mode from config",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:5001",
        help="MiroFish backend URL for full runs (default: http://localhost:5001)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Only validate the config file, do not run",
    )

    args = parser.parse_args()

    # ---- Compare mode ----
    if args.compare:
        if not args.case:
            print("ERROR: --case is required with --compare", file=sys.stderr)
            return 1
        comparison = ExperimentRunner.compare_results(
            runs_root=args.runs_root,
            case_id=args.case,
        )
        print(json.dumps(comparison, indent=2, ensure_ascii=False, default=str))
        return 0

    # ---- Run mode requires --config ----
    if not args.config:
        print("ERROR: --config is required unless using --compare", file=sys.stderr)
        parser.print_help()
        return 1

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: Config file not found: {args.config}", file=sys.stderr)
        return 1

    # ---- Validate-only mode ----
    if args.validate:
        import yaml
        with config_path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        errors = validate_config(cfg)
        if errors:
            print("Config validation FAILED:", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            return 1
        print("Config validation OK")
        run_id = compute_run_id(cfg["case_id"], cfg["variant"], cfg.get("seed", 1))
        print(f"  run_id: {run_id}")
        print(f"  memory_mode: {cfg.get('memory_mode', 'baseline')}")
        print(f"  output_dir: runs/{cfg['case_id']}/{cfg['variant']}/s{cfg.get('seed', 1)}/")
        return 0

    # ---- Load runner ----
    overrides = {}
    if args.seed is not None:
        overrides["seed"] = args.seed
    if args.memory_mode is not None:
        overrides["memory_mode"] = args.memory_mode

    try:
        runner = ExperimentRunner.from_yaml(str(config_path), **overrides)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"=== S2 Experiment Harness ===")
    print(f"  run_id:       {runner.run_id}")
    print(f"  case_id:      {runner.case_id}")
    print(f"  variant:      {runner.variant}")
    print(f"  seed:         {runner.seed}")
    print(f"  memory_mode:  {runner.memory_mode}")
    print(f"  output_dir:   {runner.output_dir}")
    print()

    # ---- Dry run ----
    if args.dry_run:
        print("Running in DRY-RUN mode (no backend invocation)...")
        result = runner.dry_run()
        print(f"\nDry run complete. Status: {result.status}")
        print(f"  output_dir:          {result.output_dir}")
        print(f"  config_snapshot:     {result.config_snapshot_path}")
        print(f"  seed_hashes:         {result.seed_hashes_path}")
        print(f"  prompt_hashes:       {result.prompt_hashes_path}")
        if result.error:
            print(f"  ERROR: {result.error}", file=sys.stderr)
            return 1
        return 0

    # ---- Full run ----
    print("Running in FULL mode (requires backend)...")
    result = runner.run(base_url=args.base_url)
    print(f"\nRun complete. Status: {result.status}")
    print(f"  output_dir:          {result.output_dir}")
    print(f"  rounds completed:    {result.num_rounds_completed}")
    print(f"  memory_mode:         {result.memory_mode}")
    if result.error:
        print(f"  ERROR: {result.error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())