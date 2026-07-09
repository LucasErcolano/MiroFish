"""
Structured report generation for schema-driven quantitative cases.
"""

import json
import re
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .report_agent import Report, ReportStatus
from .zep_tools import ZepToolsService

logger = get_logger("mirofish.structured_report_agent")


class StructuredReportAgent:
    """Generate a canonical JSON answer instead of a narrative report."""

    def __init__(
        self,
        *,
        graph_id: str,
        simulation_id: str,
        simulation_requirement: str,
        schema_id: str,
        report_context: Optional[Dict[str, Any]] = None,
    ):
        self.graph_id = graph_id
        self.simulation_id = simulation_id
        self.simulation_requirement = simulation_requirement
        self.schema_id = schema_id
        self.report_context = report_context or {}
        self.llm = LLMClient()
        self.tools = ZepToolsService()

    def generate_report(
        self,
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        report_id: Optional[str] = None,
    ) -> Report:
        import uuid

        report_id = report_id or f"report_{uuid.uuid4().hex[:12]}"
        report = Report(
            report_id=report_id,
            simulation_id=self.simulation_id,
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement,
            status=ReportStatus.GENERATING,
            created_at=datetime.now().isoformat(),
        )
        report.output_mode = "structured_json"
        report.schema_id = self.schema_id
        report.metadata = self.report_context

        try:
            if progress_callback:
                progress_callback("structured_context", 5, "Fetching simulation context")

            query = self.report_context.get("primary_query") or self.simulation_requirement
            sim_context = self.tools.get_simulation_context(
                self.graph_id,
                self.simulation_requirement,
                limit=25,
            )

            if progress_callback:
                progress_callback("structured_context", 20, "Running deep graph retrieval")

            insight = self.tools.insight_forge(
                graph_id=self.graph_id,
                query=query,
                simulation_requirement=self.simulation_requirement,
                report_context=json.dumps(self._json_safe(self.report_context), ensure_ascii=False),
                max_sub_queries=4,
            )
            panorama = self.tools.panorama_search(
                graph_id=self.graph_id,
                query=query,
                include_expired=True,
                limit=30,
            )

            quick_queries = self._quick_queries()
            quick_searches = {}
            for idx, (key, quick_query) in enumerate(quick_queries.items(), start=1):
                quick_searches[key] = self.tools.quick_search(
                    graph_id=self.graph_id,
                    query=quick_query,
                    limit=12,
                ).to_dict()
                if progress_callback:
                    progress_callback("structured_context", 20 + idx * 10, f"Retrieving {key}")

            if progress_callback:
                progress_callback("structured_answer", 70, "Generating canonical JSON answer")

            messages = self._build_messages(
                sim_context=sim_context,
                insight=insight.to_dict(),
                panorama=panorama.to_dict(),
                quick_searches=quick_searches,
            )
            answer = self.llm.chat_json(
                messages=messages,
                temperature=0.1,
                max_tokens=7000,
            )

            normalized = self._normalize_answer(answer)
            if self._has_missing_required_forecasts(normalized):
                repair_messages = self._build_repair_messages(messages, normalized)
                repaired_answer = self.llm.chat_json(
                    messages=repair_messages,
                    temperature=0.1,
                    max_tokens=7000,
                )
                repaired = self._normalize_answer(repaired_answer)
                if not self._has_missing_required_forecasts(repaired):
                    normalized = repaired

            report.structured_answer = normalized
            report.markdown_content = self._render_markdown(normalized)
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now().isoformat()

            if progress_callback:
                progress_callback("structured_answer", 100, "Structured report completed")

            return report
        except Exception as exc:
            logger.error(f"Structured report generation failed: {exc}")
            report.status = ReportStatus.FAILED
            report.error = str(exc)
            report.completed_at = datetime.now().isoformat()
            return report

    def _quick_queries(self) -> Dict[str, str]:
        if self.schema_id == "copa_america_winner_v1":
            return {
                "winner": "Argentina Colombia Copa America 2024 final predicted winner",
                "argentina": "Argentina Copa America 2024 final experience defense Messi",
                "colombia": "Colombia Copa America 2024 final unbeaten James Rodriguez threat",
                "uncertainty": "Argentina Colombia final uncertainty penalties extra time tactical risks",
            }
        return {
            "delta_1": "IPC febrero 2025 variacion mensual pronostico rango",
            "delta_2": "IPC abril 2025 variacion mensual rango tendencia",
            "delta_3": "IPC julio 2025 variacion mensual rango tendencia",
            "delta_4": "IPC diciembre 2025 inflacion acumulada 2025 estabilidad programa economico",
        }

    def _build_messages(
        self,
        *,
        sim_context: Dict[str, Any],
        insight: Dict[str, Any],
        panorama: Dict[str, Any],
        quick_searches: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        if self.schema_id == "copa_america_winner_v1":
            return self._build_copa_messages(
                sim_context=sim_context,
                insight=insight,
                panorama=panorama,
                quick_searches=quick_searches,
            )
        return self._build_ipc_messages(
            sim_context=sim_context,
            insight=insight,
            panorama=panorama,
            quick_searches=quick_searches,
        )

    def _build_ipc_messages(
        self,
        *,
        sim_context: Dict[str, Any],
        insight: Dict[str, Any],
        panorama: Dict[str, Any],
        quick_searches: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        metadata = {
            "cutoff_date": self.report_context.get("cutoff_date"),
            "temporal_package": self.report_context.get("temporal_package"),
            "source_ids": self.report_context.get("source_ids", []),
            "system_constraints_text": self.report_context.get("system_constraints_text"),
            "model": Config.LLM_MODEL_NAME,
            "simulation_id": self.simulation_id,
            "graph_id": self.graph_id,
        }

        system_prompt = (
            "You are generating a structured quantitative forecast answer.\n"
            "Return one JSON object only.\n"
            "Do not add markdown.\n"
            "Use only evidence present in the provided context.\n"
            "Treat source_packet_text as the primary evidence when it is provided.\n"
            "The task is a forecast under uncertainty: make the best estimate supported by directional, monthly, annual, or causal evidence.\n"
            "Numeric forecast fields are mandatory.\n"
            "Never leave delta_1, delta_2, delta_3, or delta_4 forecast fields null.\n"
            "Never abstain because no source gives the exact target month.\n"
            "Use wider ranges to express uncertainty.\n"
            "If evidence is weak, still produce a bounded estimate and explain the uncertainty in reason/evidence.\n"
            "Do not use post-cutoff data.\n"
            "Every important claim in evidence must include source_id values copied from the context when available.\n"
            "Preserve source_id attribution exactly as written in source_packet_text.\n"
            "Required JSON shape:\n"
            "{\n"
            '  "delta_1": {"point_estimate": number, "range_min": number, "range_max": number},\n'
            '  "delta_2": {"range_min": number, "range_max": number, "trend": "acelerando"|"estable"|"desacelerando"},\n'
            '  "delta_3": {"range_min": number, "range_max": number, "trend": "acelerando"|"estable"|"desacelerando", "reason": string},\n'
            '  "delta_4": {"point_estimate": number, "range_min": number, "range_max": number, "program_stability": "consolidado"|"incierto"|"revertido", "accumulated_2025_range_min": number, "accumulated_2025_range_max": number},\n'
            '  "causal_mechanism": {"dominant_variable": string, "main_risk": string},\n'
            '  "evidence": [{"claim": string, "source_id": [string]}],\n'
            '  "metadata": {"cutoff_date": string|null, "temporal_package": string|null, "model": string, "simulation_id": string, "graph_id": string}\n'
            "}\n"
            "For delta_1 and delta_2, infer monthly estimates from the latest monthly IPC, annual expectations, trend evidence, and risks.\n"
            "For delta_3, infer a July monthly IPC range and trend, not a bucket.\n"
            "For delta_4, provide both the December 2025 monthly IPC estimate/range and the accumulated 2025 range."
        )

        user_payload = {
            "simulation_requirement": self.simulation_requirement,
            "report_context": self._json_safe(self.report_context),
            "source_packet_text": self.report_context.get("source_packet_text"),
            "metadata": metadata,
            "simulation_context": self._json_safe(sim_context),
            "insight_forge": self._json_safe(insight),
            "panorama": self._json_safe(panorama),
            "quick_searches": self._json_safe(quick_searches),
        }

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)},
        ]

    def _build_copa_messages(
        self,
        *,
        sim_context: Dict[str, Any],
        insight: Dict[str, Any],
        panorama: Dict[str, Any],
        quick_searches: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        metadata = {
            "cutoff_date": self.report_context.get("cutoff_date"),
            "temporal_package": self.report_context.get("temporal_package"),
            "source_ids": self.report_context.get("source_ids", []),
            "system_constraints_text": self.report_context.get("system_constraints_text"),
            "model": Config.LLM_MODEL_NAME,
            "simulation_id": self.simulation_id,
            "graph_id": self.graph_id,
        }

        system_prompt = (
            "You are generating a structured pre-match football forecast answer.\n"
            "Return one JSON object only.\n"
            "Do not add markdown.\n"
            "Use only evidence present in the provided context.\n"
            "Treat source_packet_text as the primary evidence when it is provided.\n"
            "Do not use post-cutoff data or the real final result.\n"
            "You must choose exactly one predicted winner: Argentina or Colombia.\n"
            "Confidence is mandatory and must be a number from 0 to 1.\n"
            "Use source_id values copied from the context for every important claim.\n"
            "Preserve source_id attribution exactly as written in source_packet_text.\n"
            "Required JSON shape:\n"
            "{\n"
            '  "predicted_winner": "Argentina"|"Colombia",\n'
            '  "confidence": number,\n'
            '  "winner_probability_point": number,\n'
            '  "winner_probability_range": {"winner_min": number, "winner_max": number},\n'
            '  "predicted_goal_margin": {"winner_goals_margin_point": number, "winner_goals_margin_min": number, "winner_goals_margin_max": number, "rationale": string},\n'
            '  "probability_calibration": {"method": string, "confidence_rationale": string, "range_rationale": string},\n'
            '  "probability_drivers": [{"factor": string, "direction": "Argentina"|"Colombia"|"uncertainty", "source_id": [string]}],\n'
            '  "justification": [{"claim": string, "source_id": [string]}],\n'
            '  "uncertainty": [{"factor": string, "source_id": [string]}],\n'
            '  "evidence": [{"claim": string, "source_id": [string]}],\n'
            '  "metadata": {"cutoff_date": string|null, "temporal_package": string|null, "model": string, "simulation_id": string, "graph_id": string}\n'
            "}\n"
            "The probability ranges are subjective forecast ranges derived from the evidence; "
            "they do not need to sum exactly to 1, but they must be bounded between 0 and 1.\n"
            "The predicted winner probability range must be narrow: winner_max - winner_min must be <= 0.05. "
            "winner_probability_point must be inside that range.\n"
            "Predicted_goal_margin is a pre-match forecast for how many goals the selected winner wins by; "
            "do not use the real final score.\n"
            "Do not reuse a generic default probability range across different temporal packages. "
            "If the context lacks direct odds or model probabilities, lower confidence and explain uncertainty instead of using a very wide winner range. "
            "If the context includes odds, market prices, or model probabilities, anchor the midpoint to those signals "
            "and use a narrower range. Use non-round values when the evidence supports them. "
            "Explain the calibration in probability_calibration."
        )

        user_payload = {
            "simulation_requirement": self.simulation_requirement,
            "report_context": self._json_safe(self.report_context),
            "source_packet_text": self.report_context.get("source_packet_text"),
            "metadata": metadata,
            "simulation_context": self._json_safe(sim_context),
            "insight_forge": self._json_safe(insight),
            "panorama": self._json_safe(panorama),
            "quick_searches": self._json_safe(quick_searches),
        }

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)},
        ]

    def _build_repair_messages(
        self,
        original_messages: List[Dict[str, str]],
        normalized_answer: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        if self.schema_id == "copa_america_winner_v1":
            repair_task = (
                "Return the same JSON schema again, but fill every required field. "
                "Choose exactly one predicted_winner, set confidence between 0 and 1, "
                "provide winner_probability_point plus winner_min/winner_max, and include justification "
                "and uncertainty items with source_id arrays. Include probability_calibration "
                "and probability_drivers explaining why the range and confidence are not generic defaults. "
                "Include predicted_goal_margin, ensure winner_max - winner_min <= 0.05, "
                "and ensure winner_probability_point is inside that range."
            )
        else:
            repair_task = (
                "Return the same JSON schema again, but fill every required forecast field. "
                "Use broad ranges if uncertainty is high. Do not use null for delta_1, "
                "delta_2, delta_3, or delta_4."
            )
        repair_instruction = {
            "role": "user",
            "content": json.dumps(
                {
                    "error": "The previous answer left required forecast fields null or empty.",
                    "previous_answer": normalized_answer,
                    "repair_task": repair_task,
                },
                ensure_ascii=False,
                indent=2,
            ),
        }
        return [*original_messages, repair_instruction]

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(item) for item in value]
        if hasattr(value, "value") and not isinstance(value, (str, bytes, int, float, bool)):
            try:
                return self._json_safe(value.value)
            except Exception:
                pass
        return value

    def _normalize_answer(self, answer: Dict[str, Any]) -> Dict[str, Any]:
        if self.schema_id == "copa_america_winner_v1":
            return self._normalize_copa_answer(answer)
        return self._normalize_ipc_answer(answer)

    def _normalize_ipc_answer(self, answer: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {
            "delta_1": {
                "point_estimate": self._to_float(answer.get("delta_1", {}).get("point_estimate")),
                "range_min": self._to_float(answer.get("delta_1", {}).get("range_min")),
                "range_max": self._to_float(answer.get("delta_1", {}).get("range_max")),
            },
            "delta_2": {
                "range_min": self._to_float(answer.get("delta_2", {}).get("range_min")),
                "range_max": self._to_float(answer.get("delta_2", {}).get("range_max")),
                "trend": self._normalize_enum(
                    answer.get("delta_2", {}).get("trend"),
                    {"acelerando", "estable", "desacelerando"},
                ),
            },
            "delta_3": {
                "range_min": self._to_float(answer.get("delta_3", {}).get("range_min")),
                "range_max": self._to_float(answer.get("delta_3", {}).get("range_max")),
                "trend": self._normalize_enum(
                    answer.get("delta_3", {}).get("trend"),
                    {"acelerando", "estable", "desacelerando"},
                ),
                "reason": str(answer.get("delta_3", {}).get("reason") or "").strip(),
            },
            "delta_4": {
                "point_estimate": self._to_float(answer.get("delta_4", {}).get("point_estimate")),
                "range_min": self._to_float(answer.get("delta_4", {}).get("range_min")),
                "range_max": self._to_float(answer.get("delta_4", {}).get("range_max")),
                "program_stability": self._normalize_enum(
                    answer.get("delta_4", {}).get("program_stability"),
                    {"consolidado", "incierto", "revertido"},
                ),
                "accumulated_2025_range_min": self._to_float(
                    answer.get("delta_4", {}).get("accumulated_2025_range_min")
                ),
                "accumulated_2025_range_max": self._to_float(
                    answer.get("delta_4", {}).get("accumulated_2025_range_max")
                ),
            },
            "causal_mechanism": {
                "dominant_variable": str(
                    answer.get("causal_mechanism", {}).get("dominant_variable") or ""
                ).strip(),
                "main_risk": str(
                    answer.get("causal_mechanism", {}).get("main_risk") or ""
                ).strip(),
            },
            "evidence": self._normalize_evidence(answer.get("evidence")),
            "metadata": {
                "cutoff_date": self.report_context.get("cutoff_date"),
                "temporal_package": self.report_context.get("temporal_package"),
                "model": Config.LLM_MODEL_NAME,
                "simulation_id": self.simulation_id,
                "graph_id": self.graph_id,
            },
        }
        return normalized

    def _normalize_copa_answer(self, answer: Dict[str, Any]) -> Dict[str, Any]:
        probability_range = answer.get("winner_probability_range", {}) or {}
        winner = str(answer.get("predicted_winner") or "").strip()
        if winner.lower() == "argentina":
            winner = "Argentina"
        elif winner.lower() == "colombia":
            winner = "Colombia"
        else:
            winner = None
        winner_probability_point = self._to_probability(answer.get("winner_probability_point"))
        winner_min = self._to_probability(probability_range.get("winner_min"))
        winner_max = self._to_probability(probability_range.get("winner_max"))
        if winner_min is None or winner_max is None:
            if winner == "Argentina":
                winner_min = self._to_probability(probability_range.get("argentina_min"))
                winner_max = self._to_probability(probability_range.get("argentina_max"))
            elif winner == "Colombia":
                winner_min = self._to_probability(probability_range.get("colombia_min"))
                winner_max = self._to_probability(probability_range.get("colombia_max"))
        if winner_probability_point is None and winner_min is not None and winner_max is not None:
            winner_probability_point = round((winner_min + winner_max) / 2, 4)

        normalized = {
            "predicted_winner": winner,
            "confidence": self._to_probability(answer.get("confidence")),
            "winner_probability_point": winner_probability_point,
            "winner_probability_range": {
                "winner_min": winner_min,
                "winner_max": winner_max,
            },
            "predicted_goal_margin": self._normalize_goal_margin(
                answer.get("predicted_goal_margin")
            ),
            "probability_calibration": self._normalize_probability_calibration(
                answer.get("probability_calibration")
            ),
            "probability_drivers": self._normalize_probability_drivers(
                answer.get("probability_drivers")
            ),
            "justification": self._normalize_claim_list(answer.get("justification"), "claim"),
            "uncertainty": self._normalize_claim_list(answer.get("uncertainty"), "factor"),
            "evidence": self._normalize_evidence(answer.get("evidence")),
            "metadata": {
                "cutoff_date": self.report_context.get("cutoff_date"),
                "temporal_package": self.report_context.get("temporal_package"),
                "model": Config.LLM_MODEL_NAME,
                "simulation_id": self.simulation_id,
                "graph_id": self.graph_id,
            },
        }
        return normalized

    def _normalize_goal_margin(self, value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            return {
                "winner_goals_margin_point": None,
                "winner_goals_margin_min": None,
                "winner_goals_margin_max": None,
                "rationale": "",
            }
        return {
            "winner_goals_margin_point": self._to_float(value.get("winner_goals_margin_point")),
            "winner_goals_margin_min": self._to_float(value.get("winner_goals_margin_min")),
            "winner_goals_margin_max": self._to_float(value.get("winner_goals_margin_max")),
            "rationale": str(value.get("rationale") or "").strip(),
        }

    def _normalize_probability_calibration(self, value: Any) -> Dict[str, str]:
        if not isinstance(value, dict):
            return {"method": "", "confidence_rationale": "", "range_rationale": ""}
        return {
            "method": str(value.get("method") or "").strip(),
            "confidence_rationale": str(value.get("confidence_rationale") or "").strip(),
            "range_rationale": str(value.get("range_rationale") or "").strip(),
        }

    def _normalize_probability_drivers(self, values: Any) -> List[Dict[str, Any]]:
        normalized = []
        for item in values or []:
            if not isinstance(item, dict):
                continue
            direction = str(item.get("direction") or "").strip()
            if direction not in {"Argentina", "Colombia", "uncertainty"}:
                direction = "uncertainty"
            source_ids = item.get("source_id") or item.get("source_ids") or []
            if isinstance(source_ids, str):
                source_ids = [source_ids]
            normalized.append({
                "factor": str(item.get("factor") or "").strip(),
                "direction": direction,
                "source_id": [str(source_id).strip() for source_id in source_ids if str(source_id).strip()],
            })
        return normalized

    def _normalize_claim_list(self, values: Any, text_key: str) -> List[Dict[str, Any]]:
        normalized = []
        for item in values or []:
            if isinstance(item, str):
                normalized.append({text_key: item.strip(), "source_id": []})
                continue
            if not isinstance(item, dict):
                continue
            source_id = item.get("source_id") or item.get("source_ids") or []
            if isinstance(source_id, str):
                source_id = re.findall(r"[A-Z]+_[0-9]+", source_id) or [source_id]
            elif not isinstance(source_id, list):
                source_id = [str(source_id)]
            normalized.append({
                text_key: str(item.get(text_key) or item.get("claim") or "").strip(),
                "source_id": [str(value) for value in source_id if str(value).strip()],
            })
        return normalized

    def _normalize_evidence(self, evidence: Any) -> List[Dict[str, Any]]:
        normalized = []
        for item in evidence or []:
            if not isinstance(item, dict):
                continue
            source_id = item.get("source_id") or item.get("source_ids") or []
            if isinstance(source_id, str):
                source_id = re.findall(r"[A-Z]+_[0-9]+", source_id) or [source_id]
            elif not isinstance(source_id, list):
                source_id = [str(source_id)]
            normalized.append({
                "claim": str(item.get("claim") or "").strip(),
                "source_id": [str(value) for value in source_id if str(value).strip()],
            })
        return normalized

    def _has_missing_required_forecasts(self, answer: Dict[str, Any]) -> bool:
        if self.schema_id == "copa_america_winner_v1":
            probability_range = answer.get("winner_probability_range", {}) or {}
            goal_margin = answer.get("predicted_goal_margin", {}) or {}
            checks = [
                answer.get("predicted_winner"),
                answer.get("confidence"),
                answer.get("winner_probability_point"),
                probability_range.get("winner_min"),
                probability_range.get("winner_max"),
                goal_margin.get("winner_goals_margin_point"),
                goal_margin.get("winner_goals_margin_min"),
                goal_margin.get("winner_goals_margin_max"),
            ]
            if any(value is None or value == "" for value in checks):
                return True
            try:
                point = float(answer.get("winner_probability_point"))
                winner_min = float(probability_range.get("winner_min"))
                winner_max = float(probability_range.get("winner_max"))
                return (
                    winner_max - winner_min > 0.05
                    or point < winner_min
                    or point > winner_max
                )
            except (TypeError, ValueError):
                return True
        checks = [
            answer.get("delta_1", {}).get("point_estimate"),
            answer.get("delta_1", {}).get("range_min"),
            answer.get("delta_1", {}).get("range_max"),
            answer.get("delta_2", {}).get("range_min"),
            answer.get("delta_2", {}).get("range_max"),
            answer.get("delta_2", {}).get("trend"),
            answer.get("delta_3", {}).get("range_min"),
            answer.get("delta_3", {}).get("range_max"),
            answer.get("delta_3", {}).get("trend"),
            answer.get("delta_4", {}).get("point_estimate"),
            answer.get("delta_4", {}).get("range_min"),
            answer.get("delta_4", {}).get("range_max"),
            answer.get("delta_4", {}).get("program_stability"),
            answer.get("delta_4", {}).get("accumulated_2025_range_min"),
            answer.get("delta_4", {}).get("accumulated_2025_range_max"),
        ]
        return any(value is None or value == "" for value in checks)

    @staticmethod
    def _normalize_enum(value: Any, allowed: set[str]) -> Optional[str]:
        if value is None:
            return None
        lowered = str(value).strip().lower()
        return lowered if lowered in allowed else None

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)):
            return round(float(value), 4)
        match = re.search(r"-?[0-9]+(?:[.,][0-9]+)?", str(value))
        if not match:
            return None
        return round(float(match.group(0).replace(",", ".")), 4)

    def _to_probability(self, value: Any) -> Optional[float]:
        number = self._to_float(value)
        if number is None:
            return None
        if number > 1:
            number = number / 100
        return round(min(max(number, 0.0), 1.0), 4)

    def _render_markdown(self, answer: Dict[str, Any]) -> str:
        if self.schema_id == "copa_america_winner_v1":
            return self._render_copa_markdown(answer)
        return self._render_ipc_markdown(answer)

    def _render_ipc_markdown(self, answer: Dict[str, Any]) -> str:
        d1 = answer["delta_1"]
        d2 = answer["delta_2"]
        d3 = answer["delta_3"]
        d4 = answer["delta_4"]
        causal = answer["causal_mechanism"]
        evidence_lines = []
        for item in answer.get("evidence", []):
            evidence_lines.append(
                f"- {item.get('claim', '')} [{', '.join(item.get('source_id', []))}]"
            )

        return "\n".join([
            "# Structured IPC Forecast",
            "",
            f"- Cutoff: {answer['metadata'].get('cutoff_date')}",
            f"- Temporal package: {answer['metadata'].get('temporal_package')}",
            f"- Model: {answer['metadata'].get('model')}",
            "",
            "## Delta 1",
            f"- point_estimate: {d1.get('point_estimate')}",
            f"- range: {d1.get('range_min')} to {d1.get('range_max')}",
            "",
            "## Delta 2",
            f"- range: {d2.get('range_min')} to {d2.get('range_max')}",
            f"- trend: {d2.get('trend')}",
            "",
            "## Delta 3",
            f"- range: {d3.get('range_min')} to {d3.get('range_max')}",
            f"- trend: {d3.get('trend')}",
            f"- reason: {d3.get('reason')}",
            "",
            "## Delta 4",
            f"- point_estimate: {d4.get('point_estimate')}",
            f"- monthly_range: {d4.get('range_min')} to {d4.get('range_max')}",
            f"- program_stability: {d4.get('program_stability')}",
            f"- accumulated_2025_range: {d4.get('accumulated_2025_range_min')} to {d4.get('accumulated_2025_range_max')}",
            "",
            "## Causal mechanism",
            f"- dominant_variable: {causal.get('dominant_variable')}",
            f"- main_risk: {causal.get('main_risk')}",
            "",
            "## Evidence",
            *evidence_lines,
            "",
        ])

    def _render_copa_markdown(self, answer: Dict[str, Any]) -> str:
        probability = answer["winner_probability_range"]
        goal_margin = answer.get("predicted_goal_margin", {}) or {}
        calibration = answer.get("probability_calibration", {}) or {}
        justification_lines = [
            f"- {item.get('claim', '')} [{', '.join(item.get('source_id', []))}]"
            for item in answer.get("justification", [])
        ]
        driver_lines = [
            f"- {item.get('direction', '')}: {item.get('factor', '')} [{', '.join(item.get('source_id', []))}]"
            for item in answer.get("probability_drivers", [])
        ]
        uncertainty_lines = [
            f"- {item.get('factor', '')} [{', '.join(item.get('source_id', []))}]"
            for item in answer.get("uncertainty", [])
        ]
        evidence_lines = [
            f"- {item.get('claim', '')} [{', '.join(item.get('source_id', []))}]"
            for item in answer.get("evidence", [])
        ]

        return "\n".join([
            "# Structured Copa America Forecast",
            "",
            f"- Cutoff: {answer['metadata'].get('cutoff_date')}",
            f"- Temporal package: {answer['metadata'].get('temporal_package')}",
            f"- Model: {answer['metadata'].get('model')}",
            "",
            f"Ganador predicho: {answer.get('predicted_winner')}",
            f"Confianza: {answer.get('confidence')}",
            "",
            "## Probability range",
            f"- Winner probability point: {answer.get('winner_probability_point')}",
            f"- Winner range: {probability.get('winner_min')} to {probability.get('winner_max')}",
            "",
            "## Predicted goal margin",
            f"- Winner margin point: {goal_margin.get('winner_goals_margin_point')}",
            f"- Winner margin range: {goal_margin.get('winner_goals_margin_min')} to {goal_margin.get('winner_goals_margin_max')}",
            f"- Rationale: {goal_margin.get('rationale', '')}",
            "",
            "## Probability calibration",
            f"- Method: {calibration.get('method', '')}",
            f"- Confidence rationale: {calibration.get('confidence_rationale', '')}",
            f"- Range rationale: {calibration.get('range_rationale', '')}",
            "",
            "## Probability drivers",
            *driver_lines,
            "",
            "## Justificacion",
            *justification_lines,
            "",
            "## Incertidumbre",
            *uncertainty_lines,
            "",
            "## Evidence",
            *evidence_lines,
            "",
        ])
