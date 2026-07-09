"""
Unit tests for the simulation-DB metrics (Issue #28, Phase 2).

    python3 -m unittest tests.test_simulation_db -v
"""

import os
import sqlite3
import sys
import tempfile
import unittest

_RESEARCH_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "app", "research")
sys.path.insert(0, os.path.abspath(_RESEARCH_DIR))

from entropy import simulation_db as sdb  # noqa: E402
from entropy.embedder import HashingEmbedder  # noqa: E402


def _make_db(path):
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE user (user_id INTEGER, agent_id INTEGER, name TEXT)")
    c.execute("CREATE TABLE post (post_id INTEGER, user_id INTEGER, content TEXT, created_at INTEGER)")
    c.execute("CREATE TABLE comment (comment_id INTEGER, user_id INTEGER, content TEXT, created_at INTEGER)")
    c.executemany("INSERT INTO user VALUES (?,?,?)", [(1, 0, "Ana"), (2, 1, "Beto")])
    # user 1 (Ana): changes a lot over time; user 2 (Beto): repeats; created_at = round
    c.executemany("INSERT INTO post VALUES (?,?,?,?)", [
        (1, 1, "apoyo total a la propuesta economica", 0),
        (2, 1, "ahora dudo del plan fiscal", 5),
        (3, 1, "rechazo la reforma definitivamente", 10),
        (4, 2, "vamos con todo", 0),
        (5, 2, "vamos con todo", 5),
        (6, 2, "vamos con todo", 10),
    ])
    c.commit()
    c.close()


class TestLoadPosts(unittest.TestCase):
    def test_load_and_map(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "twitter_simulation.db")
            _make_db(p)
            posts = sdb.load_posts(p)
            self.assertEqual(len(posts), 6)
            ana = [x for x in posts if x["user_id"] == 1][0]
            self.assertEqual(ana["agent_id"], 0)
            self.assertEqual(ana["name"], "Ana")

    def test_find_sim_db(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "twitter_simulation.db")
            _make_db(p)
            self.assertEqual(sdb.find_sim_db(d), p)


class TestOutputDiversity(unittest.TestCase):
    def test_metrics_present(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "twitter_simulation.db")
            _make_db(p)
            rep = sdb.output_diversity(sdb.load_posts(p), embedder=HashingEmbedder(dim=64), with_embeddings=True)
            self.assertEqual(rep["n_posts"], 6)
            self.assertEqual(rep["n_authors"], 2)
            for k in ("type_token_ratio", "distinct_1", "distinct_2", "self_bleu", "vendi_score"):
                self.assertIn(k, rep)


class TestTemporalDriftPosts(unittest.TestCase):
    def test_changing_author_drifts_more(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "twitter_simulation.db")
            _make_db(p)
            rep = sdb.temporal_drift_from_posts(sdb.load_posts(p), n_buckets=3, embedder=HashingEmbedder(dim=64))
            self.assertEqual(rep["aggregate"]["n_personas_with_drift"], 2)
            ana = rep["per_persona"]["1"]  # changes
            beto = rep["per_persona"]["2"]  # repeats
            # Beto repeats -> high Self-BLEU; Ana changes -> lower
            self.assertGreater(beto["self_bleu"], ana["self_bleu"])
            # Ana drifts more in embedding space
            self.assertGreater(ana["embedding_drift"]["endpoint_distance"],
                               beto["embedding_drift"]["endpoint_distance"])

    def test_no_embeddings_mode(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "twitter_simulation.db")
            _make_db(p)
            rep = sdb.temporal_drift_from_posts(sdb.load_posts(p), with_embeddings=False)
            self.assertIn("mean_self_bleu", rep["aggregate"])
            self.assertNotIn("mean_endpoint_distance", rep["aggregate"])


if __name__ == "__main__":
    unittest.main()
