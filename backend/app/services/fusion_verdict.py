"""Best-effort Fusion verdict generation for observability artifacts."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger("mirofish.fusion_verdict")

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNS_ROOT = REPO_ROOT / "runs"


def _clip(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[:max_chars] + "\n\n[truncated]"


def _wiki_preview(wiki_context: Optional[Any]) -> str:
    if wiki_context is None:
        return "No wiki context available."
    if isinstance(wiki_context, str):
        return _clip(wiki_context, 4000)
    try:
        return _clip(json.dumps(wiki_context, ensure_ascii=False, default=str), 4000)
    except Exception:
        return _clip(str(wiki_context), 4000)


def _fallback_verdict(
    *,
    simulation_id: str,
    report_id: str,
    model: str,
    status: str,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    verdict: Dict[str, Any] = {
        "verdict_id": f"fusion_{report_id}",
        "simulation_id": simulation_id,
        "report_id": report_id,
        "generated_at": datetime.now().isoformat(),
        "status": status,
        "judge_model": model,
        "outcome": "needs_review",
        "confidence": 0.0,
        "summary": "Fusion judge did not complete; this fallback artifact keeps the observability trail explicit.",
        "supporting_findings": [],
        "risks": ["fusion_judge_unavailable"],
        "recommended_checks": [
            "Review the generated report against wiki pages and simulation action logs.",
            "Check llm_telemetry.jsonl and model_routing_audit.jsonl for model or parsing errors.",
        ],
    }
    if error:
        verdict["error"] = error
    return verdict


def _write_verdict(report_id: str, verdict: Dict[str, Any]) -> str:
    out_dir = RUNS_ROOT / "headless" / f"fusion_{report_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "verdict_raw.json"
    tmp_path = out_dir / "verdict_raw.json.tmp"
    tmp_path.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(out_path)
    return str(out_path)


def generate_fusion_verdict_for_report(
    *,
    simulation_id: str,
    report_id: str,
    report_markdown: str,
    wiki_context: Optional[Any] = None,
    simulation_requirement: Optional[str] = None,
) -> Optional[str]:
    """Generate and persist a Fusion verdict, without blocking report success."""
    if not Config.ENABLE_FUSION_VERDICT:
        return None

    model = Config.FUSION_VERDICT_MODEL
    base = _fallback_verdict(
        simulation_id=simulation_id,
        report_id=report_id,
        model=model,
        status="fallback",
    )
    running = {
        **base,
        "status": "running",
        "confidence": 0.0,
        "summary": "Fusion judge is evaluating the completed report against Wiki and simulation evidence.",
        "risks": [],
        "recommended_checks": [],
        "timeout_seconds": Config.FUSION_VERDICT_TIMEOUT_SECONDS,
    }
    _write_verdict(report_id, running)

    try:
        client = LLMClient(
            model=model,
            timeout=Config.FUSION_VERDICT_TIMEOUT_SECONDS,
            max_retries=0,
        )
        response = client.chat_json(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict simulation adjudicator. Evaluate whether the "
                        "report is internally consistent and grounded in the provided "
                        "simulation/wiki context. Return only valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Return JSON with keys: outcome, confidence, summary, "
                        "supporting_findings, risks, recommended_checks.\n\n"
                        f"Simulation ID: {simulation_id}\n"
                        f"Report ID: {report_id}\n"
                        f"Simulation requirement:\n{simulation_requirement or 'N/A'}\n\n"
                        f"Wiki context:\n{_wiki_preview(wiki_context)}\n\n"
                        "Report markdown:\n"
                        f"{_clip(report_markdown or '', Config.FUSION_VERDICT_MAX_REPORT_CHARS)}"
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        verdict = {
            **base,
            "status": "completed",
            "outcome": response.get("outcome", base["outcome"]),
            "confidence": response.get("confidence", base["confidence"]),
            "summary": response.get("summary", base["summary"]),
            "supporting_findings": response.get("supporting_findings", []),
            "risks": response.get("risks", []),
            "recommended_checks": response.get("recommended_checks", []),
            "raw_judge_response": response,
            "timeout_seconds": Config.FUSION_VERDICT_TIMEOUT_SECONDS,
        }
    except Exception as exc:  # noqa: BLE001 - observability artifact must be non-fatal
        logger.warning(
            "Fusion verdict generation failed for report %s (non-fatal): %s",
            report_id,
            exc,
        )
        verdict = {
            **base,
            "error": repr(exc),
            "timeout_seconds": Config.FUSION_VERDICT_TIMEOUT_SECONDS,
        }

    return _write_verdict(report_id, verdict)
