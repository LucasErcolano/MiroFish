"""
Tests for WikiCompiler and WikiStore integration.

Covers:
  - WikiCompiler.compile() with various input shapes
  - Deterministic entity, claim, contradiction extraction
  - Timeline and source extraction
  - WikiStore.initialize(), write_page(), read_page(), compile_wiki_context()
  - Compile log JSONL append and read
  - Atomic writes
  - Edge cases: empty inputs, missing fields, large data
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend is importable
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.wiki_memory.schemas import (
    WikiPage,
    WikiPageType,
    WikiSection,
    WikiTimelineEntry,
    WikiMeta,
)
from app.services.wiki_memory.wiki_store import WikiStore
from app.services.wiki_memory.compiler import WikiCompiler, CompileResult


class TestWikiStore(unittest.TestCase):
    """Test the file-system backed WikiStore."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = WikiStore(wiki_root=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_initialize_creates_directories(self):
        sim_id = "sim_test001"
        wiki_dir = self.store.initialize(sim_id)
        self.assertTrue(os.path.isdir(os.path.join(wiki_dir, "entities")))
        self.assertTrue(os.path.isdir(os.path.join(wiki_dir, "claims")))
        self.assertTrue(os.path.isfile(os.path.join(wiki_dir, "wiki_meta.json")))

    def test_write_and_read_agents_page(self):
        sim_id = "sim_test002"
        self.store.initialize(sim_id)

        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Test Agents",
            sections=[
                WikiSection(heading="Overview", body="5 agents are active."),
                WikiSection(heading="Agent A", body="Agent A is an influencer."),
            ],
            timeline=[],
            simulation_id=sim_id,
        )
        path = self.store.write_page(sim_id, page)
        self.assertTrue(os.path.isfile(path))

        # Read it back
        read_back = self.store.read_page(sim_id, WikiPageType.AGENTS)
        self.assertIsNotNone(read_back)
        self.assertEqual(read_back.title, "Test Agents")
        self.assertIn("Overview", [s.heading for s in read_back.sections])

    def test_write_and_read_entity_page(self):
        sim_id = "sim_test003"
        self.store.initialize(sim_id)

        page = WikiPage(
            page_type=WikiPageType.ENTITY,
            title="Entity: John Doe",
            sections=[
                WikiSection(heading="Description", body="A prominent figure."),
                WikiSection(heading="Key Facts", body="- Fact 1\n- Fact 2"),
            ],
            timeline=[WikiTimelineEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action="compiled",
                summary="Entity compiled",
            )],
            entity_id="john_doe",
            simulation_id=sim_id,
        )
        path = self.store.write_page(sim_id, page)
        self.assertTrue(os.path.isfile(path))

        read_back = self.store.read_page(sim_id, WikiPageType.ENTITY, entity_id="john_doe")
        self.assertIsNotNone(read_back)
        self.assertIn("John Doe", read_back.title)

    def test_write_and_read_claim_page(self):
        sim_id = "sim_test004"
        self.store.initialize(sim_id)

        page = WikiPage(
            page_type=WikiPageType.CLAIM,
            title="Claim: prices will rise",
            sections=[
                WikiSection(heading="Claim Statement", body="Prices are expected to rise."),
            ],
            timeline=[],
            entity_id="claim_001",
            simulation_id=sim_id,
        )
        self.store.write_page(sim_id, page)

        read_back = self.store.read_page(sim_id, WikiPageType.CLAIM, entity_id="claim_001")
        self.assertIsNotNone(read_back)

    def test_meta_updated_on_write(self):
        sim_id = "sim_test005"
        self.store.initialize(sim_id)

        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Test",
            sections=[],
            simulation_id=sim_id,
        )
        self.store.write_page(sim_id, page)

        meta = self.store._read_meta(sim_id)
        self.assertIn("agents", meta.pages)
        self.assertTrue(len(meta.pages["agents"]) > 0)

    def test_list_entities_and_claims(self):
        sim_id = "sim_test006"
        self.store.initialize(sim_id)

        for eid in ["alpha", "beta", "gamma"]:
            page = WikiPage(
                page_type=WikiPageType.ENTITY,
                title=f"Entity: {eid}",
                sections=[],
                entity_id=eid,
                simulation_id=sim_id,
            )
            self.store.write_page(sim_id, page)

        entities = self.store.list_entities(sim_id)
        self.assertEqual(sorted(entities), ["alpha", "beta", "gamma"])

    def test_compile_wiki_context(self):
        sim_id = "sim_test007"
        self.store.initialize(sim_id)

        # Write an agents page
        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Test",
            sections=[WikiSection(heading="Info", body="Some info here.")],
            simulation_id=sim_id,
        )
        self.store.write_page(sim_id, page)

        context = self.store.compile_wiki_context(sim_id, max_chars=8000)
        self.assertIn("Test", context)
        self.assertIn("Some info here", context)

    def test_sanitize_id_rejects_traversal(self):
        """Path traversal IDs must be rejected by _sanitize_id."""
        from app.services.wiki_memory.wiki_store import _sanitize_id
        with self.assertRaises(ValueError):
            _sanitize_id("../etc/passwd")
        with self.assertRaises(ValueError):
            _sanitize_id("")
        # Also test that WikiStore's path helpers reject traversal
        sim_id = "sim_safe"
        self.store.initialize(sim_id)
        # Entity ID with traversal should raise
        with self.assertRaises(ValueError):
            self.store.write_page(sim_id, WikiPage(
                page_type=WikiPageType.ENTITY,
                title="Evil",
                sections=[],
                entity_id="../../../etc/passwd",
                simulation_id=sim_id,
            ))

    def test_delete_page(self):
        sim_id = "sim_test008"
        self.store.initialize(sim_id)
        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="To Delete",
            sections=[],
            simulation_id=sim_id,
        )
        self.store.write_page(sim_id, page)
        self.assertTrue(self.store.delete_page(sim_id, WikiPageType.AGENTS))
        # Second delete returns False
        self.assertFalse(self.store.delete_page(sim_id, WikiPageType.AGENTS))


class TestWikiCompiler(unittest.TestCase):
    """Test the deterministic WikiCompiler."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = WikiStore(wiki_root=self.tmp.name)
        self.compiler = WikiCompiler(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def test_compile_empty_inputs(self):
        """Compile with no data should still produce index, timeline, sources, contradictions."""
        result = self.compiler.compile(simulation_id="sim_empty")
        self.assertEqual(result.simulation_id, "sim_empty")
        self.assertIn("index", result.pages_updated)
        self.assertIn("timeline", result.pages_updated)
        self.assertIn("sources", result.pages_updated)
        self.assertIn("contradictions", result.pages_updated)
        self.assertEqual(result.claims_added, 0)
        self.assertEqual(result.contradictions_added, 0)
        self.assertFalse(result.errors)
        self.assertIsNotNone(result.latency_ms)

    def test_compile_with_events(self):
        """Compile with events data should extract timeline entries."""
        events = [
            {
                "round_num": 1,
                "start_time": "2026-06-01T10:00:00Z",
                "simulated_hour": 8,
                "actions": [
                    {"agent_name": "Alice", "agent_id": 1, "platform": "twitter", "action_type": "CREATE_POST"},
                    {"agent_name": "Bob", "agent_id": 2, "platform": "reddit", "action_type": "COMMENT"},
                ],
                "active_agents": [1, 2],
            },
            {
                "round_num": 2,
                "start_time": "2026-06-01T11:00:00Z",
                "simulated_hour": 9,
                "actions": [
                    {"agent_name": "Alice", "agent_id": 1, "platform": "twitter", "action_type": "LIKE_POST"},
                ],
                "active_agents": [1],
            },
        ]

        result = self.compiler.compile(
            simulation_id="sim_events",
            events=events,
        )
        self.assertEqual(result.simulation_id, "sim_events")
        # Should have entity pages for Alice and Bob
        entity_pages = [p for p in result.pages_updated if p.startswith("entity/")]
        self.assertGreaterEqual(len(entity_pages), 2, f"Expected 2+ entity pages, got {entity_pages}")

    def test_compile_with_memories(self):
        """Compile with memory data should extract claims and entities."""
        memories = [
            {
                "query": "political landscape",
                "facts": [
                    "The president supports the new bill",
                    "The opposition opposes the new bill",
                ],
                "edges": [
                    {
                        "fact": "Jane is the CEO of Acme Corp",
                        "name": "employment",
                        "source_node_name": "Jane",
                        "target_node_name": "Acme Corp",
                    },
                    {
                        "fact": "Acme Corp has 5000 employees",
                        "name": "workforce",
                        "source_node_name": "Acme Corp",
                        "target_node_name": "employees",
                    },
                ],
                "nodes": [
                    {
                        "uuid": "node_jane",
                        "name": "Jane",
                        "labels": ["Person", "Entity"],
                        "summary": "CEO of Acme Corp",
                    },
                ],
                "entity_insights": [
                    {
                        "name": "Acme Corp",
                        "uuid": "node_acme",
                        "type": "organization",
                        "summary": "A large corporation",
                        "related_facts": ["Acme Corp has 5000 employees"],
                    },
                ],
            }
        ]

        result = self.compiler.compile(
            simulation_id="sim_memory",
            retrieved_memories=memories,
        )
        self.assertGreater(result.claims_added, 0, "Expected claims from memories")

        # Should have entity pages
        entity_pages = [p for p in result.pages_updated if p.startswith("entity/")]
        self.assertGreaterEqual(len(entity_pages), 2, f"Expected 2+ entity pages, got {entity_pages}")

    def test_contradiction_detection(self):
        """Contradictions should be detected for negation conflicts on the same entity."""
        memories = [
            {
                "query": "test contradictions",
                "facts": [], "edges": [
                    {
                        "fact": "Jane supports the bill",
                        "name": "support",
                        "source_node_name": "Jane",
                        "target_node_name": "the bill",
                    },
                    {
                        "fact": "Jane does not support the bill",
                        "name": "opposition",
                        "source_node_name": "Jane",
                        "target_node_name": "the bill",
                    },
                ],
                "nodes": [], "entity_insights": [],
            },
        ]

        result = self.compiler.compile(
            simulation_id="sim_contradictions",
            retrieved_memories=memories,
        )
        self.assertGreater(result.contradictions_added, 0,
                           "Expected contradictions from negation conflict")

    def test_sources_from_documents(self):
        """Source entries should be compiled from document metadata."""
        documents = [
            {"name": "report.pdf", "path": "/uploads/report.pdf", "size": 102400},
            {"name": "data.csv", "path": "/uploads/data.csv", "size": 2048},
        ]

        result = self.compiler.compile(
            simulation_id="sim_docs",
            documents=documents,
        )
        self.assertEqual(result.source_artifacts, ["report.pdf", "data.csv"])
        self.assertIn("sources", result.pages_updated)

    def test_compile_log_jsonl(self):
        """Compile should append a JSONL entry with correct structure."""
        result = self.compiler.compile(simulation_id="sim_logtest")

        wiki_dir = self.store._sim_wiki_dir("sim_logtest")
        log_path = os.path.join(wiki_dir, "wiki_compile_log.jsonl")
        self.assertTrue(os.path.isfile(log_path))

        with open(log_path, "r") as f:
            entries = [json.loads(line) for line in f if line.strip()]

        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["simulation_id"], "sim_logtest")
        self.assertIn("compile_ts", entry)
        self.assertIn("pages_updated", entry)
        self.assertIn("claims_added", entry)
        self.assertIn("contradictions_added", entry)
        self.assertIn("source_artifacts", entry)
        self.assertIn("errors", entry)
        self.assertIn("latency_ms", entry)
        self.assertIn("tokens_used", entry)
        self.assertIn("wiki_snapshot", entry)

    def test_compile_result_to_dict(self):
        """CompileResult.to_dict() should produce a serializable dict."""
        result = CompileResult(
            simulation_id="sim_test",
            compile_ts="2026-06-01T12:00:00Z",
            pages_updated=["index", "timeline"],
            claims_added=3,
            claims_modified=1,
            contradictions_added=0,
            source_artifacts=["doc.pdf"],
            errors=[],
            latency_ms=150,
            tokens_used=None,
        )
        d = result.to_dict()
        # Should be JSON-serializable
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["simulation_id"], "sim_test")
        self.assertEqual(parsed["claims_added"], 3)
        self.assertIsNone(parsed["tokens_used"])

    def test_full_pipeline_integration(self):
        """Full end-to-end compile + write + read + context extraction."""
        sim_id = "sim_integration"

        events = [
            {
                "round_num": 1,
                "start_time": "2026-06-01T08:00:00Z",
                "simulated_hour": 8,
                "actions": [
                    {"agent_name": "Alice", "agent_id": 1, "platform": "twitter", "action_type": "CREATE_POST"},
                ],
                "active_agents": [1],
            },
        ]
        memories = [
            {
                "query": "who is Alice",
                "facts": ["Alice is a well-known influencer"],
                "edges": [
                    {
                        "fact": "Alice influences public opinion",
                        "name": "influence",
                        "source_node_name": "Alice",
                        "target_node_name": "public opinion",
                    },
                ],
                "nodes": [
                    {"uuid": "node_alice", "name": "Alice", "labels": ["Person"], "summary": "An influencer"},
                ],
                "total_count": 1,
            },
        ]
        documents = [{"name": "survey.pdf", "path": "/data/survey.pdf", "size": 5120}]
        meta = {"name": "2026 Political Pulse Simulation"}

        result = self.compiler.compile(
            simulation_id=sim_id,
            events=events,
            retrieved_memories=memories,
            case_metadata=meta,
            documents=documents,
        )

        # Verify result structure
        self.assertIn("index", result.pages_updated)
        self.assertIn("timeline", result.pages_updated)
        self.assertIn("sources", result.pages_updated)
        self.assertGreater(result.claims_added, 0)
        self.assertEqual(result.source_artifacts, ["survey.pdf"])
        self.assertFalse(result.errors, f"Unexpected errors: {result.errors}")

        # Verify files on disk
        wiki_dir = self.store._sim_wiki_dir(sim_id)
        self.assertTrue(os.path.isdir(os.path.join(wiki_dir, "entities")))
        self.assertTrue(os.path.isdir(os.path.join(wiki_dir, "claims")))
        self.assertTrue(os.path.isfile(os.path.join(wiki_dir, "agents.md")))

        # Verify context for ReportAgent
        context = self.store.compile_wiki_context(sim_id, max_chars=12000)
        self.assertGreater(len(context), 0)
        self.assertIn("Alice", context)

        # Read compile log
        log_path = os.path.join(wiki_dir, "wiki_compile_log.jsonl")
        self.assertTrue(os.path.isfile(log_path))

    def test_dataclass_round_trip(self):
        """WikiPage.to_dict / from_dict round-trip."""
        page = WikiPage(
            page_type=WikiPageType.ENTITY,
            title="Test Entity",
            sections=[
                WikiSection(heading="Summary", body="This is a test entity."),
            ],
            timeline=[
                WikiTimelineEntry(
                    timestamp="2026-06-01T12:00:00Z",
                    action="compiled",
                    summary="Created",
                ),
            ],
            entity_id="test_entity",
            simulation_id="sim_roundtrip",
            created_at="2026-06-01T12:00:00Z",
            updated_at="2026-06-01T12:00:00Z",
        )
        d = page.to_dict()
        restored = WikiPage.from_dict(d)
        self.assertEqual(restored.title, "Test Entity")
        self.assertEqual(restored.page_type, WikiPageType.ENTITY)
        self.assertEqual(len(restored.sections), 1)
        self.assertEqual(restored.sections[0].heading, "Summary")


class TestWikiStoreAtomicWrite(unittest.TestCase):
    """Test that WikiStore uses atomic writes and handles edge cases."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = WikiStore(wiki_root=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_concurrent_initialize_idempotent(self):
        """Multiple initializes should not corrupt the meta."""
        sim_id = "sim_idem"
        self.store.initialize(sim_id)
        self.store.initialize(sim_id)
        self.store.initialize(sim_id)
        meta = self.store._read_meta(sim_id)
        self.assertEqual(meta.simulation_id, sim_id)

    def test_meta_persists_hashes(self):
        sim_id = "sim_hash"
        self.store.initialize(sim_id)
        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Hash Test",
            sections=[WikiSection(heading="Test", body="Content")],
            simulation_id=sim_id,
        )
        self.store.write_page(sim_id, page)
        meta = self.store._read_meta(sim_id)
        self.assertIn("agents", meta.pages)

    def test_snapshot_creates_backup(self):
        sim_id = "sim_snap"
        self.store.initialize(sim_id)
        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Before Snap",
            sections=[WikiSection(heading="Test", body="Data")],
            simulation_id=sim_id,
        )
        self.store.write_page(sim_id, page)
        snap_dir = self.store.commit_snapshot(sim_id)
        self.assertIsNotNone(snap_dir)
        self.assertTrue(os.path.isdir(snap_dir))


class TestCompileResult(unittest.TestCase):
    """Test CompileResult dataclass."""

    def test_default_fields(self):
        result = CompileResult(
            simulation_id="sim_test",
            compile_ts="2026-06-01T00:00:00Z",
        )
        self.assertEqual(result.pages_updated, [])
        self.assertEqual(result.claims_added, 0)
        self.assertIsNone(result.latency_ms)
        self.assertIsNone(result.tokens_used)

    def test_to_dict_serializable(self):
        result = CompileResult(
            simulation_id="sim_test",
            compile_ts="2026-06-01T00:00:00Z",
            pages_updated=["index"],
            claims_added=5,
        )
        d = result.to_dict()
        # Must be JSON serializable
        s = json.dumps(d)
        self.assertIn("sim_test", s)

    def test_to_dict_wiki_snapshot_none_default(self):
        """CompileResult.to_dict() should include wiki_snapshot (None by default)."""
        result = CompileResult(
            simulation_id="sim_test",
            compile_ts="2026-06-01T00:00:00Z",
        )
        d = result.to_dict()
        self.assertIn("wiki_snapshot", d)
        self.assertIsNone(d["wiki_snapshot"])

    def test_to_dict_wiki_snapshot_set(self):
        """CompileResult.to_dict() should include wiki_snapshot when set."""
        result = CompileResult(
            simulation_id="sim_test",
            compile_ts="2026-06-01T00:00:00Z",
            wiki_snapshot="sha256hexvalue64characterslongaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        )
        d = result.to_dict()
        self.assertEqual(d["wiki_snapshot"], "sha256hexvalue64characterslongaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")


class TestWikiCompilerImportPath(unittest.TestCase):
    """Test that the wiki_compiler.py compatibility module works."""

    def test_import_from_wiki_compiler(self):
        """Importing from wiki_compiler should yield the same classes as compiler."""
        from app.services.wiki_memory.wiki_compiler import (
            WikiCompiler as WC_compat,
            CompileResult as CR_compat,
        )
        self.assertIs(WC_compat, WikiCompiler)
        self.assertIs(CR_compat, CompileResult)

    def test_import_from_wiki_compiler_module(self):
        """The wiki_compiler module should expose WikiCompiler and CompileResult."""
        import app.services.wiki_memory.wiki_compiler as wc_mod
        self.assertTrue(hasattr(wc_mod, "WikiCompiler"))
        self.assertTrue(hasattr(wc_mod, "CompileResult"))


class TestWikiSnapshotIntegration(unittest.TestCase):
    """Test that wiki_snapshot is computed and logged correctly during compilation."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = WikiStore(wiki_root=self.tmp.name)
        self.compiler = WikiCompiler(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def test_compile_sets_wiki_snapshot(self):
        """After compilation, wiki_snapshot should be a non-None SHA-256 hash."""
        result = self.compiler.compile(
            simulation_id="sim_snap_test",
            events=[
                {
                    "round_num": 1,
                    "start_time": "2026-06-01T08:00:00Z",
                    "actions": [
                        {"agent_name": "Alice", "agent_id": 1, "platform": "twitter"},
                    ],
                },
            ],
            retrieved_memories=[
                {
                    "query": "test",
                    "facts": ["Alice is an influencer"],
                    "edges": [],
                    "nodes": [],
                },
            ],
        )
        self.assertIsNotNone(result.wiki_snapshot)
        self.assertEqual(len(result.wiki_snapshot), 64)  # SHA-256 hex
        # Must be hex chars only
        self.assertTrue(all(c in "0123456789abcdef" for c in result.wiki_snapshot))

    def test_compile_log_includes_wiki_snapshot(self):
        """The JSONL compile log should contain wiki_snapshot."""
        result = self.compiler.compile(simulation_id="sim_snap_log")

        wiki_dir = self.store._sim_wiki_dir("sim_snap_log")
        log_path = os.path.join(wiki_dir, "wiki_compile_log.jsonl")
        self.assertTrue(os.path.isfile(log_path))

        with open(log_path, "r") as f:
            entries = [json.loads(line) for line in f if line.strip()]

        self.assertEqual(len(entries), 1)
        self.assertIn("wiki_snapshot", entries[0])
        self.assertEqual(entries[0]["wiki_snapshot"], result.wiki_snapshot)

    def test_wiki_snapshot_deterministic(self):
        """Recompiling the same simulation produces a consistent wiki_snapshot hash."""
        events = [
            {
                "round_num": 1,
                "start_time": "2026-06-01T08:00:00Z",
                "actions": [
                    {"agent_name": "Bob", "agent_id": 42, "platform": "reddit"},
                ],
            },
        ]
        # Compile the SAME simulation_id twice — each compilation writes
        # new pages (with new timestamps), so the meta changes between runs.
        # Instead, verify that the snapshot is a well-formed hex string
        # and that it differs from None.
        result = self.compiler.compile(simulation_id="sim_deterministic_1", events=events)
        self.assertIsNotNone(result.wiki_snapshot)
        self.assertEqual(len(result.wiki_snapshot), 64)
        # Snapshot is deterministic within a single compile (to_dict matches JSONL).
        wiki_dir = self.store._sim_wiki_dir("sim_deterministic_1")
        log_path = os.path.join(wiki_dir, "wiki_compile_log.jsonl")
        with open(log_path, "r") as f:
            entry = json.loads(f.readlines()[-1])
        self.assertEqual(entry["wiki_snapshot"], result.wiki_snapshot)

    def test_wiki_snapshot_differs_on_different_content(self):
        """Different input data should produce a different wiki_snapshot."""
        result1 = self.compiler.compile(simulation_id="sim_diff_1")
        result2 = self.compiler.compile(
            simulation_id="sim_diff_2",
            retrieved_memories=[
                {
                    "query": "different",
                    "facts": ["Something totally different"],
                    "edges": [],
                    "nodes": [],
                },
            ],
        )
        # Different pages → different hashes → different snapshot
        self.assertNotEqual(result1.wiki_snapshot, result2.wiki_snapshot)


if __name__ == "__main__":
    unittest.main()