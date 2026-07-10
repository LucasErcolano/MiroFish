import json
from pathlib import Path

from scripts.run_real_smoke import resolve_smoke_api_key, validate_real_smoke


def _valid_manifest():
    return {
        "status": "completed",
        "is_real_mirofish_system": True,
        "graph_data_summary": {"node_count": 2, "edge_count": 1},
        "num_rounds_or_epochs": 9,
        "final_run_status": {"total_actions_count": 4},
        "report_id": "report_1",
        "environment_close": {"attempted": True, "success": True},
    }


def test_validate_real_smoke_accepts_complete_artifacts(tmp_path: Path):
    (tmp_path / "mirofish_report_raw.md").write_text("# Real report\n\nGrounded result.", encoding="utf-8")
    evidence = tmp_path / "simulation_artifacts" / "experimental_memory_evidence.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text(json.dumps({"memory_dir_exists": True}), encoding="utf-8")

    assert validate_real_smoke(_valid_manifest(), tmp_path, api_key="secret-key") == []


def test_validate_real_smoke_rejects_false_positive_and_secret_leak(tmp_path: Path):
    (tmp_path / "mirofish_report_raw.md").write_text("secret-key", encoding="utf-8")

    errors = validate_real_smoke(
        {
            "status": "completed",
            "is_real_mirofish_system": False,
            "graph_data_summary": {"node_count": 0, "edge_count": 0},
            "num_rounds_or_epochs": 0,
            "final_run_status": {"total_actions_count": 0},
            "report_id": None,
            "environment_close": {"attempted": False, "success": None},
        },
        tmp_path,
        api_key="secret-key",
    )

    assert any("real-system gate" in error for error in errors)
    assert any("actions" in error for error in errors)
    assert any("API key" in error for error in errors)


def test_resolve_smoke_api_key_supports_both_documented_providers():
    assert resolve_smoke_api_key({"OPENROUTER_API_KEY": "openrouter"}) == "openrouter"
    assert resolve_smoke_api_key({"DEEPINFRA_API_KEY": "deepinfra"}) == "deepinfra"
    assert resolve_smoke_api_key({"MIROFISH_SMOKE_API_KEY": "explicit"}) == "explicit"
