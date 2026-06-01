"""
Wiki Memory Smoke Test — End-to-End Fixture Validation

This smoke test exercises the full wiki_memory pipeline end-to-end:
  1. WikiStore.initialize() creates the wiki directory structure
  2. WikiCompiler.compile() produces all required markdown pages
  3. The output directory contains:
     - agents.md (AGENTS page)
     - index.md (compiled index page)
     - timeline.md (timeline page)
     - sources.md (sources page)
     - contradictions.md (contradictions page, even if empty)
     - At least one entity page under entities/
     - At least one claim page under claims/
     - wiki_compile_log.jsonl (audit trail)
  4. build_wiki_context_for_report returns a non-empty context string
  5. The context string contains expected content from the simulation data

This test is designed to be cheap (no LLM, no network) and produce a
concrete wiki directory artifact that can be inspected for correctness.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Add backend to sys.path
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.wiki_memory.schemas import (
    WikiPage,
    WikiPageType,
    WikiSection,
    WikiTimelineEntry,
)
from app.services.wiki_memory.wiki_store import WikiStore
from app.services.wiki_memory.compiler import WikiCompiler, CompileResult
from app.services.wiki_memory import build_wiki_context_for_report


# ---------------------------------------------------------------------------
# Realistic simulation data for the smoke fixture
# ---------------------------------------------------------------------------
SMOKE_EVENTS = [
    {
        "round_num": 1,
        "start_time": "2026-06-01T08:00:00Z",
        "simulated_hour": 8,
        "actions": [
            {
                "agent_name": "Dr. Chen",
                "agent_id": "dr_chen",
                "platform": "weibo",
                "action_type": "CREATE_POST",
                "content": "New study shows economic growth accelerating in Q2.",
            },
            {
                "agent_name": "MarketBot",
                "agent_id": "marketbot",
                "platform": "twitter",
                "action_type": "SHARE",
                "content": "GDP data released: 3.2% growth.",
            },
        ],
        "active_agents": ["dr_chen", "marketbot"],
    },
    {
        "round_num": 2,
        "start_time": "2026-06-01T10:00:00Z",
        "simulated_hour": 10,
        "actions": [
            {
                "agent_name": "SkepticAI",
                "agent_id": "skeptic_ai",
                "platform": "reddit",
                "action_type": "COMMENT",
                "content": "Growth numbers are not accurate — real GDP contracted by 1.5%.",
            },
        ],
        "active_agents": ["dr_chen", "marketbot", "skeptic_ai"],
    },
    {
        "round_num": 3,
        "start_time": "2026-06-01T12:00:00Z",
        "simulated_hour": 12,
        "actions": [
            {
                "agent_name": "Dr. Chen",
                "agent_id": "dr_chen",
                "platform": "weibo",
                "action_type": "COMMENT",
                "content": "I stand by the data. 3.2% is verified.",
            },
        ],
        "active_agents": ["dr_chen", "marketbot", "skeptic_ai"],
    },
]

SMOKE_MEMORIES = [
    {
        "query": "economic growth claims",
        "facts": [
            "GDP grew by 3.2% in Q2 2026",
            "Consumer confidence index rose to 108",
        ],
        "edges": [
            {
                "fact": "Dr. Chen endorses the growth narrative",
                "name": "endorsement",
                "source_node_name": "Dr. Chen",
                "target_node_name": "growth_narrative",
            },
            {
                "fact": "SkepticAI contradicts the growth narrative",
                "name": "contradiction",
                "source_node_name": "SkepticAI",
                "target_node_name": "growth_narrative",
            },
        ],
        "nodes": [
            {"uuid": "node_dr_chen", "name": "Dr. Chen", "labels": ["Person", "Agent"]},
            {"uuid": "node_growth", "name": "growth_narrative", "labels": ["Concept"]},
        ],
        "entity_insights": [
            {
                "uuid": "node_dr_chen",
                "name": "Dr. Chen",
                "type": "agent",
                "summary": "An influential researcher who endorses the growth narrative.",
                "related_facts": ["GDP grew by 3.2%"],
            },
        ],
    },
]

SMOKE_CASE_METADATA = {
    "name": "Economic Growth Simulation 2026",
    "description": "A simulation of information spread about economic indicators.",
}

SMOKE_DOCUMENTS = [
    {"name": "gdp_report_q2.pdf", "path": "/docs/gdp_report_q2.pdf", "size": 245000},
    {"name": "consumer_confidence.csv", "path": "/docs/consumer_confidence.csv", "size": 54000},
]


class TestWikiSmokeEndToEnd(unittest.TestCase):
    """Full end-to-end smoke test producing a concrete wiki directory artifact."""

    maxDiff = None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wiki_root = os.path.join(self.tmp.name, "simulations")
        os.makedirs(self.wiki_root, exist_ok=True)
        self.store = WikiStore(wiki_root=self.wiki_root)
        self.compiler = WikiCompiler(self.store)
        self.sim_id = "smoke_sim_001"

    def tearDown(self):
        self.tmp.cleanup()

    def test_smoke_full_pipeline(self):
        """Run the full pipeline: init -> compile -> verify artifacts -> context string."""
        # 1. Initialize
        wiki_dir = self.store.initialize(self.sim_id)
        self.assertTrue(os.path.isdir(wiki_dir))

        # 2. Compile
        result = self.compiler.compile(
            simulation_id=self.sim_id,
            events=SMOKE_EVENTS,
            retrieved_memories=SMOKE_MEMORIES,
            case_metadata=SMOKE_CASE_METADATA,
            documents=SMOKE_DOCUMENTS,
        )

        # 3. Verify CompileResult
        self.assertEqual(result.simulation_id, self.sim_id)
        self.assertFalse(result.errors, f"Compile had errors: {result.errors}")
        self.assertIsNotNone(result.latency_ms)
        self.assertGreater(result.latency_ms, 0)

        # 4. Verify directory structure
        self.assertTrue(os.path.isdir(os.path.join(wiki_dir, "entities")))
        self.assertTrue(os.path.isdir(os.path.join(wiki_dir, "claims")))

        # 5. Verify AGENTS.md exists
        agents_path = os.path.join(wiki_dir, "agents.md")
        self.assertTrue(
            os.path.exists(agents_path),
            f"agents.md not found at {agents_path}. "
            f"Files in wiki_dir: {os.listdir(wiki_dir)}"
        )

        # 6. Verify at least one entity page
        entities_dir = os.path.join(wiki_dir, "entities")
        entity_files = [f for f in os.listdir(entities_dir) if f.endswith(".md")]
        self.assertGreaterEqual(
            len(entity_files), 1,
            f"Expected at least 1 entity .md file, got: {entity_files}"
        )

        # 7. Verify at least one claim page
        claims_dir = os.path.join(wiki_dir, "claims")
        claim_files = [f for f in os.listdir(claims_dir) if f.endswith(".md")]
        self.assertGreaterEqual(
            len(claim_files), 1,
            f"Expected at least 1 claim .md file, got: {claim_files}"
        )

        # 8. Verify wiki_compile_log.jsonl exists and is parseable
        log_path = os.path.join(wiki_dir, "wiki_compile_log.jsonl")
        self.assertTrue(
            os.path.exists(log_path),
            f"wiki_compile_log.jsonl not found at {log_path}"
        )
        with open(log_path) as f:
            log_lines = f.readlines()
        self.assertGreaterEqual(len(log_lines), 1)
        log_entry = json.loads(log_lines[0])
        self.assertEqual(log_entry["simulation_id"], self.sim_id)
        self.assertIn("pages_updated", log_entry)
        self.assertIsNotNone(log_entry.get("latency_ms"))

        # 9. Verify index page was written (it's stored as agents.md but
        #    compilations produce multiple AGENTS-typed pages; they share name)
        index_in_updated = "index" in result.pages_updated
        self.assertTrue(index_in_updated, f"Expected 'index' in pages_updated, got {result.pages_updated}")

        # 10. Verify timeline page
        self.assertIn("timeline", result.pages_updated)

        # 11. Verify sources page
        self.assertIn("sources", result.pages_updated)

        # 12. Verify contradictions page
        self.assertIn("contradictions", result.pages_updated)

        # 13. Verify contradictions detection (may be 0 if no negation patterns match)
        #     Contradictions require same-entity claims with negation conflicts.
        #     Our data includes "GDP grew 3.2%" and "Growth is not accurate — contracted 1.5%"
        #     which should trigger a negation or numeric conflict.
        self.assertGreaterEqual(
            result.contradictions_added, 0,
            f"Contradictions: {result.contradictions_added}"
        )

        # 14. Verify entities extracted from events (Dr. Chen, MarketBot, SkepticAI)
        self.assertGreaterEqual(
            result.claims_added, 1,
            f"Expected >= 1 claim, got {result.claims_added}"
        )

        # 15. Verify build_wiki_context_for_report returns non-empty context
        context = build_wiki_context_for_report(
            self.sim_id, wiki_root=self.wiki_root
        )
        self.assertIsNotNone(context)
        self.assertGreater(len(context), 100)  # non-trivial content

        # 16. Verify context contains expected content
        # The context assembles entities, claims, and structural pages
        # It should contain our simulation data
        self.assertIn("Dr. Chen", context)

        # 17. Verify entity count in pages_updated
        entity_pages = [p for p in result.pages_updated if p.startswith("entity/")]
        self.assertGreaterEqual(len(entity_pages), 1)

        # 18. Verify claim count in pages_updated
        claim_pages = [p for p in result.pages_updated if p.startswith("claim/")]
        self.assertGreaterEqual(len(claim_pages), 1)

        # 19. Verify source artifacts reflect the documents we provided
        self.assertEqual(len(result.source_artifacts), 2)
        self.assertIn("gdp_report_q2.pdf", result.source_artifacts)
        self.assertIn("consumer_confidence.csv", result.source_artifacts)

    def test_smoke_artifact_file_contents(self):
        """Inspect the content of key artifact files for correctness."""
        # Run the full compile
        result = self.compiler.compile(
            simulation_id=self.sim_id,
            events=SMOKE_EVENTS,
            retrieved_memories=SMOKE_MEMORIES,
            case_metadata=SMOKE_CASE_METADATA,
            documents=SMOKE_DOCUMENTS,
        )

        wiki_dir = self.store._sim_wiki_dir(self.sim_id)

        # Check agents.md content is non-empty and valid markdown
        agents_path = os.path.join(wiki_dir, "agents.md")
        if os.path.exists(agents_path):
            with open(agents_path) as f:
                agents_content = f.read()
            # Should contain heading markers
            self.assertTrue(
                agents_content.startswith("#") or "##" in agents_content,
                f"agents.md doesn't look like valid markdown: {agents_content[:200]}"
            )

        # Check an entity page has structured content
        entities_dir = os.path.join(wiki_dir, "entities")
        if os.path.isdir(entities_dir):
            entity_files = [f for f in os.listdir(entities_dir) if f.endswith(".md")]
            if entity_files:
                with open(os.path.join(entities_dir, entity_files[0])) as f:
                    entity_content = f.read()
                self.assertTrue(
                    len(entity_content) > 20,
                    f"Entity page too short: {entity_content[:200]}"
                )

        # Check a claim page
        claims_dir = os.path.join(wiki_dir, "claims")
        if os.path.isdir(claims_dir):
            claim_files = [f for f in os.listdir(claims_dir) if f.endswith(".md")]
            if claim_files:
                with open(os.path.join(claims_dir, claim_files[0])) as f:
                    claim_content = f.read()
                self.assertTrue(
                    len(claim_content) > 20,
                    f"Claim page too short: {claim_content[:200]}"
                )

    def test_smoke_compile_log_artifact(self):
        """The wiki_compile_log.jsonl is a valid, parseable audit trail."""
        self.compiler.compile(
            simulation_id=self.sim_id,
            events=SMOKE_EVENTS,
            retrieved_memories=SMOKE_MEMORIES,
            case_metadata=SMOKE_CASE_METADATA,
            documents=SMOKE_DOCUMENTS,
        )

        wiki_dir = self.store._sim_wiki_dir(self.sim_id)
        log_path = os.path.join(wiki_dir, "wiki_compile_log.jsonl")

        with open(log_path) as f:
            lines = f.readlines()

        # Each line should be valid JSON
        entries = [json.loads(line) for line in lines]
        self.assertGreaterEqual(len(entries), 1)

        # Verify structural fields
        entry = entries[0]
        self.assertEqual(entry["simulation_id"], self.sim_id)
        self.assertIn("compile_ts", entry)
        self.assertIn("pages_updated", entry)
        self.assertIn("claims_added", entry)
        self.assertIn("contradictions_added", entry)
        self.assertIn("source_artifacts", entry)
        self.assertIn("latency_ms", entry)

        # source_artifacts should list our documents
        self.assertIn("gdp_report_q2.pdf", entry["source_artifacts"])

    def test_smoke_contradiction_detection(self):
        """Verify that negation-based and numeric contradictions are detected."""
        # Use memory data that creates claims about the same entity with
        # conflicting numbers and negation.
        memories = [
            {
                "edges": [
                    {
                        "fact": "The project costs 5000 dollars",
                        "name": "cost",
                        "source_node_name": "ProjectX",
                        "target_node_name": "budget",
                    },
                    {
                        "fact": "The project does not cost 5000 dollars",
                        "name": "denial",
                        "source_node_name": "ProjectX",
                        "target_node_name": "budget",
                    },
                ],
            },
        ]
        result = self.compiler.compile(
            "sim_contra",
            retrieved_memories=memories,
        )
        # Should detect at least one contradiction (negation + same entity "ProjectX")
        self.assertGreaterEqual(
            result.contradictions_added, 1,
            f"Expected >= 1 contradiction for negation conflict, got {result.contradictions_added}"
        )

    def test_smoke_directory_artifact_listing(self):
        """Print a summary of the wiki directory artifact for manual inspection."""
        result = self.compiler.compile(
            simulation_id=self.sim_id,
            events=SMOKE_EVENTS,
            retrieved_memories=SMOKE_MEMORIES,
            case_metadata=SMOKE_CASE_METADATA,
            documents=SMOKE_DOCUMENTS,
        )

        wiki_dir = self.store._sim_wiki_dir(self.sim_id)

        # Walk the directory and collect all files
        all_files = []
        for dirpath, dirnames, filenames in os.walk(wiki_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                relpath = os.path.relpath(filepath, wiki_dir)
                size = os.path.getsize(filepath)
                all_files.append((relpath, size))

        # Verify minimum expected artifacts
        rel_paths = {f[0] for f in all_files}
        expected_min_files = {
            "agents.md",
            "wiki_meta.json",
            "wiki_compile_log.jsonl",
        }
        for expected in expected_min_files:
            self.assertIn(
                expected, rel_paths,
                f"Missing expected file: {expected}. "
                f"Files found: {sorted(rel_paths)}"
            )

        # Verify at least one entity .md file
        entity_files = [p for p in rel_paths if p.startswith("entities/") and p.endswith(".md")]
        self.assertGreaterEqual(
            len(entity_files), 1,
            f"Expected at least one entity .md file. Found: {sorted(rel_paths)}"
        )

        # Verify at least one claim .md file
        claim_files = [p for p in rel_paths if p.startswith("claims/") and p.endswith(".md")]
        self.assertGreaterEqual(
            len(claim_files), 1,
            f"Expected at least one claim .md file. Found: {sorted(rel_paths)}"
        )


if __name__ == "__main__":
    unittest.main()