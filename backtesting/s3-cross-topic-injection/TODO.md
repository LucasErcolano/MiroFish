# S3 TODO

## Long range

- Produce a cross-topic V3 benchmark package that can support a PR.
- Run and evaluate all 42 topic/model/condition combinations only after smoke passes.
- Document whether positional injection effects transfer from football to Bolivia and IPC.

## Medium range

- Decide whether to add artifact-only ReportAgent reports after smoke.
- Decide whether to add artifact-only ReportAgent reports after full matrix.

## Short range

- Keep package docs synchronized with implementation.
- Run `scripts/validate_s3_package.py` after any file change.
- Use `scripts/run_s3_matrix.py --smoke --dry-run` before real execution.
- If a run is attempted, append/update evidence in `RUN_LEDGER.csv` and `STATUS.md`.

## Done

- Created branch `codex/s3-cross-topic-injection`.
- Added persistent S3 guide file for long-running autonomous work.
- Defined V3 seven-condition design and 12-run smoke subset.
- Added compact topic packets for football, Bolivia, and IPC.
- Added matrix, run ledger, validator, and resumable smoke/full runner.
- Verified package validation and smoke dry-run locally.
- Executed 12/12 smoke rows successfully across football, Bolivia, and IPC with Gemma and Llama.
- Generated `evaluation/smoke_summary.*` with committed evidence derived from local `runs/`.
- Executed the full 42-row V3 matrix successfully.
- Generated `evaluation/full_summary.*`, `condition_summary_metrics.*`, and `final_s3_report.md`.
