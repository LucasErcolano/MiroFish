# Merge Ledger

This file records every source import, merge, cherry-pick, conflict, and
validation decision. Update it during the cleanup work.

## Initial Preparation

- Date: 2026-07-09
- Worktree: `C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish-stable-cleanup`
- Branch: `codex/stable-fork-cleanup`
- Base: `origin/feat/ui-observability-dock`
- Status: preparation only; no branch imports started.

## Source Branch Summary

| Branch | Intended Use | Direct Merge? | Notes |
| --- | --- | --- | --- |
| `origin/feat/ui-observability-dock` | Base branch | Already base | Closest to current functional UI. |
| `origin/backtesting-feature-augmented` | Backtesting/multimodel/wiki/IPCs | No, import selectively | Contains baseline; also contains many raw artifacts. |
| `origin/backtesting-baseline` | Reference for baseline docs/results | Usually no | Ancestor of augmented at prep time. |
| `origin/feat/issue-28-linea6-entropia` | Entropy/linea6 feature | No | Older base; direct merge would delete modern files. |

## Import Entries

Add entries below as work starts.

### 2026-07-09 Preflight

Date: 2026-07-09
Source branch/commit: none
Import method: none
Files/areas touched: `docs/repo-cleanup/AGENT_STATE.md`,
`docs/repo-cleanup/MERGE_LEDGER.md`
Conflicts: none
Decision: Proceed from `codex/stable-fork-cleanup` based on
`origin/feat/ui-observability-dock`. Keep `origin/backtesting-baseline` as
reference because it is an ancestor of `origin/backtesting-feature-augmented`.
Do not directly merge `origin/feat/issue-28-linea6-entropia`.
Validation: branch relationship checks passed.
Notes: Current cleanup HEAD before imports is
`58af26d52b6778a50ed48fe818000415a36c044e`.

### Template

```text
Date:
Source branch/commit:
Import method:
Files/areas touched:
Conflicts:
Decision:
Validation:
Notes:
```

### 2026-07-09 Backtesting Runtime Import Phase 1

Date: 2026-07-09
Source branch/commit: `origin/backtesting-feature-augmented`
(`fce57385eb511c9b57d95a01cd8a640bd6669e6a`)
Import method: selective `git checkout <branch> -- <paths>` plus manual
patches.
Files/areas touched:

- runtime: `backend/scripts/run_reddit_simulation.py`,
  `backend/app/services/simulation_runner.py`,
  `backend/app/services/model_router.py`,
  `backend/app/services/simulation_config_generator.py`,
  `backend/app/graph/graphiti_backend.py`
- support services: `capture_artifacts.py`, `structured_report_agent.py`,
  `report_agent_s2_verdict.py`, `worldbuilding_trace.py`
- tools/configs: `tools/mirofish_headless.py`, `tools/local_embedding_server.py`,
  `configs/model_map_s2.yaml`, `scripts/set-s2-hosted-env.example.ps1`
- tests: focused S2/model-map/Graphiti/worldbuilding/Zep fallback tests
- compact fixtures/results: S2 positional-noise and positional-noise-v2 plans,
  docs, configs, summaries, and CSV/JSON/MD evaluations; raw run/output
  directories excluded.

Conflicts: no Git merge conflicts. `run_reddit_simulation.py` and
`simulation_runner.py` were patched manually to preserve the UI branch behavior
while adding scheduled events and multi-model flags.
Decision: keep UI/observability branch as base; import only runtime and compact
research evidence needed by tests/docs.
Validation:

- `uv run --frozen --python 3.11 python -m py_compile ...` passed for edited
  backend runtime files.
- `uv run --frozen --python 3.11 pytest tests/test_s2_scheduled_injection.py
  tests/test_simulation_runner_model_map.py tests/test_graphiti_dedup_bypass.py
  -q` passed: 10 tests.

Notes: `backend/.venv/` was created by `uv` locally and must remain untracked.

### 2026-07-09 Backtesting Memory/Wiki/Matrix Import Phase 2

Date: 2026-07-09
Source branch/commit: `origin/backtesting-feature-augmented`
(`fce57385eb511c9b57d95a01cd8a640bd6669e6a`)
Import method: selective `git checkout <branch> -- <paths>` plus compatibility
patches.
Files/areas touched:

- memory/wiki code: `backend/app/services/experimental_memory.py`,
  `memory_factory.py`, `memory_provider.py`, `llm_telemetry.py`,
  `backend/app/services/wiki_memory/`
- configs: `configs/model_map_example.yaml`, `configs/model_prices.yaml`
- dependency metadata: `backend/pyproject.toml`, `backend/uv.lock`
- compact backtesting docs/scripts/summaries:
  `backtesting/final-multimodel/`,
  `backtesting/ipc-trimodel-multiagent/`, and
  `backtesting/s3-cross-topic-injection/` control docs, matrices, scripts,
  ledgers, and summary CSV/JSON/MD reports.

Conflicts: no Git merge conflicts. `experimental_memory.py` was rewritten to
preserve the imported experimental-memory API while using ChromaDB only when an
embedder is configured and JSON fallback for offline tests.
Decision: commit code, configs, docs, scripts, and compact result summaries;
skip raw per-run databases, traces, and generated run directories.
Validation:

- `uv lock --python 3.11` succeeded after adding `chromadb>=0.5.0` and the
  `neo4j==5.23.0` uv override required by `camel-oasis`.
- `uv run --frozen --python 3.11 pytest tests/test_model_router.py
  tests/test_model_routing.py tests/test_experimental_memory.py
  ../tests/test_wiki_memory.py ../tests/test_wiki_memory_additional.py
  ../tests/test_wiki_compiler.py ../tests/test_wiki_report_integration.py
  ../tests/test_wiki_smoke.py -q` passed: 142 tests.

Notes: `tests/test_wiki_smoke.py` path comparison was normalized to `/` for
Windows compatibility.

### 2026-07-09 Entropy / Linea 6 Import

Date: 2026-07-09
Source branch/commit: `origin/feat/issue-28-linea6-entropia`
Import method: selective `git checkout <branch> -- <paths>`.
Files/areas touched:

- research package: `backend/app/research/`
- scripts: `backend/scripts/entropy_*.py`,
  `backend/scripts/export_run_bundle.py`,
  `backend/scripts/gen_qwen_standalone_sim.py`,
  `scripts/run_linea6_multiprovider_parallel.py`
- tests: `tests/test_entropy_metrics.py`,
  `tests/test_checkpoints_temporal.py`, `tests/test_run_bundle.py`,
  `tests/test_simulation_db.py`
- docs: `docs/linea6_entropia.md`,
  `docs/linea6_comparison_gemma_vs_llama.md`,
  `docs/linea6_comparison_3models.md`
- compact dataset/case: `backtesting/case-b-s2-bolivia-2025-runoff/`

Conflicts: none. Direct merge explicitly avoided because the branch deletes
modern UI/backtesting files when diffed against the current base.
Decision: import only isolated research code, scripts, tests, Linea 6 docs, and
the Bolivia temporal case data required by those workflows.
Validation:

- `uv run --frozen --python 3.11 python -m py_compile ...` passed for entropy
  research modules and scripts.
- `uv run --frozen --python 3.11 pytest ../tests/test_entropy_metrics.py
  ../tests/test_checkpoints_temporal.py ../tests/test_run_bundle.py
  ../tests/test_simulation_db.py -q` passed: 55 tests.

Notes: Did not import entropy branch modifications to
`backend/scripts/run_parallel_simulation.py` or `backend/scripts/run_reddit_simulation.py`
because those were older-runtime changes outside the isolated Linea 6 feature.

### 2026-07-09 Stabilization / Docker Memory Guard

Date: 2026-07-09
Source branch/commit: local stabilization on `codex/stable-fork-cleanup`
Import method: manual patches and docs.
Files/areas touched:

- runtime/reproducibility: `.env.example`, `Dockerfile`,
  `docker-compose.yml`, `Makefile`, `package.json`, `scripts/smoke_test.py`,
  `scripts/run_example.py`, `examples/minimal_case/`
- docs: `README.md`, `docs/upstream_pr_candidates.md`,
  `docs/repo-cleanup/AGENT_STATE.md`, `docs/repo-cleanup/VALIDATION_RUNBOOK.md`
- config: `backend/app/config.py`

Conflicts: none.
Decision: keep Neo4j/Graphiti behind an optional Compose profile and require
Windows memory/kernel-pool checks around Docker commands for the rest of this
task. The default Compose path should stay lower-memory.
Validation:

- Before reboot, Docker/Neo4j validation exposed abnormal Windows kernel pool
  retention. Containers/WSL were stopped.
- After reboot, memory normalized (`~16.5%` used, nonpaged pool `~0.6 GB`,
  paged pool `~0.78 GB`).

Notes: Do not run the optional Graphiti profile again unless explicitly needed.

### 2026-07-09 Entropy / Linea 6 Incremental Update

Date: 2026-07-09
Source branch/commit: `origin/feat/issue-28-linea6-entropia`
(`bccfdc7a`, fetched after it advanced from `ccd85ba7`)
Import method: selective import plus compatibility patches.
Files/areas touched:

- `backend/app/api/simulation.py`
- `scripts/run_linea6_trimodel_model_map.py`
- `scripts/extract_semantic_variance_metrics.py`
- `backtesting/case-b-s2-bolivia-2025-runoff/model_map_linea6_trimodel_template.yaml`
- `docs/linea6_entropia.md`
- `docs/upstream_pr_candidates.md`
- `docs/repo-cleanup/AGENT_STATE.md`
- `docs/repo-cleanup/MERGE_LEDGER.md`

Conflicts: no Git merge conflicts. Direct merge still avoided because the
entropy branch carries older runtime files. `llm_client.py` was not imported:
the current cleanup branch already uses the OpenAI SDK path directly, so the
old branch's Prompture escape hatch is not needed.
Decision: import the trimodel Linea 6 scripts/config and the missing API
passthrough for Reddit `model_map_path`/`no_wait`; preserve the existing
multi-model router, telemetry, runner, and headless implementations from the
stable cleanup branch.
Validation:

- `uv run --frozen --python 3.11 python -m py_compile app/api/simulation.py
  ../scripts/run_linea6_trimodel_model_map.py
  ../scripts/extract_semantic_variance_metrics.py` passed.
- `uv run --frozen --python 3.11 python
  ../scripts/run_linea6_trimodel_model_map.py --out-root
  ../outputs/linea6_trimodel_dry_run` passed; dry-run assigned 12 synthetic
  agents evenly across Qwen/Gemma/Llama and validated fake telemetry for all
  three models.
- `npm test` passed: 218 tests.
- `npm run smoke-test` passed.
- Staged artifact scan found no raw runs, DBs, traces, `outputs/`,
  `node_modules/`, backend uploads/data, or `dist/`.
- Staged secret scan found no literal API-key/token patterns.
Notes: `scripts/export_telemetry.py` was already identical to the fetched
entropy branch blob and was not changed.

### 2026-07-09 Stable Fork Audit And Hardening

Date: 2026-07-09
Source branch/commit: local hardening on `codex/stable-fork-cleanup`
Import method: no source import; focused fixes and repository cleanup.
Files/areas touched:

- startup/config: limited no-key startup, paused simulation reuse, Graph backend
  fallback, complete worldbuilding capture settings
- tests: full-suite discovery, isolation fixes, startup and stable-harness tests
- reproducibility: output validator, tracked-artifact/secret hygiene gate, CI
- Docker: healthcheck, no browser auto-open, debug disabled, memory limits,
  BuildKit dependency caches, explicit wait/test/down commands
- artifacts: compact multimodel evidence moved from `runs/` to `examples/`;
  request traces, SQLite DB, and archived HTML with a public browser key removed

Conflicts: none.
Decision: preserve compact research evidence and source case material while
removing raw runtime artifacts and making the default stack safe for no-key
reviewer startup. Keep Graphiti optional.
Validation so far:

- `npm run check` passed: hygiene, smoke, example, 322 tests, frontend build.
- root and frontend `npm audit` report zero known vulnerabilities.
- final Docker image reached `healthy`; backend/frontend returned HTTP 200,
  container smoke and all 322 Linux tests passed, and frontend built in Linux.
- runtime log scan found no browser-open error, Flask debugger/PIN, traceback,
  or child-process exit error.
- Windows memory returned to normal after stack/Docker/WSL shutdown; kernel
  pools remained stable throughout both builds.
- one short OpenRouter `qwen/qwen3-8b` text probe passed without JSON mode.

Notes: no merge to `main`, push, or PR action.
