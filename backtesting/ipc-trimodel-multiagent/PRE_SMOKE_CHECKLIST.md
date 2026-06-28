# IPC Tri-Model Pre-Smoke Checklist

Use this before the first paid IPC tri-model smoke. Do not run full matrix rows
until this checklist is green.

## Verified Preparation

- Branch: `codex/ipc-trimodel-multiagent`.
- Per-agent routing services are present:
  - `backend/app/services/model_router.py`
  - `backend/app/services/llm_telemetry.py`
- Hosted providers are accepted by the router:
  - `openrouter`
  - `deepinfra`
- `run_reddit_simulation.py` accepts `--model-map`.
- Headless/API/SimulationRunner pass `model_map_path` to Reddit simulations.
- Headless captures:
  - `mirofish_report_raw.md`
  - `report_meta.json`
  - `simulation_artifacts/model_routing_audit.jsonl`
  - `simulation_artifacts/llm_telemetry.jsonl`
  - `simulation_artifacts/experimental_memory_evidence.json`
- IPC runner exists:
  - `backtesting/ipc-trimodel-multiagent/scripts/run_ipc_trimodel_matrix.py`
- Dry-run plan exists:
  - `backtesting/ipc-trimodel-multiagent/evaluation/pre_smoke_plan.json`
- Full matrix dry-run plan exists:
  - `backtesting/ipc-trimodel-multiagent/evaluation/full_matrix_plan.json`
- Backend report/memory dependency imports:
  - `uv run --frozen --python 3.11 python -c "import chromadb; print('chromadb_ok')"`

## Pre-Smoke Commands

From repo root:

```powershell
uv run --frozen --python 3.11 python backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py --smoke --dry-run
```

Expected:

- `selected_rows` is `1`.
- row id is `ipc_trimodel_smoke_T0_R2_D2`.
- `required_key_envs.OPENROUTER_API_KEY` is `true`.
- `required_key_envs.DEEPINFRA_API_KEY` is `true`.
- command includes `--model-map`.
- env plan pins `GRAPHITI_EMBEDDER_MODEL` to `qwen/qwen3-embedding-8b`.
- `chromadb` import succeeds from `backend/`.

Then run only this paid smoke:

```powershell
uv run --frozen --python 3.11 python backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py --smoke --execute --start-backend
```

If a backend is already running and correctly configured, omit
`--start-backend`. If unsure, stop it and use `--start-backend`.

## Smoke Evidence Gate

The smoke is valid only if these files exist under
`backtesting/ipc-trimodel-multiagent/evaluation/smoke/ipc_trimodel_smoke_T0_R2_D2/`:

- `report.md`
- `eval_result.json`
- `run_notes.md`
- `run_manifest.json`
- `model_routing_audit.jsonl`
- `llm_telemetry_summary.json`
- `experimental_memory_evidence.json`
- `core_memory.json` when `experimental_memory_evidence.json` reports
  `core_memory_exists=true`
- `scheduled_events_fired.jsonl` only for S3 conditions with expected events
  greater than zero

Also verify:

- `model_routing_audit.jsonl` contains:
  - `qwen/qwen3-8b`
  - `google/gemma-3-27b-it`
  - `meta-llama/Llama-3.3-70B-Instruct-Turbo`
  The runner validates this before writing a `completed` ledger row.
- `eval_result.json` parses.
- `experimental_memory_evidence.json` shows `core_memory_exists=true`,
  `chroma_db_exists=true`, or at minimum `memory_dir_exists=true`. If all are
  false, the runner must mark the row `failed_post_run`.
- `RUN_LEDGER.csv` has the smoke attempt.
- No raw `runs/` files are staged.

Current blocker as of 2026-06-28T03:03:22-03:00:

- Latest smoke reached report generation and failed with:
  `'NoneType' object has no attribute 'get_all_nodes'`.
- Partial raw evidence had Qwen+Gemma+Llama routing and experimental memory
  initialized, but no valid report/eval and empty telemetry.
- Do not run full matrix rows until this report-generation blocker is fixed and
  the smoke gate passes.

## Full Matrix After Smoke

Only after the smoke gate passes:

```powershell
uv run --frozen --python 3.11 python backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py --temporal --execute --start-backend
uv run --frozen --python 3.11 python backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py --line5 --execute --start-backend
uv run --frozen --python 3.11 python backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py --s3 --execute --start-backend
```
