"""Run grounded Deep Search before ontology and graph construction."""

from typing import Optional, Tuple

from ..config import Config
from ..models.project import ProjectManager
from .deep_search import DeepSearchService


def augment_project_document(
    project_id: str,
    simulation_requirement: str,
    document_text: str,
    *,
    service: Optional[DeepSearchService] = None,
) -> Tuple[str, Optional[str]]:
    """Prepend one persisted research trace to a project's source document."""
    if not Config.ENABLE_DEEP_SEARCH or not simulation_requirement:
        return document_text, None

    research_content = ProjectManager.get_deep_search_result(project_id)
    if not research_content:
        research_service = service or DeepSearchService()
        research_content = research_service.perform_research(simulation_requirement)

        if not research_content or research_content.startswith("Deep Search failed"):
            raise RuntimeError(research_content or "Deep Search returned no content")
        if Config.TAVILY_API_KEY and "TAVILY GROUNDED" not in research_content:
            raise RuntimeError("Deep Search did not produce grounded Tavily research")

        ProjectManager.save_deep_search_result(project_id, research_content)

    return f"{research_content}\n\n{document_text or ''}", research_content
