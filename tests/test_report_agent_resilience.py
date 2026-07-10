import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.report_agent import (  # noqa: E402
    ReportAgent,
    ReportLogger,
    ReportManager,
    ReportOutline,
    ReportSection,
    ReportStatus,
)
from app.config import Config  # noqa: E402
from app.utils.locale import get_language_instruction, get_locale, set_locale  # noqa: E402


class DummyLLM:
    def chat(self, *args, **kwargs):
        return None

    def chat_json(self, *args, **kwargs):
        return {"title": "T", "summary": "S", "sections": []}


class SequenceLLM:
    def __init__(self, responses):
        self.responses = list(responses)

    def chat(self, *args, **kwargs):
        if self.responses:
            return self.responses.pop(0)
        return "No usable tool call here."

    def chat_json(self, *args, **kwargs):
        return {"title": "T", "summary": "S", "sections": []}


class DummyZepTools:
    pass


class RecordingZepTools:
    def __init__(self):
        self.insight_kwargs = None

    def insight_forge(self, **kwargs):
        self.insight_kwargs = kwargs
        return type("Result", (), {"to_text": lambda self: "grounded"})()


class ReportAgentResilienceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_upload_folder = Config.UPLOAD_FOLDER
        self.old_reports_dir = ReportManager.REPORTS_DIR
        Config.UPLOAD_FOLDER = self.tmp.name
        ReportManager.REPORTS_DIR = os.path.join(Config.UPLOAD_FOLDER, "reports")

    def tearDown(self):
        Config.UPLOAD_FOLDER = self.old_upload_folder
        ReportManager.REPORTS_DIR = self.old_reports_dir
        set_locale('zh')
        self.tmp.cleanup()

    def make_agent(self):
        return ReportAgent(
            graph_id="graph-test",
            simulation_id="sim-test",
            simulation_requirement="req",
            llm_client=DummyLLM(),
            zep_tools=DummyZepTools(),
        )

    def test_parse_tool_calls_treats_none_response_as_no_tool_calls(self):
        agent = self.make_agent()

        self.assertEqual(agent._parse_tool_calls(None), [])

    def test_report_limits_are_configurable_for_real_smoke_runs(self):
        tools = RecordingZepTools()
        with (
            patch.object(Config, "REPORT_AGENT_MAX_TOOL_CALLS", 1),
            patch.object(Config, "REPORT_AGENT_MAX_SUB_QUERIES", 1, create=True),
        ):
            agent = ReportAgent(
                graph_id="graph-test",
                simulation_id="sim-test",
                simulation_requirement="req",
                llm_client=DummyLLM(),
                zep_tools=tools,
            )
            agent._execute_tool("insight_forge", {"query": "x"})

        self.assertEqual(agent.MAX_TOOL_CALLS_PER_SECTION, 1)
        self.assertEqual(tools.insight_kwargs["max_sub_queries"], 1)

    def test_parse_tool_calls_accepts_gemini_action_json_block(self):
        agent = self.make_agent()

        calls = agent._parse_tool_calls('''Thought: need data\nAction:\n```json\n{"name":"insight_forge","parameters":{"query":"inflacion argentina"}}\n```''')

        self.assertEqual(calls, [{"name": "insight_forge", "parameters": {"query": "inflacion argentina"}}])

    def test_parse_tool_calls_accepts_tool_code_search_syntax(self):
        agent = self.make_agent()

        calls = agent._parse_tool_calls('<tool_code>print(insight_forge.search(query="riesgos Argentina", report_context="ctx"))</tool_code>')

        self.assertEqual(calls, [{"name": "insight_forge", "parameters": {"query": "riesgos Argentina", "report_context": "ctx"}}])

    def test_parse_tool_calls_accepts_tool_code_query_syntax(self):
        agent = self.make_agent()

        calls = agent._parse_tool_calls('<tool_code>\nprint(insight_forge.query(query="LLA 2025", report_context="ctx"))\n</tool_code>')

        self.assertEqual(calls, [{"name": "insight_forge", "parameters": {"query": "LLA 2025", "report_context": "ctx"}}])

    def test_parse_tool_calls_normalizes_topic_to_query_alias(self):
        agent = self.make_agent()

        calls = agent._parse_tool_calls('<tool_call>{"name":"insight_forge","parameters":{"topic":"LLA apoyo"}}</tool_call>')

        self.assertEqual(calls, [{"name": "insight_forge", "parameters": {"query": "LLA apoyo"}}])

    def test_parse_tool_calls_accepts_gemini_tool_code_array(self):
        agent = self.make_agent()

        calls = agent._parse_tool_calls('''```json
[
  {"tool_code":"insight_forge","parameters":{"query":"Argentina 2025"}}
]
```''')

        self.assertEqual(calls, [{"name": "insight_forge", "parameters": {"query": "Argentina 2025"}}])

    def test_generate_report_fails_closed_when_section_has_no_real_tool_calls(self):
        class NoToolAgent(ReportAgent):
            def __init__(self):
                super().__init__(
                    graph_id="graph-test",
                    simulation_id="sim-test",
                    simulation_requirement="req",
                    llm_client=SequenceLLM(["No tool call"] * 8),
                    zep_tools=DummyZepTools(),
                )

            def plan_outline(self, progress_callback=None):
                return ReportOutline(title="T", summary="S", sections=[ReportSection("A")])

        report = NoToolAgent().generate_report(report_id="report-no-tools")

        self.assertEqual(report.status, ReportStatus.FAILED)
        self.assertIn("no real tool calls", report.error)

    def test_report_section_validation_rejects_model_self_reported_tool_failure(self):
        agent = self.make_agent()

        with self.assertRaisesRegex(ValueError, "invalid self-reported tool failure"):
            agent._validate_section_content(
                "I cannot actually call the tools anymore, so no source_id is available.",
                tool_calls_count=1,
                forced=False,
            )

    def test_validate_section_rejects_leaked_thought_scaffolding(self):
        agent = self.make_agent()

        leaked = (
            "Thought\nThe user wants me to write the next section. I need to call tools.\n\n"
            "**Predicción Electoral**\n\nLLA ronda el 38%."
        )
        with self.assertRaisesRegex(ValueError, "ReACT scaffolding"):
            agent._validate_section_content(leaked, tool_calls_count=2, forced=False)

    def test_validate_section_rejects_leaked_tool_failure_narration(self):
        agent = self.make_agent()

        leaked = (
            "The `interview_agents` tool failed because the simulation environment "
            "was not running. I need to pivot and rely on other tools."
        )
        with self.assertRaisesRegex(ValueError, "reasoning/error leaked"):
            agent._validate_section_content(leaked, tool_calls_count=1, forced=False)

    def test_validate_section_rejects_leaked_tool_code_markup(self):
        agent = self.make_agent()

        leaked = '<tool_code>print(insight_forge.query(query="x"))</tool_code>'
        with self.assertRaisesRegex(ValueError, "raw tool-call markup"):
            agent._validate_section_content(leaked, tool_calls_count=2, forced=False)

    def test_clean_final_answer_strips_leading_thought_block(self):
        agent = self.make_agent()

        raw = (
            "Thought\nI should write about elections.\n\n"
            "**Predicción Electoral**\n\nLLA en 38%."
        )
        cleaned = agent._clean_final_answer(raw)
        self.assertTrue(cleaned.startswith("**Predicción Electoral**"))
        self.assertNotIn("Thought", cleaned)

    def test_clean_final_answer_strips_trailing_tool_code_block(self):
        agent = self.make_agent()

        raw = (
            'Thought\nPlan.\n<tool_code>\nprint(insight_forge.query(query="x"))\n</tool_code>'
            "\n\n**Predicción Electoral**\n\nContenido real."
        )
        cleaned = agent._clean_final_answer(raw)
        self.assertTrue(cleaned.startswith("**Predicción Electoral**"))
        self.assertNotIn("<tool_code>", cleaned)
        self.assertNotIn("Thought", cleaned)

    def test_locale_aware_outline_fallback_is_spanish_for_es(self):
        agent = self.make_agent()
        # Force plan_outline into its exception path by stubbing the LLM.

        class BoomLLM:
            def chat_json(self, *args, **kwargs):
                raise RuntimeError("forced failure")

            def chat(self, *args, **kwargs):
                return None

        agent.llm = BoomLLM()

        class StubZep:
            def get_simulation_context(self, **kwargs):
                return {"graph_statistics": {}, "total_entities": 0, "related_facts": []}

        agent.zep_tools = StubZep()

        set_locale('es')
        try:
            outline = agent.plan_outline()
        finally:
            set_locale('zh')

        # No CJK characters should appear in the Spanish fallback titles.
        joined = " ".join([outline.title, outline.summary] + [s.title for s in outline.sections])
        self.assertFalse(
            any('\u4e00' <= ch <= '\u9fff' for ch in joined),
            f"Fallback outline leaked Chinese into es locale: {joined!r}",
        )
        self.assertIn("predicción", joined.lower())

    def test_localize_tool_result_rewrites_chinese_headers_for_es_locale(self):
        agent = self.make_agent()
        set_locale('es')
        try:
            raw = (
                "## 未来预测深度分析\n"
                "分析问题: Argentina 2025\n"
                "预测场景: economía\n\n"
                "### 预测数据统计\n"
                "- 相关预测事实: 57条\n"
                "- 涉及实体: 17个\n"
                "- 关系链: 43条\n\n"
                "### 【关键事实】(请在报告中引用这些原文)\n"
                "1. \"La inflación...\""
            )
            out = agent._localize_tool_result(raw)
        finally:
            set_locale('zh')
        # The Chinese headers should be gone.
        self.assertNotIn("未来预测深度分析", out)
        self.assertNotIn("分析问题", out)
        self.assertNotIn("【关键事实】", out)
        # The Spanish equivalents should appear.
        self.assertIn("Análisis predictivo profundo", out)
        self.assertIn("Pregunta de análisis:", out)
        # Data is preserved.
        self.assertIn("Argentina 2025", out)
        self.assertIn("La inflación", out)

    def test_localize_tool_result_passthrough_for_zh_locale(self):
        agent = self.make_agent()
        set_locale('zh')
        raw = "## 未来预测深度分析\n分析问题: test"
        out = agent._localize_tool_result(raw)
        # No translations table for zh — return as-is.
        self.assertEqual(out, raw)

    def test_validate_section_rejects_mostly_chinese_content_for_es_locale(self):
        agent = self.make_agent()
        set_locale('es')
        try:
            mostly_chinese = (
                "**Resultados Electorales**\n\n"
                "根据提供的信息，我整理了关于阿根廷经济政策与社会影响的关键点。"
                "财政盈余与经济复苏是核心议题。通胀对公众舆论的影响被广泛讨论。"
                "汇率政策被认为是实现经济复苏的关键条件。国际货币基金组织的"
                "事后评估和中国、美国等国际实体在阿根廷经济政策中的角色被提及。"
            )
            with self.assertRaisesRegex(ValueError, "invalid language"):
                agent._validate_section_content(mostly_chinese, tool_calls_count=2, forced=False)
        finally:
            set_locale('zh')

    def test_validate_section_allows_chinese_content_for_zh_locale(self):
        agent = self.make_agent()
        set_locale('zh')
        mostly_chinese = (
            "**核心结论**\n\n根据提供的信息，我整理了关于阿根廷经济政策的关键点。"
            "财政盈余与经济复苏是核心议题。通胀对公众舆论的影响被广泛讨论。"
        )
        # Should NOT raise — Chinese is fine when locale is zh.
        agent._validate_section_content(mostly_chinese, tool_calls_count=2, forced=False)

    def test_thread_locale_accepts_languages_without_translation_file(self):
        set_locale('es')

        self.assertEqual(get_locale(), 'es')
        self.assertIn('español', get_language_instruction().lower())

    def test_report_logger_accepts_none_payloads_without_crashing(self):
        logger = ReportLogger("report-none-safe")

        logger.log_llm_response("section", 1, None, 1, False, False)
        logger.log_tool_result("section", 1, "quick_search", None, 1)
        logger.log_section_content("section", 1, None, 0)
        logger.log_section_full_complete("section", 1, None)

        logs = ReportManager.get_agent_log_stream("report-none-safe")
        self.assertEqual(len(logs), 4)
        self.assertEqual(logs[0]["details"]["response"], "")
        self.assertEqual(logs[1]["details"]["result"], "")
        self.assertEqual(logs[2]["details"]["content"], "")
        self.assertEqual(logs[3]["details"]["content"], "")

    def test_generate_report_reuses_completed_sections_when_retrying_same_report_id(self):
        class RetryAgent(ReportAgent):
            def __init__(self):
                super().__init__(
                    graph_id="graph-test",
                    simulation_id="sim-test",
                    simulation_requirement="req",
                    llm_client=DummyLLM(),
                    zep_tools=DummyZepTools(),
                )
                self.generated = []

            def plan_outline(self, progress_callback=None):
                return ReportOutline(
                    title="Retry Report",
                    summary="summary",
                    sections=[ReportSection("A"), ReportSection("B")],
                )

            def _generate_section_react(self, section, outline, previous_sections, progress_callback=None, section_index=0):
                self.generated.append(section.title)
                return f"generated {section.title}"

        report_id = "report-resume"
        ReportManager._ensure_report_folder(report_id)
        ReportManager.save_section(report_id, 1, ReportSection("A", "already generated A"))

        agent = RetryAgent()
        report = agent.generate_report(report_id=report_id)

        self.assertEqual(report.status, ReportStatus.COMPLETED)
        self.assertEqual(agent.generated, ["B"])
        self.assertEqual(report.outline.sections[0].content, "already generated A")
        self.assertIn("already generated A", report.markdown_content)
        self.assertIn("generated B", report.markdown_content)


if __name__ == "__main__":
    unittest.main()
