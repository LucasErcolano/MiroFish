"""
LLM客户端封装
Supports two backends:
  1. Prompture (optional) — 12+ providers: LM Studio, Ollama, Claude, Groq, Kimi, etc.
  2. OpenAI SDK (default fallback) — any OpenAI-compatible API
Install Prompture for multi-provider support: pip install prompture
"""

import json
import os
import re
from typing import Optional, Dict, Any, List

from ..config import Config

# Try to import Prompture; fall back to OpenAI SDK if not installed
try:
    from prompture.agents import Conversation
    from prompture.infra.provider_env import ProviderEnvironment
    from prompture.extraction.tools import strip_think_tags, clean_json_text
    _HAS_PROMPTURE = True
except ImportError:
    _HAS_PROMPTURE = False

if not _HAS_PROMPTURE:
    from openai import OpenAI


# Provider name → ProviderEnvironment field name
_KEY_MAP = {
    "openai": "openai_api_key",
    "claude": "claude_api_key",
    "google": "google_api_key",
    "groq": "groq_api_key",
    "grok": "grok_api_key",
    "openrouter": "openrouter_api_key",
    "moonshot": "moonshot_api_key",
}


class LLMClient:
    """LLM客户端

    When Prompture is installed, ``model`` accepts the ``"provider/model"``
    format for multi-provider support::

        "lmstudio/local-model"        → LM Studio (free, local)
        "ollama/llama3.1:8b"          → Ollama (free, local)
        "openai/gpt-4o"               → OpenAI
        "claude/claude-sonnet-4-20250514"     → Anthropic
        "moonshot/moonshot-v1-8k"     → Kimi / Moonshot
        "groq/llama-3.1-70b"          → Groq

    Without Prompture, the original OpenAI SDK backend is used (any
    OpenAI-compatible API via LLM_BASE_URL).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME

        if _HAS_PROMPTURE:
            self._init_prompture()
        else:
            self._init_openai()

    # ── Prompture backend ──────────────────────────────────────────

    def _init_prompture(self):
        env_kwargs: Dict[str, Any] = {}
        if self.api_key:
            provider = self.model.split("/")[0] if "/" in self.model else "openai"
            env_field = _KEY_MAP.get(provider)
            if env_field:
                env_kwargs[env_field] = self.api_key

        self._env = ProviderEnvironment(**env_kwargs) if env_kwargs else None
        self._driver_options: Dict[str, Any] = {}
        if self.base_url:
            self._driver_options["base_url"] = self.base_url

    def _make_conversation(self, temperature: float, max_tokens: int) -> "Conversation":
        opts: Dict[str, Any] = {
            "temperature": temperature,
            "max_tokens": max_tokens,
            **self._driver_options,
        }
        return Conversation(self.model, options=opts, env=self._env)

    # ── OpenAI fallback backend ────────────────────────────────────

    def _init_openai(self):
        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        # Some OpenAI-compatible providers (notably OpenRouter) reject or
        # 500 on requests with User-Agent starting with "OpenAI/Python",
        # which the openai SDK injects unconditionally. Adding an event_hook
        # to rewrite the header is the cleanest way to avoid that without
        # forking or downgrading the SDK.
        import httpx

        def _rewrite_ua(request: "httpx.Request") -> None:
            ua = request.headers.get("user-agent", "")
            if ua.startswith("OpenAI/Python"):
                request.headers["user-agent"] = "curl/7.88.1"

        http_client = httpx.Client(event_hooks={"request": [_rewrite_ua]})
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=http_client,
        )

    # ── Public API ─────────────────────────────────────────────────

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
    ) -> str:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）

        Returns:
            模型响应文本
        """
        if _HAS_PROMPTURE:
            content = self._chat_prompture(messages, temperature, max_tokens)
            return strip_think_tags(content)
        else:
            content = self._chat_openai(messages, temperature, max_tokens, response_format)
            # Fallback: strip think tags with regex when Prompture is not available
            return re.sub(r'<think>[\s\S]*?</think>', '', content).strip()

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        发送聊天请求并返回JSON

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            解析后的JSON对象
        """
        if _HAS_PROMPTURE:
            response = self._chat_prompture(messages, temperature, max_tokens)
            # Prompture's clean_json_text strips think tags + markdown fences
            cleaned = clean_json_text(response)
        else:
            response = self._chat_openai(
                messages, temperature, max_tokens
            )
            # Fallback cleaning when Prompture is not available
            cleaned = re.sub(r'<think>[\s\S]*?</think>', '', response).strip()
            cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\n?```\s*$', '', cleaned)
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise ValueError(f"LLM返回的JSON格式无效: {cleaned}")

    # ── Private: Prompture path ────────────────────────────────────

    def _chat_prompture(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        conv = self._make_conversation(temperature, max_tokens)

        # Inject system prompt
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        if system_parts:
            conv._messages.append({"role": "system", "content": "\n".join(system_parts)})

        # Replay prior turns
        non_system = [m for m in messages if m["role"] != "system"]
        for msg in non_system[:-1]:
            conv._messages.append({"role": msg["role"], "content": msg["content"]})

        prompt = non_system[-1]["content"] if non_system else ""
        return conv.ask(prompt)

    # ── Private: OpenAI fallback path ──────────────────────────────

    def _chat_openai(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict] = None,
    ) -> str:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        # OpenRouter Fusion requires a `plugins` array in the request body to
        # activate the multi-model deliberation. The OpenAI SDK does not
        # expose `plugins` as a first-class kwarg, so we use `extra_body` to
        # forward it.
        #
        # Two presets via the `preset` field:
        #   - "general-high" (Quality, default) — Opus + others, ~$0.008/call
        #   - "general-budget" (Budget) — cheaper models, but currently 500
        #
        # Custom panel via `analysis_models` (the models that deliberate) +
        # `model` (the judge that synthesizes). If the panel is empty or
        # `model` is missing, OpenRouter falls back to the Opus default,
        # which is expensive and defeats the purpose. So we always set
        # `model` to the cheapest judge we trust.
        #
        # Override via OPENROUTER_FUSION_PRESET (preset slug, e.g.
        # "general-high") and OPENROUTER_FUSION_PANEL (comma-separated
        # analysis_models) in the .env if needed. Default is a Budget-tier
        # panel + cheap judge for cost-conscious runs.
        if self.model.startswith("openrouter/fusion"):
            preset = os.environ.get("OPENROUTER_FUSION_PRESET")
            panel_str = os.environ.get("OPENROUTER_FUSION_PANEL", "")
            plugin: Dict[str, Any] = {"id": "fusion"}
            if preset:
                plugin["preset"] = preset
            if panel_str:
                panel = [m.strip() for m in panel_str.split(",") if m.strip()]
                if panel:
                    plugin["analysis_models"] = panel
                    # When using a custom panel, the judge must be explicit,
                    # otherwise OpenRouter falls back to Opus and 500s.
                    plugin["model"] = os.environ.get(
                        "OPENROUTER_FUSION_JUDGE", "openai/gpt-4o-mini"
                    )
            kwargs["extra_body"] = {"plugins": [plugin]}
            # Cap max_tokens to keep the multi-model call within budget.
            # Without this, Graphiti's 16K default for the judge request
            # alone exceeds typical top-up balances. The judge only needs
            # room for a structured JSON answer; 4K is plenty.
            if kwargs.get("max_tokens", 0) > 4096:
                kwargs["max_tokens"] = 4096

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
