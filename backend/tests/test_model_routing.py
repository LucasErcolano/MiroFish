"""Tests for multi-model routing + telemetry (Issue #21).

Pure-logic tests: no real LLM endpoints and no `camel` import. The routing
resolution/validation and the telemetry wrapper are exercised with fakes, so
this suite runs in CI without the simulation stack.
"""

import asyncio
import json
import os
import sys
from types import SimpleNamespace

import pytest

# Make `app` importable regardless of pytest rootdir.
_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.services.model_router import (  # noqa: E402
    ModelRouter,
    ModelRoutingError,
    policy_config_dict,
    validate_model_map,
)
from app.services.llm_telemetry import (  # noqa: E402
    TelemetrySink,
    estimate_cost,
    instrument_backend,
    load_prices,
)


def _base_map():
    return {
        "version": 1,
        "default": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key_env": "LLM_API_KEY",
            "temperature": 0.7,
            "seed": None,
        },
        "fallback": {"enabled": False},
        "by_role": {
            "FinancialInstitution": {"provider": "vllm", "model": "qwen-local", "temperature": 0.3}
        },
        "by_agent_id": {
            0: {"provider": "vllm", "model": "mistral-local", "temperature": 0.5, "seed": 42}
        },
    }


# --------------------------------------------------------------------------- #
# Resolution precedence
# --------------------------------------------------------------------------- #

def test_resolve_precedence_agent_over_role_over_default():
    router = ModelRouter(_base_map())

    # agent_id 0 has an explicit entry -> wins even though its role also matches
    p0 = router.resolve(0, role="FinancialInstitution")
    assert p0.model == "mistral-local"
    assert p0.source == "by_agent_id"
    assert p0.seed == 42
    assert p0.temperature == 0.5

    # agent_id 1 matches by_role only
    p1 = router.resolve(1, role="FinancialInstitution")
    assert p1.model == "qwen-local"
    assert p1.source == "by_role"
    assert p1.temperature == 0.3

    # agent_id 2 with no matching layer -> default
    p2 = router.resolve(2, role="Person")
    assert p2.model == "gpt-4o-mini"
    assert p2.source == "default"


def test_resolve_base_url_from_env(monkeypatch):
    m = _base_map()
    m["default"]["base_url_env"] = "MY_BASE_URL"
    monkeypatch.setenv("MY_BASE_URL", "http://example.test/v1")
    router = ModelRouter(m)
    assert router.resolve(5).base_url == "http://example.test/v1"


def test_literal_base_url_wins_over_env(monkeypatch):
    m = _base_map()
    m["default"]["base_url"] = "http://literal/v1"
    m["default"]["base_url_env"] = "MY_BASE_URL"
    monkeypatch.setenv("MY_BASE_URL", "http://fromenv/v1")
    assert ModelRouter(m).resolve(5).base_url == "http://literal/v1"


# --------------------------------------------------------------------------- #
# Fallback
# --------------------------------------------------------------------------- #

def test_fallback_disabled_by_default():
    m = _base_map()
    del m["fallback"]
    assert ModelRouter(m).fallback_enabled is False


def test_fallback_enabled_flag():
    m = _base_map()
    m["fallback"]["enabled"] = True
    assert ModelRouter(m).fallback_enabled is True


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

def test_validate_rejects_literal_api_key():
    m = _base_map()
    m["default"]["api_key"] = "sk-secret"
    with pytest.raises(ModelRoutingError, match="api_key"):
        validate_model_map(m)


def test_validate_rejects_bad_version():
    m = _base_map()
    m["version"] = 2
    with pytest.raises(ModelRoutingError, match="version"):
        validate_model_map(m)


def test_validate_rejects_unknown_field():
    m = _base_map()
    m["default"]["typo_field"] = "x"
    with pytest.raises(ModelRoutingError, match="unknown field"):
        validate_model_map(m)


def test_validate_rejects_non_int_seed():
    m = _base_map()
    m["default"]["seed"] = "not-an-int"
    with pytest.raises(ModelRoutingError, match="seed"):
        validate_model_map(m)


def test_validate_rejects_non_int_agent_id():
    m = _base_map()
    m["by_agent_id"] = {"zero": {"model": "x"}}
    with pytest.raises(ModelRoutingError, match="integers"):
        validate_model_map(m)


def test_validate_rejects_unknown_provider():
    m = _base_map()
    m["default"]["provider"] = "mystery"
    with pytest.raises(ModelRoutingError, match="provider"):
        validate_model_map(m)


def test_validate_accepts_s2_hosted_providers():
    m = _base_map()
    m["default"].update({
        "provider": "openrouter",
        "model": "qwen/qwen3-8b",
        "base_url_env": "OPENROUTER_BASE_URL",
        "api_key_env": "OPENROUTER_API_KEY",
    })
    m["by_agent_id"] = {
        1: {
            "provider": "deepinfra",
            "model": "google/gemma-3-27b-it",
            "base_url_env": "DEEPINFRA_BASE_URL",
            "api_key_env": "DEEPINFRA_API_KEY",
        }
    }

    validate_model_map(m)


# --------------------------------------------------------------------------- #
# Temperature / seed propagation
# --------------------------------------------------------------------------- #

def test_policy_config_dict_includes_temperature_and_seed():
    router = ModelRouter(_base_map())
    cfg = policy_config_dict(router.resolve(0))
    assert cfg == {"temperature": 0.5, "seed": 42}


def test_policy_config_dict_omits_null_seed():
    router = ModelRouter(_base_map())
    cfg = policy_config_dict(router.resolve(9))  # default: seed=None
    assert cfg == {"temperature": 0.7}
    assert "seed" not in cfg


# --------------------------------------------------------------------------- #
# Cost estimation
# --------------------------------------------------------------------------- #

def test_estimate_cost_known_model():
    prices = {"gpt-4o-mini": {"in": 0.00015, "out": 0.0006}}
    cost, unknown = estimate_cost("gpt-4o-mini", 1000, 1000, prices)
    assert unknown is False
    assert cost == pytest.approx(0.00075)


def test_estimate_cost_unknown_model_flagged():
    cost, unknown = estimate_cost("who-knows", 1000, 1000, {})
    assert cost == 0.0
    assert unknown is True


# --------------------------------------------------------------------------- #
# Telemetry wrapper
# --------------------------------------------------------------------------- #

def _fake_response(content, prompt_tokens=10, completion_tokens=20):
    usage = SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(usage=usage, choices=[choice])


class _FakeBackend:
    """Minimal stand-in for a CAMEL BaseModelBackend instance."""

    def __init__(self, response):
        self._response = response
        self.model_config_dict = {"temperature": 0.5}

    def run(self, messages, response_format=None, tools=None):
        return self._response

    async def arun(self, messages, response_format=None, tools=None):
        return self._response


def _make_sink(tmp_path):
    return TelemetrySink(
        path=str(tmp_path / "llm_telemetry.jsonl"),
        prices={"gpt-4o-mini": {"in": 0.00015, "out": 0.0006}},
    )


def _read_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_telemetry_run_captures_tokens_latency_hashes_cost(tmp_path):
    sink = _make_sink(tmp_path)
    sink.current_round = 3
    backend = _FakeBackend(_fake_response('{"action": "post"}'))
    instrument_backend(
        backend,
        context={"agent_id": 7, "role": "Person", "provider": "openai", "model": "gpt-4o-mini"},
        sink=sink,
    )

    backend.run([{"role": "user", "content": "hello"}])

    rows = _read_lines(sink.path)
    assert len(rows) == 1
    rec = rows[0]
    assert rec["agent_id"] == 7
    assert rec["round"] == 3
    assert rec["model"] == "gpt-4o-mini"
    assert rec["tokens_in"] == 10
    assert rec["tokens_out"] == 20
    assert rec["temperature"] == 0.5
    assert rec["prompt_hash"] and rec["response_hash"]
    assert rec["latency_ms"] >= 0
    assert rec["cost_usd_est"] == pytest.approx((10 / 1000) * 0.00015 + (20 / 1000) * 0.0006)
    assert rec["output_valid_json"] is True
    assert rec["error"] is None
    # aggregates
    assert sink.summary()["tokens_in"] == 10
    assert sink.summary()["llm_calls"] == 1


def test_telemetry_arun_captures(tmp_path):
    sink = _make_sink(tmp_path)
    backend = _FakeBackend(_fake_response('{"ok": true}'))
    instrument_backend(
        backend,
        context={"agent_id": 1, "role": None, "provider": "openai", "model": "gpt-4o-mini"},
        sink=sink,
    )

    asyncio.run(backend.arun([{"role": "user", "content": "hi"}]))

    rows = _read_lines(sink.path)
    assert len(rows) == 1
    assert rows[0]["tokens_out"] == 20


def test_telemetry_counts_parse_errors_on_non_json(tmp_path):
    sink = _make_sink(tmp_path)
    backend = _FakeBackend(_fake_response("this is not json"))
    instrument_backend(
        backend,
        context={"agent_id": 0, "role": None, "provider": "openai", "model": "gpt-4o-mini"},
        sink=sink,
    )

    backend.run([{"role": "user", "content": "x"}])

    rec = _read_lines(sink.path)[0]
    assert rec["output_valid_json"] is False
    assert sink.parse_errors == 1


def test_telemetry_records_and_reraises_on_error(tmp_path):
    sink = _make_sink(tmp_path)

    class _Boom(_FakeBackend):
        def run(self, messages, response_format=None, tools=None):
            raise RuntimeError("upstream 500")

    backend = _Boom(None)
    instrument_backend(
        backend,
        context={"agent_id": 2, "role": None, "provider": "openai", "model": "gpt-4o-mini"},
        sink=sink,
    )

    with pytest.raises(RuntimeError, match="upstream 500"):
        backend.run([{"role": "user", "content": "x"}])

    rec = _read_lines(sink.path)[0]
    assert rec["error"] is not None
    assert rec["tokens_in"] == 0
    assert sink.errors == 1


def test_telemetry_unknown_model_sets_leak_flag(tmp_path):
    sink = TelemetrySink(path=str(tmp_path / "t.jsonl"), prices={})
    backend = _FakeBackend(_fake_response('{"a": 1}'))
    instrument_backend(
        backend,
        context={"agent_id": 0, "role": None, "provider": "openai", "model": "mystery-model"},
        sink=sink,
    )
    backend.run([{"role": "user", "content": "x"}])
    rec = _read_lines(sink.path)[0]
    assert "cost_unknown_model" in rec["leak_flags"]
    assert rec["cost_usd_est"] == 0.0


def test_load_prices_missing_file_returns_empty():
    assert load_prices("/nonexistent/prices.yaml") == {}
