from pathlib import Path
import subprocess

from scripts.check_repo_hygiene import (
    find_text_secrets,
    is_forbidden_tracked_path,
    scan_repository,
)
from scripts.run_example import run_example
from scripts.validate_outputs import validate_output_dir


def test_compose_pins_neo4j_with_dynamic_label_support():
    repo_root = Path(__file__).resolve().parents[1]
    compose = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")

    assert "image: neo4j:5.26-community" in compose


def test_runtime_data_is_excluded_from_git_and_docker_context():
    repo_root = Path(__file__).resolve().parents[1]
    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8")
    dockerignore = (repo_root / ".dockerignore").read_text(encoding="utf-8")

    assert "backend/data/" in gitignore.splitlines()
    assert "backend/data" in dockerignore.splitlines()


def test_output_validator_accepts_minimal_example(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = tmp_path / "output"

    run_example(repo_root / "examples" / "minimal_case", output_dir)

    assert validate_output_dir(output_dir) == []


def test_output_validator_reports_missing_files(tmp_path):
    errors = validate_output_dir(tmp_path)

    assert any("report.md" in error for error in errors)
    assert any("metrics.json" in error for error in errors)


def test_secret_scanner_detects_high_confidence_provider_key_without_echoing_it():
    fake_key = "sk-or-v1-" + ("a" * 64)

    findings = find_text_secrets("fixture.env", f"OPENROUTER_API_KEY={fake_key}\n")

    assert [(finding.category, finding.path, finding.line) for finding in findings] == [
        ("openai_style_key", "fixture.env", 1)
    ]
    assert fake_key not in repr(findings)


def test_secret_scanner_allows_placeholders_and_environment_references():
    content = "\n".join(
        [
            "OPENROUTER_API_KEY=",
            "DEEPINFRA_API_KEY=replace-me",
            "OPENROUTER_API_KEY=PASTE_OPENROUTER_API_KEY",
            "export LLM_API_KEY=${MIROFISH_LLM_API_KEY}",
            '$env:GEMINI_API_KEY = $geminiKey',
        ]
    )

    assert find_text_secrets("example.env", content) == []


def test_hygiene_path_policy_blocks_raw_runtime_artifacts():
    assert is_forbidden_tracked_path("runs/example/telemetry.jsonl")
    assert is_forbidden_tracked_path("case/request_trace.json")
    assert is_forbidden_tracked_path("case/simulation.db")
    assert not is_forbidden_tracked_path(
        "examples/multimodel-smoke-evidence/telemetry.jsonl"
    )


def test_repository_scan_includes_untracked_nonignored_files(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    fake_key = "sk-or-v1-" + ("b" * 64)
    (tmp_path / "candidate.env").write_text(
        f"OPENROUTER_API_KEY={fake_key}\n", encoding="utf-8"
    )

    _, findings = scan_repository(tmp_path)

    assert [(item.path, item.category) for item in findings] == [
        ("candidate.env", "openai_style_key")
    ]
