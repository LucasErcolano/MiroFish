"""
Memory Mode Management (Spike S2)

Provides:
- MemoryMode enum (baseline | experimental)
- Config resolution: MEMORY_MODE env var or YAML, with backward compat for USE_EXPERIMENTAL_MEMORY
- MemoryMetrics: per-agent/per-round usage tracking
- MemoryRetrievalLog: structured log entries for memory retrieval events
- Logging helpers for mode switches and retrieval
"""

import os
import time
import json
import logging
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from collections import defaultdict
from threading import Lock

logger = logging.getLogger('mirofish.memory_mode')


class MemoryMode(Enum):
    """Supported memory modes."""
    BASELINE = "baseline"
    EXPERIMENTAL = "experimental"

    @classmethod
    def from_string(cls, value: str) -> "MemoryMode":
        """Parse a string into a MemoryMode, raising ValueError on unknown values."""
        normalized = value.strip().lower()
        if normalized == "baseline":
            return cls.BASELINE
        elif normalized == "experimental":
            return cls.EXPERIMENTAL
        else:
            raise ValueError(
                f"Invalid MEMORY_MODE '{value}'. Must be 'baseline' or 'experimental'."
            )

    def is_experimental(self) -> bool:
        return self == MemoryMode.EXPERIMENTAL

    def is_baseline(self) -> bool:
        return self == MemoryMode.BASELINE


@dataclass
class MemoryRetrievalLog:
    """Single structured log entry for a memory retrieval event."""
    timestamp: float
    mode: str                    # "baseline" or "experimental"
    agent_name: Optional[str]    # requesting agent, if available
    round_num: Optional[int]     # simulation round, if available
    query: str                   # the retrieval query
    results_count: int           # number of items returned
    provider_class: str          # class name of the provider that handled it
    latency_ms: float            # retrieval latency in milliseconds
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MemoryMetrics:
    """
    Thread-safe metrics collector for memory usage, tracked per agent and per round.

    Usage:
        metrics = MemoryMetrics()
        metrics.record_retrieval(
            agent_name="agent_0",
            round_num=3,
            mode=MemoryMode.EXPERIMENTAL,
            results_count=5,
            latency_ms=120.3,
            provider_class="ExperimentalMemoryService",
        )
        summary = metrics.get_summary()
    """

    def __init__(self):
        self._lock = Lock()
        # Per-agent counters
        self._agent_retrievals: Dict[str, int] = defaultdict(int)
        self._agent_results: Dict[str, int] = defaultdict(int)
        self._agent_latency_ms: Dict[str, List[float]] = defaultdict(list)
        # Per-round counters
        self._round_retrievals: Dict[int, int] = defaultdict(int)
        self._round_results: Dict[int, int] = defaultdict(int)
        # Global counters
        self._total_retrievals: int = 0
        self._total_results: int = 0
        self._total_latency_ms: float = 0.0
        # Mode counters
        self._mode_retrievals: Dict[str, int] = defaultdict(int)
        # Retrieval log (bounded to last N entries)
        self._retrieval_log: List[MemoryRetrievalLog] = []
        self._max_log_entries = 1000

    def record_retrieval(
        self,
        agent_name: Optional[str],
        round_num: Optional[int],
        mode: MemoryMode,
        results_count: int,
        latency_ms: float,
        provider_class: str,
        query: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ):
        """Record a single retrieval event."""
        with self._lock:
            key = agent_name or "__unknown__"
            self._agent_retrievals[key] += 1
            self._agent_results[key] += results_count
            self._agent_latency_ms[key].append(latency_ms)

            rkey = round_num if round_num is not None else -1
            self._round_retrievals[rkey] += 1
            self._round_results[rkey] += results_count

            self._total_retrievals += 1
            self._total_results += results_count
            self._total_latency_ms += latency_ms

            self._mode_retrievals[mode.value] += 1

            log_entry = MemoryRetrievalLog(
                timestamp=time.time(),
                mode=mode.value,
                agent_name=agent_name,
                round_num=round_num,
                query=query,
                results_count=results_count,
                provider_class=provider_class,
                latency_ms=latency_ms,
                extra=extra or {},
            )
            self._retrieval_log.append(log_entry)
            if len(self._retrieval_log) > self._max_log_entries:
                self._retrieval_log = self._retrieval_log[-self._max_log_entries:]

        logger.info(
            "memory_retrieval: mode=%s agent=%s round=%s results=%d latency=%.1fms provider=%s query='%.80s'",
            mode.value, agent_name, round_num, results_count, latency_ms,
            provider_class, query,
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all recorded metrics."""
        with self._lock:
            agent_summary = {}
            for agent, count in self._agent_retrievals.items():
                latencies = self._agent_latency_ms.get(agent, [])
                agent_summary[agent] = {
                    "retrievals": count,
                    "total_results": self._agent_results.get(agent, 0),
                    "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
                }

            round_summary = {}
            for rnd, count in self._round_retrievals.items():
                round_summary[str(rnd)] = {
                    "retrievals": count,
                    "total_results": self._round_results.get(rnd, 0),
                }

            return {
                "total_retrievals": self._total_retrievals,
                "total_results": self._total_results,
                "avg_latency_ms": round(
                    self._total_latency_ms / max(self._total_retrievals, 1), 2
                ),
                "mode_breakdown": dict(self._mode_retrievals),
                "per_agent": agent_summary,
                "per_round": round_summary,
                "log_entries": len(self._retrieval_log),
            }

    def get_recent_log(self, n: int = 50) -> List[Dict[str, Any]]:
        """Get the N most recent retrieval log entries."""
        with self._lock:
            return [entry.to_dict() for entry in self._retrieval_log[-n:]]

    def reset(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._agent_retrievals.clear()
            self._agent_results.clear()
            self._agent_latency_ms.clear()
            self._round_retrievals.clear()
            self._round_results.clear()
            self._total_retrievals = 0
            self._total_results = 0
            self._total_latency_ms = 0.0
            self._mode_retrievals.clear()
            self._retrieval_log.clear()


# Module-level singleton
_metrics: Optional[MemoryMetrics] = None


def get_metrics() -> MemoryMetrics:
    """Get the global MemoryMetrics instance (lazy singleton)."""
    global _metrics
    if _metrics is None:
        _metrics = MemoryMetrics()
    return _metrics


def resolve_memory_mode() -> MemoryMode:
    """
    Resolve the active memory mode from configuration.

    Priority:
    1. MEMORY_MODE env var (explicit setting)
    2. USE_EXPERIMENTAL_MEMORY env var (backward compat: 'true' -> experimental)
    3. Default: baseline
    """
    # Explicit MEMORY_MODE takes precedence
    memory_mode_str = os.environ.get("MEMORY_MODE", "").strip()
    if memory_mode_str:
        mode = MemoryMode.from_string(memory_mode_str)
        logger.info("memory_mode resolved from MEMORY_MODE env: %s", mode.value)
        return mode

    # Backward compat: USE_EXPERIMENTAL_MEMORY=true -> experimental
    use_exp = os.environ.get("USE_EXPERIMENTAL_MEMORY", "").strip().lower()
    if use_exp == "true":
        logger.info("memory_mode resolved from USE_EXPERIMENTAL_MEMORY=true (backward compat): experimental")
        return MemoryMode.EXPERIMENTAL

    logger.info("memory_mode resolved to default: baseline")
    return MemoryMode.BASELINE


def resolve_memory_mode_from_config(config) -> MemoryMode:
    """
    Resolve memory mode from a Config object.

    Checks config.MEMORY_MODE first, then falls back to
    config.USE_EXPERIMENTAL_MEMORY for backward compatibility.
    """
    # Explicit MEMORY_MODE in config
    if hasattr(config, 'MEMORY_MODE') and config.MEMORY_MODE:
        mode = MemoryMode.from_string(config.MEMORY_MODE)
        logger.info("memory_mode resolved from Config.MEMORY_MODE: %s", mode.value)
        return mode

    # Backward compat
    if hasattr(config, 'USE_EXPERIMENTAL_MEMORY') and config.USE_EXPERIMENTAL_MEMORY:
        logger.info("memory_mode resolved from Config.USE_EXPERIMENTAL_MEMORY (backward compat): experimental")
        return MemoryMode.EXPERIMENTAL

    logger.info("memory_mode resolved to default: baseline")
    return MemoryMode.BASELINE


def log_mode_switch(old_mode: MemoryMode, new_mode: MemoryMode, source: str = ""):
    """Log a memory mode switch event."""
    logger.warning(
        "memory_mode_switch: %s -> %s (source=%s)",
        old_mode.value, new_mode.value, source,
    )