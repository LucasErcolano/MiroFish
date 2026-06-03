"""
LLM客户端封装
Supports two backends:
  1. Prompture (optional) — 12+ providers: LM Studio, Ollama, Claude, Groq, Kimi, etc.
  2. OpenAI SDK (default fallback) — any OpenAI-compatible API
Install Prompture for multi-provider support: pip install prompture
"""

import json
import re
import threading
import time
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

    _request_lock = threading.Lock()
    _last_request_at = 0.0

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
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=Config.LLM_REQUEST_TIMEOUT_SECONDS,
        )

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
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=Config.LLM_REQUEST_TIMEOUT_SECONDS,
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
        content = self._request_text(messages, temperature, max_tokens, response_format)
        if _HAS_PROMPTURE:
            return strip_think_tags(content)
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
        response_format = {"type": "json_object"}
        response = self._request_text(messages, temperature, max_tokens, response_format)
        cleaned = self._clean_json_response(response)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as first_error:
            retry_messages = [
                *messages,
                {
                    "role": "user",
                    "content": (
                        "Your previous response was not complete valid JSON. "
                        "Return the same answer again as one complete JSON object only, "
                        "with no markdown fences and no extra text."
                    ),
                },
            ]
            retry_response = self._request_text(
                retry_messages,
                0,
                max(max_tokens * 2, 8192),
                response_format,
            )
            retry_cleaned = self._clean_json_response(retry_response)

            try:
                return json.loads(retry_cleaned)
            except json.JSONDecodeError:
                raise ValueError(f"LLM返回的JSON格式无效: {cleaned}") from first_error

    @staticmethod
    def _clean_json_response(response: str) -> str:
        if _HAS_PROMPTURE:
            # Prompture's clean_json_text strips think tags + markdown fences
            return clean_json_text(response)

        # Fallback cleaning when Prompture is not available
        cleaned = re.sub(r'<think>[\s\S]*?</think>', '', response).strip()
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        return cleaned.strip()

    def _request_text(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict] = None,
    ) -> str:
        def operation():
            if response_format:
                return self._chat_openai(messages, temperature, max_tokens, response_format)
            if _HAS_PROMPTURE:
                return self._chat_prompture(messages, temperature, max_tokens)
            return self._chat_openai(messages, temperature, max_tokens, response_format)

        return self._with_retries(operation)

    @classmethod
    def _wait_for_rate_limit_slot(cls):
        min_interval = Config.LLM_REQUEST_MIN_INTERVAL_SECONDS
        if min_interval <= 0:
            return

        with cls._request_lock:
            now = time.monotonic()
            wait_seconds = cls._last_request_at + min_interval - now
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            cls._last_request_at = time.monotonic()

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        if status_code in {408, 409, 429, 500, 502, 503, 504}:
            return True

        text = str(exc).lower()
        retry_markers = (
            "rate limit",
            "resource_exhausted",
            "quota",
            "timeout",
            "timed out",
            "temporarily",
            "overloaded",
            "try again",
            "429",
            "500",
            "502",
            "503",
            "504",
        )
        return any(marker in text for marker in retry_markers)

    def _with_retries(self, operation):
        max_retries = Config.LLM_REQUEST_MAX_RETRIES
        backoff = Config.LLM_REQUEST_RETRY_BACKOFF_SECONDS

        for attempt in range(max_retries + 1):
            self._wait_for_rate_limit_slot()
            try:
                return operation()
            except Exception as exc:
                if attempt >= max_retries or not self._is_retryable_error(exc):
                    raise
                time.sleep(backoff * (attempt + 1))

        raise RuntimeError("LLM request failed after retries")

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

        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if content is None:
            finish_reason = getattr(response.choices[0], "finish_reason", None)
            raise ValueError(
                "LLM returned no message content"
                + (f" (finish_reason={finish_reason})" if finish_reason else "")
            )
        return content
