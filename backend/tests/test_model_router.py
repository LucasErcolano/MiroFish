import os
import sys
from pathlib import Path

import pytest


_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_REPO_ROOT = os.path.abspath(os.path.join(_BACKEND_DIR, ".."))
for path in (_BACKEND_DIR, _REPO_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.services.model_router import ModelRouter, load_model_map  # noqa: E402


def test_model_router_prefers_agent_id_over_role_and_default(tmp_path):
    model_map_path = tmp_path / "model_map.yaml"
    model_map_path.write_text(
        """
version: 1
default:
  provider: openai
  model: qwen/qwen3-8b
  api_key_env: OPENROUTER_API_KEY
by_role:
  analyst:
    provider: openai
    model: google/gemma-3-27b-it
    api_key_env: DEEPINFRA_API_KEY
by_agent_id:
  2:
    provider: openai
    model: meta-llama/Llama-3.3-70B-Instruct-Turbo
    api_key_env: DEEPINFRA_API_KEY
        """.strip(),
        encoding="utf-8",
    )

    router = ModelRouter(load_model_map(str(model_map_path)))

    agent_policy = router.resolve(2, "analyst")
    role_policy = router.resolve(7, "analyst")
    default_policy = router.resolve(9, "observer")

    assert agent_policy.model == "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    assert agent_policy.source == "by_agent_id"
    assert role_policy.model == "google/gemma-3-27b-it"
    assert role_policy.source == "by_role"
    assert default_policy.model == "qwen/qwen3-8b"
    assert default_policy.source == "default"


def test_load_model_map_rejects_literal_api_key(tmp_path):
    model_map_path = tmp_path / "model_map.yaml"
    model_map_path.write_text(
        """
version: 1
default:
  provider: openai
  model: qwen/qwen3-8b
  api_key: should-not-be-here
        """.strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must not contain a literal 'api_key'"):
        load_model_map(str(model_map_path))


def test_ipc_trimodel_map_uses_stable_roles_for_low_depth_rows():
    model_map_path = Path(_REPO_ROOT) / "backtesting" / "ipc-trimodel-multiagent" / "model_map_ipc_trimodel.yaml"
    router = ModelRouter(load_model_map(str(model_map_path)))

    policies = [
        router.resolve(0, "Organization"),
        router.resolve(1, "Organization"),
        router.resolve(2, "Organization"),
        router.resolve(20, "Organization"),
        router.resolve(4, "LegislativeBody"),
    ]

    assert {policy.model for policy in policies} == {
        "google/gemma-3-27b-it",
        "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "qwen/qwen3-8b",
    }
    assert {policy.source for policy in policies} == {"by_agent_id", "by_role", "default"}
