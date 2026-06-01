"""
Wiki Memory — Compiler

Deterministic extraction from simulation events, retrieved memories, and
case metadata into structured wiki pages.  **No LLM dependency** — all
extraction is rule-based.

The compiler is invoked after a report completes (or on-demand) and
writes a set of markdown pages via :class:`WikiStore`, plus appends a
JSONL audit trail to ``wiki_compile_log.jsonl``.

Typical call-site::

    from app.services.wiki_memory.wiki_store import WikiStore
    from app.services.wiki_memory.compiler import WikiCompiler

    store = WikiStore()
    store.initialize("sim_abc123")

    compiler = WikiCompiler(store)
    result = compiler.compile(
        simulation_id="sim_abc123",
        events=runner_state.rounds,        # List[RoundSummary]
        retrieved_memories=search_results,  # List[SearchResult | InsightForgeResult | …]
        case_metadata=project.to_dict(),     # dict
        documents=[{"name": "doc1.pdf", "path": "/…", "size": 1234}],
    )

    # result is a CompileResult with pages_updated, counts, etc.
    print(result.to_dict())
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .schemas import (
    WikiPage,
    WikiPageType,
    WikiSection,
    WikiTimelineEntry,
)


# ------------------------------------------------------------------
# Compile result
# ------------------------------------------------------------------

@dataclass
class CompileResult:
    """Structured result returned by :meth:`WikiCompiler.compile`.

    Mirrors the fields expected in ``wiki_compile_log.jsonl`` so it can
    be written directly.
    """
    simulation_id: str
    compile_ts: str
    pages_updated: List[str] = field(default_factory=list)
    claims_added: int = 0
    claims_modified: int = 0
    contradictions_added: int = 0
    source_artifacts: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    latency_ms: Optional[int] = None
    tokens_used: Optional[int] = None  # placeholder — always None for deterministic
    wiki_snapshot: Optional[str] = None  # deterministic content hash of compiled pages

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "compile_ts": self.compile_ts,
            "pages_updated": self.pages_updated,
            "claims_added": self.claims_added,
            "claims_modified": self.claims_modified,
            "contradictions_added": self.contradictions_added,
            "source_artifacts": self.source_artifacts,
            "errors": self.errors,
            "latency_ms": self.latency_ms,
            "tokens_used": self.tokens_used,
            "wiki_snapshot": self.wiki_snapshot,
        }


# ------------------------------------------------------------------
# Compiler
# ------------------------------------------------------------------

class WikiCompiler:
    """Compile structured simulation data into wiki pages.

    Parameters
    ----------
    store:
        A :class:`WikiStore` instance.  All file I/O goes through the
        store so that atomic writes, path safety, and hash-tracking are
        handled consistently.
    """

    def __init__(self, store: Any) -> None:
        """Accept a WikiStore instance.

        We type *store* as ``Any`` to avoid a hard import cycle —
        the caller must pass a fully-initialised ``WikiStore``.
        """
        self.store = store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compile(
        self,
        simulation_id: str,
        events: Optional[Sequence[Any]] = None,
        retrieved_memories: Optional[Sequence[Any]] = None,
        case_metadata: Optional[Dict[str, Any]] = None,
        documents: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> CompileResult:
        """Run the full compilation pipeline and persist all pages.

        Parameters
        ----------
        simulation_id:
            The simulation to compile wiki pages for.
        events:
            Simulation rounds.  Each element may be a ``RoundSummary``
            dataclass, an ``AgentAction`` dict, or any object with
            ``to_dict()``.
        retrieved_memories:
            Results from Zep search tools (``SearchResult``,
            ``InsightForgeResult``, ``PanoramaResult``, etc.).
        case_metadata:
            Project / simulation metadata dict.
        documents:
            List of document descriptors (``name``, ``path``, ``size``).

        Returns
        -------
        CompileResult — also appended to ``wiki_compile_log.jsonl``.
        """
        t0 = time.monotonic()
        result = CompileResult(
            simulation_id=simulation_id,
            compile_ts=datetime.now(timezone.utc).isoformat(),
        )

        # Ensure wiki directory exists
        self.store.initialize(simulation_id)

        # Normalise inputs to plain dicts
        events_dicts = self._normalise_list(events)
        mem_dicts = self._normalise_list(retrieved_memories)
        meta = case_metadata or {}
        doc_list = list(documents) if documents else []
        result.source_artifacts = [d.get("name", str(d)) for d in doc_list]

        # ------------------------------------------------------------------
        # 1. Extract structured data from raw inputs
        # ------------------------------------------------------------------
        entities: List[Dict[str, Any]] = []
        claims: List[Dict[str, Any]] = []
        contradictions: List[Dict[str, Any]] = []
        timeline_entries: List[Dict[str, Any]] = []
        source_entries: List[Dict[str, Any]] = []

        try:
            entities = self._extract_entities(events_dicts, mem_dicts)
            claims = self._extract_claims(events_dicts, mem_dicts)
            contradictions = self._extract_contradictions(claims)
            timeline_entries = self._extract_timeline(events_dicts)
            source_entries = self._extract_sources(doc_list, mem_dicts)
        except Exception as exc:
            result.errors.append(f"extraction_error: {exc}")

        # ------------------------------------------------------------------
        # 2. Build and write wiki pages
        # ------------------------------------------------------------------
        try:
            pages = self._build_pages(
                simulation_id=simulation_id,
                entities=entities,
                claims=claims,
                contradictions=contradictions,
                timeline_entries=timeline_entries,
                source_entries=source_entries,
                meta=meta,
            )
            for name, page in pages.items():
                try:
                    path = self.store.write_page(simulation_id, page)
                    result.pages_updated.append(name)
                except Exception as exc:
                    result.errors.append(f"write_error[{name}]: {exc}")
        except Exception as exc:
            result.errors.append(f"build_pages_error: {exc}")

        # ------------------------------------------------------------------
        # 3. Compute diffs for counts
        # ------------------------------------------------------------------
        result.claims_added = len(claims)
        result.claims_modified = 0  # diff would need previous compile; placeholder
        result.contradictions_added = len(contradictions)

        # ------------------------------------------------------------------
        # 3b. Compute deterministic wiki_snapshot from page content hashes
        # ------------------------------------------------------------------
        try:
            meta_obj = self.store._read_meta(simulation_id)
            # Sort page keys for deterministic ordering, then hash the
            # concatenation of (page_key, content_hash) pairs.
            sorted_pages = sorted(meta_obj.pages.items())
            snapshot_input = "|".join(f"{k}:{v}" for k, v in sorted_pages)
            result.wiki_snapshot = hashlib.sha256(
                snapshot_input.encode("utf-8")
            ).hexdigest()
        except Exception:
            # Best-effort: if meta read fails, leave wiki_snapshot as None
            pass

        # ------------------------------------------------------------------
        # 4. Persist compile log
        # ------------------------------------------------------------------
        result.latency_ms = int((time.monotonic() - t0) * 1000)
        self._append_compile_log(simulation_id, result.to_dict())

        return result

    # ------------------------------------------------------------------
    # Normalisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_list(items: Optional[Sequence[Any]]) -> List[Dict[str, Any]]:
        """Convert a heterogeneous list of dataclasses / dicts / objects
        into a list of plain dicts."""
        if not items:
            return []
        out: List[Dict[str, Any]] = []
        for item in items:
            if isinstance(item, dict):
                out.append(item)
            elif hasattr(item, "to_dict"):
                out.append(item.to_dict())
            elif hasattr(item, "__dict__"):
                out.append(vars(item))
            else:
                out.append({"raw": str(item)})
        return out

    # ------------------------------------------------------------------
    # Entity extraction
    # ------------------------------------------------------------------

    def _extract_entities(
        self,
        events: List[Dict[str, Any]],
        memories: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Extract unique entities from events and memory results.

        Each entity dict: ``id``, ``name``, ``type``, ``summary``,
        ``mentioned_in``, ``related_facts``.
        """
        seen: Dict[str, Dict[str, Any]] = {}

        # 1. From events — collect agent names as entities
        for ev in events:
            actions = ev.get("actions", [])
            if isinstance(actions, list):
                for act in actions:
                    self._add_entity_from_action(seen, act)
            else:
                # Single action dict
                self._add_entity_from_action(seen, ev)

        # 2. From memories — entity nodes and insights
        for mem in memories:
            for node in mem.get("nodes", []):
                if isinstance(node, dict):
                    eid = node.get("uuid") or node.get("name", "")
                    if eid and eid not in seen:
                        seen[eid] = {
                            "id": eid,
                            "name": node.get("name", eid),
                            "type": self._primary_label(node.get("labels", [])),
                            "summary": node.get("summary", ""),
                            "mentioned_in": [],
                            "related_facts": [],
                        }
            for insight in mem.get("entity_insights", []):
                if isinstance(insight, dict):
                    eid = insight.get("uuid") or insight.get("name", "")
                    if eid:
                        if eid in seen:
                            seen[eid]["summary"] = seen[eid].get("summary") or insight.get("summary", "")
                            for f in insight.get("related_facts", []):
                                if f not in seen[eid]["related_facts"]:
                                    seen[eid]["related_facts"].append(f)
                        else:
                            seen[eid] = {
                                "id": eid,
                                "name": insight.get("name", eid),
                                "type": insight.get("type", "entity"),
                                "summary": insight.get("summary", ""),
                                "mentioned_in": [],
                                "related_facts": list(insight.get("related_facts", [])),
                            }

        return list(seen.values())

    @staticmethod
    def _add_entity_from_action(
        seen: Dict[str, Dict[str, Any]],
        action: Dict[str, Any],
    ) -> None:
        """Add an agent entity from an action dict if not already known."""
        name = action.get("agent_name", "")
        aid = action.get("agent_id")
        if not name and aid is None:
            return
        key = str(aid) if aid is not None else name
        if key in seen:
            return
        seen[key] = {
            "id": key,
            "name": name or f"Agent-{aid}",
            "type": "agent",
            "summary": "",
            "mentioned_in": [action.get("round_num", 0)],
            "related_facts": [],
        }

    @staticmethod
    def _primary_label(labels: List[str]) -> str:
        """Return the most specific label from a list of graph labels."""
        for lbl in labels:
            if lbl not in ("Entity", "Node", "entity", "node"):
                return lbl
        return "entity"

    # ------------------------------------------------------------------
    # Claim extraction
    # ------------------------------------------------------------------

    def _extract_claims(
        self,
        events: List[Dict[str, Any]],
        memories: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Extract factual claims from Zep edges/facts.

        Each claim dict: ``id``, ``statement``, ``source``, ``entities``,
        ``evidence``.
        """
        claims: List[Dict[str, Any]] = []
        seen_facts: Dict[str, int] = {}  # fact text → claim index
        claim_id = 0

        # 1. From memory edges (Zep EdgeInfo dicts)
        for mem in memories:
            for edge in mem.get("edges", []):
                if isinstance(edge, dict):
                    fact = edge.get("fact", "")
                    if not fact:
                        continue
                    if fact in seen_facts:
                        idx = seen_facts[fact]
                        src = edge.get("source_node_name", "")
                        tgt = edge.get("target_node_name", "")
                        if src and src not in claims[idx]["entities"]:
                            claims[idx]["entities"].append(src)
                        if tgt and tgt not in claims[idx]["entities"]:
                            claims[idx]["entities"].append(tgt)
                        continue

                    seen_facts[fact] = claim_id
                    claims.append({
                        "id": f"claim_{claim_id:03d}",
                        "statement": fact,
                        "source": edge.get("name", "zep_edge"),
                        "entities": [
                            e for e in [
                                edge.get("source_node_name", ""),
                                edge.get("target_node_name", ""),
                            ] if e
                        ],
                        "evidence": [fact],
                    })
                    claim_id += 1

            # 2. From semantic_facts (InsightForgeResult)
            for fact_text in mem.get("semantic_facts", []):
                if isinstance(fact_text, str) and fact_text.strip():
                    ft = fact_text.strip()
                    if ft in seen_facts:
                        continue
                    seen_facts[ft] = claim_id
                    claims.append({
                        "id": f"claim_{claim_id:03d}",
                        "statement": ft,
                        "source": "semantic_search",
                        "entities": [],
                        "evidence": [ft],
                    })
                    claim_id += 1

            # 3. From plain facts list (SearchResult)
            for fact_text in mem.get("facts", []):
                if isinstance(fact_text, str) and fact_text.strip():
                    ft = fact_text.strip()
                    if ft in seen_facts:
                        continue
                    seen_facts[ft] = claim_id
                    claims.append({
                        "id": f"claim_{claim_id:03d}",
                        "statement": ft,
                        "source": "search_result",
                        "entities": [],
                        "evidence": [ft],
                    })
                    claim_id += 1

        return claims

    # ------------------------------------------------------------------
    # Contradiction detection
    # ------------------------------------------------------------------

    def _extract_contradictions(
        self,
        claims: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Detect potential contradictions among claims.

        Uses deterministic heuristics (negation words, numeric conflicts)
        rather than LLM calls.

        Each contradiction dict: ``id``, ``claim_ids``, ``description``.
        """
        contradictions: List[Dict[str, Any]] = []
        negation_patterns = [
            r"\b(not|no|never|nobody|nothing|neither|cannot|can't|don't|doesn't|didn't|won't|wouldn't|isn't|aren't|wasn't|weren't)\b",
        ]

        # Group claims by entities they mention
        entity_claims: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for c in claims:
            for ent in c.get("entities", []):
                entity_claims[ent.lower()].append(c)

        # Check for negation conflicts within the same entity's claims
        cid = 0
        for entity, entity_claim_list in entity_claims.items():
            if len(entity_claim_list) < 2:
                continue
            negated: List[Dict[str, Any]] = []
            affirmative: List[Dict[str, Any]] = []
            for c in entity_claim_list:
                stmt = c["statement"].lower()
                is_negated = any(re.search(pat, stmt) for pat in negation_patterns)
                if is_negated:
                    negated.append(c)
                else:
                    affirmative.append(c)
            if negated and affirmative:
                contradictions.append({
                    "id": f"contradiction_{cid:03d}",
                    "claim_ids": [c["id"] for c in negated + affirmative[:1]],
                    "description": (
                        f"Entity '{entity}' has both affirmative and negated claims: "
                        f"'{affirmative[0]['statement'][:80]}…' vs "
                        f"'{negated[0]['statement'][:80]}…'"
                    ),
                })
                cid += 1

        # Check for numeric conflicts in statements about the same entity
        for entity, entity_claim_list in entity_claims.items():
            nums_in_claims: List[Tuple[Dict[str, Any], List[float]]] = []
            for c in entity_claim_list:
                nums = [float(m) for m in re.findall(r"\b(\d+\.?\d*)\b", c["statement"])]
                if nums:
                    nums_in_claims.append((c, nums))
            for i in range(len(nums_in_claims)):
                for j in range(i + 1, len(nums_in_claims)):
                    c1, n1 = nums_in_claims[i]
                    c2, n2 = nums_in_claims[j]
                    if n1 != n2 and any(a != b for a in n1 for b in n2):
                        pair_key = tuple(sorted([c1["id"], c2["id"]]))
                        already = any(
                            tuple(sorted(c["claim_ids"])) == pair_key
                            for c in contradictions
                        )
                        if not already:
                            contradictions.append({
                                "id": f"contradiction_{cid:03d}",
                                "claim_ids": list(pair_key),
                                "description": (
                                    f"Potential numeric conflict for '{entity}': "
                                    f"'{c1['statement'][:80]}…' vs "
                                    f"'{c2['statement'][:80]}…'"
                                ),
                            })
                            cid += 1

        return contradictions

    # ------------------------------------------------------------------
    # Timeline extraction
    # ------------------------------------------------------------------

    def _extract_timeline(
        self,
        events: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build a chronological timeline from event data.

        Each entry: ``timestamp``, ``round_num``, ``summary``,
        ``actions_count``, ``platforms``, ``active_agents``.
        """
        timeline: List[Dict[str, Any]] = []

        for ev in events:
            actions = ev.get("actions", [])
            round_num = ev.get("round_num", ev.get("current_round", 0))
            start_time = ev.get("start_time", ev.get("timestamp", ""))
            simulated_hour = ev.get("simulated_hour", 0)

            platforms = set()
            action_count = 0
            for act in (actions if isinstance(actions, list) else []):
                if isinstance(act, dict):
                    platforms.add(act.get("platform", "unknown"))
                    action_count += 1

            timeline.append({
                "timestamp": start_time,
                "round_num": round_num,
                "simulated_hour": simulated_hour,
                "summary": (
                    f"Round {round_num}: {action_count} action(s) "
                    f"on {', '.join(sorted(platforms)) or 'no platform'}"
                ),
                "actions_count": action_count,
                "platforms": sorted(platforms),
                "active_agents": ev.get("active_agents", []),
            })

        # Sort by round number
        timeline.sort(key=lambda e: e.get("round_num", 0))
        return timeline

    # ------------------------------------------------------------------
    # Source extraction
    # ------------------------------------------------------------------

    def _extract_sources(
        self,
        documents: List[Dict[str, Any]],
        memories: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Compile source references from case documents and memory queries.

        Each source: ``name``, ``type``, ``description``, ``reference``.
        """
        sources: List[Dict[str, Any]] = []

        # 1. Case documents
        for doc in documents:
            sources.append({
                "name": doc.get("name", "unknown"),
                "type": "document",
                "description": f"Uploaded document ({_fmt_size(doc.get('size', 0))})",
                "reference": doc.get("path", ""),
            })

        # 2. Memory query sources
        for i, mem in enumerate(memories):
            query = mem.get("query", "")
            if query:
                sources.append({
                    "name": f"memory_query_{i + 1}",
                    "type": "memory_search",
                    "description": f"Zep search: '{query[:100]}'",
                    "reference": "",
                })
            total = mem.get("total_count", 0) or len(mem.get("facts", []))
            if total > 0:
                sources.append({
                    "name": f"memory_result_{i + 1}",
                    "type": "memory_result",
                    "description": f"{total} fact(s) retrieved via {mem.get('query', 'unknown query')[:60]}",
                    "reference": f"source_artifact:memory_{i + 1}",
                })

        return sources

    # ------------------------------------------------------------------
    # Page builders — returns {name: WikiPage} using WikiPageType
    # ------------------------------------------------------------------

    def _build_pages(
        self,
        simulation_id: str,
        entities: List[Dict[str, Any]],
        claims: List[Dict[str, Any]],
        contradictions: List[Dict[str, Any]],
        timeline_entries: List[Dict[str, Any]],
        source_entries: List[Dict[str, Any]],
        meta: Dict[str, Any],
    ) -> Dict[str, WikiPage]:
        """Assemble all wiki pages from extracted data.

        Root-level pages (index, timeline, sources, contradictions) use
        ``WikiPageType.AGENTS`` since the schema only has AGENTS /
        ENTITY / CLAIM.  Per-entity and per-claim pages use ENTITY and
        CLAIM respectively.

        Returns a mapping of page-name → WikiPage.
        """
        pages: Dict[str, WikiPage] = {}
        now = datetime.now(timezone.utc).isoformat()

        # ----------------------------------------------------------------
        # agents.md — agent knowledge page
        # ----------------------------------------------------------------
        agent_names = sorted({
            ent.get("name", ent.get("id", "unknown"))
            for ent in entities
            if ent.get("type") == "agent"
        })
        agent_sections: List[WikiSection] = []
        agent_sections.append(WikiSection(
            heading="Overview",
            body=(
                f"Simulation **{simulation_id}** agent knowledge base\n\n"
                f"- Agent entities: {len(agent_names)}\n"
                f"- Total entities: {len(entities)}\n"
                f"- Claims: {len(claims)}\n"
            ),
        ))
        if agent_names:
            agent_sections.append(WikiSection(
                heading="Agents",
                body="\n".join(f"- {name}" for name in agent_names),
            ))
        else:
            agent_sections.append(WikiSection(
                heading="Agents",
                body="No agent entities were extracted.",
            ))

        pages["agents"] = WikiPage(
            page_type=WikiPageType.AGENTS,
            title=f"Simulation {simulation_id} — Agents",
            sections=agent_sections,
            timeline=[WikiTimelineEntry(
                timestamp=now, action="compiled", summary="Agent knowledge compiled",
            )],
            simulation_id=simulation_id,
            created_at=now,
            updated_at=now,
        )

        # ----------------------------------------------------------------
        # index.md  (WikiPageType.AGENTS — reused as "top-level page")
        # ----------------------------------------------------------------
        index_sections: List[WikiSection] = []
        index_sections.append(WikiSection(
            heading="Overview",
            body=(
                f"Simulation **{simulation_id}**"
                + (f" — {meta.get('name', '')}" if meta.get("name") else "")
                + f"\n\n"
                f"- Entities: {len(entities)}\n"
                f"- Claims: {len(claims)}\n"
                f"- Contradictions: {len(contradictions)}\n"
                f"- Source artifacts: {len(source_entries)}\n"
                f"- Timeline rounds: {len(timeline_entries)}\n"
            ),
        ))
        index_sections.append(WikiSection(
            heading="Pages",
            body=(
                "- [Timeline](timeline.md)\n"
                "- [Sources](sources.md)\n"
                "- [Contradictions](contradictions.md)\n"
                f"- Entities ({len(entities)}): see `entities/` directory\n"
                f"- Claims ({len(claims)}): see `claims/` directory\n"
            ),
        ))

        pages["index"] = WikiPage(
            page_type=WikiPageType.AGENTS,
            title=f"Simulation {simulation_id} — Wiki Index",
            sections=index_sections,
            timeline=[WikiTimelineEntry(
                timestamp=now, action="compiled", summary="Wiki compiled",
            )],
            entity_id="index",
            simulation_id=simulation_id,
            created_at=now,
            updated_at=now,
        )

        # ----------------------------------------------------------------
        # timeline.md
        # ----------------------------------------------------------------
        tl_sections: List[WikiSection] = []
        tl_lines: List[str] = []
        for entry in timeline_entries:
            ts = entry.get("timestamp", "—")
            rn = entry.get("round_num", "?")
            sh = entry.get("simulated_hour", "")
            hour_str = f" (hour {sh})" if sh else ""
            platforms = entry.get("platforms", [])
            plat_str = ", ".join(platforms) if platforms else "—"
            agents = entry.get("active_agents", [])
            agents_str = ", ".join(str(a) for a in agents[:5])
            if len(agents) > 5:
                agents_str += f" +{len(agents) - 5} more"
            tl_lines.append(
                f"| {ts} | {rn} | {entry.get('actions_count', 0)} | {plat_str} | {agents_str} |"
            )
        tl_body = (
            "| Timestamp | Round | Actions | Platforms | Active Agents |\n"
            "|-----------|-------|---------|-----------|---------------|\n"
            + "\n".join(tl_lines)
            if tl_lines
            else "No timeline events recorded."
        )
        tl_sections.append(WikiSection(heading="Chronological Timeline", body=tl_body))

        pages["timeline"] = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Timeline",
            sections=tl_sections,
            timeline=[WikiTimelineEntry(
                timestamp=now, action="compiled", summary="Timeline compiled",
            )],
            entity_id="timeline",
            simulation_id=simulation_id,
            created_at=now,
            updated_at=now,
        )

        # ----------------------------------------------------------------
        # sources.md   (top-level index of all source artefacts)
        # ----------------------------------------------------------------
        src_sections: List[WikiSection] = []
        src_lines: List[str] = []
        for s in source_entries:
            src_lines.append(
                f"| {s['name']} | {s['type']} | {s['description']} |"
            )
        src_body = (
            "| Name | Type | Description |\n"
            "|------|------|-------------|\n"
            + "\n".join(src_lines)
            if src_lines
            else "No source artifacts recorded."
        )
        src_sections.append(WikiSection(heading="Source Artifacts", body=src_body))

        pages["sources"] = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Sources",
            sections=src_sections,
            timeline=[WikiTimelineEntry(
                timestamp=now, action="compiled", summary="Sources compiled",
            )],
            entity_id="sources",
            simulation_id=simulation_id,
            created_at=now,
            updated_at=now,
        )

        # ----------------------------------------------------------------
        # contradictions.md
        # ----------------------------------------------------------------
        ct_sections: List[WikiSection] = []
        if contradictions:
            ct_lines: List[str] = []
            for c in contradictions:
                ids = ", ".join(c["claim_ids"])
                ct_lines.append(f"### {c['id']}\n\n{c['description']}\n\n**Claims**: {ids}\n")
            ct_sections.append(WikiSection(
                heading="Detected Contradictions",
                body="\n".join(ct_lines),
            ))
        else:
            ct_sections.append(WikiSection(
                heading="Detected Contradictions",
                body="No contradictions detected in current data.",
            ))

        pages["contradictions"] = WikiPage(
            page_type=WikiPageType.AGENTS,
            title="Contradictions",
            sections=ct_sections,
            timeline=[WikiTimelineEntry(
                timestamp=now, action="compiled", summary="Contradictions compiled",
            )],
            entity_id="contradictions",
            simulation_id=simulation_id,
            created_at=now,
            updated_at=now,
        )

        # ----------------------------------------------------------------
        # Entity pages
        # ----------------------------------------------------------------
        for ent in entities:
            eid = ent.get("id", "unknown")
            slug = _sanitize_page_id(eid)
            ent_sections: List[WikiSection] = []

            # Summary
            summary = ent.get("summary", "") or "No summary available."
            ent_sections.append(WikiSection(heading="Description", body=summary))

            # Related facts
            facts = ent.get("related_facts", [])
            if facts:
                fact_body = "\n".join(f"- {f}" for f in facts)
                ent_sections.append(WikiSection(heading="Key Facts", body=fact_body))

            # Mentioned in rounds
            rounds = ent.get("mentioned_in", [])
            if rounds:
                rounds_body = f"Active in rounds: {', '.join(str(r) for r in sorted(set(rounds)))}"
                ent_sections.append(WikiSection(heading="Activity", body=rounds_body))

            pages[f"entity/{eid}"] = WikiPage(
                page_type=WikiPageType.ENTITY,
                title=ent.get("name", slug),
                sections=ent_sections,
                timeline=[WikiTimelineEntry(
                    timestamp=now,
                    action="compiled",
                    summary=f"Entity '{ent.get('name', slug)}' compiled",
                )],
                entity_id=eid,
                simulation_id=simulation_id,
                created_at=now,
                updated_at=now,
            )

        # ----------------------------------------------------------------
        # Claim pages
        # ----------------------------------------------------------------
        for cl in claims:
            cid = cl.get("id", "claim_unknown")
            # Note: entity_id field is repurposed as the claim's unique id
            # because WikiPageType.CLAIM uses entity_id for the filename
            cl_sections: List[WikiSection] = []

            # Statement
            cl_sections.append(WikiSection(
                heading="Claim Statement",
                body=cl.get("statement", "No statement."),
            ))

            # Source
            src = cl.get("source", "unknown")
            cl_sections.append(WikiSection(
                heading="Source",
                body=f"Extracted via: {src}",
            ))

            # Entities
            ents = cl.get("entities", [])
            if ents:
                ent_body = "\n".join(
                    f"- [[entity/{e}|{e}]]" for e in ents
                )
                cl_sections.append(WikiSection(heading="Related Entities", body=ent_body))

            # Evidence
            ev = cl.get("evidence", [])
            if ev:
                ev_body = "\n".join(f"> {e}" for e in ev)
                cl_sections.append(WikiSection(heading="Evidence", body=ev_body))

            pages[f"claim/{cid}"] = WikiPage(
                page_type=WikiPageType.CLAIM,
                title=cl.get("statement", cid)[:80],
                sections=cl_sections,
                timeline=[WikiTimelineEntry(
                    timestamp=now,
                    action="compiled",
                    summary=f"Claim '{cid}' compiled",
                )],
                entity_id=cid,
                simulation_id=simulation_id,
                created_at=now,
                updated_at=now,
            )

        return pages

    # ------------------------------------------------------------------
    # Compile-log persistence
    # ------------------------------------------------------------------

    def _append_compile_log(self, simulation_id: str, entry: Dict[str, Any]) -> str:
        """Append a JSON-line entry to ``wiki_compile_log.jsonl``.

        Returns the log file path.
        """
        wiki_dir = self.store._sim_wiki_dir(simulation_id)
        os.makedirs(wiki_dir, exist_ok=True)
        log_path = os.path.join(wiki_dir, "wiki_compile_log.jsonl")
        line = json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line)
        return log_path


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def _sanitize_page_id(text: str) -> str:
    """Sanitize a page/entity/claim ID for safe filesystem use.

    Delegates to WikiStore's _sanitize_id when available, falls back
    to basic slugify.
    """
    text = text.lower().strip()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_\-]", "", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_") or "untitled"


def _fmt_size(size: Any) -> str:
    """Format a byte size as a human-readable string."""
    try:
        size = int(size)
    except (ValueError, TypeError):
        return "unknown size"
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"