# S3 Overnight Goal Guide

## Objective

Build the S3 V3 cross-topic scheduled-injection benchmark across three domains:

- football: Argentina vs Colombia Copa America 2024 final, from the existing Issue 19 artifacts.
- bolivia: 2025 Bolivia presidential runoff, from `origin/feat/issue-17-bolivia-runoff-backtesting-pr`.
- ipc: Argentina IPC 2025 forecast, from `origin/feat/case-b-backtesting`.

Use only the DeepInfra models:

- `google/gemma-3-27b-it`
- `meta-llama/Llama-3.3-70B-Instruct-Turbo`

## Required Persistent Files

Create and keep updated under `backtesting/s3-cross-topic-injection/`:

- `S3_CONTEXT.md`: short orientation and decisions.
- `TODO.md`: hierarchical TODO with long, medium, and immediate tasks.
- `STATUS.md`: current phase, last command, next command, blockers, completed items.
- `RUNBOOK.md`: reproducible commands.
- `LESSONS_S3.md`: pitfalls to avoid.
- `matrix.yaml`: topics, models, conditions, timing, and injection documents.
- `RUN_LEDGER.csv`: one row per attempted run.

After compaction or resume, read `S3_CONTEXT.md`, `TODO.md`, `STATUS.md`, and `RUNBOOK.md` before doing work.

## V3 Matrix

Per topic and model, use seven conditions:

- `baseline-control`
- `signal-early`
- `signal-mid`
- `signal-late`
- `counter-signal-mid`
- `noise-near-mid`
- `noise-off-mid`

Full matrix:

```text
3 topics x 2 models x 7 conditions = 42 simulation runs
```

Recommended timing over 20 rounds:

- early: `round_pct=0.10`
- mid: `round_pct=0.50`
- late: `round_pct=0.90`

## Smoke First

Do not start all 42 runs immediately. First validate the pipeline with:

```text
3 topics x 2 models x 2 conditions = 12 smoke runs
```

Smoke conditions:

- `baseline-control`
- `signal-mid`

If smoke passes, continue with the remaining full matrix when time/resources allow.

## Data Rules

- Prefer targeted file extraction with `git show` from remote branches; do not merge whole PR branches unless necessary.
- Keep `runs/` local and uncommitted.
- Do not store secrets in files or logs.
- Separate committed evidence from local reproducibility evidence.
- For IPC, resolve or document the ground-truth inconsistency before scoring:
  - `answer_key_post_x/ground_truth.md`: Apr 2025 = 3.7, Jul 2025 ~= 3.0.
  - root `ground_truth.json`: Apr 2025 = 2.8, Jul 2025 = 1.9.
  - Prefer the documented `answer_key_post_x/ground_truth.md` unless stronger evidence is found.

## Evaluation

For every condition, verify:

- run completed or failed with recorded error;
- baseline fired zero scheduled events;
- injected condition fired exactly one scheduled event;
- fired round matches timing;
- posts/comments/traces summarized;
- raw evaluator output preserved.

Topic metrics:

- football: predicted winner, confidence, injected-document use, noise contamination.
- bolivia: winner, vote-share estimates, margin error, injected-document use.
- ipc: MAE/range hit/direction hit, unsupported numeric claims, injected-document use.

Use artifact-only ReportAgent if feasible. Do not allow ReportAgent to read shared graph/Zep state for final S3 reports.

## Git Rules

- Work on `codex/s3-cross-topic-injection` unless already on an appropriate S3 branch.
- Do not revert unrelated user changes.
- Do not touch frontend unless strictly necessary.
- Before committing, inspect git status and stage only S3-relevant files.
- Run relevant checks before committing.
- Do not push or open a PR unless explicitly asked.
