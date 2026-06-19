"""
Unit tests for the Línea 6 entropy/diversity metrics (Issue #28).

These import the ``entropy`` package standalone (without going through the Flask
``app`` factory) so they run with system Python + numpy and need no backend venv
or network. Run from the repo root:

    python3 -m unittest tests.test_entropy_metrics -v
"""

import json
import math
import os
import sys
import tempfile
import unittest

# Import the entropy package directly, bypassing backend/app/__init__.py (Flask).
_RESEARCH_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "app", "research")
sys.path.insert(0, os.path.abspath(_RESEARCH_DIR))

from entropy import metrics  # noqa: E402
from entropy import embeddings  # noqa: E402
from entropy import personas  # noqa: E402
from entropy.embedder import HashingEmbedder  # noqa: E402


class TestShannonEntropy(unittest.TestCase):
    def test_uniform_binary_is_one_bit(self):
        self.assertAlmostEqual(metrics.shannon_entropy({"a": 1, "b": 1}), 1.0)

    def test_uniform_four_is_two_bits(self):
        self.assertAlmostEqual(metrics.categorical_entropy(["a", "b", "c", "d"]), 2.0)

    def test_degenerate_is_zero(self):
        self.assertEqual(metrics.categorical_entropy(["a", "a", "a"]), 0.0)

    def test_drops_none_and_empty(self):
        # Only two real labels → 1 bit, regardless of None/"" noise.
        self.assertAlmostEqual(metrics.categorical_entropy(["a", "b", None, ""]), 1.0)

    def test_normalized_entropy_bounds(self):
        self.assertAlmostEqual(metrics.normalized_entropy(["a", "b", "c", "d"]), 1.0)
        self.assertEqual(metrics.normalized_entropy(["a", "a"]), 0.0)

    def test_effective_number_equals_categories_when_uniform(self):
        self.assertAlmostEqual(metrics.effective_number(["a", "b", "c", "d"]), 4.0)


class TestLexicalDiversity(unittest.TestCase):
    def test_distinct_n_all_unique(self):
        self.assertAlmostEqual(metrics.distinct_n(["one two three"], n=1), 1.0)

    def test_distinct_n_with_repeats(self):
        # tokens: a a a -> 1 unique / 3 total
        self.assertAlmostEqual(metrics.distinct_n(["a a a"], n=1), 1.0 / 3.0)

    def test_type_token_ratio(self):
        self.assertAlmostEqual(metrics.type_token_ratio(["a b a b"]), 0.5)

    def test_self_bleu_identical_is_high(self):
        texts = ["the quick brown fox", "the quick brown fox", "the quick brown fox"]
        self.assertGreater(metrics.self_bleu(texts), 0.9)

    def test_self_bleu_disjoint_is_low(self):
        texts = ["alpha beta gamma delta", "uno dos tres cuatro", "ichi ni san shi"]
        self.assertLess(metrics.self_bleu(texts), 0.1)

    def test_self_bleu_single_text_is_zero(self):
        self.assertEqual(metrics.self_bleu(["only one"]), 0.0)


class TestDivergence(unittest.TestCase):
    def test_js_identical_is_zero(self):
        self.assertAlmostEqual(metrics.jensen_shannon_divergence(["a", "b"], ["a", "b"]), 0.0)

    def test_js_disjoint_is_one_in_base2(self):
        self.assertAlmostEqual(metrics.jensen_shannon_divergence(["a", "a"], ["b", "b"]), 1.0)

    def test_js_symmetric(self):
        p = {"a": 0.7, "b": 0.3}
        q = {"a": 0.2, "b": 0.8}
        self.assertAlmostEqual(
            metrics.jensen_shannon_divergence(p, q),
            metrics.jensen_shannon_divergence(q, p),
        )


class TestProfileReport(unittest.TestCase):
    def setUp(self):
        self.profiles = [
            {"gender": "M", "mbti": "INTJ", "country": "AR", "profession": "eng",
             "age": 31, "interested_topics": ["ai", "policy"], "persona": "a builder of systems"},
            {"gender": "F", "mbti": "ENFP", "country": "AR", "profession": "doc",
             "age": 44, "interested_topics": ["health"], "persona": "a careful healer"},
            {"gender": "F", "mbti": "INTJ", "country": "BO", "profession": "eng",
             "age": 29, "interested_topics": "ai;ethics", "persona": "a builder of bridges"},
        ]

    def test_report_has_all_fields(self):
        rep = metrics.profile_categorical_report(self.profiles)
        for f in ("gender", "mbti", "country", "profession", "age_bucket", "interested_topics"):
            self.assertIn(f, rep)
            self.assertIn("entropy_bits", rep[f])
            self.assertIn("effective_n", rep[f])

    def test_topics_flattened_from_list_and_string(self):
        rep = metrics.profile_categorical_report(self.profiles)
        # ai, policy, health, ai, ethics -> 4 unique
        self.assertEqual(rep["interested_topics"]["unique"], 4)

    def test_age_bucketing(self):
        self.assertEqual(metrics.age_bucket(31), "30-39")
        self.assertEqual(metrics.age_bucket(29), "20-29")
        self.assertIsNone(metrics.age_bucket(None))


class TestEmbeddingMetrics(unittest.TestCase):
    def setUp(self):
        self.emb = HashingEmbedder(dim=64)

    def test_hashing_embedder_deterministic(self):
        a = self.emb.embed_texts(["hello world"])
        b = self.emb.embed_texts(["hello world"])
        self.assertEqual(a, b)

    def test_vendi_identical_is_one(self):
        vecs = self.emb.embed_texts(["same text here"] * 5)
        self.assertAlmostEqual(embeddings.vendi_score(vecs), 1.0, places=4)

    def test_vendi_orthogonal_approaches_n(self):
        # Disjoint vocabularies → near-orthogonal hashed vectors → Vendi ~ n.
        vecs = self.emb.embed_texts(["alpha beta", "gamma delta", "epsilon zeta"])
        self.assertGreater(embeddings.vendi_score(vecs), 2.5)

    def test_mean_pairwise_distance_identical_is_zero(self):
        vecs = self.emb.embed_texts(["x y z"] * 4)
        self.assertAlmostEqual(embeddings.mean_pairwise_distance(vecs), 0.0, places=4)

    def test_embedding_drift_shape(self):
        vecs = self.emb.embed_texts(["start state", "middle state", "end state"])
        drift = embeddings.embedding_drift(vecs)
        self.assertEqual(len(drift["steps"]), 2)
        self.assertGreaterEqual(drift["path_length"], 0.0)
        self.assertIn("endpoint_distance", drift)


class TestPersonaLoaders(unittest.TestCase):
    def test_load_json_list_and_sim_dir(self):
        with tempfile.TemporaryDirectory() as d:
            data = [{"username": "u1", "persona": "p1", "mbti": "INTJ"}]
            with open(os.path.join(d, "reddit_profiles.json"), "w", encoding="utf-8") as f:
                json.dump(data, f)
            loaded = personas.load_profiles_from_sim_dir(d)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["mbti"], "INTJ")

    def test_load_csv(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "twitter_profiles.csv")
            with open(path, "w", encoding="utf-8") as f:
                f.write("username,persona,interested_topics\n")
                f.write("u1,a builder,ai;policy\n")
            loaded = personas.load_profiles(path)
            self.assertEqual(loaded[0]["interested_topics"], "ai;policy")

    def test_persona_texts(self):
        profs = [{"persona": "builder", "bio": "of systems"}, {"persona": "healer"}]
        texts = personas.persona_texts(profs)
        self.assertEqual(texts, ["builder of systems", "healer"])


if __name__ == "__main__":
    unittest.main()
