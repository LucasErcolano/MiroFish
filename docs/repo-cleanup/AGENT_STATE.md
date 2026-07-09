# Stable Fork Cleanup Agent State

Last updated: 2026-07-09

## Current Status

Preparation only. The cleanup task has not started.

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

## Not Started Yet

- No merges into this branch.
- No cherry-picks.
- No source file imports from backtesting or entropy branches.
- No Docker or README rewrites.
- No tests run yet in this worktree.
- No push.

## Next Step When User Approves Start

Run the preflight commands from `VALIDATION_RUNBOOK.md`, then update this file
with current branch tips and begin Phase 1 in `PLAN.md`.
