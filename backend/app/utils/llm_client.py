"""
LLM客户端封装
Supports two backends:
  1. Prompture (optional) — 12+ providers: LM Studio, Ollama, Claude, Groq, Kimi, etc.
  2. OpenAI SDK (default fallback) — any OpenAI-compatible API
Install Prompture for multi-provider support: pip install prompture
"""

import json
import logging
import re
import time
import os
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

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
    """LLM客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        
        # METHODOLOGICAL FIX: 
        # If we have a custom base_url (DeepInfra, OpenRouter, Google), 
        # we bypass Prompture and use raw OpenAI SDK to ensure routing is 100% reliable 
        # and not manipulated by intermediate drivers.
        
        if self.base_url and "api.openai.com" not in self.base_url:
            self._use_prompture = False
        else:
            self._use_prompture = _HAS_PROMPTURE

        print(f"[DEBUG LLMClient] initialized with model={self.model}, base_url={self.base_url}, use_prompture={self._use_prompture}")

        if self._use_prompture:
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
        from openai import OpenAI
        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        # Ensure base_url ends with /v1 or /v1beta/openai if needed, 
        # but usually the provided URL in Config is correct.
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    # ── Public API ─────────────────────────────────────────────────

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
    ) -> str:
        if self._use_prompture:
            content = self._chat_prompture(messages, temperature, max_tokens)
            return strip_think_tags(content)
        else:
            content = self._chat_openai(messages, temperature, max_tokens, response_format)
            return re.sub(r'<think(?:ing)?>[\s\S]*?</think(?:ing)?>|<thought>[\s\S]*?</thought>', '', content).strip()

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> Dict[str, Any]:
        if self._use_prompture:
            response = self._chat_prompture(messages, temperature, max_tokens)
            cleaned = clean_json_text(response)
        else:
            response = self._chat_openai(messages, temperature, max_tokens)
            cleaned = re.sub(r'<think(?:ing)?>[\s\S]*?</think(?:ing)?>|<thought>[\s\S]*?</thought>', '', response).strip()
            cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\n?```\s*$', '', cleaned)
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # 1. Try to sanitize control characters (common issue with Qwen)
            try:
                sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', cleaned)
                return json.loads(sanitized)
            except:
                pass
            
            # 2. Final attempt to extract anything between { }
            match = re.search(r'(\{[\s\S]*\})', cleaned)
            if match:
                try: 
                    # Try raw extract
                    return json.loads(match.group(1))
                except: 
                    # Try sanitized extract
                    try:
                        sanitized_extract = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', match.group(1))
                        return json.loads(sanitized_extract)
                    except:
                        pass
                        
            raise ValueError(f"LLM返回的JSON格式无效: {cleaned[:200]}...")

    def _chat_prompture(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
        conv = self._make_conversation(temperature, max_tokens)
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        if system_parts:
            conv._messages.append({"role": "system", "content": "\n".join(system_parts)})
        non_system = [m for m in messages if m["role"] != "system"]
        for msg in non_system[:-1]:
            conv._messages.append({"role": msg["role"], "content": msg["content"]})
        prompt = non_system[-1]["content"] if non_system else ""
        return conv.ask(prompt)

    def _chat_openai(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int, response_format: Optional[Dict] = None) -> str:
        # Strip provider prefix if present for raw OpenAI calls
        model_name = self.model
        if "openrouter/" in model_name:
            # OpenRouter wants the full string but without our internal 'openrouter/' prefix.
            # Actually, OpenRouter models look like 'google/gemini...' or 'qwen/qwen...'.
            # The orchestrator already stripped 'openrouter/' in actual_model, but just in case:
            model_name = model_name.replace("openrouter/", "")
        elif "deepinfra/" in model_name:
            # DeepInfra needs the author/model format (e.g. google/gemma-3...)
            model_name = model_name.replace("deepinfra/", "")
        elif "generativelanguage.googleapis" in str(self.base_url):
            # If using Google's endpoint, they only want the model name, not 'google/'
            if "google/" in model_name:
                model_name = model_name.replace("google/", "")

        kwargs = {"model": model_name, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        if response_format: kwargs["response_format"] = response_format

        import openai
        max_attempts = 6
        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(**kwargs)
                return response.choices[0].message.content
            except openai.RateLimitError:
                if attempt < max_attempts - 1: time.sleep(15 * (attempt + 1))
                else: raise
            except Exception as e:
                if "401" in str(e) and "openrouter" in self.base_url:
                    # Fallback for OpenRouter: Ensure model includes full path
                    kwargs["model"] = self.model
                    continue
                raise e
