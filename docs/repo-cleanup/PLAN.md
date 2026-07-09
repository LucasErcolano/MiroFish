# Stable Fork Cleanup Plan

## P0: Integration Safety

- Confirm current branch is `codex/stable-fork-cleanup`.
- Confirm base is `origin/feat/ui-observability-dock`.
- Confirm source branches exist and are up to date.
- Keep all work local until Joaco explicitly authorizes push.
- Keep raw artifacts out of the commit.

## P1: Selective Feature Integration

### Observability Dock

Status: already in base branch.

Expected scope:

- Backend artifact endpoints and simulation manager support.
- Frontend observability dock, telemetry views, report/wiki views.
- Tests/docs from `feat/ui-observability-dock`.

### Backtesting / Multi-Model / Wiki Memory

Source: `origin/backtesting-feature-augmented`.

Import selectively:

- Runtime code needed for model routing, telemetry, scheduled injections,
  structured reports, report-agent verdicts, wiki/report memory, and IPC
  tri-model support.
- Compact docs and summary metrics.
- Focused tests.

Do not import:

- Raw `runs/`.
- Local DBs.
- Request/worldbuilding traces unless explicitly compact and necessary.
- Massive generated output directories.

### Baseline

Source: `origin/backtesting-baseline`.

Use as reference only unless re-verification shows unique files not present in
`backtesting-feature-augmented`.

### Entropy / Linea 6

Source: `origin/feat/issue-28-linea6-entropia`.

Import surgically:

- `backend/app/research/entropy/`
- `backend/app/research/dataset/`
- Entropy scripts.
- Entropy tests.
- Linea 6 docs.

Do not merge the branch directly.

## P2: Repo Stabilization

- Replace upstream-oriented README sections with a fork-focused quick start.
- Ensure `.env.example` documents required and optional keys.
- Add a minimal example path under `examples/` if missing.
- Add or repair `Makefile` commands:
  - `make test`
  - `make smoke-test`
  - `make run-example`
  - `make docker-up`
- Ensure Docker/Compose can build locally and run a visible health/smoke path.
- Keep browser UI flow and batch/headless flow both documented.

## P3: Documentation For Upstream PR Candidates

Create final docs under `docs/`:

- `docs/upstream_pr_candidates.md`
- Per-feature docs if missing:
  - observability dock
  - multi-model routing and telemetry
  - wiki-backed report memory
  - scheduled injection/backtesting
  - entropy/linea6
  - Docker/smoke harness

Each feature entry must state:

- Problem solved.
- What changed.
- Main files touched.
- How to use.
- Dependencies and env vars.
- Upstream PR review checklist.

## P4: Validation

Run the staged validation in `VALIDATION_RUNBOOK.md`.

Minimum before final commit:

- Git diff has no accidental raw artifacts.
- Backend syntax/import smoke passes.
- Targeted pytest passes or failures are documented.
- Frontend build passes or failures are documented.
- Docker path is verified or limitations are documented.
- README commands match actual commands.
