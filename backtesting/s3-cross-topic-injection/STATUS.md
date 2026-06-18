# S3 Status

Last update: 2026-06-18

Current phase: full matrix complete, deterministic analysis complete.

Completed:

- Branch created: `codex/s3-cross-topic-injection`.
- Persistent goal guide exists: `OVERNIGHT_GOAL_GUIDE.md`.
- S3 context, TODO, runbook, matrix, ledger, topic packets, and scripts were added.
- Package validation passed with 3 topics, 2 models, 7 conditions, 12 smoke rows, and 42 full rows.
- Smoke dry-run passed and lists all 12 rows without requiring an API key.
- Canary `football/gemma/baseline-control-r20` executed. Backend manifest reported zero rounds, but physical artifacts show a completed Reddit run: `reddit_simulation.db` has posts/traces and `simulation.log` reached round 20/20. The S3 runner now audits DB/log evidence and event counts directly.
- Smoke execution completed for 12/12 rows: 3 topics x 2 models x (`baseline-control`, `signal-mid`).
- Smoke summary generated in `evaluation/smoke_summary.md`, `.csv`, and `.json`.
- All baselines fired 0 scheduled events; all `signal-mid` rows fired exactly 1 scheduled event.
- Prepared simulation reuse is working: each topic/model pair reuses one prepared simulation across baseline and signal-mid.
- Full 42-row matrix completed and summarized in `evaluation/full_summary.*`.
- Deterministic condition metrics generated in `evaluation/condition_summary_metrics.*`.
- Final S3 report written in `evaluation/final_s3_report.md`.

In progress:

- None.

Not started:

- Artifact-only ReportAgent pass.
- Commit latest analysis artifacts.

Known risks:

- IPC has conflicting ground-truth files in PR #22. This package uses the answer-key markdown; see `topics/ipc/ground_truth_decision.md`.
- Bolivia and IPC were not originally implemented as scheduled-injection simulations. This package makes compact S3 topic packets from prior PR artifacts.
- Existing backend model selection is environment-driven. For real smoke, backend must be started with the intended DeepInfra model or via `scripts/run_s3_matrix.py --start-backend`.
- Backend progress counters can be stale/zero even after a real OASIS run. Use artifact evidence from `simulation_artifacts/`.
- `--no-wait-after-run` is required for autonomous headless S3 runs; disabling it can leave Reddit waiting for IPC commands.
- Llama is kept as simulation model for Llama rows, but Graphiti extraction uses Gemma to avoid schema drift in `ExtractedEntities`.
- Deterministic metrics count injected documents when they are posted; use them for directional pressure, not as a semantic final judge.
