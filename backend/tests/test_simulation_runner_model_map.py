import json

from app.services.simulation_runner import SimulationRunner


class _FakeProcess:
    pid = 4321


class _FakeThread:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        pass


def _write_ready_simulation(root, sim_id):
    sim_dir = root / sim_id
    sim_dir.mkdir(parents=True)
    (sim_dir / "simulation_config.json").write_text(
        json.dumps(
            {
                "time_config": {
                    "total_simulation_hours": 1,
                    "minutes_per_round": 30,
                }
            }
        ),
        encoding="utf-8",
    )
    return sim_dir


def test_simulation_runner_passes_model_map_to_reddit_command(tmp_path, monkeypatch):
    sim_root = tmp_path / "simulations"
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "run_reddit_simulation.py").write_text("print('ok')\n", encoding="utf-8")
    _write_ready_simulation(sim_root, "sim_model_map")

    captured = {}

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return _FakeProcess()

    monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(sim_root))
    monkeypatch.setattr(SimulationRunner, "SCRIPTS_DIR", str(scripts_dir))
    monkeypatch.setattr("app.services.simulation_runner.subprocess.Popen", fake_popen)
    monkeypatch.setattr("app.services.simulation_runner.threading.Thread", _FakeThread)
    SimulationRunner._run_states.clear()
    SimulationRunner._processes.clear()
    SimulationRunner._monitor_threads.clear()

    SimulationRunner.start_simulation(
        simulation_id="sim_model_map",
        platform="reddit",
        max_rounds=2,
        no_wait=True,
        model_map_path="backtesting/ipc-trimodel-multiagent/model_map_ipc_trimodel.yaml",
    )

    assert "--model-map" in captured["cmd"]
    index = captured["cmd"].index("--model-map")
    assert captured["cmd"][index + 1] == "backtesting/ipc-trimodel-multiagent/model_map_ipc_trimodel.yaml"
    SimulationRunner._stdout_files["sim_model_map"].close()
    SimulationRunner._stdout_files.clear()


def test_simulation_runner_rejects_model_map_for_parallel(tmp_path, monkeypatch):
    sim_root = tmp_path / "simulations"
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "run_parallel_simulation.py").write_text("print('ok')\n", encoding="utf-8")
    _write_ready_simulation(sim_root, "sim_parallel")

    monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(sim_root))
    monkeypatch.setattr(SimulationRunner, "SCRIPTS_DIR", str(scripts_dir))

    try:
        SimulationRunner.start_simulation(
            simulation_id="sim_parallel",
            platform="parallel",
            model_map_path="model_map.yaml",
        )
    except ValueError as exc:
        assert "only supported for reddit" in str(exc)
    else:
        raise AssertionError("expected ValueError for model_map_path with parallel platform")
