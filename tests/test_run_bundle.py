"""
Unit tests for the run-bundle dataset export (Issue #28, PD).

Builds a synthetic backend/uploads tree and verifies that build_bundle stitches
question + plan + result together, and that append_to_dataset deduplicates.

    python3 -m unittest tests.test_run_bundle -v
"""

import json
import os
import sys
import tempfile
import unittest

_RESEARCH_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "app", "research")
sys.path.insert(0, os.path.abspath(_RESEARCH_DIR))

from dataset import run_bundle  # noqa: E402


def _make_uploads(root, pid="proj_1", sid="sim_1", rid="rep_1"):
    pdir = os.path.join(root, "projects", pid)
    sdir = os.path.join(root, "simulations", sid)
    rdir = os.path.join(root, "reports", rid)
    os.makedirs(pdir)
    os.makedirs(os.path.join(sdir, "twitter"))
    os.makedirs(os.path.join(sdir, "reddit"))
    os.makedirs(rdir)

    with open(os.path.join(pdir, "project.json"), "w", encoding="utf-8") as f:
        json.dump({
            "project_id": pid,
            "simulation_requirement": "Predict the runoff outcome from the seed material.",
            "files": [{"filename": "seed.md", "size": 1234, "path": os.path.join(pdir, "seed.md")}],
            "total_text_length": 4200,
            "ontology": {"types": ["Voter", "Party"]},
        }, f)
    with open(os.path.join(pdir, "seed.md"), "w", encoding="utf-8") as f:
        f.write("seed content")
    with open(os.path.join(pdir, "extracted_text.txt"), "w", encoding="utf-8") as f:
        f.write("full extracted seed text")

    with open(os.path.join(sdir, "simulation_config.json"), "w", encoding="utf-8") as f:
        json.dump({
            "simulation_id": sid, "project_id": pid, "graph_id": "graph_1",
            "llm_model": "google/gemma-3-27b-it",
            "generation_reasoning": "72h sim, evening peak; mix of supportive/opposing voters.",
            "time_config": {"total_simulation_hours": 72, "minutes_per_round": 60},
            "event_config": {"hot_topics": ["runoff"]},
            "agent_configs": [
                {"entity_type": "Voter", "stance": "supporting"},
                {"entity_type": "Voter", "stance": "opposing"},
                {"entity_type": "Party", "stance": "neutral"},
            ],
            "generated_at": "2026-06-19T10:00:00",
        }, f)
    with open(os.path.join(sdir, "run_state.json"), "w", encoding="utf-8") as f:
        json.dump({
            "runner_status": "completed", "current_round": 72, "total_rounds": 72,
            "twitter_actions_count": 1200, "reddit_actions_count": 800,
            "twitter_completed": True, "reddit_completed": True,
        }, f)
    with open(os.path.join(sdir, "twitter", "actions.jsonl"), "w", encoding="utf-8") as f:
        f.write('{"round":1}\n{"round":2}\n')
    with open(os.path.join(sdir, "reddit_profiles.json"), "w", encoding="utf-8") as f:
        json.dump([
            {"username": "v1", "persona": "a builder", "mbti": "INTJ"},
            {"username": "v2", "persona": "a healer", "mbti": "ENFP"},
        ], f)

    with open(os.path.join(rdir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"report_id": rid, "simulation_id": sid, "graph_id": "graph_1",
                   "status": "completed", "created_at": "t0", "completed_at": "t1"}, f)
    with open(os.path.join(rdir, "full_report.md"), "w", encoding="utf-8") as f:
        f.write("# Forecast\nThe runoff leans 52/48.")
    with open(os.path.join(rdir, "outline.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "Forecast", "sections": [{"title": "Summary"}]}, f)
    return pid, sid, rid


class TestBuildBundle(unittest.TestCase):
    def test_bundle_stitches_all_three_parts(self):
        with tempfile.TemporaryDirectory() as root:
            pid, sid, rid = _make_uploads(root)
            b = run_bundle.build_bundle(uploads_root=root, project_id=pid, simulation_id=sid, report_id=rid)
            self.assertEqual(b["model"], "google/gemma-3-27b-it")
            self.assertIn("runoff outcome", b["input"]["question"])
            self.assertIn("evening peak", b["plan"]["reasoning"])
            self.assertEqual(b["plan"]["agents"]["n_agents"], 3)
            self.assertEqual(b["plan"]["agents"]["stance_distribution"]["supporting"], 1)
            self.assertIn("52/48", b["result"]["report_markdown"])
            self.assertEqual(b["result"]["run_state"]["runner_status"], "completed")
            self.assertEqual(b["result"]["run_state"]["twitter_actions_logged"], 2)
            self.assertEqual(b["ids"]["graph_id"], "graph_1")
            self.assertTrue(b["content_hash"])
            # full personas embedded by default ("todo el planning")
            self.assertEqual(len(b["plan"]["personas"]), 2)
            self.assertEqual(b["plan"]["personas"][0]["persona"], "a builder")

    def test_personas_can_be_excluded(self):
        with tempfile.TemporaryDirectory() as root:
            pid, sid, rid = _make_uploads(root)
            b = run_bundle.build_bundle(uploads_root=root, project_id=pid, simulation_id=sid,
                                        report_id=rid, include_personas=False)
            self.assertIsNone(b["plan"]["personas"])

    def test_seed_files_hashed_and_text_optional(self):
        with tempfile.TemporaryDirectory() as root:
            pid, sid, rid = _make_uploads(root)
            b = run_bundle.build_bundle(uploads_root=root, project_id=pid, simulation_id=sid,
                                        report_id=rid, include_seed_text=True)
            self.assertEqual(b["input"]["seed"]["files"][0]["filename"], "seed.md")
            self.assertTrue(b["input"]["seed"]["files"][0]["sha256"])
            self.assertEqual(b["input"]["seed"]["extracted_text"], "full extracted seed text")

    def test_run_dir_resolves_ids_from_manifest(self):
        with tempfile.TemporaryDirectory() as root:
            pid, sid, rid = _make_uploads(root)
            run_dir = os.path.join(root, "headless_run")
            os.makedirs(run_dir)
            with open(os.path.join(run_dir, "run_manifest.json"), "w", encoding="utf-8") as f:
                json.dump({"identifiers": {"project_id": pid, "simulation_id": sid, "report_id": rid}}, f)
            b = run_bundle.build_bundle(uploads_root=root, run_dir=run_dir)
            self.assertEqual(b["ids"]["simulation_id"], sid)
            self.assertIn("runoff outcome", b["input"]["question"])


class TestDatasetAppend(unittest.TestCase):
    def test_append_and_dedup(self):
        with tempfile.TemporaryDirectory() as root:
            pid, sid, rid = _make_uploads(root)
            b = run_bundle.build_bundle(uploads_root=root, project_id=pid, simulation_id=sid, report_id=rid)
            rec = run_bundle.to_training_record(b)
            ds = os.path.join(root, "datasets", "runs.jsonl")
            self.assertTrue(run_bundle.append_to_dataset(rec, ds))
            self.assertFalse(run_bundle.append_to_dataset(rec, ds))  # duplicate content_hash
            with open(ds, "r", encoding="utf-8") as f:
                lines = [ln for ln in f if ln.strip()]
            self.assertEqual(len(lines), 1)
            row = json.loads(lines[0])
            self.assertEqual(row["prompt"], b["input"]["question"])
            self.assertIn("52/48", row["completion"])
            self.assertEqual(row["model"], "google/gemma-3-27b-it")


if __name__ == "__main__":
    unittest.main()
