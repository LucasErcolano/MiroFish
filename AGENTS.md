@C:\Users\joaco\.codex\RTK.md

# MiroFish Agent Notes

## Read First After Compaction Or In New Threads

For the IPC tri-model multi-agent benchmark, always read these files before
editing code or running simulations:

1. `backtesting/ipc-trimodel-multiagent/AGENT_STATE.md`
2. `backtesting/ipc-trimodel-multiagent/TODO.md`
3. `backtesting/ipc-trimodel-multiagent/RUNBOOK.md`
4. `backtesting/ipc-trimodel-multiagent/DECISIONS.md`
5. `backtesting/ipc-trimodel-multiagent/PRE_SMOKE_CHECKLIST.md`
6. `backtesting/ipc-trimodel-multiagent/RUN_LEDGER.csv`
7. `backtesting/ipc-trimodel-multiagent/RESULTS_ANALYSIS.md`

If context was compacted, do not restart discovery from scratch. Continue from
`AGENT_STATE.md`, then update it with any new state before long-running work.

## Current Research Objective

The IPC 2025 tri-model multi-agent benchmark is complete. Current work should
focus on validation, documentation consistency, commit, and push unless the
user explicitly asks for more simulations.

Completed benchmark scope:

- Temporal line: multi-agent T0, T1, T2, T3.
- Line 5 depth: multi-agent R10, R20, R40, R80 on IPC T3.
- S3 noise/signals: IPC 7-condition scheduled-injection matrix.
- Models inside the same simulation: Qwen, Gemma, and Llama via model routing.
- Memory mode: use the experimental Karpathy/MemGPT-style memory path.
- Before building IPC graphs, implement or enable the Graphiti dedup bypass.

## Non-Negotiable Execution Rules

- Use the branch `codex/ipc-trimodel-multiagent` unless the user redirects.
- Preferred source for missing multi-model system pieces is
  `origin/backtesting-feature-augmented`. Import selectively; do not merge or
  copy that branch wholesale.
- Use that branch's `run_reddit_simulation.py` only as a reference for
  `--model-map`, routing audit, and telemetry. Preserve this branch's
  scheduled-event/injection implementation.
- Do not run the full matrix until the smoke checklist in `RUNBOOK.md` passes.
- Use `backtesting/ipc-trimodel-multiagent/scripts/run_ipc_trimodel_matrix.py`
  for smoke and matrix rows. It requires explicit `--dry-run` or `--execute`;
  use `--smoke --dry-run` before the first paid smoke.
- Do not treat three separate single-model runs as the multi-agent result.
  The multi-agent condition must produce `model_routing_audit.jsonl` showing
  Qwen, Gemma, and Llama in one simulation, and
  `llm_telemetry_summary.json` showing all three models made calls.
- Treat memory as verified only when compact evidence includes
  `experimental_memory_evidence.json` and, when present,
  `core_memory.json`; document fallback/missing memory in `RUN_LEDGER.csv`.
- Do not print API keys. Only report presence/absence.
- Do not commit raw `runs/`, backend logs, uploads, caches, or databases.
- Commit only code/config/docs plus compact result artifacts under
  `backtesting/ipc-trimodel-multiagent/evaluation/`.
- Update `RUN_LEDGER.csv` after every attempted run, including failures.
- Update `AGENT_STATE.md` before and after any long-running command.
- Update `LESSONS.md` when a failure teaches a reusable rule.
- Keep `RUNBOOK.md` synchronized with commands that actually worked.

## Local Environment Defaults

- Backend uses Python 3.11 through `uv`.
- Prefer `uv run --frozen --python 3.11 ...`.
- Neo4j is expected at `bolt://localhost:7687`.
- `OPENROUTER_API_KEY` and `DEEPINFRA_API_KEY` should come from the environment.
- Set `DEEPINFRA_BASE_URL=https://api.deepinfra.com/v1/openai` when missing.
- Set `USE_EXPERIMENTAL_MEMORY=true` for benchmark simulations.
- Use `GRAPHITI_LLM_MODEL=google/gemma-3-27b-it` for stable Graphiti extraction
  unless a specific row intentionally tests another extractor.
- Use `GRAPHITI_EMBEDDER_MODEL=qwen/qwen3-embedding-8b` with
  `GRAPHITI_EMBEDDER_BASE_URL=https://openrouter.ai/api/v1` unless a row
  explicitly tests a different embedder.

## Repo Safety

- Preserve unrelated user changes. There is a stash named
  `codex-temp-before-bringing-merged-final-multimodel` from this workstream.
- Use `apply_patch` for manual edits.
- Prefer `rg`/`rtk grep` and targeted reads over broad output dumps.
- If a command output may contain secrets, summarize only presence/absence.
