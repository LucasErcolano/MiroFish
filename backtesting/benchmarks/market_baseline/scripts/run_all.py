#!/usr/bin/env python3
"""Run the full market baseline pipeline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPTS = [
    "extract_temporal_cutoffs.py",
    "extract_mirofish_predictions.py",
    "build_market_odds_csv.py",
    "compute_metrics.py",
    "build_report.py",
]


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    for script in SCRIPTS:
        print(f"==> {script}")
        subprocess.run([sys.executable, str(script_dir / script)], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

