# IPC Tri-Model Multi-Agent Benchmark

This package is the durable workspace for the IPC 2025 tri-model multi-agent
benchmark.

Goal: test whether a single MiroFish simulation with Qwen, Gemma, and Llama
agents improves mathematical IPC forecast accuracy, reduces JSON/format
collapse, and resists irrelevant noise better than single-model baselines.

Read the experiment evidence in this order:

1. `DECISIONS.md`
2. `PRE_SMOKE_CHECKLIST.md`
3. `RUN_LEDGER.csv`
4. `RESULTS_ANALYSIS.md`

Files:

- `matrix.yaml`: intended experimental matrix.
- `model_map_ipc_trimodel.yaml`: per-agent model routing map.
- `scripts/run_ipc_trimodel_matrix.py`: dry-run/execute entrypoint for smoke,
  temporal, Line 5, and S3 rows.
- `PRE_SMOKE_CHECKLIST.md`: exact gate before paid smoke.
- `RUN_LEDGER.csv`: append-only run ledger.
- `RESULTS_ANALYSIS.md`: canonical temporal, Line 5, and S3 result summary.
- `evaluation/`: compact result summaries only.

Raw outputs belong under `runs/ipc_trimodel_multiagent/` and should not be
committed.
