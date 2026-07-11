import json
from pathlib import Path

from app.config import Config
from app.services import fusion_verdict


def test_fusion_verdict_fallback_persists_observable_artifact(tmp_path, monkeypatch):
    class FailingLLMClient:
        def __init__(self, *args, **kwargs):
            raise ValueError("missing test key")

    monkeypatch.setattr(Config, "ENABLE_FUSION_VERDICT", True)
    monkeypatch.setattr(Config, "FUSION_VERDICT_MODEL", "openrouter/fusion")
    monkeypatch.setattr(fusion_verdict, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(fusion_verdict, "LLMClient", FailingLLMClient)

    path = fusion_verdict.generate_fusion_verdict_for_report(
        simulation_id="sim_test",
        report_id="report_test",
        report_markdown="## Result\nGrounded report.",
        wiki_context={"pages": ["index.md"]},
        simulation_requirement="Test requirement",
    )

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assert data["simulation_id"] == "sim_test"
    assert data["report_id"] == "report_test"
    assert data["status"] == "fallback"
    assert data["outcome"] == "needs_review"
    assert data["error"]
