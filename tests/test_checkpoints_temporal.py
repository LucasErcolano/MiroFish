"""
Unit tests for the checkpoint-interview plumbing (D3) and temporal drift (D4).

    python3 -m unittest tests.test_checkpoints_temporal -v
"""

import os
import sys
import unittest

_RESEARCH_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "app", "research")
sys.path.insert(0, os.path.abspath(_RESEARCH_DIR))

from entropy import checkpoints, temporal  # noqa: E402
from entropy.embedder import HashingEmbedder  # noqa: E402


class TestCheckpointPlan(unittest.TestCase):
    def test_three_checkpoints(self):
        plan = checkpoints.checkpoint_rounds(72, 3)
        self.assertEqual([c["label"] for c in plan], ["start", "mid", "end"])
        self.assertEqual([c["round"] for c in plan], [0, 36, 72])

    def test_rounding(self):
        self.assertEqual([c["round"] for c in checkpoints.checkpoint_rounds(10, 3)], [0, 5, 10])

    def test_n_checkpoints_generic(self):
        plan = checkpoints.checkpoint_rounds(100, 5)
        self.assertEqual([c["round"] for c in plan], [0, 25, 50, 75, 100])


class TestParseInterview(unittest.TestCase):
    def test_dual_platform(self):
        result = {"platforms": {
            "twitter": {"agent_id": 0, "response": "tw text", "platform": "twitter"},
            "reddit": {"agent_id": 0, "response": "rd text", "platform": "reddit"},
        }}
        self.assertEqual(checkpoints.parse_interview_result(result),
                         {"twitter": "tw text", "reddit": "rd text"})

    def test_single_platform(self):
        result = {"agent_id": 0, "response": "hello", "platform": "twitter"}
        self.assertEqual(checkpoints.parse_interview_result(result), {"twitter": "hello"})

    def test_empty(self):
        self.assertEqual(checkpoints.parse_interview_result({}), {})


class TestSequences(unittest.TestCase):
    def _records(self):
        plan = checkpoints.checkpoint_rounds(10, 3)
        q = {"id": "stance", "text": "?"}
        recs = []
        # intentionally out of order to test sorting
        for cp in reversed(plan):
            recs.append(checkpoints.make_record(1, cp, q, "twitter", f"resp-{cp['label']}"))
        return recs

    def test_grouping_and_order(self):
        seqs = checkpoints.responses_to_sequences(self._records())
        key = (1, "stance", "twitter")
        self.assertIn(key, seqs)
        self.assertEqual(seqs[key], ["resp-start", "resp-mid", "resp-end"])

    def test_platform_filter(self):
        recs = self._records()
        seqs = checkpoints.responses_to_sequences(recs, platform="reddit")
        self.assertEqual(seqs, {})


class TestTemporalDrift(unittest.TestCase):
    def setUp(self):
        self.emb = HashingEmbedder(dim=64)

    def test_no_change_low_drift_high_selfbleu(self):
        seqs = {(1, "stance", "tw"): ["i support the measure", "i support the measure", "i support the measure"]}
        rep = temporal.temporal_drift_report(seqs, embedder=self.emb)
        self.assertGreater(rep["aggregate"]["mean_self_bleu"], 0.9)
        self.assertAlmostEqual(rep["aggregate"]["mean_endpoint_distance"], 0.0, places=4)

    def test_change_higher_drift_lower_selfbleu(self):
        same = {(1, "q", "tw"): ["alpha alpha alpha", "alpha alpha alpha", "alpha alpha alpha"]}
        diff = {(2, "q", "tw"): ["alpha beta gamma", "delta epsilon zeta", "eta theta iota"]}
        r_same = temporal.temporal_drift_report(same, embedder=self.emb)
        r_diff = temporal.temporal_drift_report(diff, embedder=self.emb)
        self.assertGreater(r_same["aggregate"]["mean_self_bleu"], r_diff["aggregate"]["mean_self_bleu"])
        self.assertGreater(r_diff["aggregate"]["mean_endpoint_distance"],
                           r_same["aggregate"]["mean_endpoint_distance"])

    def test_self_bleu_only_when_no_embeddings(self):
        seqs = {(1, "q", "tw"): ["a b c", "d e f"]}
        rep = temporal.temporal_drift_report(seqs, with_embeddings=False)
        self.assertIn("mean_self_bleu", rep["aggregate"])
        self.assertNotIn("mean_endpoint_distance", rep["aggregate"])


class TestStanceJS(unittest.TestCase):
    def test_no_population_change_is_zero(self):
        labels = {"start": ["s", "o", "n"], "end": ["s", "o", "n"]}
        out = temporal.stance_js_divergence(labels)
        self.assertAlmostEqual(out["endpoint"], 0.0)

    def test_full_flip_is_high(self):
        labels = {"start": ["s", "s", "s"], "end": ["o", "o", "o"]}
        out = temporal.stance_js_divergence(labels)
        self.assertAlmostEqual(out["endpoint"], 1.0)
        self.assertEqual(out["consecutive"][0]["from"], "start")


if __name__ == "__main__":
    unittest.main()
