# Research branch: S1/S2/S3 backtesting integration

This branch is **research-only** and intentionally not merged into `main`.
It exists to preserve the S1/S2/S3 backtesting artefacts and supporting
research code from PRs #15, #16, #22, #24, #25, #26, #29 without
disrupting the production codebase.

## Base

Branched from `83829b1325b4b44733caa11bb3d87a0c5dcb03a9` (commit
`feat(S3): implementar deduplicación semántica de agentes y pipeline
de Deep Search autónomo`), which is the last commit common to all
seven source PRs.

## What's included

### Code (16 new files, single-commit cherry-picks)

Each file was lifted via `git show <commit>:<path>` from the originating
PR to avoid pulling in changes to files shared with `main`.

| File | From | Commit |
|---|---|---|
| `backend/.python-version` | #22 | `834857c` |
| `backend/app/services/capture_artifacts.py` | #24 | `5722acd` |
| `backend/app/services/report_agent_s2_verdict.py` | #22 | `84837d6` |
| `backend/app/services/structured_report_agent.py` | #24 | `5722acd` |
| `backend/app/services/worldbuilding_trace.py` | #24 | `1eb1c55` |
| `backend/scripts/run_s2_line5.py` | #22 | `84837d6` |
| `backend/tests/test_s2_narrative_scoring.py` | #25 | `cbd7e6d` |
| `backend/tests/test_s2_scheduled_injection.py` | #25 | `cbd7e6d` |
| `backend/tests/test_simulation_prepared_status.py` | #25 | `cbd7e6d` |
| `config_matrix.yaml` | #22 | `84837d6` |
| `configs/model_map_s2.yaml` | #25 | `eb88f17` |
| `docs/s2-issue19-tomorrow-runbook.md` | #25 | `eb88f17` |
| `docs/superpowers/plans/2026-06-07-report-agent-artifact-only.md` | #25 | `3f77489` |
| `scripts/set-s2-hosted-env.example.ps1` | #25 | `eb88f17` |
| `tests/test_worldbuilding_trace.py` | #24 | `1eb1c55` |
| `tools/local_embedding_server.py` | #22 | `0b491c2` |

### Artifacts (1657 files from the 7 PRs, in merge order)

Merge order is **oldest → newest** so that later PRs overwrite earlier
ones with the canonical version.

| PR | Source branch | What was imported |
|---|---|---|
| #15 | `feat/issue-10-backtesting-case-a` | `backtesting/OBJECTIVE.md`, `backtesting/case-a/` (Copa America 2024) |
| #16 | `chore/pilot-arg-2025-q1-artifacts` | `cases/PILOT-ARG-2025-Q1/S1_evaluation.md`, `runs/headless/top1-deepinfra-pilot-arg-2025-q1-poll/*` |
| #25 | `codex/s2-issue19-baseline` | `backtesting/case-a-s2-positional-noise*/` (V1 + V2) |
| #22 | `feat/case-b-backtesting` | `cases/CASE-B1-BTC-ETF-JAN2024/`, `cases/CASE-B2-ARG-IPC-2025/`, `cases/RUNBOOK.md`, `cases/backtesting_analysis.md` |
| #24 | `feat/issue-17-bolivia-runoff-backtesting-pr` | `backtesting/case-b-s2-bolivia-2025-runoff/`, `backtesting/case-c-s2-arg-ipc-line5-gemma/`, `backtesting/case-d-s2-copa-america-line5-gemma/`, `backtesting/S2_TEMPORAL_RESULTS_MATRIX.md`, `backtesting/configs/`, `backtesting/scripts/` |
| #26 | `codex/s3-cross-topic-injection` | `backtesting/s3-cross-topic-injection/` (3×2×7 matrix) |
| #29 | `feat/line5-llama-bolivia-copa-results` | `backtesting/LINE5_LLAMA_BOLIVIA_COPA.md` + final overwrite of Bolivia/Copa/BTC-IPC artefacts |

## What was NOT included (and why)

### `3a6e8ca` "sanitize graphiti attributes for neo4j" (PR #24)

This was PR #24's first attempt at fixing the `CypherTypeError:
Encountered: Map{}` bug. It defined `_is_neo4j_property_scalar` and
`_sanitize_neo4j_property_value` in `graphiti_backend.py`.

**Why excluded**: superseded by the more complete flatten fix in
commit `02df297` on `main` (PR #31), which adds `_flatten_for_neo4j`,
`_flatten_attributes`, and `_apply_flatten_pass` plus 21 unit tests
and an e2e test. The PR #24 version had no tests and only covered
partial coercion.

**Historical reference**: the commit is reachable as
`pr-24`'s `3a6e8cafd65f6ec1627b3c0b49ea2f02a936a1b2`.

### `bcc097d` "force neo4j==5.23.0 via uv override" (PR #22)

This was PR #22's workaround for the `camel-oasis==0.2.5` metadata
pinning `neo4j==5.23.0`.

**Why excluded**: would conflict with `graphiti-core==0.28.2`'s
requirement of `neo4j>=5.26.0`. The current main (post PR #31) has
the correct recipe:

```
uv pip install -r requirements.txt
uv pip install --no-deps camel-oasis==0.2.5
```

**Note**: `backend/.python-version` (Python 3.12 pin) from PR #22
**was** kept — it does not conflict with the main recipe.

## How to use this branch

```bash
# Install venv using the same recipe as main (Python 3.12, Rust, no-deps for camel-oasis)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal
. "$HOME/.cargo/env"
cd backend
uv venv --python 3.12 .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install --no-deps camel-oasis==0.2.5

# Explore artefacts
ls backtesting/
ls cases/
ls runs/
```

## When (not) to merge this into main

**Do not merge to main** while the 7 source PRs are still open and
while main has diverged via PR #14/#23/#27. The shared files between
these PRs and main (config.py, graphiti_backend.py, llm_client.py,
report_agent.py, simulation_manager.py, etc.) have already received
better versions on main.

**If you want to merge anyway**: the cleanest path is to cherry-pick
the individual commits that add new code (the 16-file list above) on
top of current main, and import each artefact directory separately.
Expect 2-4 hours of conflict resolution across the 11 shared files.
