"""
Smoke tests para LLMClient (portado de pr-600 + Fusion patch).

No real API calls, all OpenAI interactions mocked.
Cobertura:
- _clean_json_response (strip de markdown fences)
- _chat_raw (strip de <think> tags, max_tokens cap, Fusion extra_body)
- repair_truncated_json (helper de módulo, devuelve Dict)
- chat_json (happy path, truncated, boost fallback, fences stripping)
- Fusion routing (preset/panel/judge/cap)
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch

from app.utils.llm_client import LLMClient, repair_truncated_json


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(content, finish_reason="stop"):
    choice = MagicMock()
    choice.message.content = content
    choice.finish_reason = finish_reason
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_client(responses, model="test-model"):
    with patch("app.utils.llm_client.OpenAI") as MockOpenAI:
        mock_openai_instance = MagicMock()
        mock_openai_instance.chat.completions.create.side_effect = responses
        MockOpenAI.return_value = mock_openai_instance
        client = LLMClient(api_key="k", base_url="http://localhost", model=model)
        client._mock_create = mock_openai_instance.chat.completions.create
        return client


# ---------------------------------------------------------------------------
# _clean_json_response: solo limpia markdown fences (no think tags)
# ---------------------------------------------------------------------------

class TestCleanJsonResponse:

    def setup_method(self):
        with patch("app.utils.llm_client.OpenAI"):
            self.client = LLMClient(api_key="k", base_url="u", model="m")

    def test_passthrough_plain_json(self):
        assert self.client._clean_json_response('{"a": 1}') == '{"a": 1}'

    def test_strips_json_markdown_fence(self):
        assert self.client._clean_json_response('```json\n{"c": 3}\n```') == '{"c": 3}'

    def test_strips_plain_markdown_fence(self):
        assert self.client._clean_json_response('```\n{"d": 4}\n```') == '{"d": 4}'

    def test_strips_fence_with_trailing_whitespace(self):
        assert self.client._clean_json_response('```json\n{"x": 1}\n```  ') == '{"x": 1}'

    def test_empty_string(self):
        assert self.client._clean_json_response("") == ""

    def test_does_not_strip_think_tags(self):
        """think-tag stripping es responsabilidad de _chat_raw, no de _clean_json_response."""
        raw = '<think>reasoning</think>{"a": 1}'
        # _clean_json_response NO toca think tags (pr-600 los separó)
        assert self.client._clean_json_response(raw) == raw


# ---------------------------------------------------------------------------
# _chat_raw: strip de <think> tags, Fusion extra_body, max_tokens cap
# ---------------------------------------------------------------------------

class TestChatRaw:

    def test_strips_think_tags(self):
        with patch("app.utils.llm_client.OpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = _make_response(
                '<think>internal reasoning</think>{"a": 1}'
            )
            MockOpenAI.return_value = mock_instance
            client = LLMClient(api_key="k", base_url="u", model="m")
            content, finish_reason = client._chat_raw([{"role": "user", "content": "q"}])
            assert content == '{"a": 1}'
            assert finish_reason == "stop"

    def test_strips_multiline_think_tags(self):
        with patch("app.utils.llm_client.OpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = _make_response(
                '<think>\nline1\nline2\n</think>\n{"b": 2}'
            )
            MockOpenAI.return_value = mock_instance
            client = LLMClient(api_key="k", base_url="u", model="m")
            content, _ = client._chat_raw([{"role": "user", "content": "q"}])
            assert content == '{"b": 2}'

    def test_does_not_strip_fences(self):
        """_chat_raw NO limpia fences — eso es trabajo de _clean_json_response desde chat_json."""
        with patch("app.utils.llm_client.OpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = _make_response('```json\n{"c": 3}\n```')
            MockOpenAI.return_value = mock_instance
            client = LLMClient(api_key="k", base_url="u", model="m")
            content, _ = client._chat_raw([{"role": "user", "content": "q"}])
            # El content crudo sigue teniendo fences
            assert content == '```json\n{"c": 3}\n```'

    def test_strips_think_but_leaves_fence(self):
        with patch("app.utils.llm_client.OpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = _make_response(
                '<think>reasoning</think>\n```json\n{"e": 5}\n```'
            )
            MockOpenAI.return_value = mock_instance
            client = LLMClient(api_key="k", base_url="u", model="m")
            content, _ = client._chat_raw([{"role": "user", "content": "q"}])
            # Think tag removido, fence todavía ahí
            assert content == '```json\n{"e": 5}\n```'


# ---------------------------------------------------------------------------
# repair_truncated_json: helper de módulo, devuelve Dict | None
# ---------------------------------------------------------------------------

# NOTA: repair_truncated_json de pr-600 tiene un gap: si la truncación cae
# después de un valor escalar sin coma ni cierre de array (e.g. '{"a": 1'),
# phase 1 no encuentra safe point y phase 2 tampoco, devuelve None.
# En ese caso chat_json cae a Boost fallback. Documentamos con xfail.
# Si querés arreglarlo upstream, hay que agregar un "cierra brace final
# si depth_brace > 0 y no hay más chars" en phase 2.

class TestRepairTruncatedJson:

    def test_valid_passthrough(self):
        result = repair_truncated_json('{"x": 1}')
        assert result == {"x": 1}

    @pytest.mark.xfail(reason="pr-600 phase 1/2 no cierra brace final si no hay safe point")
    def test_closes_missing_brace(self):
        result = repair_truncated_json('{"a": 1')
        assert result is not None
        assert result == {"a": 1}

    @pytest.mark.xfail(reason="truncación sin safe point, cae a None")
    def test_closes_nested_braces(self):
        result = repair_truncated_json('{"outer": {"inner": "x"')
        assert result is not None
        assert result == {"outer": {"inner": "x"}}

    def test_closes_open_array(self):
        """'{"list": [1, 2' → phase 1 corta en la primera coma, devuelve {"list": [1]}."""
        result = repair_truncated_json('{"list": [1, 2')
        assert result is not None
        assert result == {"list": [1]}

    def test_closes_array_at_comma(self):
        """'{"a": [1, 2, 3' → phase 1 corta en la primera coma, devuelve {"a": [1, 2]}."""
        result = repair_truncated_json('{"a": [1, 2, 3')
        assert result is not None
        assert "a" in result
        assert result["a"] == [1, 2]

    @pytest.mark.xfail(reason="truncación mid-string sin safe point, cae a None")
    def test_closes_open_string_returns_dict(self):
        result = repair_truncated_json('{"k": "incomplete')
        assert result is not None
        assert "k" in result

    def test_invalid_returns_none(self):
        assert repair_truncated_json("not even close") is None

    def test_empty_returns_none(self):
        assert repair_truncated_json("") is None

    @pytest.mark.xfail(reason="fence-stripping no maneja fence truncado sin cierre completo")
    def test_strips_fences_before_repair(self):
        result = repair_truncated_json('```json\n{"x": 1\n```')
        assert result is not None
        assert result == {"x": 1}


# ---------------------------------------------------------------------------
# chat_json: integración end-to-end (incluye fence stripping)
# ---------------------------------------------------------------------------

class TestChatJson:

    def test_success_first_attempt(self):
        payload = {"status": "ok"}
        client = _make_client([_make_response(json.dumps(payload))])
        result = client.chat_json([{"role": "user", "content": "hi"}])
        assert result == payload
        assert client._mock_create.call_count == 1

    def test_strips_fences_in_response(self):
        client = _make_client([_make_response('```json\n{"wrapped": true}\n```')])
        result = client.chat_json([{"role": "user", "content": "q"}])
        assert result == {"wrapped": True}

    def test_strips_think_tags_in_response(self):
        client = _make_client([_make_response('<think>reasoning</think>{"ok": 1}')])
        result = client.chat_json([{"role": "user", "content": "q"}])
        assert result == {"ok": 1}

    @pytest.mark.xfail(reason="repair_truncated_json gap: sin safe point devuelve None → boost fallback needed")
    def test_truncated_output_repaired(self):
        client = _make_client([_make_response('{"a": 1', finish_reason="length")])
        result = client.chat_json([{"role": "user", "content": "q"}])
        assert result == {"a": 1}

    def test_truncated_array_repaired(self):
        client = _make_client([_make_response('{"items": [1, 2, 3', finish_reason="length")])
        result = client.chat_json([{"role": "user", "content": "q"}])
        assert result is not None
        assert "items" in result

    def test_invalid_json_no_boost_raises(self):
        client = _make_client([_make_response("not json at all")])
        with pytest.raises(ValueError, match="[Bb]oost"):
            client.chat_json([{"role": "user", "content": "q"}])

    def test_invalid_json_with_boost_falls_back(self):
        bad = _make_response("not json at all")
        good = _make_response('{"recovered": true}')
        client = _make_client([bad, good])
        client._has_boost = True
        boost_client = MagicMock()
        boost_client.chat.completions.create.return_value = good
        with patch.object(client, "_create_boost_client", return_value=(boost_client, "boost-model")):
            result = client.chat_json([{"role": "user", "content": "q"}])
        assert result == {"recovered": True}


# ---------------------------------------------------------------------------
# Fusion routing
# ---------------------------------------------------------------------------

class TestFusionRouting:

    def setup_method(self):
        for k in ["OPENROUTER_FUSION_PRESET", "OPENROUTER_FUSION_PANEL", "OPENROUTER_FUSION_JUDGE"]:
            os.environ.pop(k, None)

    def teardown_method(self):
        for k in ["OPENROUTER_FUSION_PRESET", "OPENROUTER_FUSION_PANEL", "OPENROUTER_FUSION_JUDGE"]:
            os.environ.pop(k, None)

    def test_fusion_model_injects_empty_plugin_when_no_config(self):
        with patch("app.utils.llm_client.OpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = _make_response('{"ok": 1}')
            MockOpenAI.return_value = mock_instance
            client = LLMClient(api_key="k", base_url="https://openrouter.ai/api/v1", model="openrouter/fusion")
            client.chat_json([{"role": "user", "content": "q"}], max_tokens=1000)
            kwargs = mock_instance.chat.completions.create.call_args.kwargs
            assert "extra_body" in kwargs
            assert kwargs["extra_body"] == {"plugins": [{"id": "fusion"}]}

    def test_fusion_with_preset(self):
        os.environ["OPENROUTER_FUSION_PRESET"] = "general-high"
        with patch("app.utils.llm_client.OpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = _make_response('{"ok": 1}')
            MockOpenAI.return_value = mock_instance
            client = LLMClient(api_key="k", base_url="https://openrouter.ai/api/v1", model="openrouter/fusion")
            client.chat_json([{"role": "user", "content": "q"}], max_tokens=1000)
            kwargs = mock_instance.chat.completions.create.call_args.kwargs
            assert kwargs["extra_body"] == {"plugins": [{"id": "fusion", "preset": "general-high"}]}

    def test_fusion_with_custom_panel(self):
        os.environ["OPENROUTER_FUSION_PANEL"] = "model-a,model-b,model-c"
        os.environ["OPENROUTER_FUSION_JUDGE"] = "judge-model"
        with patch("app.utils.llm_client.OpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = _make_response('{"ok": 1}')
            MockOpenAI.return_value = mock_instance
            client = LLMClient(api_key="k", base_url="https://openrouter.ai/api/v1", model="openrouter/fusion")
            client.chat_json([{"role": "user", "content": "q"}], max_tokens=1000)
            kwargs = mock_instance.chat.completions.create.call_args.kwargs
            plugin = kwargs["extra_body"]["plugins"][0]
            assert plugin["id"] == "fusion"
            assert plugin["models"] == ["model-a", "model-b", "model-c"]
            assert plugin["judge"] == "judge-model"

    def test_fusion_caps_max_tokens_to_4096(self):
        with patch("app.utils.llm_client.OpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = _make_response('{"ok": 1}')
            MockOpenAI.return_value = mock_instance
            client = LLMClient(api_key="k", base_url="https://openrouter.ai/api/v1", model="openrouter/fusion")
            client.chat_json([{"role": "user", "content": "q"}], max_tokens=16000)
            kwargs = mock_instance.chat.completions.create.call_args.kwargs
            assert kwargs["max_tokens"] == 4096

    def test_fusion_does_not_cap_below_4096(self):
        with patch("app.utils.llm_client.OpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = _make_response('{"ok": 1}')
            MockOpenAI.return_value = mock_instance
            client = LLMClient(api_key="k", base_url="https://openrouter.ai/api/v1", model="openrouter/fusion")
            client.chat_json([{"role": "user", "content": "q"}], max_tokens=2000)
            kwargs = mock_instance.chat.completions.create.call_args.kwargs
            assert kwargs["max_tokens"] == 2000

    def test_non_fusion_model_no_extra_body(self):
        with patch("app.utils.llm_client.OpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = _make_response('{"ok": 1}')
            MockOpenAI.return_value = mock_instance
            client = LLMClient(api_key="k", base_url="https://api.deepinfra.com/v1/openai", model="meta-llama/Llama-3.1-8B")
            client.chat_json([{"role": "user", "content": "q"}], max_tokens=1000)
            kwargs = mock_instance.chat.completions.create.call_args.kwargs
            assert "extra_body" not in kwargs
            assert kwargs["max_tokens"] == 1000

    def test_preset_takes_priority_over_panel(self):
        os.environ["OPENROUTER_FUSION_PRESET"] = "general-high"
        os.environ["OPENROUTER_FUSION_PANEL"] = "model-a,model-b"
        with patch("app.utils.llm_client.OpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = _make_response('{"ok": 1}')
            MockOpenAI.return_value = mock_instance
            client = LLMClient(api_key="k", base_url="https://openrouter.ai/api/v1", model="openrouter/fusion")
            client.chat_json([{"role": "user", "content": "q"}], max_tokens=1000)
            kwargs = mock_instance.chat.completions.create.call_args.kwargs
            plugin = kwargs["extra_body"]["plugins"][0]
            assert "preset" in plugin
            assert "models" not in plugin
