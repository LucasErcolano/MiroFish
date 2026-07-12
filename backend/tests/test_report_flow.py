import pytest

from app import create_app
from app.models.task import TaskManager, TaskStatus
from app.services.report_agent import (
    Report,
    ReportAgent,
    ReportManager,
    ReportOutline,
    ReportSection,
    ReportStatus,
)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(tmp_path / "reports"))
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_check_report_status_without_report_returns_empty_state(client):
    response = client.get("/api/report/check/sim_no_report")

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["data"]["simulation_id"] == "sim_no_report"
    assert body["data"]["has_report"] is False
    assert body["data"]["report_id"] is None
    assert body["data"]["interview_unlocked"] is False


def test_check_report_status_with_completed_report(client):
    report = Report(
        report_id="report_existing",
        simulation_id="sim_with_report",
        graph_id="graph_1",
        simulation_requirement="Explain the run",
        status=ReportStatus.COMPLETED,
        markdown_content="# Report",
        created_at="2026-06-27T12:00:00",
        completed_at="2026-06-27T12:01:00",
    )
    ReportManager.save_report(report)

    response = client.get("/api/report/check/sim_with_report")

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["data"]["has_report"] is True
    assert body["data"]["report_id"] == "report_existing"
    assert body["data"]["report_status"] == "completed"
    assert body["data"]["interview_unlocked"] is True


def test_generate_status_uses_post_body_task_id(client):
    manager = TaskManager()
    task_id = manager.create_task("report_generate", metadata={"simulation_id": "sim_task"})
    manager.update_task(
        task_id,
        status=TaskStatus.PROCESSING,
        progress=42,
        message="Generating report",
    )

    response = client.post(
        "/api/report/generate/status",
        json={"task_id": task_id, "simulation_id": "sim_task"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["data"]["task_id"] == task_id
    assert body["data"]["status"] == "processing"
    assert body["data"]["progress"] == 42


def test_section_generation_returns_grounded_fallback_when_forced_final_llm_fails(monkeypatch):
    class FakeLLM:
        def __init__(self):
            self.calls = 0

        def chat(self, *args, **kwargs):
            self.calls += 1
            if self.calls <= 5:
                return (
                    '<tool_call>{"name": "quick_search", '
                    '"parameters": {"query": "NVDA AMD TSM target prices"}}</tool_call>'
                )
            raise TypeError("'NoneType' object is not subscriptable")

    agent = ReportAgent(
        graph_id="graph_1",
        simulation_id="sim_1",
        simulation_requirement="Compare NVDA, AMD, and TSM 12-month returns.",
        llm_client=FakeLLM(),
        zep_tools=object(),
    )
    monkeypatch.setattr(
        agent,
        "_execute_tool",
        lambda *args, **kwargs: (
            "NVDA base case $250, AMD base case $620, TSM base case $470. "
            "Key drivers: AI demand, data center growth, valuation risk."
        ),
    )

    outline = ReportOutline(
        title="AI Semiconductor Stocks",
        summary="Compare NVDA, AMD, and TSM.",
        sections=[ReportSection(title="Projected Stock Performance & Key Drivers")],
    )

    content = agent._generate_section_react(
        outline.sections[0],
        outline,
        previous_sections=[],
        section_index=1,
    )

    assert "Projected Stock Performance & Key Drivers" in content
    assert "NVDA base case $250" in content
    assert "AI demand" in content
