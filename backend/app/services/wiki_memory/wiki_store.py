"""
WikiStore — Filesystem-Backed Wiki Directory Manager

Manages wiki content for simulation contexts stored under:
    uploads/simulations/{simulation_id}/wiki/

Each simulation's wiki directory contains:
    wiki/
      wiki_meta.json       — metadata (hashes, timestamps)
      agents.md            — agent knowledge page
      entities/
        {entity_id}.md     — per-entity pages
      claims/
        {claim_id}.md      — per-claim pages

Key design decisions (from parent audit t_bea45913):
  - Path safety: all IDs are sanitized; traversal attacks are rejected.
  - Atomic writes: content is written to a temp file then renamed.
  - Backward compat: wiki_context defaults to None; existing code is unaffected.
  - Markdown-first: content is stored as .md files; metadata as .json sidecars.

Integrators: inject `wiki_context` into ReportAgent.__init__ and prompt templates.
Do NOT redesign GraphRAG/Zep. This is a supplementary prior-knowledge layer.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...config import Config
from ...utils.logger import get_logger
from .schemas import (
    WikiMeta,
    WikiPage,
    WikiPageType,
    WikiSection,
    WikiTimelineEntry,
)

logger = get_logger("mirofish.wiki_store")

# ---------------------------------------------------------------------------
# Path-safety helpers
# ---------------------------------------------------------------------------

# Only allow alphanumeric, hyphens, underscores, and dots (no directory traversal).
_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9._-]{1,128}$")
_ROOT_PAGE_NAMES = {"index", "agents", "timeline", "sources", "contradictions"}


def _sanitize_id(raw_id: str) -> str:
    """Sanitize a page/entity/claim ID for safe filesystem use.

    Rejects empty strings, path traversal attempts, and IDs with
    characters outside [a-zA-Z0-9._-].
    """
    if not raw_id or not raw_id.strip():
        raise ValueError("Wiki ID must not be empty")
    sanitized = raw_id.strip()
    if not _SAFE_ID_RE.match(sanitized):
        raise ValueError(
            f"Invalid Wiki ID: {raw_id!r}. "
            f"Only alphanumeric, hyphens, underscores, and dots are allowed."
        )
    # Double-check no path traversal even after sanitization.
    if ".." in sanitized or "/" in sanitized or "\\" in sanitized:
        raise ValueError(f"Invalid Wiki ID (path traversal): {raw_id!r}")
    return sanitized


def _safe_join(base_dir: str, *parts: str) -> str:
    """Join path parts under base_dir, verifying the result stays inside base_dir."""
    joined = os.path.normpath(os.path.join(base_dir, *parts))
    base = os.path.normpath(base_dir)
    if not joined.startswith(base + os.sep) and joined != base:
        raise ValueError(
            f"Path traversal detected: {joined} escapes base {base}"
        )
    return joined


# ---------------------------------------------------------------------------
# Atomic write helper
# ---------------------------------------------------------------------------

def _atomic_write(target_path: str, content: str, encoding: str = "utf-8") -> None:
    """Write content to target_path atomically via temp file + rename.

    This prevents partial writes on crash. Works on the same filesystem.
    """
    target_dir = os.path.dirname(target_path)
    os.makedirs(target_dir, exist_ok=True)

    # Write to a temp file in the same directory (same filesystem for rename).
    fd, tmp_path = tempfile.mkstemp(dir=target_dir, prefix=".wiki_tmp_")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
        # Atomic on POSIX when src/dst are on same mount point.
        os.replace(tmp_path, target_path)
    except Exception:
        # Clean up temp file on failure.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# WikiStore
# ---------------------------------------------------------------------------

class WikiStore:
    """Filesystem-backed Wiki directory manager for simulation contexts.

    Usage:
        store = WikiStore()
        store.initialize("sim_abc123")

        # Write an agents page
        agents_page = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Simulation Agents",
            sections=[...],
        )
        store.write_page("sim_abc123", agents_page)

        # Read it back
        page = store.read_page("sim_abc123", WikiPageType.AGENTS)
        md = page.to_markdown()

        # Append a timeline entry
        store.append_timeline("sim_abc123", WikiPageType.AGENTS, ...)

        # Create a snapshot (backup)
        store.commit_snapshot("sim_abc123")
    """

    # Root for all wiki data — mirrors {UPLOAD_FOLDER}/simulations/{sim_id}/wiki/
    # but is configurable for testing.
    WIKI_ROOT: str = os.path.join(
        Config.UPLOAD_FOLDER, "simulations"
    )

    # Maximum wiki content size that will be loaded (in bytes). Prevents OOM on
    # pathological files. 10 MB is generous for text wiki pages.
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    def __init__(self, wiki_root: Optional[str] = None):
        """Initialize WikiStore.

        Args:
            wiki_root: Override the root directory for wiki storage.
                      Defaults to Config.UPLOAD_FOLDER/simulations.
        """
        if wiki_root is not None:
            self._wiki_root = wiki_root
        else:
            self._wiki_root = self.WIKI_ROOT

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _sim_wiki_dir(self, simulation_id: str) -> str:
        """Return the wiki directory for a simulation."""
        safe_id = _sanitize_id(simulation_id)
        path = _safe_join(self._wiki_root, safe_id, "wiki")
        return path

    def _page_path(self, simulation_id: str, page_type: WikiPageType) -> str:
        """Return the markdown file path for a top-level page type."""
        wiki_dir = self._sim_wiki_dir(simulation_id)
        filename = f"{page_type.value}.md"
        return _safe_join(wiki_dir, filename)

    def _named_root_page_path(self, simulation_id: str, page_name: str) -> str:
        """Return the markdown file path for a named top-level wiki page."""
        safe_name = _sanitize_id(page_name)
        if safe_name not in _ROOT_PAGE_NAMES:
            raise ValueError(f"Unknown root wiki page: {page_name!r}")
        wiki_dir = self._sim_wiki_dir(simulation_id)
        return _safe_join(wiki_dir, f"{safe_name}.md")

    def _entity_path(self, simulation_id: str, entity_id: str) -> str:
        """Return the markdown file path for an entity page."""
        safe_entity = _sanitize_id(entity_id)
        wiki_dir = self._sim_wiki_dir(simulation_id)
        return _safe_join(wiki_dir, "entities", f"{safe_entity}.md")

    def _claim_path(self, simulation_id: str, claim_id: str) -> str:
        """Return the markdown file path for a claim page."""
        safe_claim = _sanitize_id(claim_id)
        wiki_dir = self._sim_wiki_dir(simulation_id)
        return _safe_join(wiki_dir, "claims", f"{safe_claim}.md")

    def _meta_path(self, simulation_id: str) -> str:
        """Return the path to wiki_meta.json for a simulation."""
        wiki_dir = self._sim_wiki_dir(simulation_id)
        return _safe_join(wiki_dir, "wiki_meta.json")

    # ------------------------------------------------------------------
    # Initialize
    # ------------------------------------------------------------------

    def initialize(self, simulation_id: str) -> str:
        """Create the wiki directory structure for a simulation.

        Creates:
            {wiki_root}/{simulation_id}/wiki/
            {wiki_root}/{simulation_id}/wiki/entities/
            {wiki_root}/{simulation_id}/wiki/claims/
            {wiki_root}/{simulation_id}/wiki/wiki_meta.json

        Returns the wiki directory path.
        """
        wiki_dir = self._sim_wiki_dir(simulation_id)
        os.makedirs(os.path.join(wiki_dir, "entities"), exist_ok=True)
        os.makedirs(os.path.join(wiki_dir, "claims"), exist_ok=True)

        # Write initial meta if it doesn't exist
        meta_path = self._meta_path(simulation_id)
        if not os.path.exists(meta_path):
            meta = WikiMeta(simulation_id=simulation_id)
            _atomic_write(meta_path, meta.to_json())

        logger.info(f"Wiki directory initialized: {wiki_dir}")
        return wiki_dir

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def write_page(self, simulation_id: str, page: WikiPage) -> str:
        """Write a wiki page to disk atomically.

        Args:
            simulation_id: The simulation context.
            page: The WikiPage to persist.

        Returns:
            The file path written to.
        """
        self.initialize(simulation_id)  # ensure dirs exist

        if page.page_type == WikiPageType.AGENTS:
            if page.entity_id:
                path = self._named_root_page_path(simulation_id, page.entity_id)
            else:
                path = self._page_path(simulation_id, page.page_type)
        elif page.page_type == WikiPageType.ENTITY:
            if not page.entity_id:
                raise ValueError("ENTITY page requires entity_id")
            path = self._entity_path(simulation_id, page.entity_id)
        elif page.page_type == WikiPageType.CLAIM:
            if not page.entity_id:
                raise ValueError("CLAIM page requires entity_id as claim identifier")
            path = self._claim_path(simulation_id, page.entity_id)
        else:
            raise ValueError(f"Unknown page type: {page.page_type}")

        # Update timestamps
        now = datetime.now(timezone.utc).isoformat()
        page.updated_at = now
        if not page.created_at:
            page.created_at = now

        content_md = page.to_markdown()
        _atomic_write(path, content_md)

        # Update meta with hash
        self._update_meta_hash(simulation_id, page)
        logger.info(f"Wiki page written: {path}")
        return path

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def read_page(self, simulation_id: str, page_type: WikiPageType,
                  entity_id: Optional[str] = None) -> Optional[WikiPage]:
        """Read a wiki page from disk.

        Args:
            simulation_id: The simulation context.
            page_type: Type of page to read.
            entity_id: Required for ENTITY and CLAIM page types.

        Returns:
            WikiPage if found, None if the file doesn't exist.
        """
        if page_type == WikiPageType.AGENTS:
            if entity_id and entity_id in _ROOT_PAGE_NAMES:
                path = self._named_root_page_path(simulation_id, entity_id)
            else:
                path = self._page_path(simulation_id, page_type)
        elif page_type == WikiPageType.ENTITY:
            if not entity_id:
                raise ValueError("ENTITY page read requires entity_id")
            path = self._entity_path(simulation_id, entity_id)
        elif page_type == WikiPageType.CLAIM:
            if not entity_id:
                raise ValueError("CLAIM page read requires entity_id")
            path = self._claim_path(simulation_id, entity_id)
        else:
            raise ValueError(f"Unknown page type: {page_type}")

        if not os.path.exists(path):
            return None

        self._check_file_size(path)

        with open(path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        # Parse the markdown back into a WikiPage
        page = self._parse_markdown(raw_content, page_type, entity_id)
        page.raw_content = raw_content
        page.simulation_id = simulation_id

        # Try to load timestamps from meta
        meta = self._read_meta(simulation_id)
        page_hash = page.content_hash()
        page_meta = meta.pages.get(
            f"{page_type.value}/{entity_id}" if entity_id else page_type.value,
            None,
        )
        # Timestamps are stored in the page dict already; sync from metadata
        # if available (the write sets them).

        return page

    def read_agents_page(self, simulation_id: str) -> Optional[WikiPage]:
        """Convenience: read the AGENTS page for a simulation."""
        return self.read_page(simulation_id, WikiPageType.AGENTS)

    def read_entity_page(self, simulation_id: str, entity_id: str) -> Optional[WikiPage]:
        """Convenience: read an ENTITY page."""
        return self.read_page(simulation_id, WikiPageType.ENTITY, entity_id=entity_id)

    def read_claim_page(self, simulation_id: str, claim_id: str) -> Optional[WikiPage]:
        """Convenience: read a CLAIM page."""
        return self.read_page(simulation_id, WikiPageType.CLAIM, entity_id=claim_id)

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    def list_entities(self, simulation_id: str) -> List[str]:
        """List all entity IDs that have wiki pages for a simulation."""
        wiki_dir = self._sim_wiki_dir(simulation_id)
        entities_dir = os.path.join(wiki_dir, "entities")
        if not os.path.isdir(entities_dir):
            return []
        return sorted(
            Path(f).stem
            for f in os.listdir(entities_dir)
            if f.endswith(".md")
        )

    def list_claims(self, simulation_id: str) -> List[str]:
        """List all claim IDs that have wiki pages for a simulation."""
        wiki_dir = self._sim_wiki_dir(simulation_id)
        claims_dir = os.path.join(wiki_dir, "claims")
        if not os.path.isdir(claims_dir):
            return []
        return sorted(
            Path(f).stem
            for f in os.listdir(claims_dir)
            if f.endswith(".md")
        )

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    def append_timeline(
        self,
        simulation_id: str,
        page_type: WikiPageType,
        action: str,
        summary: str,
        metadata: Optional[Dict[str, Any]] = None,
        entity_id: Optional[str] = None,
    ) -> WikiTimelineEntry:
        """Append a timeline entry to an existing wiki page.

        Reads the page, appends to the timeline, and re-writes it.
        Creates the page from its template if it doesn't exist yet.

        Args:
            simulation_id: The simulation context.
            page_type: Type of page.
            action: Timeline action label (e.g. "updated", "snapshot").
            summary: Human-readable summary of what changed.
            metadata: Optional dict of machine-readable metadata.
            entity_id: Required for ENTITY/CLAIM pages.

        Returns:
            The timeline entry that was appended.
        """
        page = self.read_page(simulation_id, page_type, entity_id=entity_id)
        if page is None:
            # Create from template
            page = self.create_from_template(simulation_id, page_type, entity_id=entity_id)

        entry = WikiTimelineEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            summary=summary,
            metadata=metadata or {},
        )
        page.timeline.append(entry)
        self.write_page(simulation_id, page)
        logger.info(
            f"Timeline entry appended: {page_type.value}"
            f"{f'/{entity_id}' if entity_id else ''} [{action}]"
        )
        return entry

    # ------------------------------------------------------------------
    # Snapshot / Backup
    # ------------------------------------------------------------------

    def commit_snapshot(self, simulation_id: str) -> Optional[str]:
        """Create a timestamped snapshot (backup) of the entire wiki directory.

        Saves to: {wiki_dir}/.snapshots/{ISO-timestamp}/

        This is a safe fallback — if the snapshot fails (e.g. disk full),
        the error is logged but NOT raised, so the caller can continue.

        Returns:
            Snapshot directory path, or None on failure.
        """
        wiki_dir = self._sim_wiki_dir(simulation_id)
        if not os.path.isdir(wiki_dir):
            logger.warning(f"Cannot snapshot — wiki dir does not exist: {wiki_dir}")
            return None

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        snap_dir = os.path.join(wiki_dir, ".snapshots", ts)

        try:
            shutil.copytree(wiki_dir, snap_dir, dirs_exist_ok=False)
            logger.info(f"Wiki snapshot created: {snap_dir}")
            return snap_dir
        except Exception as exc:
            # Safe fallback: log and continue. Snapshotting is best-effort.
            logger.warning(f"Wiki snapshot failed (non-fatal): {exc}")
            return None

    # ------------------------------------------------------------------
    # Template-based creation
    # ------------------------------------------------------------------

    def create_from_template(
        self,
        simulation_id: str,
        page_type: WikiPageType,
        entity_id: Optional[str] = None,
        title: Optional[str] = None,
        extra_sections: Optional[List[WikiSection]] = None,
    ) -> WikiPage:
        """Create a WikiPage from the bundled template, filling in placeholders.

        Args:
            simulation_id: The simulation context.
            page_type: Type of page to create.
            entity_id: Required for ENTITY and CLAIM types.
            title: Override title (default derived from template).
            extra_sections: Additional sections to append.

        Returns:
            The created WikiPage (also written to disk).
        """
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        template_name = f"{page_type.value}.md"
        template_path = os.path.join(template_dir, template_name)

        # Read template content
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                template_md = f.read()
        else:
            # Minimal fallback if templates not yet installed
            template_md = f"# {page_type.value.capitalize()}\n\n(No template available)\n"

        # Determine default title
        if title is None:
            title = f"{page_type.value.capitalize()}"
            if entity_id:
                title = f"{page_type.value.capitalize()}: {entity_id}"

        # Parse template sections
        sections = self._parse_sections_from_md(template_md, extra_sections)

        page = WikiPage(
            page_type=page_type,
            title=title,
            sections=sections,
            entity_id=entity_id,
            simulation_id=simulation_id,
        )

        self.write_page(simulation_id, page)
        return page

    # ------------------------------------------------------------------
    # Compiled context for ReportAgent
    # ------------------------------------------------------------------

    def compile_wiki_context(self, simulation_id: str, max_chars: int = 8000) -> str:
        """Compile all wiki content for a simulation into a single markdown string.

        This is designed to be injected as `wiki_context` into the ReportAgent's
        prompt templates. Content is truncated to `max_chars` to stay within
        the prompt token budget.

        Args:
            simulation_id: The simulation context.
            max_chars: Maximum character length (default 8000 ≈ 2000 tokens).

        Returns:
            Concatenated markdown from all wiki pages, or empty string if none.
        """
        wiki_dir = self._sim_wiki_dir(simulation_id)
        if not os.path.isdir(wiki_dir):
            return ""

        parts: List[str] = []
        total_chars = 0

        # 1. Top-level pages (agents/index/timeline/sources/contradictions)
        for root_name in ["agents", "index", "timeline", "sources", "contradictions"]:
            if total_chars >= max_chars:
                break
            page = self.read_page(simulation_id, WikiPageType.AGENTS, entity_id=root_name)
            if page:
                md = page.to_markdown()
                remaining = max_chars - total_chars
                if len(md) <= remaining:
                    parts.append(md)
                    total_chars += len(md)
                else:
                    parts.append(md[:remaining] + "\n[...truncated]")
                    total_chars = max_chars
                    break

        # 2. ENTITY pages
        for eid in self.list_entities(simulation_id):
            if total_chars >= max_chars:
                break
            entity_page = self.read_entity_page(simulation_id, eid)
            if entity_page:
                md = entity_page.to_markdown()
                remaining = max_chars - total_chars
                if len(md) <= remaining:
                    parts.append(md)
                    total_chars += len(md)
                else:
                    # Truncate this page to fit
                    parts.append(md[:remaining] + "\n[...truncated]")
                    total_chars = max_chars
                    break

        # 3. CLAIM pages
        for cid in self.list_claims(simulation_id):
            if total_chars >= max_chars:
                break
            claim_page = self.read_claim_page(simulation_id, cid)
            if claim_page:
                md = claim_page.to_markdown()
                remaining = max_chars - total_chars
                if len(md) <= remaining:
                    parts.append(md)
                    total_chars += len(md)
                else:
                    parts.append(md[:remaining] + "\n[...truncated]")
                    total_chars = max_chars
                    break

        if not parts:
            return ""

        return "\n\n---\n\n".join(parts)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_page(self, simulation_id: str, page_type: WikiPageType,
                    entity_id: Optional[str] = None) -> bool:
        """Delete a wiki page file.

        Returns True if the file was deleted, False if it didn't exist.
        """
        if page_type == WikiPageType.AGENTS:
            if entity_id and entity_id in _ROOT_PAGE_NAMES:
                path = self._named_root_page_path(simulation_id, entity_id)
            else:
                path = self._page_path(simulation_id, page_type)
        elif page_type == WikiPageType.ENTITY:
            if not entity_id:
                raise ValueError("ENTITY page delete requires entity_id")
            path = self._entity_path(simulation_id, entity_id)
        elif page_type == WikiPageType.CLAIM:
            if not entity_id:
                raise ValueError("CLAIM page delete requires entity_id")
            path = self._claim_path(simulation_id, entity_id)
        else:
            raise ValueError(f"Unknown page type: {page_type}")

        if os.path.exists(path):
            os.unlink(path)
            logger.info(f"Wiki page deleted: {path}")
            return True
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_meta(self, simulation_id: str) -> WikiMeta:
        """Read wiki_meta.json, returning empty WikiMeta if not found."""
        meta_path = self._meta_path(simulation_id)
        if not os.path.exists(meta_path):
            return WikiMeta(simulation_id=simulation_id)
        with open(meta_path, "r", encoding="utf-8") as f:
            return WikiMeta.from_json(f.read())

    def _write_meta(self, simulation_id: str, meta: WikiMeta) -> None:
        """Persist wiki_meta.json atomically."""
        meta_path = self._meta_path(simulation_id)
        _atomic_write(meta_path, meta.to_json())

    def _update_meta_hash(self, simulation_id: str, page: WikiPage) -> None:
        """Update the content hash in wiki_meta.json after a page write."""
        meta = self._read_meta(simulation_id)
        key = (
            f"{page.page_type.value}/{page.entity_id}"
            if page.entity_id
            else page.page_type.value
        )
        meta.pages[key] = page.content_hash()
        meta.updated_at = datetime.now(timezone.utc).isoformat()
        self._write_meta(simulation_id, meta)

    def _check_file_size(self, path: str) -> None:
        """Verify a file is within size limits before reading."""
        size = os.path.getsize(path)
        if size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"Wiki file too large ({size} bytes, max {self.MAX_FILE_SIZE}): {path}"
            )

    @staticmethod
    def _parse_sections_from_md(
        md: str, extra: Optional[List[WikiSection]] = None
    ) -> List[WikiSection]:
        """Parse markdown into WikiSection list by splitting on headings.

        Handles ## and ### headings. Content before the first heading
        is placed in a section with an empty heading.
        """
        sections: List[WikiSection] = []
        lines = md.split("\n")
        current_heading = ""
        current_lines: List[str] = []
        current_level = 2

        for line in lines:
            # Skip the top-level title (# Title)
            if line.startswith("# ") and not line.startswith("## "):
                continue

            if line.startswith("## ") or line.startswith("### "):
                # Flush current section
                body = "\n".join(current_lines).strip()
                if current_heading or body:
                    sections.append(WikiSection(
                        heading=current_heading,
                        body=body,
                        level=current_level,
                    ))
                # Start new section
                if line.startswith("### "):
                    current_level = 3
                    current_heading = line.lstrip("#").strip()
                else:
                    current_level = 2
                    current_heading = line.lstrip("#").strip()
                current_lines = []
            else:
                current_lines.append(line)

        # Flush last section
        body = "\n".join(current_lines).strip()
        if current_heading or body:
            sections.append(WikiSection(
                heading=current_heading,
                body=body,
                level=current_level,
            ))

        if extra:
            sections.extend(extra)

        return sections

    @staticmethod
    def _parse_markdown(
        raw_content: str,
        page_type: WikiPageType,
        entity_id: Optional[str] = None,
    ) -> WikiPage:
        """Parse raw markdown content into a WikiPage object.

        Extracts the title from the first # heading, splits the rest
        into sections.
        """
        lines = raw_content.split("\n")
        title = page_type.value.capitalize()
        content_start = 0

        # Extract title from first # heading
        for i, line in enumerate(lines):
            if line.startswith("# ") and not line.startswith("## "):
                title = line.lstrip("#").strip()
                content_start = i + 1
                break

        remaining_md = "\n".join(lines[content_start:])
        sections = WikiStore._parse_sections_from_md(remaining_md)

        # Parse timeline from sections (look for "## Timeline" section)
        timeline: List[WikiTimelineEntry] = []
        non_timeline_sections: List[WikiSection] = []
        for section in sections:
            if section.heading.lower() == "timeline":
                # Parse timeline entries from body
                for tl_line in section.body.split("\n"):
                    tl_line = tl_line.strip()
                    if tl_line.startswith("- **"):
                        # Format: - **2026-06-01T12:00:00Z** [action] summary
                        try:
                            # Extract timestamp
                            ts_end = tl_line.index("**", 4)
                            timestamp = tl_line[4:ts_end]
                            rest = tl_line[ts_end + 2:].strip()  # after **
                            # Extract action
                            if rest.startswith("["):
                                bracket_end = rest.index("]")
                                action = rest[1:bracket_end]
                                summary = rest[bracket_end + 1:].strip()
                            else:
                                action = "updated"
                                summary = rest
                            timeline.append(WikiTimelineEntry(
                                timestamp=timestamp,
                                action=action,
                                summary=summary,
                            ))
                        except (ValueError, IndexError):
                            continue
                    # Skip non-entry lines
            else:
                non_timeline_sections.append(section)

        return WikiPage(
            page_type=page_type,
            title=title,
            sections=non_timeline_sections,
            timeline=timeline,
            entity_id=entity_id,
        )