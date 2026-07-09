import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("run_ipc_trimodel_matrix.py")
SPEC = importlib.util.spec_from_file_location("run_ipc_trimodel_matrix", SCRIPT_PATH)
matrix_runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = matrix_runner
SPEC.loader.exec_module(matrix_runner)


def _row(tmp_path, condition=None):
    return matrix_runner.MatrixRow(
        line="smoke",
        row_id="ipc_trimodel_smoke_T0_R2_D2",
        package="T0",
        input_file=tmp_path / "seed_T0.md",
        requirement="predict",
        rounds=2,
        density=2,
        condition=condition,
        injection_plan=None,
        expected_events=1 if condition else 0,
        raw_dir=tmp_path / "raw",
        committed_dir=tmp_path / "committed",
    )


def _write_required_files(row, memory_payload=None):
    row.committed_dir.mkdir(parents=True, exist_ok=True)
    for name in [
        "report.md",
        "eval_result.json",
        "structured_answer.json",
        "run_notes.md",
    ]:
        (row.committed_dir / name).write_text("{}\n", encoding="utf-8")
    (row.committed_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "num_rounds_or_epochs": 1,
                "final_run_status": {
                    "current_round": 1,
                    "simulated_hours": 1,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (row.committed_dir / "llm_telemetry_summary.json").write_text(
        json.dumps(
            {
                "llm_calls": 3,
                "tokens_in": 10,
                "tokens_out": 20,
                "cost_usd_est": 0.001,
                "models": [
                    "google/gemma-3-27b-it",
                    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                    "qwen/qwen3-8b",
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    audit_records = [
        {"agent_id": 0, "model": "qwen/qwen3-8b"},
        {"agent_id": 1, "model": "google/gemma-3-27b-it"},
        {"agent_id": 2, "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo"},
    ]
    (row.committed_dir / "model_routing_audit.jsonl").write_text(
        "\n".join(json.dumps(record) for record in audit_records) + "\n",
        encoding="utf-8",
    )
    payload = memory_payload or {
        "memory_dir_exists": True,
        "core_memory_exists": False,
        "chroma_db_exists": True,
    }
    (row.committed_dir / "experimental_memory_evidence.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_validate_committed_evidence_accepts_required_smoke_artifacts(tmp_path):
    row = _row(tmp_path)
    _write_required_files(row)

    assert matrix_runner.validate_committed_evidence(row) == []


def test_validate_committed_evidence_reports_missing_required_artifact(tmp_path):
    row = _row(tmp_path)
    _write_required_files(row)
    (row.committed_dir / "model_routing_audit.jsonl").unlink()

    assert "model_routing_audit.jsonl" in matrix_runner.validate_committed_evidence(row)


def test_validate_committed_evidence_rejects_empty_memory_evidence(tmp_path):
    row = _row(tmp_path)
    _write_required_files(
        row,
        memory_payload={
            "memory_dir_exists": False,
            "core_memory_exists": False,
            "chroma_db_exists": False,
        },
    )

    assert "experimental_memory_evidence.json:no_memory_artifacts" in matrix_runner.validate_committed_evidence(row)


def test_validate_committed_evidence_requires_scheduled_events_for_s3(tmp_path):
    row = _row(tmp_path, condition="signal-mid")
    _write_required_files(row)

    assert "scheduled_events_fired.jsonl" in matrix_runner.validate_committed_evidence(row)


def test_validate_committed_evidence_allows_zero_event_s3_control_without_event_log(tmp_path):
    row = replace(_row(tmp_path, condition="baseline-control"), expected_events=0)
    _write_required_files(row)

    assert "scheduled_events_fired.jsonl" not in matrix_runner.validate_committed_evidence(row)


def test_validate_committed_evidence_requires_all_three_routed_models(tmp_path):
    row = _row(tmp_path)
    _write_required_files(row)
    (row.committed_dir / "model_routing_audit.jsonl").write_text(
        json.dumps({"agent_id": 0, "model": "qwen/qwen3-8b"}) + "\n",
        encoding="utf-8",
    )

    missing = matrix_runner.validate_committed_evidence(row)
    assert any(item.startswith("model_routing_audit.jsonl:missing_models=") for item in missing)


def test_validate_committed_evidence_rejects_zero_round_false_positive(tmp_path):
    row = _row(tmp_path)
    _write_required_files(row)
    (row.committed_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "num_rounds_or_epochs": 0,
                "final_run_status": {
                    "current_round": 0,
                    "simulated_hours": 0,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert "run_manifest.json:no_completed_rounds" in matrix_runner.validate_committed_evidence(row)


def test_validate_committed_evidence_rejects_zero_llm_calls(tmp_path):
    row = _row(tmp_path)
    _write_required_files(row)
    (row.committed_dir / "llm_telemetry_summary.json").write_text(
        json.dumps(
            {
                "llm_calls": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd_est": 0.0,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert "llm_telemetry_summary.json:no_llm_calls" in matrix_runner.validate_committed_evidence(row)


def test_validate_committed_evidence_requires_all_three_telemetry_models(tmp_path):
    row = _row(tmp_path)
    _write_required_files(row)
    (row.committed_dir / "llm_telemetry_summary.json").write_text(
        json.dumps(
            {
                "llm_calls": 3,
                "tokens_in": 10,
                "tokens_out": 20,
                "cost_usd_est": 0.001,
                "models": [
                    "google/gemma-3-27b-it",
                    "qwen/qwen3-8b",
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    missing = matrix_runner.validate_committed_evidence(row)
    assert any(item.startswith("llm_telemetry_summary.json:missing_models=") for item in missing)


def test_validate_committed_evidence_accepts_stale_status_with_reddit_comments(tmp_path):
    row = _row(tmp_path)
    _write_required_files(row)
    (row.committed_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "num_rounds_or_epochs": 0,
                "final_run_status": {
                    "current_round": 0,
                    "simulated_hours": 0,
                    "total_actions_count": 0,
                    "reddit_actions_count": 0,
                },
                "reddit_db_summary": {
                    "comment_count": 4,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert "run_manifest.json:no_completed_rounds" not in matrix_runner.validate_committed_evidence(row)


def test_validate_committed_evidence_checks_scheduled_event_count(tmp_path):
    row = _row(tmp_path, condition="signal-mid")
    _write_required_files(row)
    (row.committed_dir / "scheduled_events_fired.jsonl").write_text("{}\n{}\n", encoding="utf-8")

    missing = matrix_runner.validate_committed_evidence(row)
    assert "scheduled_events_fired.jsonl:event_count=2,expected=1" in missing


def test_validate_committed_evidence_accepts_expected_scheduled_event_count(tmp_path):
    row = _row(tmp_path, condition="signal-mid")
    _write_required_files(row)
    (row.committed_dir / "scheduled_events_fired.jsonl").write_text("{}\n", encoding="utf-8")

    assert matrix_runner.validate_committed_evidence(row) == []


def test_build_env_bypasses_incomplete_simulation_dedup(monkeypatch):
    monkeypatch.delenv("SIMILARITY_THRESHOLD", raising=False)

    env = matrix_runner.build_env({"graph": {}, "model_map": "model_map.yaml"})

    assert env["SIMILARITY_THRESHOLD"] == "0"
