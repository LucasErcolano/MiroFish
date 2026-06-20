"""
Tests for wiki_memory module — WikiStore, schemas, and templates.

These tests run against a tmpdir (no dependency on Flask app config or uploads)
and verify all core operations: path safety, CRUD, timeline, snapshots, compile.
"""

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
import pytest

# ---------------------------------------------------------------------------
# Add backend to sys.path (same pattern as other MiroFish tests)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# ---------------------------------------------------------------------------
# We pass wiki_root explicitly to avoid coupling to Config.UPLOAD_FOLDER.
# ---------------------------------------------------------------------------

# Import directly from submodules — using importlib to avoid triggering
# the full services __init__.py (which pulls in zep_cloud and other heavy deps).
import importlib
_schemas = importlib.import_module("app.services.wiki_memory.schemas")
_store = importlib.import_module("app.services.wiki_memory.wiki_store")

WikiMeta = _schemas.WikiMeta
WikiPage = _schemas.WikiPage
WikiPageType = _schemas.WikiPageType
WikiSection = _schemas.WikiSection
WikiTimelineEntry = _schemas.WikiTimelineEntry

WikiStore = _store.WikiStore
_sanitize_id = _store._sanitize_id
_safe_join = _store._safe_join
_atomic_write = _store._atomic_write


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_wiki_root(tmp_path):
    """Create a temporary wiki root directory."""
    root = str(tmp_path / "simulations")
    os.makedirs(root, exist_ok=True)
    return root


@pytest.fixture
def store(tmp_wiki_root):
    """Create a WikiStore using a tmp directory."""
    return WikiStore(wiki_root=tmp_wiki_root)


SIM_ID = "sim_test123"


# ---------------------------------------------------------------------------
# Path safety tests
# ---------------------------------------------------------------------------

class TestPathSafety:
    def test_sanitize_id_valid(self):
        assert _sanitize_id("sim_abc123") == "sim_abc123"
        assert _sanitize_id("entity-1") == "entity-1"
        assert _sanitize_id("claim.test") == "claim.test"

    def test_sanitize_id_empty(self):
        with pytest.raises(ValueError, match="must not be empty"):
            _sanitize_id("")

    def test_sanitize_id_traversal(self):
        with pytest.raises(ValueError, match="Invalid Wiki ID"):
            _sanitize_id("../etc/passwd")

    def test_sanitize_id_spaces(self):
        with pytest.raises(ValueError, match="Invalid Wiki ID"):
            _sanitize_id("has spaces")

    def test_sanitize_id_double_dot(self):
        with pytest.raises(ValueError, match="path traversal"):
            _sanitize_id("..")

    def test_safe_join_normal(self):
        result = _safe_join("/base", "sub", "file.md")
        assert result == os.path.normpath("/base/sub/file.md")

    def test_safe_join_traversal(self):
        with pytest.raises(ValueError, match="Path traversal"):
            _safe_join("/base", "../../etc/passwd")


# ---------------------------------------------------------------------------
# Atomic write tests
# ---------------------------------------------------------------------------

class TestAtomicWrite:
    def test_atomic_write_creates_file(self, tmp_path):
        target = str(tmp_path / "test.txt")
        _atomic_write(target, "hello world")
        assert os.path.exists(target)
        with open(target, "r") as f:
            assert f.read() == "hello world"

    def test_atomic_write_overwrites(self, tmp_path):
        target = str(tmp_path / "test.txt")
        _atomic_write(target, "first")
        _atomic_write(target, "second")
        with open(target, "r") as f:
            assert f.read() == "second"

    def test_atomic_write_creates_parent_dirs(self, tmp_path):
        target = str(tmp_path / "deep" / "nested" / "dir" / "file.md")
        _atomic_write(target, "content")
        assert os.path.exists(target)
        with open(target, "r") as f:
            assert f.read() == "content"


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestWikiSection:
    def test_to_markdown(self):
        s = WikiSection(heading="Description", body="Some text here.", level=2)
        md = s.to_markdown()
        assert md == "## Description\n\nSome text here."

    def test_to_markdown_level3(self):
        s = WikiSection(heading="Details", body="More text.", level=3)
        md = s.to_markdown()
        assert md == "### Details\n\nMore text."


class TestWikiPage:
    def test_content_hash_stable(self):
        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Test Page",
            sections=[WikiSection(heading="Overview", body="Hello", level=2)],
        )
        h1 = page.content_hash()
        h2 = page.content_hash()
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_to_markdown(self):
        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Agents",
            sections=[
                WikiSection(heading="Overview", body="All agents", level=2),
                WikiSection(heading="Agent A", body="Alpha agent", level=3),
            ],
        )
        md = page.to_markdown()
        assert "# Agents" in md
        assert "## Overview" in md
        assert "### Agent A" in md

    def test_to_markdown_with_timeline(self):
        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Agents",
            sections=[WikiSection(heading="Overview", body="Desc", level=2)],
            timeline=[
                WikiTimelineEntry(
                    timestamp="2026-06-01T12:00:00Z",
                    action="created",
                    summary="Initial creation",
                )
            ],
        )
        md = page.to_markdown()
        assert "## Timeline" in md
        assert "[created]" in md

    def test_roundtrip_dict(self):
        page = WikiPage(
            page_type=WikiPageType.ENTITY,
            title="Entity 1",
            sections=[WikiSection(heading="Facts", body="fact A", level=2)],
            entity_id="ent_1",
            simulation_id="sim_test",
        )
        d = page.to_dict()
        restored = WikiPage.from_dict(d)
        assert restored.page_type == WikiPageType.ENTITY
        assert restored.title == "Entity 1"
        assert restored.entity_id == "ent_1"
        assert len(restored.sections) == 1


class TestWikiMeta:
    def test_roundtrip(self):
        meta = WikiMeta(
            simulation_id="sim_abc",
            pages={"agents": "hash123"},
        )
        json_str = meta.to_json()
        restored = WikiMeta.from_json(json_str)
        assert restored.simulation_id == "sim_abc"
        assert restored.pages["agents"] == "hash123"


# ---------------------------------------------------------------------------
# WikiStore tests
# ---------------------------------------------------------------------------

class TestWikiStore:

    def test_initialize_creates_directory(self, store, tmp_wiki_root):
        wiki_dir = store.initialize(SIM_ID)
        assert os.path.isdir(wiki_dir)
        assert os.path.isdir(os.path.join(wiki_dir, "entities"))
        assert os.path.isdir(os.path.join(wiki_dir, "claims"))
        assert os.path.exists(os.path.join(wiki_dir, "wiki_meta.json"))

    def test_initialize_idempotent(self, store):
        store.initialize(SIM_ID)
        store.initialize(SIM_ID)  # should not raise

    def test_write_and_read_agents_page(self, store):
        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Simulation Agents",
            sections=[
                WikiSection(heading="Overview", body="5 agents in the simulation", level=2),
            ],
        )
        path = store.write_page(SIM_ID, page)
        assert os.path.exists(path)

        loaded = store.read_agents_page(SIM_ID)
        assert loaded is not None
        assert loaded.title == "Simulation Agents"
        assert len(loaded.sections) >= 1

    def test_write_and_read_entity_page(self, store):
        page = WikiPage(
            page_type=WikiPageType.ENTITY,
            title="Entity: alice",
            sections=[
                WikiSection(heading="Description", body="Alice is a researcher", level=2),
            ],
            entity_id="alice",
        )
        store.write_page(SIM_ID, page)

        loaded = store.read_entity_page(SIM_ID, "alice")
        assert loaded is not None
        assert loaded.title == "Entity: alice"
        assert loaded.entity_id == "alice"

    def test_write_and_read_claim_page(self, store):
        page = WikiPage(
            page_type=WikiPageType.CLAIM,
            title="Claim: claim_1",
            sections=[
                WikiSection(heading="Claim Statement", body="Alice influences Bob", level=2),
            ],
            entity_id="claim_1",
        )
        store.write_page(SIM_ID, page)

        loaded = store.read_claim_page(SIM_ID, "claim_1")
        assert loaded is not None
        assert "claim_1" in loaded.title

    def test_read_nonexistent_returns_none(self, store):
        result = store.read_agents_page("sim_nonexistent")
        assert result is None

    def test_list_entities(self, store):
        # Write two entity pages
        for eid in ["alice", "bob"]:
            page = WikiPage(
                page_type=WikiPageType.ENTITY,
                title=f"Entity: {eid}",
                sections=[WikiSection(heading="Desc", body=f"Description of {eid}", level=2)],
                entity_id=eid,
            )
            store.write_page(SIM_ID, page)

        entities = store.list_entities(SIM_ID)
        assert "alice" in entities
        assert "bob" in entities

    def test_list_claims(self, store):
        for cid in ["claim_1", "claim_2"]:
            page = WikiPage(
                page_type=WikiPageType.CLAIM,
                title=f"Claim: {cid}",
                sections=[WikiSection(heading="Claim", body=f"Claim {cid}", level=2)],
                entity_id=cid,
            )
            store.write_page(SIM_ID, page)

        claims = store.list_claims(SIM_ID)
        assert "claim_1" in claims
        assert "claim_2" in claims

    def test_append_timeline(self, store):
        # Create an agents page first
        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Test Agents",
            sections=[WikiSection(heading="Overview", body="Test", level=2)],
        )
        store.write_page(SIM_ID, page)

        # Append timeline entry
        entry = store.append_timeline(
            SIM_ID,
            WikiPageType.AGENTS,
            action="updated",
            summary="Added new agent profile",
            metadata={"agent": "charlie"},
        )
        assert entry.action == "updated"
        assert entry.summary == "Added new agent profile"

        # Verify the timeline entry persists
        loaded = store.read_agents_page(SIM_ID)
        assert len(loaded.timeline) == 1
        assert loaded.timeline[0].action == "updated"

    def test_delete_page(self, store):
        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="To Delete",
            sections=[WikiSection(heading="Overview", body="Will be deleted", level=2)],
        )
        store.write_page(SIM_ID, page)
        assert store.read_agents_page(SIM_ID) is not None

        result = store.delete_page(SIM_ID, WikiPageType.AGENTS)
        assert result is True
        assert store.read_agents_page(SIM_ID) is None

    def test_delete_nonexistent(self, store):
        result = store.delete_page(SIM_ID, WikiPageType.AGENTS)
        assert result is False

    def test_commit_snapshot(self, store):
        # Create some content
        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Snapshot Test",
            sections=[WikiSection(heading="Overview", body="Before snapshot", level=2)],
        )
        store.write_page(SIM_ID, page)

        snap_dir = store.commit_snapshot(SIM_ID)
        assert snap_dir is not None
        assert os.path.isdir(snap_dir)
        # Should contain copies of files
        assert os.path.exists(os.path.join(snap_dir, "agents.md"))

    def test_commit_snapshot_nonexistent_sim(self, store):
        result = store.commit_snapshot("sim_nonexistent")
        # Should return None gracefully
        assert result is None

    def test_compile_wiki_context(self, store):
        # Write agents page
        agents = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Test Agents",
            sections=[
                WikiSection(heading="Overview", body="5 agents total", level=2),
            ],
        )
        store.write_page(SIM_ID, agents)

        # Write entity page
        entity = WikiPage(
            page_type=WikiPageType.ENTITY,
            title="Entity: alice",
            sections=[
                WikiSection(heading="Description", body="Alice is a researcher", level=2),
            ],
            entity_id="alice",
        )
        store.write_page(SIM_ID, entity)

        # Compile context
        context = store.compile_wiki_context(SIM_ID, max_chars=10000)
        assert "Test Agents" in context
        assert "Entity: alice" in context
        assert "---" in context  # separator between pages

    def test_compile_wiki_context_truncation(self, store):
        # Write a large agents page
        big_content = "X" * 5000
        agents = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Big Page",
            sections=[
                WikiSection(heading="Big", body=big_content, level=2),
            ],
        )
        store.write_page(SIM_ID, agents)

        # Compile with small max_chars
        context = store.compile_wiki_context(SIM_ID, max_chars=500)
        assert len(context) <= 550  # small allowance for truncation marker

    def test_create_from_template(self, store):
        page = store.create_from_template(
            SIM_ID,
            WikiPageType.AGENTS,
            title="Template Test",
        )
        assert page is not None
        assert page.page_type == WikiPageType.AGENTS
        assert page.title == "Template Test"

        # Verify persisted
        loaded = store.read_agents_page(SIM_ID)
        assert loaded is not None
        assert loaded.title == "Template Test"

    def test_meta_hash_tracking(self, store):
        page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Hash Test",
            sections=[WikiSection(heading="Overview", body="Content", level=2)],
        )
        store.write_page(SIM_ID, page)

        # Read meta and check hash is recorded
        meta = store._read_meta(SIM_ID)
        assert "agents" in meta.pages
        assert len(meta.pages["agents"]) == 64  # SHA-256 hex

    def test_path_safety_in_simulation_id(self, store):
        with pytest.raises(ValueError):
            store.initialize("../../../etc/passwd")

    def test_path_safety_in_entity_id(self, store):
        with pytest.raises(ValueError):
            store._entity_path(SIM_ID, "../../etc/passwd")


# ---------------------------------------------------------------------------
# Integration-ish test: full workflow
# ---------------------------------------------------------------------------

class TestFullWorkflow:
    def test_create_update_snapshot_read(self, store):
        sim_id = "sim_workflow"

        # 1. Initialize
        store.initialize(sim_id)

        # 2. Create agents page from template
        agents = store.create_from_template(
            sim_id, WikiPageType.AGENTS, title="Workflow Agents"
        )
        assert agents is not None

        # 3. Create entity page
        entity = WikiPage(
            page_type=WikiPageType.ENTITY,
            title="Entity: researcher_1",
            sections=[
                WikiSection(heading="Description", body="A researcher studying misinformation", level=2),
                WikiSection(heading="Key Facts", body="- Highest influence score\n- Posts daily", level=2),
            ],
            entity_id="researcher_1",
        )
        store.write_page(sim_id, entity)

        # 4. Create claim page
        claim = WikiPage(
            page_type=WikiPageType.CLAIM,
            title="Claim: influence_hypothesis",
            sections=[
                WikiSection(heading="Claim Statement", body="Influencers drive 80% of misinformation", level=2),
            ],
            entity_id="influence_hypothesis",
        )
        store.write_page(sim_id, claim)

        # 5. Append timeline
        store.append_timeline(
            sim_id, WikiPageType.ENTITY, action="updated",
            summary="Added researcher_1 profile",
            entity_id="researcher_1",
        )

        # 6. Snapshot
        snap = store.commit_snapshot(sim_id)
        assert snap is not None

        # 7. Compile context
        context = store.compile_wiki_context(sim_id)
        assert "Workflow Agents" in context
        assert "researcher_1" in context
        assert "influence_hypothesis" in context

        # 8. List operations
        entities = store.list_entities(sim_id)
        claims = store.list_claims(sim_id)
        assert "researcher_1" in entities
        assert "influence_hypothesis" in claims


if __name__ == "__main__":
    pytest.main([__file__, "-v"])