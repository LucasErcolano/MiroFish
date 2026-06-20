"""Configurable per-agent / per-role LLM routing for MiroFish simulations.

Issue #21 (S2 Dev 2). Turns the S1 spike's inline per-agent model selection
into a real, auditable feature driven by a YAML model map.

Resolution precedence (highest wins): ``by_agent_id`` > ``by_role`` > ``default``.

The map loading / validation / resolution logic here is intentionally free of
any ``camel`` import so it can be unit-tested without the heavy simulation
dependency. The CAMEL backend is only constructed in :func:`build_backend`,
which imports ``camel`` lazily.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import yaml


class ModelRoutingError(ValueError):
    """Raised on an invalid model map or an unbuildable backend."""


# Known OpenAI-compatible providers. The value documents the conventional
# default env vars; any provider name is accepted (all routed through the
# OpenAI-compatible CAMEL backend) but unknown names are flagged in validation.
PROVIDERS: Dict[str, Dict[str, str]] = {
    "openai": {"base_url_env": "LLM_BASE_URL", "api_key_env": "LLM_API_KEY"},
    "vllm": {"base_url_env": "LOCAL_LLM_BASE_URL", "api_key_env": "LOCAL_LLM_API_KEY"},
    "lmstudio": {"base_url_env": "LOCAL_LLM_BASE_URL", "api_key_env": "LOCAL_LLM_API_KEY"},
    "groq": {"base_url_env": "GROQ_BASE_URL", "api_key_env": "GROQ_API_KEY"},
}

_POLICY_FIELDS = {
    "provider",
    "model",
    "base_url",
    "base_url_env",
    "api_key_env",
    "temperature",
    "seed",
}


@dataclass
class ModelPolicy:
    """The resolved model route for a single agent."""

    agent_id: int
    role: Optional[str]
    provider: str
    model: str
    base_url: Optional[str]
    api_key_env: str
    temperature: Optional[float]
    seed: Optional[int]
    source: str  # which layer won: "by_agent_id" | "by_role" | "default"

    def resolve_api_key(self) -> str:
        return os.environ.get(self.api_key_env, "")

    def to_audit(self) -> Dict[str, Any]:
        """Redacted dict for the routing audit (never includes the key value)."""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "seed": self.seed,
            "api_key_env": self.api_key_env,
            "api_key_set": bool(self.resolve_api_key()),
            "source": self.source,
        }


def _validate_layer(name: str, layer: Dict[str, Any]) -> None:
    if not isinstance(layer, dict):
        raise ModelRoutingError(f"Model map layer '{name}' must be a mapping")
    unknown = set(layer) - _POLICY_FIELDS
    if unknown:
        raise ModelRoutingError(
            f"Model map layer '{name}' has unknown field(s): {sorted(unknown)}"
        )
    # Secrets policy: keys come from the environment, never inline.
    if "api_key" in layer:
        raise ModelRoutingError(
            f"Model map layer '{name}' must not contain a literal 'api_key'; "
            "use 'api_key_env' to name an environment variable instead."
        )
    provider = layer.get("provider")
    if provider is not None and provider not in PROVIDERS:
        # Not fatal (all providers are OpenAI-compatible), but surface it.
        raise ModelRoutingError(
            f"Model map layer '{name}' uses unknown provider '{provider}'. "
            f"Known providers: {sorted(PROVIDERS)}. Add it to PROVIDERS if intended."
        )
    temp = layer.get("temperature")
    if temp is not None and not isinstance(temp, (int, float)):
        raise ModelRoutingError(f"Model map layer '{name}': temperature must be a number")
    seed = layer.get("seed")
    if seed is not None and not isinstance(seed, int):
        raise ModelRoutingError(f"Model map layer '{name}': seed must be an integer or null")


def validate_model_map(model_map: Dict[str, Any]) -> None:
    """Validate the structure of a loaded model map. Raises ModelRoutingError."""
    if not isinstance(model_map, dict):
        raise ModelRoutingError("Model map must be a mapping")
    if model_map.get("version") != 1:
        raise ModelRoutingError("Model map 'version' must be 1")

    default = model_map.get("default")
    if not isinstance(default, dict):
        raise ModelRoutingError("Model map must define a 'default' mapping")
    if not default.get("model"):
        raise ModelRoutingError("Model map 'default' must define a 'model'")
    _validate_layer("default", default)

    fallback = model_map.get("fallback", {})
    if not isinstance(fallback, dict):
        raise ModelRoutingError("Model map 'fallback' must be a mapping")
    if "enabled" in fallback and not isinstance(fallback["enabled"], bool):
        raise ModelRoutingError("Model map 'fallback.enabled' must be a boolean")

    for role, layer in (model_map.get("by_role") or {}).items():
        _validate_layer(f"by_role.{role}", layer)
    for agent_id, layer in (model_map.get("by_agent_id") or {}).items():
        if not isinstance(agent_id, int):
            raise ModelRoutingError(
                f"by_agent_id keys must be integers, got '{agent_id}' ({type(agent_id).__name__})"
            )
        _validate_layer(f"by_agent_id.{agent_id}", layer)


def load_model_map(path: str) -> Dict[str, Any]:
    """Load and validate a model map YAML file."""
    if not os.path.exists(path):
        raise ModelRoutingError(f"Model map not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        model_map = yaml.safe_load(f)
    validate_model_map(model_map)
    return model_map


class ModelRouter:
    """Resolves a :class:`ModelPolicy` per agent from a validated model map."""

    def __init__(self, model_map: Dict[str, Any]):
        validate_model_map(model_map)
        self._map = model_map
        self._default = model_map["default"]
        self._by_role = model_map.get("by_role") or {}
        self._by_agent_id = model_map.get("by_agent_id") or {}

    @classmethod
    def from_file(cls, path: str) -> "ModelRouter":
        return cls(load_model_map(path))

    @property
    def fallback_enabled(self) -> bool:
        return bool((self._map.get("fallback") or {}).get("enabled", False))

    def resolve(self, agent_id: int, role: Optional[str] = None) -> ModelPolicy:
        """Resolve the effective policy for an agent (default < role < agent_id)."""
        merged = dict(self._default)
        source = "default"
        if role is not None and role in self._by_role:
            merged.update(self._by_role[role])
            source = "by_role"
        if agent_id in self._by_agent_id:
            merged.update(self._by_agent_id[agent_id])
            source = "by_agent_id"

        provider = merged.get("provider", "openai")
        # Resolve base_url: literal wins, else env var named by base_url_env.
        base_url = merged.get("base_url")
        if not base_url and merged.get("base_url_env"):
            base_url = os.environ.get(merged["base_url_env"], "") or None
        api_key_env = merged.get("api_key_env") or PROVIDERS.get(provider, {}).get(
            "api_key_env", "LLM_API_KEY"
        )
        return ModelPolicy(
            agent_id=agent_id,
            role=role,
            provider=provider,
            model=merged["model"],
            base_url=base_url,
            api_key_env=api_key_env,
            temperature=merged.get("temperature"),
            seed=merged.get("seed"),
            source=source,
        )


def policy_config_dict(policy: ModelPolicy) -> Dict[str, Any]:
    """Build the CAMEL model_config_dict from a policy (temperature/seed)."""
    cfg: Dict[str, Any] = {}
    if policy.temperature is not None:
        cfg["temperature"] = policy.temperature
    if policy.seed is not None:
        cfg["seed"] = policy.seed
    return cfg


def build_backend(policy: ModelPolicy):
    """Construct a CAMEL OpenAI-compatible backend for a resolved policy.

    Imports ``camel`` lazily so the routing logic above stays testable without
    the simulation stack installed.
    """
    api_key = policy.resolve_api_key()
    if not api_key:
        raise ModelRoutingError(
            f"agent_id={policy.agent_id}: no API key in env var '{policy.api_key_env}'"
        )

    from camel.models import ModelFactory  # lazy
    from camel.types import ModelPlatformType  # lazy

    return ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=policy.model,
        api_key=api_key,
        url=policy.base_url or None,
        model_config_dict=policy_config_dict(policy) or None,
    )
