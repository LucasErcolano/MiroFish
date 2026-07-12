import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tools.mirofish_frontend_parity_check import check_frontend_replay_parity
from tools.mirofish_headless import MiroFishHeadlessRunner, build_backend_env, sanitize_for_artifact

REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeMiroFishHandler(BaseHTTPRequestHandler):
    requests_seen = []
    graph_task_calls = 0
    prepare_calls = 0
    run_status_calls = 0
    report_status_calls = 0

    def log_message(self, *_args):
        return

    @classmethod
    def reset(cls):
        cls.requests_seen = []
        cls.graph_task_calls = 0
        cls.prepare_calls = 0
        cls.run_status_calls = 0
        cls.report_status_calls = 0

    def _record(self, body):
        content_type = self.headers.get("Content-Type", "")
        parsed = None
        if body and "application/json" in content_type:
            parsed = json.loads(body.decode("utf-8"))
        self.__class__.requests_seen.append({
            "method": self.command,
            "path": self.path,
            "content_type": content_type,
            "json": parsed,
        })

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self._record(body)

        if self.path == "/api/graph/ontology/generate":
            self._send_json({"success": True, "data": {"project_id": "proj_1", "ontology": {}, "files": []}})
        elif self.path == "/api/graph/build":
            self._send_json({"success": True, "data": {"task_id": "task_graph"}})
        elif self.path == "/api/simulation/create":
            self._send_json({"success": True, "data": {"simulation_id": "sim_1"}})
        elif self.path == "/api/simulation/prepare":
            self._send_json({"success": True, "data": {"task_id": "task_prepare", "status": "preparing"}})
        elif self.path == "/api/simulation/prepare/status":
            self.__class__.prepare_calls += 1
            self._send_json({"success": True, "data": {"task_id": "task_prepare", "status": "completed", "progress": 100}})
        elif self.path == "/api/simulation/start":
            self._send_json({"success": True, "data": {"runner_status": "running", "process_pid": 123}})
        elif self.path == "/api/simulation/close-env":
            self._send_json({"success": True, "data": {"message": "closed"}})
        elif self.path == "/api/report/generate":
            self._send_json({"success": True, "data": {"task_id": "task_report", "report_id": "report_1", "status": "generating"}})
        elif self.path == "/api/report/generate/status":
            self.__class__.report_status_calls += 1
            self._send_json({"success": True, "data": {"task_id": "task_report", "report_id": "report_1", "status": "completed", "progress": 100}})
        else:
            self._send_json({"success": False, "error": f"unexpected POST {self.path}"}, status=404)

    def do_GET(self):
        self._record(b"")
        if self.path == "/api/graph/task/task_graph":
            self.__class__.graph_task_calls += 1
            self._send_json({"success": True, "data": {"task_id": "task_graph", "status": "completed", "progress": 100}})
        elif self.path == "/api/graph/project/proj_1":
            self._send_json({"success": True, "data": {"project_id": "proj_1", "graph_id": "graph_1", "status": "graph_completed"}})
        elif self.path == "/api/graph/data/graph_1":
            self._send_json({"success": True, "data": {"node_count": 1, "edge_count": 0}})
        elif self.path == "/api/simulation/sim_1/run-status":
            self.__class__.run_status_calls += 1
            self._send_json({"success": True, "data": {"runner_status": "completed", "current_round": 2, "total_rounds": 2, "twitter_current_round": 2, "reddit_current_round": 2, "total_actions_count": 1}})
        elif self.path == "/api/simulation/sim_1/run-status/detail":
            self._send_json({"success": True, "data": {"recent_actions": []}})
        elif self.path == "/api/simulation/sim_1/agent-stats":
            self._send_json({"success": True, "data": {"total_agents": 1}})
        elif self.path.startswith("/api/simulation/sim_1/actions"):
            self._send_json({"success": True, "data": []})
        elif self.path.startswith("/api/simulation/sim_1/timeline"):
            self._send_json({"success": True, "data": []})
        elif self.path == "/api/report/report_1":
            self._send_json({"success": True, "data": {"report_id": "report_1", "markdown_content": "ok"}})
        else:
            self._send_json({"success": False, "error": f"unexpected GET {self.path}"}, status=404)


class HeadlessRunnerTests(unittest.TestCase):
    def setUp(self):
        FakeMiroFishHandler.reset()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeMiroFishHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def test_replays_frontend_flow_and_writes_sanitized_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_file = Path(tmp) / "seed.txt"
            input_file.write_text("seed text", encoding="utf-8")
            out_dir = Path(tmp) / "run"

            runner = MiroFishHeadlessRunner(
                base_url=self.base_url,
                output_dir=out_dir,
                poll_interval=0,
                timeout_seconds=5,
            )
            result = runner.run_full_flow(
                files=[input_file],
                simulation_requirement="predict test",
                project_name="Parity Test",
                max_rounds=2,
                graph_chunk_size=2000,
                generate_report=True,
            )

            self.assertEqual(result["status"], "completed")
            paths = [(r["method"], r["path"]) for r in FakeMiroFishHandler.requests_seen]
            self.assertIn(("POST", "/api/graph/ontology/generate"), paths)
            self.assertIn(("POST", "/api/graph/build"), paths)
            self.assertIn(("POST", "/api/simulation/create"), paths)
            self.assertIn(("POST", "/api/simulation/prepare"), paths)
            self.assertIn(("POST", "/api/simulation/start"), paths)
            self.assertIn(("POST", "/api/report/generate"), paths)
            self.assertIn(("POST", "/api/simulation/close-env"), paths)

            graph_build_payload = next(r["json"] for r in FakeMiroFishHandler.requests_seen if r["path"] == "/api/graph/build")
            self.assertEqual(graph_build_payload, {"project_id": "proj_1", "chunk_size": 2000})

            report_status_payload = next(r["json"] for r in FakeMiroFishHandler.requests_seen if r["path"] == "/api/report/generate/status")
            self.assertEqual(report_status_payload, {"task_id": "task_report"})

            start_payload = next(r["json"] for r in FakeMiroFishHandler.requests_seen if r["path"] == "/api/simulation/start")
            self.assertEqual(start_payload, {
                "simulation_id": "sim_1",
                "platform": "parallel",
                "force": True,
                "enable_graph_memory_update": True,
                "no_wait": False,
                "max_rounds": 2,
            })

            prepare_payload = next(r["json"] for r in FakeMiroFishHandler.requests_seen if r["path"] == "/api/simulation/prepare")
            self.assertEqual(prepare_payload, {
                "simulation_id": "sim_1",
                "use_llm_for_profiles": True,
                "parallel_profile_count": 5,
            })

            manifest = json.loads((out_dir / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["flow_provenance"], "frontend_replay_backend_api")
            self.assertEqual(manifest["num_rounds_or_epochs_requested"], 2)
            self.assertEqual(manifest["num_rounds_or_epochs"], 2)
            self.assertEqual(manifest["is_real_mirofish_system"], True)

            trace = json.loads((out_dir / "request_trace.json").read_text(encoding="utf-8"))
            trace_text = json.dumps(trace)
            key_prefix = "AI" + "zaSy"
            self.assertNotIn(key_prefix, trace_text)

    def test_sanitize_and_backend_env_never_write_plain_keys_to_artifacts(self):
        key_prefix = "AI" + "zaSy"
        key1 = key_prefix + "ExamplePrimarySecret"
        key2 = key_prefix + "ExampleBackupSecret"
        sanitized = sanitize_for_artifact({"LLM_API_KEY": key1, "nested": {"backup": key2}})
        self.assertEqual(sanitized["LLM_API_KEY"], "<redacted>")
        self.assertEqual(sanitized["nested"]["backup"], "<redacted>")

        env = build_backend_env(
            base_env={},
            gemini_api_keys=[key1, key2],
            model="gemini-2.5-flash-lite",
        )
        self.assertEqual(env["LLM_API_KEY"], key1)
        self.assertEqual(env["LLM_BOOST_API_KEY"], key2)
        self.assertEqual(env["LLM_BASE_URL"], "https://generativelanguage.googleapis.com/v1beta/openai/")
        self.assertEqual(env["LLM_MODEL_NAME"], "gemini-2.5-flash-lite")

    def test_static_frontend_parity_check_passes_for_current_api_wrappers(self):
        result = check_frontend_replay_parity(REPO_ROOT)
        self.assertTrue(result["ok"], result)
        self.assertIn("/api/simulation/start", result["frontend_endpoints"])
        self.assertIn("/api/simulation/start", result["runner_endpoints"])

    def test_real_run_gate_requires_rounds_and_actions(self):
        self.assertFalse(MiroFishHeadlessRunner._is_real_run({
            "runner_status": "completed",
            "current_round": 2,
            "total_actions_count": 0,
        }))
        self.assertFalse(MiroFishHeadlessRunner._is_real_run({
            "runner_status": "completed",
            "current_round": 0,
            "total_actions_count": 2,
        }))
        self.assertTrue(MiroFishHeadlessRunner._is_real_run({
            "runner_status": "completed",
            "current_round": 2,
            "total_actions_count": 2,
        }))


if __name__ == "__main__":
    unittest.main()
