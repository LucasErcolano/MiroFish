# Wiki-Backed Report Memory

> **Status**: Production — integrated into ReportAgent pipeline (opt-in, defaults to `None`)

This document covers the wiki_memory module: a deterministic, filesystem-backed memory layer that compiles simulation context into markdown pages and injects them into ReportAgent prompts as prior knowledge.

---

## 1. Architecture Overview

```
Simulation events / Zep memories / Case metadata
        │
        ▼
  ┌──────────────┐
  │ WikiCompiler  │  ← deterministic extraction (no LLM)
  └──────┬───────┘
         │ .compile()
         ▼
  ┌──────────────┐
  │   WikiStore   │  ← filesystem CRUD, atomic writes, path safety
  └──────┬───────┘
         │ wiki directory on disk:
         │   uploads/simulations/{sim_id}/wiki/
         │     ├── agents.md
         │     ├── entities/{id}.md
         │     ├── claims/{id}.md
         │     └── wiki_meta.json
         ▼
  ┌──────────────────────────────┐
  │ build_wiki_context_for_report│  ← convenience helper
  └──────────────┬───────────────┘
                 │ returns str | None
                 ▼
  ┌──────────────────┐
  │   ReportAgent    │  ← wiki_context injected into prompts
  └──────────────────┘
```

### Key design decisions

| Decision | Rationale |
|----------|-----------|
| **Filesystem-backed** (no database) | Simple, inspectable, no infra dependency |
| **Atomic writes** (temp file + `os.replace`) | Crash safety — no partial writes |
| **Path safety** (`_sanitize_id` + `_safe_join`) | No directory traversal attacks |
| **Deterministic compilation** (no LLM) | Fast, reproducible, no token cost |
| **Opt-in injection** (`wiki_context=None` default) | Zero regression risk — baseline unchanged |
| **Budget-capped context** (`max_chars=8000`) | ≈ 2000 tokens, keeps prompt budget manageable |

---

## 2. Module Layout

```
backend/app/services/wiki_memory/
├── __init__.py          # Public API + build_wiki_context_for_report()
├── schemas.py           # WikiPage, WikiSection, WikiPageType, WikiTimelineEntry, WikiMeta
├── wiki_store.py         # WikiStore — CRUD, timeline, snapshots, compile_wiki_context
├── compiler.py           # WikiCompiler + CompileResult
└── templates/
    ├── agents.md         # Template for AGENTS pages
    ├── entity.md         # Template for ENTITY pages
    └── claim.md          # Template for CLAIM pages
```

### Test files

```
tests/
├── test_wiki_memory.py               # WikiStore, schemas, path safety, atomic writes
├── test_wiki_compiler.py             # WikiCompiler, CompileResult, extraction pipeline
└── test_wiki_report_integration.py   # build_wiki_context_for_report, ReportAgent injection
```

---

## 3. Public API

### 3.1 WikiStore

```python
from app.services.wiki_memory import WikiStore, WikiPage, WikiPageType, WikiSection

store = WikiStore()                    # uses Config.UPLOAD_FOLDER
store = WikiStore(wiki_root="/tmp/s")  # override root for testing

# Lifecycle
wiki_dir = store.initialize("sim_abc123")

# Write
page = WikiPage(
    page_type=WikiPageType.AGENTS,
    title="Simulation Agents",
    sections=[WikiSection(heading="Overview", body="5 agents active.")],
    simulation_id="sim_abc123",
)
path = store.write_page("sim_abc123", page)

# Read
page = store.read_page("sim_abc123", WikiPageType.AGENTS)
page = store.read_entity_page("sim_abc123", "john_doe")
page = store.read_claim_page("sim_abc123", "claim_001")

# List
entities = store.list_entities("sim_abc123")
claims = store.list_claims("sim_abc123")

# Timeline
entry = store.append_timeline("sim_abc123", WikiPageType.AGENTS,
                               action="updated", summary="Added new section")

# Snapshot (best-effort, does not raise on failure)
snap_path = store.commit_snapshot("sim_abc123")

# Compile context for ReportAgent (capped at max_chars)
context = store.compile_wiki_context("sim_abc123", max_chars=8000)
# Returns "" if no pages exist, otherwise concatenated markdown

# Delete
store.delete_page("sim_abc123", WikiPageType.AGENTS)
```

### 3.2 WikiCompiler

```python
from app.services.wiki_memory import WikiStore, WikiCompiler

store = WikiStore(wiki_root="/tmp/simulations")
store.initialize("sim_abc123")

compiler = WikiCompiler(store)
result = compiler.compile(
    simulation_id="sim_abc123",
    events=[...],              # List[RoundSummary | dict]
    retrieved_memories=[...],  # List[SearchResult | dict]
    case_metadata={...},       # dict
    documents=[...],           # List[dict] with name/path/size
)

# result is a CompileResult dataclass:
#   .simulation_id, .compile_ts, .pages_updated, .claims_added,
#   .claims_modified, .contradictions_added, .source_artifacts,
#   .errors, .latency_ms, .tokens_used (always None for deterministic)
print(result.to_dict())
```

The compiler produces these wiki pages:
- **index.md** — top-level overview (entity/claim/contradiction/source counts)
- **AGENTS.md** — agent knowledge page
- **timeline.md** — chronological event timeline (markdown table)
- **sources.md** — source artifact index (markdown table)
- **contradictions.md** — detected contradictions between claims
- **entities/{id}.md** — per-entity page
- **claims/{id}.md** — per-claim page

A JSONL audit trail (`wiki_compile_log.jsonl`) is appended to the wiki directory on every compile.

### 3.3 build_wiki_context_for_report

```python
from app.services.wiki_memory import build_wiki_context_for_report

# Convenience helper — tries existing pages, falls back to compiling from raw data
wiki_context = build_wiki_context_for_report(
    "sim_abc123",
    max_chars=8000,
    wiki_root="/tmp/simulations",  # optional override
    events=[...],                   # optional raw data
    retrieved_memories=[...],       # optional raw data
    case_metadata={...},            # optional raw data
    documents=[...],                # optional raw data
)

# Returns str (markdown) or None (no wiki data available)
# Gracefully degrades — any exception returns None
```

### 3.4 ReportAgent Integration

```python
from app.services.report_agent import ReportAgent

# Without wiki context (baseline — unchanged behavior)
agent = ReportAgent(graph_id="g1", simulation_id="sim1",
                    simulation_requirement="...", llm_client=llm, zep_tools=zep)

# With wiki context (opt-in)
wiki_context = build_wiki_context_for_report("sim1")
agent = ReportAgent(graph_id="g1", simulation_id="sim1",
                    simulation_requirement="...",
                    llm_client=llm, zep_tools=zep,
                    wiki_context=wiki_context)
```

When `wiki_context` is set:
- `plan_outline` injects it into the user prompt as prior knowledge.
- `_generate_section_react` injects it into the system prompt.
- Each injection is wrapped in a `<wiki_audit_context>` XML block with a disclaimer: *"This is prior knowledge from earlier simulation runs, NOT verified ground truth."*

When `wiki_context` is `None` (the default), no injection occurs and behavior is identical to before.

---

## 4. Data Flow

```
1. Simulation runs → events, memories, documents produced

2. WikiCompiler.compile(events, memories, metadata, documents)
   ├── _extract_entities()      → entities list
   ├── _extract_claims()        → claims list
   ├── _extract_contradictions() → contradictions list
   ├── _extract_timeline()      → timeline entries
   ├── _extract_sources()       → source entries
   └── _build_pages()           → {index, agents, timeline, sources,
                                    contradictions, entities/*, claims/*}
       → WikiStore.write_page() for each page
       → append to wiki_compile_log.jsonl

3. build_wiki_context_for_report(sim_id)
   ├── Try: WikiStore.compile_wiki_context(sim_id)
   │     → read all pages, concatenate markdown ≤ max_chars
   ├── Fallback: WikiCompiler.compile() → then re-read
   └── Return str | None

4. ReportAgent.__init__(wiki_context=context_str)
   └── Stored as self.wiki_context
       ├── plan_outline: injects into user prompt
       └── _generate_section_react: injects into system prompt
```

---

## 5. Storage Layout

```
uploads/simulations/{simulation_id}/wiki/
├── agents.md                    # AGENTS page (agent knowledge)
├── index.md                     # top-level summary page
├── timeline.md                  # chronological timeline
├── sources.md                   # source artifact index
├── contradictions.md            # contradiction summary
├── entities/
│   ├── john_doe.md              # Per-entity page
│   └── jane_smith.md
├── claims/
│   ├── claim_000.md             # Per-claim page
│   └── claim_001.md
├── wiki_meta.json               # Hash tracking, timestamps
├── wiki_compile_log.jsonl       # Append-only audit trail
└── .snapshots/                   # Timestamped backups
    └── 20260601T120000/
```

---

## 6. Contradiction Detection

The compiler uses **deterministic heuristics** (no LLM) to detect contradictions:

1. **Negation conflicts**: If the same entity has both affirmative and negated claims (e.g., "Agent A is active" vs "Agent A is not active").

2. **Numeric conflicts**: If the same entity has claims with different numbers (e.g., "Agent A posted 5 times" vs "Agent A posted 3 times").

Detected contradictions are written to the `contradictions` wiki page and included in the audit context.

---

## 7. Limitations

- **No LLM extraction**: All entity/claim/contradiction extraction is rule-based. Complex or implicit claims won't be detected.
- **No file locking**: Atomic writes prevent partial writes, but concurrent WikiStore instances could race on the same file. The JSONL append pattern (one line per compile) mitigates this.
- **compile_wiki_context truncation**: When content exceeds `max_chars`, pages are skipped or truncated. This means large wikis may lose less important pages.
- **Template parsing**: `_parse_sections_from_md` uses regex-based heading extraction. Complex or malformed markdown may not parse perfectly.
- **No incremental compilation**: Each `compile()` call rebuilds all pages from scratch. There's no diffing or incremental update.
- **WikiPageType schema limitation**: Root-level pages (index, timeline, sources, contradictions) are stored as `WikiPageType.AGENTS` because the enum only has AGENTS/ENTITY/CLAIM. The filename routing uses the `entity_id` field for claim pages.

---

## 8. Testing

### Running the test suite

```bash
# All wiki memory tests
python -m pytest tests/test_wiki_memory.py tests/test_wiki_compiler.py tests/test_wiki_report_integration.py -v

# Quick smoke (WikiStore + compiler only, no ReportAgent import)
python -m pytest tests/test_wiki_memory.py tests/test_wiki_compiler.py -v
```

### Test coverage by area

| Area | Tests |
|------|-------|
| Path safety (`_sanitize_id`, `_safe_join`) | `TestPathSafety` (7 tests) |
| Atomic writes | `TestAtomicWrite` (3 tests) |
| Schema round-trips | `TestWikiSection`, `TestWikiPage`, `TestWikiMeta` |
| WikiStore CRUD | `TestWikiStore` — initialize, write, read, list, delete, create_from_template |
| Timeline | `TestWikiStore::test_append_timeline` |
| Snapshots | `TestWikiStore::test_commit_snapshot` |
| compile_wiki_context | `TestWikiStore::test_compile_wiki_context`, `test_compile_wiki_context_truncation` |
| WikiCompiler | `TestWikiCompiler` — compile from events, memories, full pipeline, empty inputs, compile log, contradictions |
| Integration | `TestBuildWikiContextForReport` — no data, existing pages, compile from raw, truncation, error degradation |
| ReportAgent injection | `TestReportAgentWikiContextIntegration` — init, defaults, prompt injection |

### Smoke test

```bash
python -m pytest tests/test_wiki_smoke.py -v
```

This smoke test creates a wiki directory with all required artifacts and validates the output structure.

---

## 9. Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `WikiStore.WIKI_ROOT` | `Config.UPLOAD_FOLDER/simulations` | Root directory for all wiki data |
| `WikiStore.MAX_FILE_SIZE` | 10 MB | Max file size for read operations |
| `max_chars` (compile_wiki_context) | 8000 | Character budget for ReportAgent context (~2000 tokens) |
| `WikiCompiler` store type | `Any` | Accepts WikiStore, typed loose to avoid circular imports |

All parameters are explicitly configurable in tests via `wiki_root` override — no dependency on Flask app config.

---

## 10. MVP Activation

The wiki memory feature is **opt-in and non-invasive**. It defaults to inactive (no changes to existing behavior) and activates only through explicit code paths — no config flags, environment variables, or feature toggles are involved.

### 10.1 Baseline behavior (no activation)

When `wiki_context` is not provided (the default), `ReportAgent` behaves identically to before the feature was introduced:

```python
# DEFAULT: no wiki context, unchanged baseline
agent = ReportAgent(
    graph_id="g1",
    simulation_id="sim1",
    simulation_requirement="...",
    llm_client=llm,
    zep_tools=zep,
)
# agent.wiki_context is None → no prompt injection, no wiki I/O
```

No file I/O, no import side effects, no prompt modifications. The module can be imported safely without activating anything.

### 10.2 Activation path 1 — Explicit `wiki_context` parameter

The direct way: compute the context string yourself and pass it to `ReportAgent`:

```python
from app.services.wiki_memory import build_wiki_context_for_report

wiki_context = build_wiki_context_for_report("sim_abc123")
# Returns str (markdown) or None (no wiki data available)

agent = ReportAgent(
    graph_id="g1",
    simulation_id="sim1",
    simulation_requirement="...",
    llm_client=llm,
    zep_tools=zep,
    wiki_context=wiki_context,  # ← explicit opt-in
)
```

When `wiki_context` is a non-empty string:
- `plan_outline` wraps it in a `<wiki_audit_context>` XML block and appends it to the user prompt.
- `_generate_section_react` wraps it in a `<wiki_audit_context>` XML block and appends it to the system prompt.
- Both injections include the disclaimer: *"This is prior knowledge from earlier simulation runs, NOT verified ground truth."*

When `wiki_context` is `None` (the return value when no wiki data exists): no injection occurs, baseline behavior.

### 10.3 Activation path 2 — `wiki_context` via file path

`WikiStore` reads wiki pages from the filesystem at `uploads/simulations/{sim_id}/wiki/`. If a previous `WikiCompiler.compile()` run has written pages to this directory, `build_wiki_context_for_report` will find and assemble them — no config flag needed. The "activation" is simply that compiled pages exist on disk:

```python
# Step 1: Compile wiki pages from simulation data (one-time or per-run)
from app.services.wiki_memory import WikiStore, WikiCompiler

store = WikiStore()  # uses default Config.UPLOAD_FOLDER
store.initialize("sim_abc123")

compiler = WikiCompiler(store)
result = compiler.compile(
    simulation_id="sim_abc123",
    events=runner_state.rounds,
    retrieved_memories=search_results,
    case_metadata=project.to_dict(),
    documents=[{"name": "doc1.pdf", "size": 1234}],
)
# Pages are now written to uploads/simulations/sim_abc123/wiki/

# Step 2: On next report generation, the compiled pages are picked up
wiki_context = build_wiki_context_for_report("sim_abc123")
# Returns the assembled markdown from the wiki/ directory
```

The `wiki_context` argument to `build_wiki_context_for_report` accepts an optional `wiki_root` parameter for test overrides:

```python
# In tests, use a tmpdir:
wiki_context = build_wiki_context_for_report(
    "sim_test",
    wiki_root="/tmp/test_simulations",
)
```

### 10.4 What `build_wiki_context_for_report` does internally

1. Creates a `WikiStore` (optionally with a custom `wiki_root`).
2. Calls `store.initialize(simulation_id)` to ensure the wiki directory exists.
3. Attempts `store.compile_wiki_context(simulation_id)` to read existing pages.
4. If no pages exist yet and raw data was provided (`events`, `retrieved_memories`, `case_metadata`, `documents`), compiles from scratch via `WikiCompiler.compile()`, then re-reads.
5. Returns the assembled markdown string (capped at `max_chars`), or `None` if no wiki data is available.
6. On any exception, logs the error and returns `None` (graceful degradation — never crashes the pipeline).

### 10.5 Key contract: no hidden activation

- There is **no config flag** or environment variable that activates wiki memory. It is purely code-path driven.
- The `wiki_context` parameter on `ReportAgent.__init__` defaults to `None`.
- `build_wiki_context_for_report` is a convenience function, not a hook. It must be called explicitly.
- The feature is safe to import in any context: `from app.services.wiki_memory import WikiStore, WikiCompiler` has no side effects beyond module loading.

---

## 11. Limitations

- **No LLM extraction**: All entity/claim/contradiction extraction is rule-based. Complex or implicit claims will not be detected.
- **No file locking**: Atomic writes prevent partial writes, but concurrent WikiStore instances could race on the same file. The JSONL append pattern (one line per compile) mitigates this.
- **compile_wiki_context truncation**: When content exceeds `max_chars`, pages are skipped or truncated. Large wikis may lose less important pages.
- **Template parsing**: `_parse_sections_from_md` uses regex-based heading extraction. Complex or malformed markdown may not parse perfectly.
- **No incremental compilation**: Each `compile()` call rebuilds all pages from scratch. There is no diffing or incremental update.
- **WikiPageType schema limitation**: Root-level pages (index, timeline, sources, contradictions) are stored as `WikiPageType.AGENTS` because the enum only has AGENTS/ENTITY/CLAIM. The filename routing uses the `entity_id` field for claim pages.