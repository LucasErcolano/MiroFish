"""
Additional tests for wiki_memory module — filling gaps in coverage.

Covers:
  - Wiki init edge cases (re-init, nonexistent read, double init)
  - Safe page writes (overwrite, entity without entity_id, claim without entity_id)
  - Timeline update edge cases (append to non-existent page, multiple entries)
  - Claim generation (from edges, from semantic_facts, from facts, dedup)
  - Compiler edge cases (normalise_list, dataclass/attribute input)
  - build_wiki_context_for_report with compile fallback
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Add backend to sys.path
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.wiki_memory.schemas import (
    WikiMeta,
    WikiPage,
    WikiPageType,
    WikiSection,
    WikiTimelineEntry,
)
from app.services.wiki_memory.wiki_store import WikiStore, _sanitize_id
from app.services.wiki_memory.compiler import WikiCompiler, CompileResult


# ---------------------------------------------------------------------------
# Wiki init edge cases
# ---------------------------------------------------------------------------

class TestWikiInitEdgeCases(unittest.TestCase):
    """Edge cases around WikiStore.initialize()."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = WikiStore(wiki_root=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_initialize_creates_entities_and_claims_dirs(self):
        """Init creates both entities/ and claims/ subdirectories."""
        wiki_dir = self.store.initialize("sim_edge1")
        self.assertTrue(os.path.isdir(os.path.join(wiki_dir, "entities")))
        self.assertTrue(os.path.isdir(os.path.join(wiki_dir, "claims")))

    def test_initialize_creates_meta_json(self):
        """Init writes wiki_meta.json with simulation_id."""
        self.store.initialize("sim_edge2")
        meta_path = os.path.join(
            self.tmp.name, "sim_edge2", "wiki", "wiki_meta.json"
        )
        self.assertTrue(os.path.exists(meta_path))
        with open(meta_path) as f:
            meta = json.load(f)
        self.assertEqual(meta["simulation_id"], "sim_edge2")

    def test_double_initialize_idempotent(self):
        """Calling initialize twice on same sim_id does not corrupt data."""
        self.store.initialize("sim_double")
        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Persistent",
            sections=[WikiSection(heading="Test", body="data")],
            simulation_id="sim_double",
        )
        self.store.write_page("sim_double", page)

        # Re-initialize
        self.store.initialize("sim_double")

        # Data should still be there
        loaded = self.store.read_agents_page("sim_double")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.title, "Persistent")

    def test_initialize_rejects_path_traversal(self):
        """Path traversal in simulation_id must be rejected."""
        with self.assertRaises(ValueError):
            self.store.initialize("../../etc")

    def test_initialize_different_sims_independent(self):
        """Two different simulation IDs produce independent directories."""
        dir1 = self.store.initialize("sim_a")
        dir2 = self.store.initialize("sim_b")
        self.assertNotEqual(dir1, dir2)
        self.assertTrue(os.path.isdir(dir1))
        self.assertTrue(os.path.isdir(dir2))


# ---------------------------------------------------------------------------
# Safe page write edge cases
# ---------------------------------------------------------------------------

class TestSafePageWrites(unittest.TestCase):
    """Edge cases around write_page safety and validation."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = WikiStore(wiki_root=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_entity_page_requires_entity_id(self):
        """ENTITY page write must raise ValueError if entity_id is missing."""
        self.store.initialize("sim_safe1")
        page = WikiPage(
            page_type=WikiPageType.ENTITY,
            title="No ID Entity",
            sections=[WikiSection(heading="Desc", body="Missing entity_id")],
        )
        with self.assertRaises(ValueError):
            self.store.write_page("sim_safe1", page)

    def test_claim_page_requires_entity_id(self):
        """CLAIM page write must raise ValueError if entity_id is missing."""
        self.store.initialize("sim_safe2")
        page = WikiPage(
            page_type=WikiPageType.CLAIM,
            title="No ID Claim",
            sections=[WikiSection(heading="Claim", body="Missing entity_id")],
        )
        with self.assertRaises(ValueError):
            self.store.write_page("sim_safe2", page)

    def test_overwrite_agents_page(self):
        """Writing an agents page twice should overwrite the file."""
        self.store.initialize("sim_safe3")
        page1 = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Version 1",
            sections=[WikiSection(heading="V1", body="First version")],
            simulation_id="sim_safe3",
        )
        self.store.write_page("sim_safe3", page1)

        page2 = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Version 2",
            sections=[WikiSection(heading="V2", body="Second version")],
            simulation_id="sim_safe3",
        )
        self.store.write_page("sim_safe3", page2)

        loaded = self.store.read_agents_page("sim_safe3")
        self.assertEqual(loaded.title, "Version 2")

    def test_overwrite_entity_page(self):
        """Writing the same entity page twice should overwrite."""
        self.store.initialize("sim_safe4")
        page1 = WikiPage(
            page_type=WikiPageType.ENTITY,
            title="Entity V1",
            sections=[WikiSection(heading="Desc", body="First")],
            entity_id="ent1",
            simulation_id="sim_safe4",
        )
        self.store.write_page("sim_safe4", page1)

        page2 = WikiPage(
            page_type=WikiPageType.ENTITY,
            title="Entity V2",
            sections=[WikiSection(heading="Desc", body="Second")],
            entity_id="ent1",
            simulation_id="sim_safe4",
        )
        self.store.write_page("sim_safe4", page2)

        loaded = self.store.read_entity_page("sim_safe4", "ent1")
        self.assertEqual(loaded.title, "Entity V2")

    def test_read_uninitialized_sim_returns_none(self):
        """Reading a page from a non-existent sim directory returns None."""
        result = self.store.read_agents_page("sim_nonexistent")
        self.assertIsNone(result)

    def test_entity_read_requires_entity_id(self):
        """ENTITY page read must raise ValueError if entity_id is missing."""
        with self.assertRaises(ValueError):
            self.store.read_page("sim_any", WikiPageType.ENTITY)

    def test_claim_read_requires_entity_id(self):
        """CLAIM page read must raise ValueError if entity_id is missing."""
        with self.assertRaises(ValueError):
            self.store.read_page("sim_any", WikiPageType.CLAIM)


# ---------------------------------------------------------------------------
# Timeline update edge cases
# ---------------------------------------------------------------------------

class TestTimelineEdgeCases(unittest.TestCase):
    """Timeline-specific edge cases not covered by the main test suite."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = WikiStore(wiki_root=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_append_timeline_creates_page_from_template(self):
        """Appending a timeline to a non-existent page creates it from template first."""
        self.store.initialize("sim_tl1")
        entry = self.store.append_timeline(
            "sim_tl1",
            WikiPageType.AGENTS,
            action="created",
            summary="First entry on empty page",
        )
        self.assertEqual(entry.action, "created")

        loaded = self.store.read_agents_page("sim_tl1")
        self.assertIsNotNone(loaded)
        self.assertEqual(len(loaded.timeline), 1)
        self.assertEqual(loaded.timeline[0].action, "created")

    def test_append_multiple_timeline_entries(self):
        """Multiple timeline appends accumulate entries."""
        self.store.initialize("sim_tl2")
        self.store.create_from_template("sim_tl2", WikiPageType.AGENTS, title="TL Test")

        entries = []
        for i in range(5):
            entry = self.store.append_timeline(
                "sim_tl2",
                WikiPageType.AGENTS,
                action=f"round_{i}",
                summary=f"Update {i}",
            )
            entries.append(entry)

        loaded = self.store.read_agents_page("sim_tl2")
        self.assertEqual(len(loaded.timeline), 5)
        actions = [e.action for e in loaded.timeline]
        self.assertEqual(actions, ["round_0", "round_1", "round_2", "round_3", "round_4"])

    def test_timeline_with_metadata(self):
        """Timeline entry preserves metadata dict."""
        self.store.initialize("sim_tl3")
        self.store.create_from_template("sim_tl3", WikiPageType.AGENTS)

        entry = self.store.append_timeline(
            "sim_tl3",
            WikiPageType.AGENTS,
            action="compiled",
            summary="Wiki compiled",
            metadata={"agent": "ReportAgent", "pages": 3},
        )
        self.assertEqual(entry.metadata["agent"], "ReportAgent")
        self.assertEqual(entry.metadata["pages"], 3)

    def test_append_timeline_entity_page(self):
        """Timeline can be appended to an entity page."""
        self.store.initialize("sim_tl4")
        entity = WikiPage(
            page_type=WikiPageType.ENTITY,
            title="Entity: carol",
            sections=[WikiSection(heading="Desc", body="Carol is an analyst")],
            entity_id="carol",
            simulation_id="sim_tl4",
        )
        self.store.write_page("sim_tl4", entity)

        entry = self.store.append_timeline(
            "sim_tl4",
            WikiPageType.ENTITY,
            action="updated",
            summary="Added new facts",
            entity_id="carol",
        )
        self.assertEqual(entry.action, "updated")

        loaded = self.store.read_entity_page("sim_tl4", "carol")
        self.assertEqual(len(loaded.timeline), 1)


# ---------------------------------------------------------------------------
# Claim generation edge cases (via compiler)
# ---------------------------------------------------------------------------

class TestClaimGeneration(unittest.TestCase):
    """Test claim extraction and deduplication from WikiCompiler."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = WikiStore(wiki_root=self.tmp.name)
        self.compiler = WikiCompiler(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def test_claims_from_facts(self):
        """Plain text facts in memory dicts are extracted as claims."""
        memories = [
            {
                "facts": [
                    "The market is volatile",
                    "Interest rates rose 2%",
                ],
            },
        ]
        result = self.compiler.compile("sim_cl1", retrieved_memories=memories)
        # Should have at least 2 claims (one per fact)
        self.assertGreaterEqual(result.claims_added, 2)

    def test_claims_from_semantic_facts(self):
        """semantic_facts in memory dicts are extracted as claims."""
        memories = [
            {
                "semantic_facts": [
                    "Inflation decreased in Q3",
                    "Consumer confidence is high",
                ],
            },
        ]
        result = self.compiler.compile("sem1", retrieved_memories=memories)
        self.assertGreaterEqual(result.claims_added, 2)

    def test_claim_deduplication(self):
        """Duplicate facts across memories should not produce duplicate claims."""
        memories = [
            {"facts": ["Jane is the CEO"]},
            {"facts": ["Jane is the CEO"]},
        ]
        result = self.compiler.compile("sem2", retrieved_memories=memories)
        # Same fact text should only produce one claim
        self.assertLessEqual(result.claims_added, 1)

    def test_claims_from_edges(self):
        """Zep edge facts produce claims with entity references."""
        memories = [
            {
                "edges": [
                    {
                        "fact": "Jane manages the marketing team",
                        "name": "manages",
                        "source_node_name": "Jane",
                        "target_node_name": "marketing_team",
                    },
                ],
            },
        ]
        result = self.compiler.compile("sem3", retrieved_memories=memories)
        self.assertGreaterEqual(result.claims_added, 1)
        # The claim page should have been written
        wiki_dir = os.path.join(self.tmp.name, "sem3", "wiki")
        claims_dir = os.path.join(wiki_dir, "claims")
        self.assertTrue(os.path.isdir(claims_dir))
        claim_files = os.listdir(claims_dir)
        self.assertGreaterEqual(len(claim_files), 1)

    def test_empty_events_and_memories(self):
        """Compile with no data still produces structural pages (index, timeline, etc.)."""
        result = self.compiler.compile("sem_empty")
        self.assertIn("index", result.pages_updated)
        self.assertIn("timeline", result.pages_updated)
        self.assertIn("sources", result.pages_updated)
        self.assertIn("contradictions", result.pages_updated)
        self.assertEqual(result.claims_added, 0)
        self.assertEqual(result.contradictions_added, 0)


# ---------------------------------------------------------------------------
# Compiler normalisation edge cases
# ---------------------------------------------------------------------------

class TestCompilerNormalisation(unittest.TestCase):
    """Test _normalise_list with various input types."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = WikiStore(wiki_root=self.tmp.name)
        self.compiler = WikiCompiler(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def test_normalise_dicts(self):
        """Plain dicts pass through unchanged."""
        result = self.compiler._normalise_list([{"a": 1}, {"b": 2}])
        self.assertEqual(result, [{"a": 1}, {"b": 2}])

    def test_normalise_dataclass_like_objects(self):
        """Objects with __dict__ are converted."""
        class SimpleObj:
            def __init__(self, x):
                self.x = x

        result = self.compiler._normalise_list([SimpleObj(42)])
        self.assertEqual(result, [{"x": 42}])

    def test_normalise_to_dict_objects(self):
        """Objects with to_dict() are converted via that method."""
        class ToDictObj:
            def __init__(self, val):
                self.val = val
            def to_dict(self):
                return {"val": self.val}

        result = self.compiler._normalise_list([ToDictObj("hello")])
        self.assertEqual(result, [{"val": "hello"}])

    def test_normalise_fallback_to_str(self):
        """Non-dict, non-dataclass objects fall back to {'raw': str(obj)}."""
        result = self.compiler._normalise_list([42, True])
        self.assertEqual(len(result), 2)
        self.assertIn("raw", result[0])
        self.assertEqual(result[0]["raw"], "42")

    def test_normalise_none_returns_empty(self):
        """None input returns empty list."""
        result = self.compiler._normalise_list(None)
        self.assertEqual(result, [])

    def test_normalise_empty_list(self):
        """Empty list returns empty list."""
        result = self.compiler._normalise_list([])
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# CompileResult serialization
# ---------------------------------------------------------------------------

class TestCompileResultSerialization(unittest.TestCase):
    """Additional CompileResult serialization tests."""

    def test_to_dict_all_fields(self):
        """All fields serialize correctly to JSON-compatible dict."""
        result = CompileResult(
            simulation_id="sim_cr",
            compile_ts="2026-06-01T12:00:00Z",
            pages_updated=["index", "agents"],
            claims_added=3,
            claims_modified=1,
            contradictions_added=2,
            source_artifacts=["doc1.pdf", "doc2.pdf"],
            errors=["warning: skipped empty round"],
            latency_ms=150,
            tokens_used=None,
        )
        d = result.to_dict()
        self.assertEqual(d["simulation_id"], "sim_cr")
        self.assertEqual(d["claims_added"], 3)
        self.assertEqual(d["claims_modified"], 1)
        self.assertEqual(d["contradictions_added"], 2)
        self.assertIsNone(d["tokens_used"])
        # Should be JSON serializable
        json_str = json.dumps(d)
        self.assertIsInstance(json_str, str)

    def test_compile_result_defaults(self):
        """Default values for optional fields."""
        result = CompileResult(
            simulation_id="sim_defaults",
            compile_ts="2026-06-01T12:00:00Z",
        )
        self.assertEqual(result.pages_updated, [])
        self.assertEqual(result.claims_added, 0)
        self.assertEqual(result.errors, [])
        self.assertIsNone(result.latency_ms)
        self.assertIsNone(result.tokens_used)


# ---------------------------------------------------------------------------
# build_wiki_context_for_report compile fallback
# ---------------------------------------------------------------------------

class TestBuildWikiContextCompileFallback(unittest.TestCase):
    """Test that build_wiki_context_for_report compiles from raw data when no
    existing pages exist."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wiki_root = os.path.join(self.tmp.name, "simulations")
        os.makedirs(self.wiki_root, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_fallback_compiles_from_events(self):
        """When no wiki pages exist but events are provided, compilation runs and returns context."""
        from app.services.wiki_memory import build_wiki_context_for_report

        events = [
            {
                "round_num": 1,
                "actions": [
                    {"agent_name": "AgentX", "agent_id": "ax1", "platform": "weibo"},
                ],
            },
        ]
        result = build_wiki_context_for_report(
            "sim_new_compile",
            wiki_root=self.wiki_root,
            events=events,
            case_metadata={"name": "Test Case Fallback"},
        )
        self.assertIsNotNone(result)
        self.assertIn("AgentX", result)


if __name__ == "__main__":
    unittest.main()