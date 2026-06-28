import json
import os
import sys
from pathlib import Path


_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_REPO_ROOT = os.path.abspath(os.path.join(_BACKEND_DIR, ".."))
for path in (_BACKEND_DIR, _REPO_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from scripts.run_reddit_simulation import RedditSimulationRunner  # noqa: E402
from tools.mirofish_headless import apply_injection_plan_to_simulation_config  # noqa: E402


def _runner_with_events(events):
    runner = RedditSimulationRunner.__new__(RedditSimulationRunner)
    runner.config = {"event_config": {"scheduled_events": events}}
    runner._fired_scheduled_event_keys = set()
    return runner


def test_round_pct_resolution_for_issue19_40_rounds():
    assert RedditSimulationRunner._resolve_scheduled_round({"round_pct": 0.10}, 40) == 3
    assert RedditSimulationRunner._resolve_scheduled_round({"round_pct": 0.50}, 40) == 19
    assert RedditSimulationRunner._resolve_scheduled_round({"round_pct": 0.90}, 40) == 35


def test_explicit_round_is_one_based_and_clamped():
    assert RedditSimulationRunner._resolve_scheduled_round({"round": 1}, 40) == 0
    assert RedditSimulationRunner._resolve_scheduled_round({"round": 999}, 40) == 39
    assert RedditSimulationRunner._resolve_scheduled_round({"round": 0}, 40) == 0


def test_scheduled_events_for_round_skips_already_fired():
    runner = _runner_with_events([
        {"id": "signal", "round_pct": 0.50, "target_platform": "reddit", "action": "create_post"},
    ])

    assert runner._scheduled_events_for_round(18, 40) == []
    due = runner._scheduled_events_for_round(19, 40)
    assert len(due) == 1
    assert due[0][0] == "signal"

    runner._fired_scheduled_event_keys.add("signal")
    assert runner._scheduled_events_for_round(19, 40) == []


def test_runner_prefers_cli_model_map_over_config(tmp_path):
    config_path = tmp_path / "simulation_config.json"
    config_path.write_text(
        json.dumps(
            {
                "model_map_path": "from-config.yaml",
                "agent_configs": [],
                "event_config": {"initial_posts": [], "scheduled_events": []},
            }
        ),
        encoding="utf-8",
    )

    runner = RedditSimulationRunner(
        config_path=str(config_path),
        wait_for_commands=False,
        model_map_path="from-cli.yaml",
    )

    assert runner.model_map_path == "from-cli.yaml"


def test_apply_real_issue19_injection_plan_to_reddit_config(tmp_path):
    sim_id = "sim_issue19_test"
    sim_dir = tmp_path / "backend" / "uploads" / "simulations" / sim_id
    sim_dir.mkdir(parents=True)
    config_path = sim_dir / "simulation_config.json"
    config_path.write_text(
        json.dumps({"event_config": {"initial_posts": [], "scheduled_events": []}}),
        encoding="utf-8",
    )

    plan_path = Path(_REPO_ROOT) / "backtesting" / "case-a-s2-positional-noise" / "injection_plan.yaml"
    result = apply_injection_plan_to_simulation_config(
        repo_root=tmp_path,
        simulation_id=sim_id,
        injection_plan=plan_path,
        condition="signal-mid",
    )

    assert result["condition"] == "signal-mid"
    assert result["scheduled_events_count"] == 1

    config = json.loads(config_path.read_text(encoding="utf-8"))
    event = config["event_config"]["scheduled_events"][0]
    assert event["target_platform"] == "reddit"
    assert event["action"] == "create_post"
    assert event["round_pct"] == 0.50
    assert "Argentina" in event["content"]
    assert "Colombia" in event["content"]


def test_apply_v2_nested_injection_plan_to_reddit_config(tmp_path):
    sim_id = "sim_issue19_v2_test"
    sim_dir = tmp_path / "backend" / "uploads" / "simulations" / sim_id
    sim_dir.mkdir(parents=True)
    config_path = sim_dir / "simulation_config.json"
    config_path.write_text(
        json.dumps({"event_config": {"initial_posts": [], "scheduled_events": []}}),
        encoding="utf-8",
    )

    plan_path = Path(_REPO_ROOT) / "backtesting" / "case-a-s2-positional-noise-v2" / "injection_plan_v2.yaml"
    result = apply_injection_plan_to_simulation_config(
        repo_root=tmp_path,
        simulation_id=sim_id,
        injection_plan=plan_path,
        condition="v2-counter-colombia-mid",
    )

    assert result["condition"] == "v2-counter-colombia-mid"
    assert result["scheduled_events_count"] == 1

    config = json.loads(config_path.read_text(encoding="utf-8"))
    event = config["event_config"]["scheduled_events"][0]
    assert event["id"] == "counter-colombia"
    assert event["target_platform"] == "reddit"
    assert event["round_pct"] == 0.50
    assert "Counter-Signal Document" in event["content"]
    assert "Colombia" in event["content"]
    assert "James Rodriguez" in event["content"]
