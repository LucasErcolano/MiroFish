# Context Dump For Fresh Thread

You are working in the MiroFish repo:

```text
C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish
```

Current branch:

```text
codex/ipc-trimodel-multiagent
```

This branch starts from `origin/backtesting-baseline` and has already merged
`origin/codex/final-multimodel-baseline`.

Primary objective:

The IPC 2025 tri-model multi-agent benchmark with Qwen, Gemma, and Llama inside
each simulation is complete. The remaining work is validation, documentation
consistency, commit, push, or explicit follow-up. The completed test scope was:

1. Temporal T0-T3: whether multi-agent lowers MAE faster and more stably than
   single models.
2. Line 5 depth R10-R80: whether multi-agent R40 can beat single-agent R80 on
   MAE with fewer tokens/cost.
3. S3 noise/signals: whether tri-model consensus is harder to fool with
   irrelevant noise.

Critical files to read first:

```text
AGENTS.md
backtesting/ipc-trimodel-multiagent/AGENT_STATE.md
backtesting/ipc-trimodel-multiagent/TODO.md
backtesting/ipc-trimodel-multiagent/RUNBOOK.md
backtesting/ipc-trimodel-multiagent/DECISIONS.md
backtesting/ipc-trimodel-multiagent/PRE_SMOKE_CHECKLIST.md
backtesting/ipc-trimodel-multiagent/RUN_LEDGER.csv
backtesting/ipc-trimodel-multiagent/RESULTS_ANALYSIS.md
docs/superpowers/plans/2026-06-27-ipc-trimodel-multiagent.md
```

Important constraints:

- `backend/app/services/model_router.py`, `backend/app/services/llm_telemetry.py`,
  and `configs/model_prices.yaml` were selectively imported from
  `origin/backtesting-feature-augmented`.
- `run_reddit_simulation.py` has `--model-map`, routing audit, and telemetry
  integration while preserving scheduled events.
- Headless/API/SimulationRunner propagate `model_map_path` to Reddit runs.
- Headless captures compact memory evidence from
  `backend/data/simulations/<simulation_id>` into
  `simulation_artifacts/experimental_memory_evidence.json`.
- The IPC runner is
  `backtesting/ipc-trimodel-multiagent/scripts/run_ipc_trimodel_matrix.py`.
- Do not rerun paid simulations unless the user explicitly asks or a validation
  failure requires a targeted rerun.
- Implement/enable Graphiti dedup bypass before IPC graph build.
- Use `USE_EXPERIMENTAL_MEMORY=true`.
- Use `model_map_ipc_trimodel.yaml` and verify both `model_routing_audit.jsonl`
  and `llm_telemetry_summary.json` contain all three models.
- Do not commit raw `runs/`.
- Update `AGENT_STATE.md`, `TODO.md`, `RUNBOOK.md`, `RUN_LEDGER.csv`, and
  `LESSONS.md` as work progresses.
- Use `--smoke --dry-run` before the paid smoke. The first smoke row is
  `ipc_trimodel_smoke_T0_R2_D2`.

Known env:

- `OPENROUTER_API_KEY` was present.
- `DEEPINFRA_API_KEY` was present.
- Neo4j was running on `7474/7687`.
- Set `DEEPINFRA_BASE_URL=https://api.deepinfra.com/v1/openai`.
- Set `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`.

Current result summary:

- Temporal T0-T3 completed. T1/T2/T3 improved February absolute error to 0.1;
  T2 was the best temporal packet by score and December error.
- Line5 R10/R20/R40/R80 completed. R10 was the strongest trimodel depth row;
  R80 was expensive and had the most telemetry errors.
- S3 7/7 canonical rows completed. Baseline-control was strongest, while
  signal/noise injections mostly degraded results. This is a negative/nuanced
  result for the robustness hypothesis.
- Objective structured evaluation had parse_errors=0 for every canonical row.

Final validation already run during completion:

- runner tests: 13 passed.
- backend router tests: 3 passed.
- headless tests: 5 passed.
- backend routing/memory/dedup/injection tests: 17 passed.
- `git diff --check` produced only line-ending warnings.
