from unittest.mock import Mock
import os

import pytest

import run
from app import config as config_module


def test_project_env_does_not_override_exported_credentials(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("LLM_API_KEY=file-value\n", encoding="utf-8")
    monkeypatch.setenv("LLM_API_KEY", "process-value")

    config_module._load_project_env(str(env_path))

    assert os.environ["LLM_API_KEY"] == "process-value"


def test_main_allows_health_only_startup_when_configuration_is_incomplete(monkeypatch):
    app = Mock()
    monkeypatch.setattr(run.Config, "validate", classmethod(lambda cls: ["LLM_API_KEY missing"]))
    monkeypatch.setattr(run.Config, "ALLOW_UNCONFIGURED_STARTUP", True, raising=False)
    monkeypatch.setattr(run, "create_app", lambda: app)

    run.main()

    app.run.assert_called_once()


def test_main_rejects_incomplete_configuration_by_default(monkeypatch):
    monkeypatch.setattr(run.Config, "validate", classmethod(lambda cls: ["LLM_API_KEY missing"]))
    monkeypatch.setattr(run.Config, "ALLOW_UNCONFIGURED_STARTUP", False, raising=False)

    with pytest.raises(SystemExit) as exc_info:
        run.main()

    assert exc_info.value.code == 1
