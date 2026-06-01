from __future__ import annotations

"""Wiki Memory — Public API

Exposes the WikiStore, WikiCompiler, and schema classes for Wiki-backed
Report Memory integration.

Usage::

    from app.services.wiki_memory import WikiStore, WikiCompiler, WikiPage, WikiPageType

    store = WikiStore()
    store.initialize("sim_abc123")

    compiler = WikiCompiler(store)
    result = compiler.compile(
        simulation_id="sim_abc123",
        events=[...],
        retrieved_memories=[...],
        case_metadata={...},
        documents=[...],
    )

    # For ReportAgent prompt injection:
    context = store.compile_wiki_context("sim_abc123", max_chars=8000)

Convenience integration helper::

    from app.services.wiki_memory import build_wiki_context_for_report

    wiki_context = build_wiki_context_for_report("sim_abc123")
    # Pass wiki_context (str or None) to ReportAgent(wiki_context=...)
"""

from .schemas import (
    WikiMeta,
    WikiPage,
    WikiPageType,
    WikiSection,
    WikiTimelineEntry,
)
from .wiki_store import WikiStore
from .compiler import WikiCompiler, CompileResult


def build_wiki_context_for_report(
    simulation_id: str,
    *,
    max_chars: int = 8000,
    wiki_root: str | None = None,
    events=None,
    retrieved_memories=None,
    case_metadata=None,
    documents=None,
) -> str | None:
    """Build wiki audit context for ReportAgent prompt injection.

    This is the primary integration point between the wiki_memory module
    and ReportAgent. It:

    1. Tries to read an existing compiled wiki from WikiStore.
    2. If no wiki pages exist yet, optionally compiles one from the
       provided events/memories/metadata.
    3. Returns the compiled markdown context string (capped at
       max_chars), or None if no wiki data is available.

    The caller should pass the result to ``ReportAgent(wiki_context=...)``
    without further processing. A None return means "no wiki context
    available" — baseline behavior is unchanged.

    Args:
        simulation_id: Simulation ID to compile wiki context for.
        max_chars: Maximum context length in characters (default 8000 ≈
            2000 tokens). Keeps the prompt budget manageable.
        wiki_root: Optional override for the wiki storage root. Pass
            this in tests to use a tmpdir. Defaults to WikiStore.WIKI_ROOT.
        events: Optional list of simulation events for compilation.
        retrieved_memories: Optional memory search results for compilation.
        case_metadata: Optional project/simulation metadata dict.
        documents: Optional list of document descriptor dicts.

    Returns:
        Compiled wiki context string, or None if no wiki data exists.
    """
    from ...utils.logger import get_logger

    logger = get_logger("mirofish.wiki_memory.integration")

    try:
        store = WikiStore(wiki_root=wiki_root)
        store.initialize(simulation_id)

        # Try to read existing compiled wiki context first.
        # If pages exist, compile_wiki_context assembles them.
        context = store.compile_wiki_context(simulation_id, max_chars=max_chars)

        if context:
            logger.info(
                "Wiki audit context loaded from existing pages for %s (%d chars)",
                simulation_id,
                len(context),
            )
            return context

        # No existing wiki pages — try to compile from raw data if provided.
        if events or retrieved_memories or case_metadata or documents:
            compiler = WikiCompiler(store)
            result = compiler.compile(
                simulation_id=simulation_id,
                events=events,
                retrieved_memories=retrieved_memories,
                case_metadata=case_metadata,
                documents=documents,
            )
            if result.errors:
                logger.warning(
                    "Wiki compilation for %s had %d errors: %s",
                    simulation_id,
                    len(result.errors),
                    result.errors[:3],
                )
            # Now re-read the compiled pages.
            context = store.compile_wiki_context(
                simulation_id, max_chars=max_chars
            )
            if context:
                logger.info(
                    "Wiki audit context compiled for %s (%d chars, %d pages)",
                    simulation_id,
                    len(context),
                    len(result.pages_updated),
                )
                return context

        # No wiki data available — return None so caller skips injection.
        logger.info("No wiki context available for %s — baseline mode", simulation_id)
        return None

    except Exception:
        # Graceful degradation: log and return None rather than crashing
        # the report generation pipeline.
        logger.exception(
            "Failed to build wiki context for %s — falling back to baseline",
            simulation_id,
        )
        return None


__all__ = [
    "WikiMeta",
    "WikiPage",
    "WikiPageType",
    "WikiSection",
    "WikiTimelineEntry",
    "WikiStore",
    "WikiCompiler",
    "CompileResult",
    "build_wiki_context_for_report",
]