import os
import sys
import tempfile
import unittest
from pathlib import Path

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


class DummyLLM:
    def chat(self, *args, **kwargs):
        return None

    def chat_json(self, *args, **kwargs):
        return {"title": "T", "summary": "S", "sections": []}


class DummyZepTools:
    pass


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
