# IPC Tri-Model Multi-Agent Benchmark

This package is the durable workspace for the IPC 2025 tri-model multi-agent
benchmark.

Goal: test whether a single MiroFish simulation with Qwen, Gemma, and Llama
agents improves mathematical IPC forecast accuracy, reduces JSON/format
collapse, and resists irrelevant noise better than single-model baselines.

Start here after compaction:

1. `AGENT_STATE.md`
2. `TODO.md`
3. `RUNBOOK.md`
4. `DECISIONS.md`
5. `PRE_SMOKE_CHECKLIST.md`
6. `RUN_LEDGER.csv`
7. `RESULTS_ANALYSIS.md`

Files:

- `matrix.yaml`: intended experimental matrix.
- `model_map_ipc_trimodel.yaml`: per-agent model routing map.
- `scripts/run_ipc_trimodel_matrix.py`: dry-run/execute entrypoint for smoke,
  temporal, Line 5, and S3 rows.
- `PRE_SMOKE_CHECKLIST.md`: exact gate before paid smoke.
- `RUN_LEDGER.csv`: append-only run ledger.
- `RESULTS_ANALYSIS.md`: canonical temporal, Line 5, and S3 result summary.
- `THREAD_CONTEXT_DUMP.md`: context package for a fresh Codex thread.
- `HANDOFF_PROMPT.md`: prompt to send to a fresh thread.
- `evaluation/`: compact result summaries only.

Raw outputs belong under `runs/ipc_trimodel_multiagent/` and should not be
committed.
