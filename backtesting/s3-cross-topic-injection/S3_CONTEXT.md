# S3 Cross-Topic Injection Context

Objective: extend the S2 scheduled-injection experiment across three prediction topics using the same two DeepInfra models:

- `google/gemma-3-27b-it`
- `meta-llama/Llama-3.3-70B-Instruct-Turbo`

Topics:

- `football`: Argentina vs Colombia Copa America final, based on the Issue 19/S2 football work in this repo.
- `bolivia`: Bolivia 2025 runoff prediction, based on PR #24 / `origin/feat/issue-17-bolivia-runoff-backtesting-pr`.
- `ipc`: Argentina IPC 2025 prediction, based on PR #22 / `origin/feat/case-b-backtesting`.

Canonical V3 conditions:

- `baseline-control`: no scheduled event.
- `signal-early`: one relevant signal at early round.
- `signal-mid`: one relevant signal at mid round.
- `signal-late`: one relevant signal at late round.
- `counter-signal-mid`: one contrary relevant signal at mid round.
- `noise-near-mid`: one near-topic distractor at mid round.
- `noise-off-mid`: one off-topic distractor at mid round.

Smoke scope before any full overnight run:

- 3 topics x 2 models x 2 conditions = 12 runs.
- Conditions: `baseline-control`, `signal-mid`.

Important constraints:

- Do not run the full 42-run matrix until the smoke package validates.
- Keep `runs/` local and uncommitted.
- Update `RUN_LEDGER.csv` after every executed or skipped run attempt.
- Preserve raw outputs and evaluator artifacts.
- Verify event audit: baseline must fire 0 events; all injected conditions must fire exactly 1 event.
- IPC scoring uses `topics/ipc/ground_truth_decision.md` because PR #22 has conflicting answer-key artifacts.
- ReportAgent is optional for S3 and should be artifact-only if used; do not depend on shared Graph/Zep state.

Primary files to read after compaction:

1. `OVERNIGHT_GOAL_GUIDE.md`
2. `S3_CONTEXT.md`
3. `TODO.md`
4. `STATUS.md`
5. `RUNBOOK.md`
6. `LESSONS_S3.md`
7. `matrix.yaml`
8. `RUN_LEDGER.csv`
