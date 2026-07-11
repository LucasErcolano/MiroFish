"""
report_agent_quality_guards.py — Hermes-added quality guards & resilience layer.

This module contains the additions we built on top of upstream MiroFish to make
Report Agent runs robust enough for unattended local-model evaluation. None of
this code exists in upstream MiroFish, and none of it is a translation of
upstream strings — translations live in ``report_agent_native_locales`` and
include things like the localized prompt templates and the tool-result header
table together with the ``localize_tool_result`` function that applies it.

Categories:

1. **Tool-call parser extensions** — accept multiple alternative formats that
   Gemini / Mistral / Qwen emit instead of the canonical
   ``<tool_call>{"name":...,"parameters":{...}}</tool_call>``.

   * ``<tool_code>print(insight_forge.search(...))</tool_code>``
   * ``<tool_code>print(insight_forge.query(...))</tool_code>``
   * ``Action: {...}`` and ``Action:\n```json {...} ```
   * Plain ```json fenced JSON``` blocks
   * JSON arrays of tool calls (e.g. ``[{"tool_code": "...", ...}]``)
   * Aliases: ``tool`` / ``tool_code`` → ``name``; ``params`` → ``parameters``;
     ``topic`` → ``query``.

2. **Fail-closed section validator** — reject sections that were not grounded
   in real tool output, contain leaked ReACT scaffolding, model self-reported
   tool failures, raw tool markup, or are in the wrong language for the locale.

3. **Final-answer scrubber** — strip leaked ``Thought\\n...`` blocks and trailing
   ``<tool_code>``/``<tool_call>`` payloads from candidate Final Answers BEFORE
   they reach the validator, so legitimate replies that just had a noisy prelude
   are recoverable.

4. **Interview-agents OASIS-down detector** — when ``interview_agents`` returns
   a "simulation environment is not running" body, the agent uses this helper
   to detect the failure and transparently re-route the request through
   ``insight_forge`` so the model gets grounded data instead of an error
   message it would otherwise leak into the report body.

All public callables are intentionally module-level functions that take the
caller's state explicitly (locale, simulation_requirement, etc.). This keeps
the module independent from ``ReportAgent`` so it stays easy to upstream or
move sideways into a separate package.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# 1. Tool-call parser extensions
# ─────────────────────────────────────────────────────────────────────────────


def _coerce_to_valid_tool_call(data: Any, valid_tool_names: Iterable[str]) -> Optional[Dict[str, Any]]:
    """Return a normalized ``{"name", "parameters"}`` dict or None.

    Accepts aliases ``tool`` / ``tool_code`` → ``name``, ``params`` → ``parameters``,
    ``topic`` → ``query``. Rejects payloads whose tool name is not in the
    whitelist.
    """
    if not isinstance(data, dict):
        return None

    # Normalize alias keys.
    if "tool" in data and "name" not in data:
        data["name"] = data.pop("tool")
    if "tool_code" in data and "name" not in data:
        data["name"] = data.pop("tool_code")
    if "params" in data and "parameters" not in data:
        data["parameters"] = data.pop("params")

    tool_name = data.get("name")
    if not tool_name or tool_name not in set(valid_tool_names):
        return None

    parameters = data.get("parameters", {})
    if not isinstance(parameters, dict):
        return None

    # Common alias from Mistral / Qwen variants.
    if "topic" in parameters and "query" not in parameters:
        parameters["query"] = parameters.pop("topic")

    return {"name": tool_name, "parameters": parameters}


def parse_tool_calls(response: Optional[str], valid_tool_names: Iterable[str]) -> List[Dict[str, Any]]:
    """Parse zero-or-more tool calls out of an LLM response.

    Accepts a wide range of formats (see module docstring).
    Returns a list of normalized ``{"name": ..., "parameters": {...}}`` dicts.
    Empty list when no parseable tool call is present.
    """
    if response is None:
        return []

    tool_calls: List[Dict[str, Any]] = []
    whitelist = set(valid_tool_names)

    def add_if_valid(candidate: Any) -> None:
        if isinstance(candidate, list):
            for item in candidate:
                add_if_valid(item)
            return
        coerced = _coerce_to_valid_tool_call(candidate, whitelist) if isinstance(candidate, dict) else None
        if coerced is not None:
            tool_calls.append(coerced)

    # 1) Canonical <tool_call>{...}</tool_call>.
    for match in re.finditer(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", response, re.DOTALL):
        try:
            add_if_valid(json.loads(match.group(1)))
        except json.JSONDecodeError:
            pass
    if tool_calls:
        return tool_calls

    # 2) ```json fenced JSON (object or array) — common in Gemini / Claude.
    fence_pattern = r"```(?:json)?\s*([\[{].*?[\]}])\s*```"
    for match in re.finditer(fence_pattern, response, re.DOTALL | re.IGNORECASE):
        try:
            add_if_valid(json.loads(match.group(1)))
        except json.JSONDecodeError:
            pass
    if tool_calls:
        return tool_calls

    # 3) <tool_code>print(tool.search|query(kw=...))</tool_code> — Gemini variant.
    #    We parse the kwargs shape — never execute the code.
    tool_code_pattern = r"<tool_code>\s*print\(\s*(\w+)\.(?:search|query)\((.*?)\)\s*\)\s*</tool_code>"
    for match in re.finditer(tool_code_pattern, response, re.DOTALL):
        tool_name = match.group(1)
        args_text = match.group(2)
        if tool_name not in whitelist:
            continue
        # Very small kwargs parser — handles k="v" with double-quoted strings.
        params: Dict[str, Any] = {}
        for kw_match in re.finditer(r'(\w+)\s*=\s*"((?:[^"\\]|\\.)*)"', args_text):
            key = kw_match.group(1)
            value = bytes(kw_match.group(2), "utf-8").decode("unicode_escape")
            params[key] = value
        if "topic" in params and "query" not in params:
            params["query"] = params.pop("topic")
        tool_calls.append({"name": tool_name, "parameters": params})
    if tool_calls:
        return tool_calls

    # 4) Bare ``Action: {...}`` style.
    for match in re.finditer(r"Action\s*:\s*(\{.*?\})", response, re.DOTALL):
        try:
            add_if_valid(json.loads(match.group(1)))
        except json.JSONDecodeError:
            pass

    return tool_calls


# ─────────────────────────────────────────────────────────────────────────────
# 2. Fail-closed section validator
# ─────────────────────────────────────────────────────────────────────────────


_INVALID_MARKERS = (
    "i cannot actually call the tools",
    "cannot actually call tools",
    "exceeding the tool call limit",
    "exceeded the tool call limit",
    "no source_id",
    "unable to provide concrete simulation data",
    "无法提供具体的模拟数据引用",
    "由于未能成功调用工具",
    "由于已达到工具调用限制",
    "假设了模拟中可能出现",
)

_REASONING_LEAK_MARKERS = (
    "the `interview_agents` tool failed",
    "the interview_agents tool failed",
    "tool failed because",
    "the previous tool call",
    "the simulation environment was not running",
    "i need to pivot",
    "i need to adapt my strategy",
    "my plan is now to",
    "let's start by",
    "let me start by",
    "i will start with",
    "i'll start with",
    "my next step should be",
    "since the `interview_agents`",
    "采访失败：模拟环境未运行",
    "我需要调整策略",
)

_ARGENTINA_FOREIGN_CASE_MARKERS = ("甲醛", "宿舍", "学生", "学校", "微信群", "微博")


def validate_section_content(
    content: str,
    *,
    tool_calls_count: int,
    forced: bool,
    locale: str,
    simulation_requirement: str,
    cjk_threshold: float = 0.30,
) -> None:
    """Raise ``ValueError`` if a section is unfit to be published.

    Fail-closed rules:
    - No real tool calls were made.
    - Forced final emission without any tool calls.
    - Self-reported tool failure markers in the body.
    - Leaked ReACT reasoning / pivot narration.
    - Leaked raw tool markup (``<tool_call>`` / ``<tool_code>``).
    - Leading ``Thought\\n`` scaffolding block.
    - Foreign-case markers (formaldehyde / Weibo / etc.) when the simulation
      requirement is the Argentina pilot family of benchmarks.
    - Locale mismatch: >``cjk_threshold`` Chinese characters when locale ≠ zh.
    """
    text = "" if content is None else str(content)
    lowered = text.lower()

    if tool_calls_count <= 0:
        raise ValueError("invalid report section: no real tool calls")
    if forced and tool_calls_count <= 0:
        raise ValueError("invalid report section: forced generation without real tool calls")
    if any(marker in lowered for marker in _INVALID_MARKERS):
        raise ValueError("invalid self-reported tool failure in report section")
    if any(marker in lowered for marker in _REASONING_LEAK_MARKERS):
        raise ValueError("invalid agent reasoning/error leaked into report section")
    if re.search(r"(?:^|\n)\s*Thought\s*\n", text):
        raise ValueError("invalid ReACT scaffolding leaked into report section")
    if re.search(r"<tool_code>|<tool_call>", text):
        raise ValueError("invalid raw tool-call markup leaked into report section")

    argentina_context = re.search(
        r"argentina|argentino|milei|lla|pilot-arg",
        simulation_requirement,
        re.IGNORECASE,
    )
    if argentina_context and any(m in text for m in _ARGENTINA_FOREIGN_CASE_MARKERS):
        raise ValueError("invalid foreign-case marker in report section")

    if locale != "zh":
        non_ws = [c for c in text if not c.isspace()]
        if non_ws:
            cjk_count = sum(1 for c in non_ws if "\u4e00" <= c <= "\u9fff")
            cjk_ratio = cjk_count / len(non_ws)
            if cjk_ratio > cjk_threshold:
                raise ValueError(
                    f"invalid language in report section: locale={locale} "
                    f"but section is {cjk_ratio:.0%} Chinese"
                )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Final-answer scrubber
# ─────────────────────────────────────────────────────────────────────────────


def clean_final_answer(text: str) -> str:
    """Strip leading ``Thought\\n...`` blocks and tool-markup payloads.

    Some models (notably Gemini, smaller Qwen variants) prepend a ``Thought``
    block or include ``<tool_code>``/``<tool_call>`` snippets before the actual
    final answer. We drop everything before the LAST tool-markup closing tag
    and remove a leading ``Thought\\n...\\n\\n`` block. The validator still runs
    after this as a hard safety net.
    """
    cleaned = text.strip()
    for closer in ("</tool_code>", "</tool_call>"):
        idx = cleaned.rfind(closer)
        if idx != -1:
            cleaned = cleaned[idx + len(closer):].strip()
    match = re.match(r"^Thought\s*\n.*?\n\s*\n", cleaned, re.DOTALL)
    if match:
        cleaned = cleaned[match.end():].strip()
    return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# 4. interview_agents OASIS-down detector
# ─────────────────────────────────────────────────────────────────────────────


def is_interview_agents_unavailable(result_text: str) -> bool:
    """True when the interview_agents body indicates OASIS is offline.

    Used by the report agent to transparently fall back to ``insight_forge``
    with the same topic instead of surfacing the error to the LLM (which would
    otherwise leak the failure narration into the report body).
    """
    if not result_text:
        return False
    return any(marker in result_text for marker in _INTERVIEW_FAILURE_MARKERS)


def is_tool_result_failure(result_text: Any) -> bool:
    """Return True when a tool response contains no usable grounding evidence."""
    text = "" if result_text is None else str(result_text).strip()
    if not text:
        return True
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "工具执行失败",
            "未知工具",
            "tool execution failed",
            "unknown tool",
            "采访api调用失败",
            "采访失败：",
            "采访过程发生错误",
            "未找到可采访的agent人设文件",
            "（无采访记录）",
            "interview failed",
            "no interview records",
        )
    )
