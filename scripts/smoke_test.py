#!/usr/bin/env python3
"""Offline smoke test for the stable MiroFish fork."""

from __future__ import annotations

import argparse
import py_compile
import sys
from pathlib import Path

from run_example import run_example
from validate_outputs import validate_output_dir

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    Path("README.md"),
    Path(".env.example"),
    Path("backend/pyproject.toml"),
    Path("frontend/package.json"),
    Path("examples/minimal_case/case_card.md"),
    Path("examples/minimal_case/input.md"),
    Path("examples/minimal_case/rubric.md"),
    Path("examples/minimal_case/config.yaml"),
]

PY_COMPILE_PATHS = [
    Path("backend/app/services/model_router.py"),
    Path("backend/app/services/experimental_memory.py"),
    Path("backend/app/services/wiki_memory/wiki_compiler.py"),
    Path("backend/app/research/entropy/metrics.py"),
    Path("backend/app/research/dataset/run_bundle.py"),
    Path("backend/scripts/run_reddit_simulation.py"),
    Path("scripts/run_example.py"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a deterministic smoke test")
    parser.add_argument(
        "--output-dir",
        default="outputs/smoke_test",
        help="Directory where smoke outputs will be written",
    )
    args = parser.parse_args()

    missing = [str(path) for path in REQUIRED_PATHS if not (REPO_ROOT / path).exists()]
    if missing:
        print("Smoke test failed. Missing required paths:")
        for path in missing:
            print(f"  - {path}")
        return 1

    for path in PY_COMPILE_PATHS:
        py_compile.compile(str(REPO_ROOT / path), doraise=True)

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    run_example(REPO_ROOT / "examples/minimal_case", output_dir)
    output_errors = validate_output_dir(output_dir)
    if output_errors:
        print("Smoke test failed. Invalid outputs:")
        for error in output_errors:
            print(f"  - {error}")
        return 1

    print(f"Smoke test passed. Output written to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
