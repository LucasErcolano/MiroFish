"""Run and strictly validate a small paid MiroFish end-to-end smoke test."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.mirofish_headless import MiroFishHeadlessRunner, write_json  # noqa: E402


DEFAULT_SEED = REPO_ROOT / "backtesting" / "case-a-s2-positional-noise" / "input" / "seed_bundle.md"
DEFAULT_REQUIREMENT = (
    "Predice el ganador y el marcador probable de la final de la Copa America 2024 "
    "entre Argentina y Colombia, con una justificacion breve."
)


def resolve_smoke_api_key(environ: dict[str, str] | os._Environ[str]) -> str | None:
    """Select the secret used only to scan generated smoke artifacts."""
    return (
        environ.get("MIROFISH_SMOKE_API_KEY")
        or environ.get("OPENROUTER_API_KEY")
        or environ.get("DEEPINFRA_API_KEY")
    )


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def validate_real_smoke(manifest: dict[str, Any], output_dir: Path, api_key: str | None = None) -> list[str]:
    errors: list[str] = []
    if manifest.get("status") != "completed":
        errors.append(f"run status is {manifest.get('status')!r}, expected 'completed'")
    if manifest.get("is_real_mirofish_system") is not True:
        errors.append("real-system gate did not pass")

    graph = manifest.get("graph_data_summary") or {}
    if _int(graph.get("node_count")) <= 0 or _int(graph.get("edge_count")) <= 0:
        errors.append("graph has no nodes or edges")
    if _int(manifest.get("num_rounds_or_epochs")) <= 0:
        errors.append("no completed simulation rounds were observed")

    run_status = manifest.get("final_run_status") or {}
    if _int(run_status.get("total_actions_count")) <= 0:
        errors.append("no OASIS actions were observed")
    if not manifest.get("report_id"):
        errors.append("ReportAgent did not return a report_id")

    report_path = output_dir / "mirofish_report_raw.md"
    if not report_path.is_file() or report_path.stat().st_size < 10:
        errors.append("ReportAgent markdown is missing or empty")

    memory_path = output_dir / "simulation_artifacts" / "experimental_memory_evidence.json"
    if not memory_path.is_file():
        errors.append("experimental memory evidence is missing")
    else:
        memory = json.loads(memory_path.read_text(encoding="utf-8"))
        if memory.get("memory_dir_exists") is not True:
            errors.append("experimental memory directory was not created")

    close = manifest.get("environment_close") or {}
    if close.get("attempted") is not True or close.get("success") is not True:
        errors.append(f"OASIS environment cleanup failed: {close.get('error')}")

    if api_key:
        for path in output_dir.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".log"}:
                continue
            if api_key in path.read_text(encoding="utf-8", errors="ignore"):
                errors.append(f"API key leaked into artifact {path.relative_to(output_dir)}")
                break
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5001")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--poll-timeout", type=int, default=1800)
    args = parser.parse_args()

    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else REPO_ROOT / "outputs" / "real-smoke" / datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    runner = MiroFishHeadlessRunner(
        base_url=args.base_url,
        output_dir=output_dir,
        repo_root=REPO_ROOT,
        poll_interval=2,
        accept_language="es",
    )
    manifest = runner.run_full_flow(
        files=[DEFAULT_SEED],
        simulation_requirement=DEFAULT_REQUIREMENT,
        project_name="MiroFish real provider smoke",
        max_rounds=9,
        platform="parallel",
        generate_report=True,
        poll_timeout_seconds=args.poll_timeout,
        close_environment=True,
        graph_chunk_size=2000,
    )

    errors = validate_real_smoke(manifest, output_dir, resolve_smoke_api_key(os.environ))
    validation = {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "output_dir": str(output_dir.resolve()),
    }
    write_json(output_dir / "real_smoke_validation.json", validation)
    if errors:
        raise SystemExit("Real smoke failed:\n- " + "\n- ".join(errors))

    print("Real MiroFish smoke passed.")
    print(f"Artifacts: {output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
