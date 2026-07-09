from unittest.mock import Mock

import pytest

import run


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
