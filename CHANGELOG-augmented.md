# CHANGELOG-augmented: backtesting-feature-augmented branch

This branch extends `backtesting-baseline` with two S2 features
cherry-picked from PRs #14 and #23. It preserves all the S1/S2/S3
research artefacts (cases/, runs/, backtesting/) from the baseline
and adds the features **without** the PR #31 integration work
(no Fusion LLM, no flatten fix, no SIMULATION_LLM_, no Tavily).

## Base

Branched from `backtesting-baseline` (commit `002ccb21`), which itself
branches from `83829b1` (pre-PR#31 S3 dedup baseline).

## Features added (top of baseline)

### 1. Multi-model agents + LLM observability (from PR #14, --no-ff merge `c41cdc8`)

New code:
- `backend/app/services/model_router.py` — routing with precedence
  `by_agent_id > by_role > default`, secrets via env only.
- `backend/app/services/llm_telemetry.py` — per-call tokens/latency/cost/
  hashes/JSON-validity/round, wrapping the CAMEL backend instance.
- `backend/tests/test_model_routing.py` — unit tests for routing
  precedence and secret hygiene.

New configs and scripts:
- `configs/model_map_example.yaml` — example per-agent routing map.
- `configs/model_prices.yaml` — per-model price table for cost estimation.
- `scripts/export_telemetry.py` — stdlib-only CSV+JSONL export.
- `tools/watchdog_40rounds.sh` — guard script for long simulations.

New docs:
- `docs/multimodel_agents.md`
- `docs/local-llm-2agent-2model-notes.md`
- `docs/local-llm-qwen-smoke.md`
- `docs/s1-heterogeneous-llm-agents-evidence.md`

New smoke artefacts:
- `runs/smoke_multimodel/` — `agent_model_map.gemini.yaml`,
  `llm_telemetry.jsonl`, `model_routing_audit.jsonl`,
  `telemetry.csv`, `telemetry_summary.jsonl`.

Integration in `run_reddit_simulation.py` (added by PR #14 merge).

### 2. Wiki-backed Report Memory (from PR #23, --no-ff merge `93b9164`)

New code:
- `backend/app/services/wiki_memory/__init__.py`
- `backend/app/services/wiki_memory/wiki_store.py` — `WikiStore`
- `backend/app/services/wiki_memory/wiki_compiler.py` — `WikiCompiler`
- `backend/app/services/wiki_memory/compiler.py` — `build_wiki_context_for_report(...)`
- `backend/app/services/wiki_memory/schemas.py`
- `backend/app/services/wiki_memory/templates/{agents,claim,entity}.md`

New tests (5 files):
- `tests/test_wiki_memory.py`
- `tests/test_wiki_memory_additional.py`
- `tests/test_wiki_compiler.py`
- `tests/test_wiki_report_integration.py`
- `tests/test_wiki_smoke.py`

New scripts and docs:
- `scripts/real_lite_smoke.py` — bounded real-lite smoke for wiki.
- `docs/wiki_backed_report_memory.md`

Integration in `report_agent.py` via the `<wiki_audit_context>` tag (the
wiki context is injected into ReportAgent prompts; non-fatal fallback
to `wiki_context=None` on error/missing data).

## What was NOT added (and why)

These features exist on main but are **intentionally excluded** from
this branch because they came in after the chosen baseline (`83829b1`):

| Feature | Excluded | Source on main | Why excluded |
|---|---|---|---|
| `SIMULATION_LLM_*` env vars | ✓ | `f20bfd9` | Pre-PR#31 baseline; not relevant for backtesting research. |
| Multi-model LLM client (Fusion) | ✓ | cherry-pick `feat/pr318-600-cherrypick` | Pre-PR#31 baseline; the LLM client is pre-Fusion. |
| `_clean_json_response` | ✓ | cherry-pick `feat/pr318-600-cherrypick` | Pre-PR#31 baseline. |
| `_flatten_for_neo4j` | ✓ | PR #31 commit `02df297` | Pre-PR#31 baseline; the CypherTypeError bug exists in this branch by design. |
| Tavily search provider | ✓ | PR #27 | Pre-PR#31 baseline; `deep_search.py` is the older DuckDuckGo-only version. |
| Wiki memory codebase enhancements (PR #23 had additional) | partial | PR #23 | The full PR #23 history was merged via `--no-ff`, so all wiki commits are present. |

## Conflict resolution

The merge of PR #23 had a single content conflict in `.gitignore`. It
was resolved by taking the PR's version of `.gitignore` (the feature-
augmented `.gitignore` is the canonical one used for the multi-model
and wiki features).

All other files merged cleanly because the baseline branch's older
state of shared files (`config.py`, `simulation_manager.py`, etc.)
was on the same side as the PR's modifications in most cases.

## How to activate the new features

### Multi-model

```bash
# 1. Set up env vars for the models you want to route to
export LLM_API_KEY=...
export OPENAI_API_KEY=...
export GEMINI_API_KEY=...

# 2. Use the example map or write your own
cp configs/model_map_example.yaml configs/agent_model_map.yaml
# Edit configs/agent_model_map.yaml with your agents and roles

# 3. Run with --model-map
cd backend
python scripts/run_reddit_simulation.py --model-map ../configs/agent_model_map.yaml

# 4. Inspect telemetry
cat runs/smoke_multimodel/llm_telemetry.jsonl
cat runs/smoke_multimodel/model_routing_audit.jsonl
python scripts/export_telemetry.py  # CSV summary
```

### Wiki memory

```bash
# 1. Run the smoke (standalone, no Neo4j required)
cd backend
python scripts/real_lite_smoke.py

# 2. Or trigger wiki compilation from a real run
# The wiki is built during the ReportAgent's planning step.
# Set WIKI_OUTPUT_DIR in your env to control where artefacts are written.
export WIKI_OUTPUT_DIR=/tmp/wiki_test
```

## Test commands

```bash
# Wiki tests (5 files, all standalone — no Neo4j required)
cd backend
.venv/bin/python -m pytest ../tests/test_wiki_memory.py ../tests/test_wiki_memory_additional.py ../tests/test_wiki_compiler.py ../tests/test_wiki_report_integration.py ../tests/test_wiki_smoke.py -v

# Multi-model routing tests (1 file, standalone)
.venv/bin/python -m pytest ../backend/tests/test_model_routing.py -v
```

## Known limitations of this branch

1. **CypherTypeError bug exists**: this branch has the pre-flatten-fix
   `graphiti_backend.py`. If you save EntityNode/Edge with nested
   dicts in `attributes`, Neo4j will reject with `Encountered: Map{}`.
   The fix exists on main (commit `02df297`) but is intentionally not
   backported here. If you need to save such entities, cherry-pick the
   flatten fix on top, or use a different Neo4j version that auto-
   flattens.

2. **LLM client is pre-Fusion**: the cascading fallback, structured
   output plugin, and `_clean_json_response` are not available. If
   the underlying LLM returns prose-prefixed JSON or unbalanced
   brackets, parsing may fail. This is acceptable for backtesting
   (where the prompt is well-controlled) but not for production.

3. **No S3 dedup of isolated nodes at the level of PR #27**: the
   baseline has the S3 dedup, but the PR #23 wiki integration may
   have changed graphiti_backend.py in ways that interact with it.
   See `git log backtesting-baseline..HEAD -- backend/app/graph/graphiti_backend.py`
   for the actual diff.

## Source PRs

- #14: `codex/s1-local-llm-spike` (closes #8, #21) — `c41cdc8`
- #23: `issue-20-s2-memory-feature` (closes #20) — `93b9164`

See also:
- `../CHANGELOG-research.md` — what is in `backtesting-baseline`
- `../backtesting/README.md` — index of the S1/S2/S3 research artefacts
