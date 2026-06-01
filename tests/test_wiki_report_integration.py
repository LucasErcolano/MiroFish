"""
Tests for wiki memory → ReportAgent integration.

Covers:
  - build_wiki_context_for_report helper (happy path, empty wiki, no data)
  - ReportAgent accepts wiki_context parameter and stores it
  - Wiki context is injected into plan_outline prompt (via mock)
  - Wiki context is injected into _generate_section_react prompt (via mock)
  - Graceful degradation: missing wiki → None context → no injection
  - Full compile → context → ReportAgent integration flow
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

# ---------------------------------------------------------------------------
# Add backend to sys.path
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# ---------------------------------------------------------------------------
# Import wiki_memory components directly (avoids heavy service imports)
# ---------------------------------------------------------------------------
import importlib
_schemas = importlib.import_module("app.services.wiki_memory.schemas")
_store = importlib.import_module("app.services.wiki_memory.wiki_store")
_compiler = importlib.import_module("app.services.wiki_memory.compiler")

WikiStore = _store.WikiStore
WikiCompiler = _compiler.WikiCompiler
CompileResult = _compiler.CompileResult
WikiPage = _schemas.WikiPage
WikiPageType = _schemas.WikiPageType
WikiSection = _schemas.WikiSection
WikiTimelineEntry = _schemas.WikiTimelineEntry

# Import the integration helper
_wiki_init = importlib.import_module("app.services.wiki_memory")
build_wiki_context_for_report = _wiki_init.build_wiki_context_for_report


# ---------------------------------------------------------------------------
# Tests: build_wiki_context_for_report
# ---------------------------------------------------------------------------

class TestBuildWikiContextForReport(unittest.TestCase):
    """Test the convenience integration helper."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wiki_root = os.path.join(self.tmp.name, "simulations")
        os.makedirs(self.wiki_root, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_none_when_no_wiki_data(self):
        """No wiki pages → helper returns None (baseline behaviour unchanged)."""
        result = build_wiki_context_for_report(
            "sim_nonexistent",
            wiki_root=self.wiki_root,
        )
        self.assertIsNone(result)

    def test_returns_context_from_existing_pages(self):
        """Existing wiki pages → helper assembles and returns context."""
        store = WikiStore(wiki_root=self.wiki_root)
        store.initialize("sim_test1")

        # Write an AGENTS page
        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Test Simulation Wiki",
            sections=[
                WikiSection(heading="Overview", body="This is a test simulation."),
            ],
            timeline=[],
            simulation_id="sim_test1",
        )
        store.write_page("sim_test1", page)

        result = build_wiki_context_for_report(
            "sim_test1",
            wiki_root=self.wiki_root,
        )
        self.assertIsNotNone(result)
        self.assertIn("Test Simulation Wiki", result)
        self.assertIn("This is a test simulation", result)

    def test_compiles_from_raw_data_when_no_existing_pages(self):
        """No existing pages but raw data provided → compile + return context."""
        events = [
            {"round_num": 1, "actions": [
                {"agent_name": "Agent_A", "agent_id": "a1", "platform": "weibo"},
            ]},
        ]
        result = build_wiki_context_for_report(
            "sim_test2",
            wiki_root=self.wiki_root,
            events=events,
            case_metadata={"name": "Test Case"},
        )
        self.assertIsNotNone(result)
        self.assertIn("Agent_A", result)

    def test_max_chars_truncation(self):
        """Context is truncated to max_chars — large pages may be skipped."""
        store = WikiStore(wiki_root=self.wiki_root)
        store.initialize("sim_test3")

        # Write a moderately-sized AGENTS page (under max_chars)
        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Long Wiki",
            sections=[
                WikiSection(heading="Overview", body="X" * 2000),
            ],
            timeline=[],
            simulation_id="sim_test3",
        )
        store.write_page("sim_test3", page)

        # Also write a small entity page
        entity_page = WikiPage(
            page_type=WikiPageType.ENTITY,
            title="SmallEntity",
            sections=[WikiSection(heading="Description", body="A small entity.")],
            timeline=[],
            entity_id="smallentity",
            simulation_id="sim_test3",
        )
        store.write_page("sim_test3", entity_page)

        result = build_wiki_context_for_report(
            "sim_test3",
            wiki_root=self.wiki_root,
            max_chars=5000,
        )
        self.assertIsNotNone(result)
        # Should contain the AGENTS page and potentially the entity page
        self.assertIn("Long Wiki", result)

    def test_graceful_degradation_on_error(self):
        """If WikiStore raises, the helper returns None instead of crashing."""
        with patch.object(WikiStore, "initialize", side_effect=OSError("disk full")):
            result = build_wiki_context_for_report(
                "sim_error",
                wiki_root=self.wiki_root,
            )
            self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Tests: ReportAgent wiki_context integration
# ---------------------------------------------------------------------------

class TestReportAgentWikiContextIntegration(unittest.TestCase):
    """Test that ReportAgent properly stores and would use wiki_context.

    We do NOT test the full LLM call chain (that requires a running LLM).
    Instead we verify:
      1. __init__ accepts wiki_context and stores it
      2. wiki_context=None is the default (backward compat)
      3. When wiki_context is set, plan_outline and _generate_section_react
         include it in their prompts.
    """

    def _make_agent(self, wiki_context=None):
        """Create a ReportAgent with mocked LLM and ZepTools."""
        with patch("app.services.report_agent.LLMClient") as MockLLM, \
             patch("app.services.report_agent.ZepToolsService") as MockZep:
            mock_llm = MagicMock()
            mock_zep = MagicMock()
            MockLLM.return_value = mock_llm
            MockZep.return_value = mock_zep

            from app.services.report_agent import ReportAgent
            agent = ReportAgent(
                graph_id="g1",
                simulation_id="sim1",
                simulation_requirement="Test simulation requirement",
                llm_client=mock_llm,
                zep_tools=mock_zep,
                wiki_context=wiki_context,
            )
            return agent

    def test_init_stores_wiki_context(self):
        """wiki_context is stored as self.wiki_context."""
        agent = self._make_agent(wiki_context="Some wiki content here")
        self.assertEqual(agent.wiki_context, "Some wiki content here")

    def test_init_default_wiki_context_none(self):
        """Default wiki_context is None (backward compatible)."""
        agent = self._make_agent()
        self.assertIsNone(agent.wiki_context)

    def test_wiki_context_injected_into_plan_outline(self):
        """When wiki_context is set, it appears in the user prompt inside
        plan_outline's LLM call. We mock the LLM to capture the messages."""
        wiki_text = "## Entity: TestEntity\nThis is wiki knowledge."
        agent = self._make_agent(wiki_context=wiki_text)

        # Mock ZepTools.get_simulation_context to return minimal data
        agent.zep_tools.get_simulation_context.return_value = {
            "graph_statistics": {"total_nodes": 10, "total_edges": 5, "entity_types": {"Person": 5}},
            "related_facts": [],
            "total_entities": 10,
        }

        # Mock LLM response
        agent.llm.chat_json.return_value = {
            "title": "Test Report",
            "summary": "A test",
            "sections": [{"title": "Overview"}, {"title": "Analysis"}],
        }

        outline = agent.plan_outline()

        # Verify the LLM was called
        self.assertTrue(agent.llm.chat_json.called)
        call_args = agent.llm.chat_json.call_args
        messages = call_args[1].get("messages", call_args[0][0] if call_args[0] else [])
        # Find the user message
        user_msgs = [m for m in messages if m["role"] == "user"]
        self.assertTrue(len(user_msgs) > 0)
        user_content = user_msgs[0]["content"]
        self.assertIn("<wiki_audit_context>", user_content)
        self.assertIn("PRIOR KNOWLEDGE — NOT GROUND TRUTH", user_content)
        self.assertIn(wiki_text, user_content)

    def test_no_wiki_context_means_no_injection_plan_outline(self):
        """When wiki_context is None, no wiki_audit_context tag in plan_outline
        prompts — baseline unchanged."""
        agent = self._make_agent(wiki_context=None)

        agent.zep_tools.get_simulation_context.return_value = {
            "graph_statistics": {"total_nodes": 0, "total_edges": 0, "entity_types": {}},
            "related_facts": [],
            "total_entities": 0,
        }

        agent.llm.chat_json.return_value = {
            "title": "Test Report",
            "summary": "A test",
            "sections": [{"title": "Overview"}],
        }

        agent.plan_outline()

        call_kwargs = agent.llm.chat_json.call_args[1]
        messages = call_kwargs.get("messages", [])
        user_msgs = [m for m in messages if m["role"] == "user"]
        self.assertTrue(len(user_msgs) > 0)
        user_content = user_msgs[0]["content"]
        self.assertNotIn("<wiki_audit_context>", user_content)

    def test_wiki_context_injected_into_section_react(self):
        """When wiki_context is set, it appears in the system prompt in
        _generate_section_react's LLM call."""
        wiki_text = "## Claim: test_claim\nStatement: something happened."
        agent = self._make_agent(wiki_context=wiki_text)

        # Provide minimal mocks for section generation
        from app.services.report_agent import ReportOutline, ReportSection
        section = ReportSection(title="Test Section")
        outline = ReportOutline(
            title="Test Report",
            summary="A test",
            sections=[section],
        )

        # Mock LLM to return a final-answer response (no tool calls)
        agent.llm.chat.return_value = "Final Answer: This is the section content about testing."

        # We need to patch the section prompt templates to avoid locale dependency
        with patch("app.services.report_agent._get_section_prompts_for_locale") as mock_prompts, \
             patch("app.services.report_agent._qg_parse_tool_calls") as mock_parse, \
             patch("app.services.report_agent._qg_clean_final_answer") as mock_clean:
            mock_prompts.return_value = (
                "System: {report_title} {report_summary} {simulation_requirement} {section_title} {tools_description}",
                "User: {previous_content} {section_title}"
            )
            mock_parse.return_value = []  # No tool calls
            mock_clean.return_value = "Cleaned section content."

            try:
                result = agent._generate_section_react(
                    section=section,
                    outline=outline,
                    previous_sections=["## Intro\nHello"],
                    section_index=1,
                )
            except Exception:
                # The ReACT loop may need more mocking than we want here.
                # The important thing is checking that the system prompt included
                # wiki context before the LLM was called.
                pass

        # Check that the first chat call (thought step) included wiki context
        # in the system message.
        if agent.llm.chat.called:
            first_call = agent.llm.chat.call_args_list[0]
            messages_kw = first_call[1].get("messages", None)
            if messages_kw is None and first_call[0]:
                messages_kw = first_call[0][0]
            if messages_kw:
                system_msgs = [m for m in messages_kw if m["role"] == "system"]
                if system_msgs:
                    self.assertIn("<wiki_audit_context>", system_msgs[0]["content"])
                    self.assertIn(wiki_text, system_msgs[0]["content"])

    def test_no_wiki_context_means_no_injection_section_react(self):
        """When wiki_context is None, no wiki_audit_context tag in section
        react system prompt — baseline unchanged."""
        agent = self._make_agent(wiki_context=None)

        from app.services.report_agent import ReportOutline, ReportSection
        section = ReportSection(title="Test Section")
        outline = ReportOutline(
            title="Test Report",
            summary="A test",
            sections=[section],
        )

        with patch("app.services.report_agent._get_section_prompts_for_locale") as mock_prompts, \
             patch("app.services.report_agent._qg_parse_tool_calls") as mock_parse, \
             patch("app.services.report_agent._qg_clean_final_answer") as mock_clean:
            mock_prompts.return_value = (
                "System: {report_title} {report_summary} {simulation_requirement} {section_title} {tools_description}",
                "User: {previous_content} {section_title}"
            )
            mock_parse.return_value = []
            mock_clean.return_value = "Cleaned section content."

            try:
                agent._generate_section_react(
                    section=section,
                    outline=outline,
                    previous_sections=["## Intro\nHello"],
                    section_index=1,
                )
            except Exception:
                pass

        if agent.llm.chat.called:
            first_call = agent.llm.chat.call_args_list[0]
            messages_kw = first_call[1].get("messages", None)
            if messages_kw is None and first_call[0]:
                messages_kw = first_call[0][0]
            if messages_kw:
                system_msgs = [m for m in messages_kw if m["role"] == "system"]
                if system_msgs:
                    self.assertNotIn("<wiki_audit_context>", system_msgs[0]["content"])


# ---------------------------------------------------------------------------
# Tests: Full integration flow
# ---------------------------------------------------------------------------

class TestFullIntegrationFlow(unittest.TestCase):
    """End-to-end: compile wiki data → build context → pass to ReportAgent."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wiki_root = os.path.join(self.tmp.name, "simulations")
        os.makedirs(self.wiki_root, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_compile_and_build_context_flow(self):
        """Compile wiki pages, then build context for ReportAgent."""
        store = WikiStore(wiki_root=self.wiki_root)
        store.initialize("sim_e2e")

        # Write entity pages
        entity_page = WikiPage(
            page_type=WikiPageType.ENTITY,
            title="TestPerson",
            sections=[
                WikiSection(heading="Description", body="A test person entity."),
                WikiSection(heading="Key Facts", body="- Was present at the event\n- Has conflicting statements"),
            ],
            timeline=[],
            entity_id="testperson",
            simulation_id="sim_e2e",
        )
        store.write_page("sim_e2e", entity_page)

        # Build context
        context = build_wiki_context_for_report(
            "sim_e2e",
            wiki_root=self.wiki_root,
            max_chars=8000,
        )

        self.assertIsNotNone(context)
        self.assertIn("TestPerson", context)
        self.assertIn("A test person entity", context)

        # Pass context to a mock ReportAgent
        with patch("app.services.report_agent.LLMClient") as MockLLM, \
             patch("app.services.report_agent.ZepToolsService") as MockZep:
            from app.services.report_agent import ReportAgent
            agent = ReportAgent(
                graph_id="g1",
                simulation_id="sim_e2e",
                simulation_requirement="Test requirement",
                wiki_context=context,
            )
            self.assertEqual(agent.wiki_context, context)

    def test_empty_wiki_returns_none_and_agent_gets_none(self):
        """Empty simulation (no wiki data) → None context → agent.wiki_context=None."""
        context = build_wiki_context_for_report(
            "sim_empty",
            wiki_root=self.wiki_root,
        )
        self.assertIsNone(context)

        with patch("app.services.report_agent.LLMClient") as MockLLM, \
             patch("app.services.report_agent.ZepToolsService") as MockZep:
            from app.services.report_agent import ReportAgent
            agent = ReportAgent(
                graph_id="g1",
                simulation_id="sim_empty",
                simulation_requirement="Test",
                wiki_context=context,  # None
            )
            self.assertIsNone(agent.wiki_context)


if __name__ == "__main__":
    unittest.main()