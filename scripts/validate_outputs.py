#!/usr/bin/env python3
"""Validate the stable fork's deterministic output contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_OUTPUTS = ("report.md", "metrics.json", "run_config.yaml", "logs.txt")


def validate_output_dir(output_dir: Path) -> list[str]:
    errors: list[str] = []
    for filename in REQUIRED_OUTPUTS:
        path = output_dir / filename
        if not path.is_file():
            errors.append(f"missing required output: {filename}")
        elif path.stat().st_size == 0:
            errors.append(f"empty required output: {filename}")

    metrics_path = output_dir / "metrics.json"
    if metrics_path.is_file():
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"invalid metrics.json: {exc}")
        else:
            if not isinstance(metrics, dict):
                errors.append("metrics.json must contain an object")
            else:
                if not metrics.get("case_id"):
                    errors.append("metrics.json missing case_id")
                if not metrics.get("mode"):
                    errors.append("metrics.json missing mode")
                declared = metrics.get("outputs")
                if declared != list(REQUIRED_OUTPUTS):
                    errors.append("metrics.json outputs do not match the output contract")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", nargs="?", default="outputs/example_run", type=Path)
    args = parser.parse_args()

    errors = validate_output_dir(args.output_dir)
    if errors:
        print("Output validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Output validation passed: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
