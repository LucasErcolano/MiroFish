"""
Wiki Memory — Schemas and Data Structures

Defines the data models for Wiki-backed Report Memory:
  - WikiSection: a single section within a wiki page (entity, claim, or agents)
  - WikiPage: a complete wiki page for one simulation context
  - WikiMeta: persisted metadata alongside wiki content (hash, timestamps)

These are pure data classes with serialization helpers. They do NOT perform I/O.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class WikiPageType(str, Enum):
    """Type of wiki page, mirroring the template files."""
    AGENTS = "agents"
    ENTITY = "entity"
    CLAIM = "claim"


@dataclass
class WikiTimelineEntry:
    """A single entry in a wiki page's timeline / changelog."""
    timestamp: str
    action: str  # "created", "updated", "snapshot", "timeline_append"
    summary: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WikiTimelineEntry":
        return cls(**data)


@dataclass
class WikiSection:
    """A single section within a wiki page.

    Sections correspond to headings in the markdown template:
      - For AGENTS: each section describes one agent profile
      - For ENTITY: the main description, evidence, and relations sections
      - For CLAIM: the claim body, supporting/contradicting evidence
    """
    heading: str
    body: str
    level: int = 2  # markdown heading level (##)

    def to_markdown(self) -> str:
        prefix = "#" * self.level
        return f"{prefix} {self.heading}\n\n{self.body}"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WikiSection":
        return cls(**data)


@dataclass
class WikiPage:
    """A complete wiki page, combining frontmatter, sections, and timeline.

    This is the in-memory representation that WikiStore reads/writes.
    """
    page_type: WikiPageType
    title: str
    sections: List[WikiSection] = field(default_factory=list)
    timeline: List[WikiTimelineEntry] = field(default_factory=list)
    raw_content: Optional[str] = None  # original markdown if loaded from disk

    # Optional metadata
    entity_id: Optional[str] = None
    simulation_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def content_hash(self) -> str:
        """SHA-256 hash of the composed markdown for change detection."""
        md = self.to_markdown()
        return hashlib.sha256(md.encode("utf-8")).hexdigest()

    def to_markdown(self) -> str:
        """Compose full markdown from sections + timeline."""
        parts: List[str] = []

        # Title
        parts.append(f"# {self.title}\n")

        # Sections
        for section in self.sections:
            parts.append(section.to_markdown())
            parts.append("")  # blank line between sections

        # Timeline footer
        if self.timeline:
            parts.append("## Timeline\n")
            for entry in self.timeline:
                parts.append(
                    f"- **{entry.timestamp}** [{entry.action}] {entry.summary}"
                )
            parts.append("")

        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_type": self.page_type.value,
            "title": self.title,
            "sections": [asdict(s) for s in self.sections],
            "timeline": [asdict(t) for t in self.timeline],
            "entity_id": self.entity_id,
            "simulation_id": self.simulation_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WikiPage":
        sections = [WikiSection.from_dict(s) for s in data.get("sections", [])]
        timeline = [WikiTimelineEntry.from_dict(t) for t in data.get("timeline", [])]
        return cls(
            page_type=WikiPageType(data["page_type"]),
            title=data["title"],
            sections=sections,
            timeline=timeline,
            entity_id=data.get("entity_id"),
            simulation_id=data.get("simulation_id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class WikiMeta:
    """Metadata persisted as wiki_meta.json alongside wiki pages.

    Tracks content hashes for cache invalidation and freshness checks.
    """
    simulation_id: str
    pages: Dict[str, str] = field(default_factory=dict)  # page_name -> content_hash
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WikiMeta":
        return cls(**data)

    @classmethod
    def from_json(cls, text: str) -> "WikiMeta":
        return cls.from_dict(json.loads(text))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)