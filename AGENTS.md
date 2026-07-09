@C:\Users\joaco\.codex\RTK.md

# Stable Fork Cleanup Agent Notes

## Read First After Compaction Or In New Threads

This worktree is for preparing a stable, presentable MiroFish fork. Before
editing code, running merges, or changing documentation, read:

1. `docs/repo-cleanup/AGENT_STATE.md`
2. `docs/repo-cleanup/PLAN.md`
3. `docs/repo-cleanup/MERGE_LEDGER.md`
4. `docs/repo-cleanup/ARTIFACT_POLICY.md`
5. `docs/repo-cleanup/VALIDATION_RUNBOOK.md`
6. `docs/repo-cleanup/FEATURE_PR_CANDIDATES_DRAFT.md`
7. `docs/repo-cleanup/START_PROMPT.md`
8. `docs/repo-cleanup/SUBAGENT_PROMPTS.md`

If context was compacted, continue from `AGENT_STATE.md`. Do not rediscover the
entire repo unless those files are stale or contradictory.

## Current Objective

Prepare `codex/stable-fork-cleanup` as a clean integration branch for a stable
MiroFish fork. The final target is a reproducible, documented repository with a
simple smoke path, Docker/Compose instructions, and clear upstream PR candidate
feature documentation.

## Source Branch Policy

- Base branch: `origin/feat/ui-observability-dock`.
- Required source branches to inspect/import selectively:
  - `origin/backtesting-feature-augmented`
  - `origin/backtesting-baseline`
  - `origin/feat/issue-28-linea6-entropia`
- `backtesting-baseline` is already an ancestor of
  `backtesting-feature-augmented`; treat it as reference unless re-verification
  proves otherwise.
- Do not merge `feat/issue-28-linea6-entropia` directly. It was based on older
  code and deletes modern features when diffed against current `main`; import
  only its entropy/linea6 feature files.
- Do not import raw run artifacts, local DBs, traces, caches, or huge output
  dumps. Follow `ARTIFACT_POLICY.md`.

## Execution Rules

- Do not push unless Joaco explicitly asks.
- Do not start branch imports or conflict resolution until the user asks to
  begin the actual cleanup task.
- Before each major phase, update `AGENT_STATE.md`.
- After each import/merge attempt, update `MERGE_LEDGER.md` with branch, files,
  conflicts, decision, and validation.
- Prefer `rtk` for searches/reads when it fits; use raw commands with
  `# raw-ok` only when exact Git output is needed.
- Use `apply_patch` for manual file edits.
- Keep the main checkout at `MiroFish` untouched unless explicitly redirected.
