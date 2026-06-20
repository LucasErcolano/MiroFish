"""Per-call LLM telemetry for multi-model simulations (Issue #21).

The agents in a MiroFish simulation do NOT call ``LLMClient`` — they call the
CAMEL model backend created by ``ModelFactory.create`` and driven by OASIS. So
telemetry must wrap that backend, not ``LLMClient``.

:func:`instrument_backend` monkeypatches a CAMEL ``BaseModelBackend`` *instance*
(``run`` and ``arun``). This keeps ``isinstance(model, BaseModelBackend)`` true
(CAMEL's ChatAgent relies on it) and intercepts every call OASIS routes through
``ModelManager.current_model.run/arun``.

Each call appends one JSON line to ``<sim_dir>/llm_telemetry.jsonl`` with the
schema required by the issue plus cost/temperature/error fields.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import yaml


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _hash_messages(messages: Any) -> str:
    try:
        return _sha256(json.dumps(messages, sort_keys=True, default=str, ensure_ascii=False))
    except Exception:
        return _sha256(repr(messages))


# --------------------------------------------------------------------------- #
# Cost estimation
# --------------------------------------------------------------------------- #

def load_prices(path: Optional[str]) -> Dict[str, Dict[str, float]]:
    """Load the per-model price table (USD per 1k tokens). Empty if missing."""
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("prices", {}) or {}


def estimate_cost(
    model: str, tokens_in: int, tokens_out: int, prices: Dict[str, Dict[str, float]]
) -> Tuple[float, bool]:
    """Return (cost_usd, unknown_model). Unknown models cost 0.0 and flag True."""
    entry = prices.get(model)
    if entry is None:
        lowered = {k.lower(): v for k, v in prices.items()}
        entry = lowered.get(model.lower())
    if entry is None:
        for name, v in prices.items():
            if model.startswith(name) or name.startswith(model):
                entry = v
                break
    if entry is None:
        return 0.0, True
    cost = (tokens_in / 1000.0) * entry.get("in", 0.0) + (
        tokens_out / 1000.0
    ) * entry.get("out", 0.0)
    return round(cost, 8), False


# --------------------------------------------------------------------------- #
# Sink
# --------------------------------------------------------------------------- #

@dataclass
class TelemetrySink:
    """Collects per-call records into a JSONL file and aggregates totals.

    ``current_round`` is a mutable the simulation runner updates before each
    ``env.step``, so every record written during that step is stamped with the
    correct round (OASIS does not expose the round at the model-call layer).
    """

    path: str
    prices: Dict[str, Dict[str, float]] = field(default_factory=dict)
    current_round: int = 0

    # aggregates
    records: int = 0
    errors: int = 0
    parse_errors: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd_est: float = 0.0
    latency_ms_total: float = 0.0

    def __post_init__(self) -> None:
        self._lock = threading.Lock()
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        # truncate any stale file from a previous run
        open(self.path, "w", encoding="utf-8").close()

    def record(self, rec: Dict[str, Any]) -> None:
        with self._lock:
            self.records += 1
            self.tokens_in += rec.get("tokens_in", 0) or 0
            self.tokens_out += rec.get("tokens_out", 0) or 0
            self.cost_usd_est += rec.get("cost_usd_est", 0.0) or 0.0
            self.latency_ms_total += rec.get("latency_ms", 0.0) or 0.0
            if rec.get("error"):
                self.errors += 1
            if rec.get("output_valid_json") is False:
                self.parse_errors += 1
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def summary(self) -> Dict[str, Any]:
        latency_sec = round(self.latency_ms_total / 1000.0, 4)
        mean_latency = (
            round(self.latency_ms_total / self.records, 2) if self.records else 0.0
        )
        return {
            "llm_calls": self.records,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd_est": round(self.cost_usd_est, 8),
            "latency_sec": latency_sec,
            "mean_latency_ms": mean_latency,
            "errors": self.errors,
            "parse_errors": self.parse_errors,
        }


# --------------------------------------------------------------------------- #
# Response extraction
# --------------------------------------------------------------------------- #

def _extract_usage(response: Any) -> Tuple[int, int]:
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return 0, 0
    pt = getattr(usage, "prompt_tokens", None)
    ct = getattr(usage, "completion_tokens", None)
    if pt is None and isinstance(usage, dict):
        pt = usage.get("prompt_tokens")
        ct = usage.get("completion_tokens")
    return int(pt or 0), int(ct or 0)


def _extract_content(response: Any) -> Optional[str]:
    try:
        choices = getattr(response, "choices", None)
        if choices is None and isinstance(response, dict):
            choices = response.get("choices")
        if not choices:
            return None
        first = choices[0]
        message = getattr(first, "message", None)
        if message is None and isinstance(first, dict):
            message = first.get("message")
        content = getattr(message, "content", None)
        if content is None and isinstance(message, dict):
            content = message.get("content")
        return content
    except Exception:
        return None


def _is_valid_json(content: Optional[str]) -> Optional[bool]:
    """True/False if content parses as JSON; None if there is no content."""
    if content is None or content == "":
        return None
    try:
        json.loads(content)
        return True
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------- #
# Instrumentation
# --------------------------------------------------------------------------- #

def instrument_backend(
    backend: Any,
    *,
    context: Dict[str, Any],
    sink: TelemetrySink,
) -> Any:
    """Monkeypatch a CAMEL backend instance to record per-call telemetry.

    ``context`` must carry: agent_id, role, provider, model. Returns the same
    (now instrumented) backend so it can be passed straight to OASIS.
    """
    orig_run = backend.run
    orig_arun = backend.arun

    def _temperature() -> Optional[float]:
        cfg = getattr(backend, "model_config_dict", None)
        if isinstance(cfg, dict):
            return cfg.get("temperature")
        return None

    def _build_record(
        messages: Any, response: Any, latency_ms: float, error: Optional[str]
    ) -> Dict[str, Any]:
        tokens_in, tokens_out = (0, 0) if response is None else _extract_usage(response)
        content = None if response is None else _extract_content(response)
        cost, unknown = estimate_cost(
            context.get("model", ""), tokens_in, tokens_out, sink.prices
        )
        leak_flags: List[str] = []
        if unknown:
            leak_flags.append("cost_unknown_model")
        valid_json = _is_valid_json(content)
        return {
            "timestamp": datetime.now().isoformat(),
            "round": sink.current_round,
            "agent_id": context.get("agent_id"),
            "role": context.get("role"),
            "provider": context.get("provider"),
            "model": context.get("model"),
            "temperature": _temperature(),
            "prompt_hash": _hash_messages(messages),
            "response_hash": _sha256(content) if content else None,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": round(latency_ms, 2),
            "cost_usd_est": cost,
            "output_valid_json": valid_json,
            "error": error,
            "leak_flags": leak_flags,
        }

    def wrapped_run(messages, response_format=None, tools=None):
        t0 = time.perf_counter()
        try:
            response = orig_run(messages, response_format, tools)
        except Exception as exc:  # noqa: BLE001 - we re-raise after logging
            latency_ms = (time.perf_counter() - t0) * 1000.0
            sink.record(_build_record(messages, None, latency_ms, repr(exc)))
            raise
        latency_ms = (time.perf_counter() - t0) * 1000.0
        sink.record(_build_record(messages, response, latency_ms, None))
        return response

    async def wrapped_arun(messages, response_format=None, tools=None):
        t0 = time.perf_counter()
        try:
            response = await orig_arun(messages, response_format, tools)
        except Exception as exc:  # noqa: BLE001 - we re-raise after logging
            latency_ms = (time.perf_counter() - t0) * 1000.0
            sink.record(_build_record(messages, None, latency_ms, repr(exc)))
            raise
        latency_ms = (time.perf_counter() - t0) * 1000.0
        sink.record(_build_record(messages, response, latency_ms, None))
        return response

    backend.run = wrapped_run
    backend.arun = wrapped_arun
    return backend
