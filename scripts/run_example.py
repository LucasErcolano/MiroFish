#!/usr/bin/env python3
"""Run the repository's deterministic minimal example.

This is not a substitute for a paid LLM/OASIS simulation. It is a reproducible
batch path that proves the checkout can load an example and generate the
documented output files.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"required example file missing: {path}")
    return path.read_text(encoding="utf-8")


def run_example(case_dir: Path, output_dir: Path) -> dict:
    case_card = read_text(case_dir / "case_card.md")
    seed_input = read_text(case_dir / "input.md")
    rubric = read_text(case_dir / "rubric.md")
    config = read_text(case_dir / "config.yaml")

    output_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat()

    report = "\n".join(
        [
            "# Minimal Example Report",
            "",
            "This offline fixture loaded the case card, seed evidence, rubric, and config.",
            "",
            "Conclusion: Signal A is better supported by the provided seed evidence.",
            "",
            "No LLM calls, API keys, databases, or raw simulation artifacts were used.",
        ]
    )
    metrics = {
        "case_id": "minimal_case",
        "mode": "offline_fixture",
        "created_at": created_at,
        "loaded_files": {
            "case_card_chars": len(case_card),
            "input_chars": len(seed_input),
            "rubric_chars": len(rubric),
            "config_chars": len(config),
        },
        "outputs": ["report.md", "metrics.json", "run_config.yaml", "logs.txt"],
    }

    (output_dir / "report.md").write_text(report + "\n", encoding="utf-8")
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "run_config.yaml").write_text(config, encoding="utf-8")
    (output_dir / "logs.txt").write_text(
        f"{created_at} minimal example completed\n",
        encoding="utf-8",
    )
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the MiroFish minimal example")
    parser.add_argument(
        "--case-dir",
        default="examples/minimal_case",
        help="Path to the minimal case directory",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/example_run",
        help="Directory where outputs will be written",
    )
    args = parser.parse_args()

    case_dir = Path(args.case_dir)
    output_dir = Path(args.output_dir)
    if not case_dir.is_absolute():
        case_dir = REPO_ROOT / case_dir
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir

    metrics = run_example(case_dir, output_dir)
    print(f"Example run passed. Output written to {args.output_dir}")
    print(json.dumps({"case_id": metrics["case_id"], "mode": metrics["mode"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
