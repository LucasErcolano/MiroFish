# Stable Fork Cleanup Agent State

Last updated: 2026-07-09

## Current Status

Cleanup task is in final validation/commit phase. The selective imports from
`origin/backtesting-feature-augmented` and
`origin/feat/issue-28-linea6-entropia` have been applied. Runtime/docs/smoke
stabilization is in place.

Created isolated worktree:

- Path: `C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish-stable-cleanup`
- Branch: `codex/stable-fork-cleanup`
- Base: `origin/feat/ui-observability-dock`
- Base commit: `5e4262ef63238c6eee5a1c18ae71a56d9ae08189`

The original checkout remains at:

- Path: `C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish`
- Branch at preparation time: `backtesting-feature-augmented`
- Known local untracked items there: `backend/.venv/`, `backend/data/`

## Known Branch Facts To Re-Verify Before Importing

- `origin/feat/ui-observability-dock` is `origin/main + 2 commits` and is the
  cleanest functional base for the stable fork.
- `origin/backtesting-baseline` is an ancestor of
  `origin/backtesting-feature-augmented`.
- `origin/feat/issue-28-linea6-entropia` should not be merged directly because
  it appears to delete modern features when compared to current `main`.

## Active Goal

When Joaco says to begin, integrate the stable fork in this order:

1. Keep the UI/observability branch as the base.
2. Selectively import backtesting and multi-model material from
   `backtesting-feature-augmented`.
3. Selectively import entropy/linea6 material from
   `feat/issue-28-linea6-entropia`.
4. Clean artifacts and documentation.
5. Add/repair smoke, run-example, tests, and Docker flow.
6. Validate and commit.

## Preflight Evidence

- Current branch: `codex/stable-fork-cleanup`
- Current HEAD: `58af26d52b6778a50ed48fe818000415a36c044e`
- Branch is ahead of `origin/feat/ui-observability-dock` by the prep commit
  only.
- Re-verified:
  - `origin/backtesting-baseline` is ancestor of
    `origin/backtesting-feature-augmented`.
  - `origin/main` is ancestor of `origin/feat/ui-observability-dock`.
  - `origin/backtesting-feature-augmented` is not ancestor of
    `origin/feat/issue-28-linea6-entropia`.

## Imported So Far

Current uncommitted/staged import from `origin/backtesting-feature-augmented`
includes:

- `backend/app/services/capture_artifacts.py`
- `backend/app/services/report_agent_s2_verdict.py`
- `backend/app/services/structured_report_agent.py`
- `backend/app/services/worldbuilding_trace.py`
- `backend/scripts/run_s2_line5.py`
- `configs/model_map_s2.yaml`
- `scripts/set-s2-hosted-env.example.ps1`
- `tools/local_embedding_server.py`
- focused backend/root tests for S2 narrative scoring, scheduled injection,
  simulation model maps, Graphiti dedup bypass, prepared status, Zep fallback,
  and worldbuilding traces.

Manual runtime patches already applied:

- `backend/app/services/model_router.py`: OpenRouter and DeepInfra provider
  defaults.
- `backend/app/services/simulation_config_generator.py`: Qwen JSON-mode
  avoidance and object-shape fallback parsing.
- `backend/app/graph/graphiti_backend.py`: `GRAPHITI_BYPASS_NODE_DEDUP`
  helper/path while preserving the UI branch's graph code.

## Completed In This Working Tree

- Backtesting/multimodel/wiki/scheduled-injection runtime imported
  selectively.
- Entropy/Linea 6 research package, scripts, tests, docs, and Bolivia temporal
  case imported selectively.
- README quick start, `.env.example`, `Makefile`, root npm commands,
  `examples/minimal_case/`, `scripts/smoke_test.py`, and
  `scripts/run_example.py` added.
- Docker/Compose now builds locally. Neo4j is behind the optional `graphiti`
  profile so the default stack is lower-memory.
- `docs/upstream_pr_candidates.md` added.

## Validation Evidence So Far

- Final post-reboot validation:
  - `uv run --frozen --python 3.11 python -m py_compile ...` passed for
    edited backend runtime/config files.
  - `npm run smoke-test` passed.
  - `npm run run-example` passed.
  - `npm test` passed: 207 tests.
  - `npm run build` passed with Vite chunk-size/import warnings only.
  - `docker compose config --quiet` passed with memory stable before/after
    (`nonpaged ~0.63 GB`, `paged ~0.85-0.86 GB`).
  - `git diff --check` passed with CRLF warnings only.
  - Changed-path artifact scan found no new raw runs, DBs, request traces,
    `outputs/`, `node_modules/`, `dist/`, backend uploads, or backend data.
- `uv run --frozen --python 3.11 pytest ...` for scheduled injection,
  model-map, Graphiti bypass: 10 passed.
- Wiki/memory/routing suite: 142 passed.
- Entropy/Linea 6 suite: 55 passed.
- Root `npm run smoke-test`: passed.
- Root `npm run run-example`: passed.
- Root `npm test`: 207 passed.
- Root `npm run build`: frontend build passed with Vite chunk warnings.
- `docker compose build`: passed on second cached attempt.

Docker note: an earlier `docker compose up` with Neo4j in the default stack
consumed excessive system memory. The app/Neo4j containers were stopped, stale
Docker/WSL processes were cleaned, and Compose was changed so Neo4j only starts
with `docker compose --profile graphiti up --build`. Do not run the full
Graphiti profile again unless Joaco explicitly wants that validation.

System memory note: after cleanup, process memory was sane, but Windows still
showed high kernel pool (`~20 GB` nonpaged, `~12 GB` paged). That cannot be
fully reclaimed from this non-admin shell; likely requires admin pool-tag
diagnostics or reboot.

Post-reboot check: memory returned to normal (`~16.5%` used, nonpaged pool
`~0.6 GB`, paged pool `~0.78 GB`). For the rest of this task, check Windows
memory and kernel pool before and after any Docker command. If nonpaged/paged
pool starts growing abnormally again, stop Docker/WSL validation and document
the exact counters instead of continuing to run containers.

## Still Not Done

- Final local commit.
- No push.

## Next Step

Stage the final diff, inspect the staged stat, and create the local commit. Do
not push.
