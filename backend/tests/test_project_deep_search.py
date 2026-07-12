from pathlib import Path

import pytest

from app.config import Config
from app.models.project import ProjectManager
from app.services.deep_search import build_search_query
from app.services.project_deep_search import augment_project_document


class FakeDeepSearch:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def perform_research(self, theme):
        self.calls.append(theme)
        return self.result


def test_tavily_query_is_compacted_to_provider_limit():
    query = build_search_query("topic\n" + ("detailed requirement " * 40))

    assert len(query) <= 400
    assert "\n" not in query
    assert query.startswith("topic detailed requirement")


@pytest.fixture()
def project_store(tmp_path, monkeypatch):
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path / "projects"))
    project = ProjectManager.create_project("Deep Search test")
    return project


def test_disabled_deep_search_leaves_project_document_unchanged(project_store, monkeypatch):
    monkeypatch.setattr(Config, "ENABLE_DEEP_SEARCH", False)
    service = FakeDeepSearch("unused")

    augmented, research = augment_project_document(
        project_store.project_id,
        "topic",
        "seed text",
        service=service,
    )

    assert augmented == "seed text"
    assert research is None
    assert service.calls == []


def test_grounded_research_is_saved_and_prepended_before_graph_build(project_store, monkeypatch):
    monkeypatch.setattr(Config, "ENABLE_DEEP_SEARCH", True)
    monkeypatch.setattr(Config, "TAVILY_API_KEY", "configured")
    result = "--- AUTONOMOUS DEEP SEARCH (TAVILY GROUNDED): topic ---\n\nEvidence"
    service = FakeDeepSearch(result)

    augmented, research = augment_project_document(
        project_store.project_id,
        "topic",
        "seed text",
        service=service,
    )

    assert augmented.startswith(result)
    assert augmented.endswith("seed text")
    assert research == result
    assert service.calls == ["topic"]
    assert ProjectManager.get_deep_search_result(project_store.project_id) == result


def test_existing_project_research_is_reused_without_second_request(project_store, monkeypatch):
    monkeypatch.setattr(Config, "ENABLE_DEEP_SEARCH", True)
    monkeypatch.setattr(Config, "TAVILY_API_KEY", "configured")
    cached = "--- AUTONOMOUS DEEP SEARCH (TAVILY GROUNDED): cached ---\n\nEvidence"
    ProjectManager.save_deep_search_result(project_store.project_id, cached)
    service = FakeDeepSearch("should not run")

    augmented, research = augment_project_document(
        project_store.project_id,
        "topic",
        "seed text",
        service=service,
    )

    assert augmented.startswith(cached)
    assert research == cached
    assert service.calls == []


def test_configured_tavily_fails_closed_on_internal_knowledge_fallback(project_store, monkeypatch):
    monkeypatch.setattr(Config, "ENABLE_DEEP_SEARCH", True)
    monkeypatch.setattr(Config, "TAVILY_API_KEY", "configured")
    service = FakeDeepSearch(
        "--- AUTONOMOUS DEEP SEARCH (LLM INTERNAL KNOWLEDGE): topic ---\n\nUnverified"
    )

    with pytest.raises(RuntimeError, match="grounded Tavily research"):
        augment_project_document(
            project_store.project_id,
            "topic",
            "seed text",
            service=service,
        )
