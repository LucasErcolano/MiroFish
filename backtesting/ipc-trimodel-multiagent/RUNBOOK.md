# IPC Tri-Model Runbook

Keep this file synchronized with commands that actually work.

## Environment

Run from repo root unless a command says otherwise.

```powershell
$env:OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
$env:DEEPINFRA_BASE_URL = "https://api.deepinfra.com/v1/openai"
$env:USE_EXPERIMENTAL_MEMORY = "true"

$env:GRAPH_BACKEND = "graphiti"
$env:GRAPHITI_URI = "bolt://localhost:7687"
$env:GRAPHITI_USER = "neo4j"
$env:GRAPHITI_PASSWORD = "mirofishpassword"
$env:GRAPHITI_DATABASE = "neo4j"

$env:GRAPHITI_LLM_BASE_URL = $env:DEEPINFRA_BASE_URL
$env:GRAPHITI_LLM_MODEL = "google/gemma-3-27b-it"
$env:GRAPHITI_LLM_CLIENT_MODE = "generic"
$env:GRAPHITI_EMBEDDER_BASE_URL = $env:OPENROUTER_BASE_URL
$env:GRAPHITI_EMBEDDER_MODEL = "qwen/qwen3-embedding-8b"
$env:GRAPHITI_EMBEDDER_DIM = "4096"

$env:LLM_REQUEST_TIMEOUT = "60"
$env:OASIS_PROFILE_MAX_TOKENS = "2048"
$env:OASIS_PROFILE_MAX_ATTEMPTS = "2"
$env:MIROFISH_PREPARE_STALE_AFTER_SECONDS = "420"
$env:SIMILARITY_THRESHOLD = "0"

$env:PYTHONIOENCODING = "utf-8"
```

Do not print API keys. Verify presence only:

```powershell
$names='OPENROUTER_API_KEY','DEEPINFRA_API_KEY'
foreach($n in $names){
  $v=[Environment]::GetEnvironmentVariable($n,'Process')
  $u=[Environment]::GetEnvironmentVariable($n,'User')
  [pscustomobject]@{Name=$n; ProcessPresent=[bool]$v; UserPresent=[bool]$u}
}
```

## Baseline Checks

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Expected: a Neo4j container exposing `7474` and `7687`.

```powershell
cd backend
uv run --frozen --python 3.11 python -m py_compile app\services\model_router.py scripts\run_reddit_simulation.py
uv run --frozen --python 3.11 python -c "import chromadb; print('chromadb_ok')"
uv run --frozen --python 3.11 pytest tests\test_zep_tools_backend_fallback.py -q
```

Expected: exit code 0.

`chromadb` is required by the report/memory path. The 2026-06-28 paid smoke
reached report generation and failed with `No module named 'chromadb'`; fix the
backend dependency/runtime and restart the backend before the next paid smoke.

When `USE_EXPERIMENTAL_MEMORY=true`, verify `ZepToolsService` still has a graph
backend. Report Agent uses experimental memory for contextual recall, but still
needs Graphiti/Zep graph tools for report planning and statistics.

## Model Map Validation

Use Python import-level validation so failures happen before paid runs:

```powershell
cd backend
uv run --frozen --python 3.11 python -c "from app.services.model_router import load_model_map; m=load_model_map('..\backtesting\ipc-trimodel-multiagent\model_map_ipc_trimodel.yaml'); print('model_map_ok', sorted((m.get('by_agent_id') or {}).keys()))"
```

Expected: `model_map_ok` and agent IDs mapped to Gemma/Llama overrides, with
Qwen as default.

Current status: this validation passed after importing routing/telemetry from
`origin/backtesting-feature-augmented` and adding hosted provider support.

If this fails with `No module named 'app.services.model_router'`, the branch is
missing the S2 multi-model routing layer. Preferred source branch:

```text
origin/backtesting-feature-augmented
```

Useful source files from that branch:

```text
backend/app/services/model_router.py
backend/app/services/llm_telemetry.py
configs/model_prices.yaml
configs/model_map_example.yaml
backend/tests/test_model_routing.py
```

Reference-only integration file:

```text
backend/scripts/run_reddit_simulation.py
```

Do not copy the runner wholesale from `origin/backtesting-feature-augmented`.
Cherry-pick its `--model-map`, `model_routing_audit.jsonl`, and
`llm_telemetry.jsonl` integration into the current runner because the current
branch already has the more complete S3 scheduled-event implementation.

Fallback source commit:

```text
a6e0ae6 feat(sim): per-agent multi-model routing + LLM telemetry (#21)
```

Known validation mismatch to fix before smoke:

```text
configs/model_map_s2.yaml and model_map_ipc_trimodel.yaml use provider names
openrouter/deepinfra. The source model_router.py allowlist from the augmented
branch validates only openai/vllm/lmstudio/groq. Either add openrouter and
deepinfra to PROVIDERS with the right env defaults, or use provider: openai
with provider-specific base_url_env values.
```

Current status: `openrouter` and `deepinfra` were added to `PROVIDERS`, so the
IPC model map can keep provider-specific names.

## Dedup Bypass Gate

Before building any IPC graph, implement an env-controlled bypass in
`backend/app/graph/graphiti_backend.py`.

Intended env:

```powershell
$env:GRAPHITI_BYPASS_NODE_DEDUP = "true"
```

A graph smoke is valid only if logs or run notes confirm the bypass was active
before graph build.

## Smoke Run Gate

The first smoke should be tiny and should not run the full matrix.

Plan it first:

```powershell
uv run --frozen --python 3.11 python backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py --smoke --dry-run
```

Current status: this dry-run passed and wrote
`backtesting/ipc-trimodel-multiagent/evaluation/pre_smoke_plan.json`.

The complete 15-row dry-run plan also passed and wrote
`backtesting/ipc-trimodel-multiagent/evaluation/full_matrix_plan.json`.

The original default R2 smoke can be a false positive because the first two
simulated hours may have no active agents. Use enough rounds to reach active
agents and let the smoke gate reject zero-activity artifacts.

Run it only when ready to spend credits:

```powershell
uv run --frozen --python 3.11 python backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py --smoke --execute --start-backend --smoke-rounds 12
```

If `http://127.0.0.1:5001/health` and
`http://127.0.0.1:5001/api/graph/project/list` already return HTTP 200 from a
correctly configured backend, run the same smoke without `--start-backend`:

```powershell
uv run --frozen --python 3.11 python backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py --smoke --execute --smoke-rounds 12
```

The current valid smoke target is `ipc_trimodel_smoke_T0_R12_D2`; it uses
`seed_T0.md`, 12 rounds, and the same trimodel
`model_map_ipc_trimodel.yaml`.

`model_map_ipc_trimodel.yaml` must keep effective, not merely assigned,
tri-model coverage. A fixed `by_agent_id` map can pass routing-audit checks but
fail low-depth rows if those IDs never speak. The current IPC map routes stable
roles instead:

- default: Qwen (`qwen/qwen3-8b`)
- `Organization`: Gemma (`google/gemma-3-27b-it`)
- `MediaOutlet` and `FiscalConsultancy`: Llama
  (`meta-llama/Llama-3.3-70B-Instruct-Turbo`)

Before a paid matrix rerun after map edits, validate the real map from
`backend/`:

```powershell
uv run --frozen --python 3.11 python -c "from app.services.model_router import ModelRouter, load_model_map; r=ModelRouter(load_model_map('../backtesting/ipc-trimodel-multiagent/model_map_ipc_trimodel.yaml')); print([(role,r.resolve(i,role).model,r.resolve(i,role).source) for i,role in [(20,'Organization'),(2,'MediaOutlet'),(4,'LegislativeBody')]])"
```

For IPC rows, the benchmark runner intentionally passes `--no-report` to the
generic web ReportAgent and then calls `StructuredReportAgent` from the backend
uv environment. The objective evidence is:

- `structured_answer.json`
- `structured_report.md`
- `eval_result.json` produced by `eval_objective.py --structured-answer`

The generic narrative ReportAgent output is not the IPC scoring source because
it does not reliably preserve all requested numeric forecast fields.

Historical smoke blocker:

```text
report_generate failed with:
'NoneType' object has no attribute 'get_all_nodes'
```

This happened after graph build and simulation execution. The same attempt had
Qwen+Gemma+Llama in `model_routing_audit.jsonl` and initialized experimental
memory, but it did not produce a valid report/eval result and telemetry was
empty. Debug the report graph-client initialization path before retrying the
smoke. Do not run temporal, line5, or S3 from this state.

Current smoke gate also rejects false-positive completed rows when
`run_manifest.json` shows zero completed rounds/current round/simulated hours,
or when `llm_telemetry_summary.json` has `llm_calls=0`.

For full temporal/depth/S3 rows, keep profile generation bounded. A T3 temporal
retry completed Graphiti but then stayed in `/api/simulation/prepare/status` at
`[2/4] generating_profiles: 0/37` with a stale task timestamp and no
`reddit_profiles.json`. The IPC runner now sets:

- `LLM_REQUEST_TIMEOUT=60`
- `OASIS_PROFILE_MAX_TOKENS=2048`
- `OASIS_PROFILE_MAX_ATTEMPTS=2`
- `MIROFISH_PREPARE_STALE_AFTER_SECONDS=420`
- `SIMILARITY_THRESHOLD=0`

If a row still fails there, inspect the raw simulation directory and backend log
before rerunning. Do not launch another matrix while a stale prepare poller is
still alive.

`SIMILARITY_THRESHOLD=0` bypasses the simulation-preparation semantic dedup
path. This is separate from `GRAPHITI_BYPASS_NODE_DEDUP=true`; both are needed
for IPC because the graph dedup and agent dedup systems fail in different
stages.

Required artifacts:

- `model_routing_audit.jsonl` with Qwen, Gemma, and Llama.
- `llm_telemetry.jsonl`.
- `structured_answer.json` with all IPC forecast fields.
- `experimental_memory_evidence.json` plus `core_memory.json` when available,
  or a documented fallback.
- `eval_result.json` with `parse_errors` and score.

Do not proceed to full temporal/line5/S3 until these exist.

## Completed Matrix Status

Canonical result summary:

```text
backtesting/ipc-trimodel-multiagent/RESULTS_ANALYSIS.md
```

Canonical compact evidence:

```text
backtesting/ipc-trimodel-multiagent/evaluation/temporal/
backtesting/ipc-trimodel-multiagent/evaluation/line5/
backtesting/ipc-trimodel-multiagent/evaluation/s3/
```

Useful single-row rerun commands:

```powershell
uv run --frozen --python 3.11 python backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py --temporal --rows ipc_trimodel_T3_R40_D2 --execute --start-backend
uv run --frozen --python 3.11 python backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py --line5 --rows ipc_trimodel_T3_R80_D2 --execute --start-backend
uv run --frozen --python 3.11 python backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py --s3 --conditions noise-off-mid --execute --start-backend
```

If a row finishes objective evaluation but is marked `failed_post_run`, trust
the post-run gate. For this benchmark, `completed` requires both routing audit
and telemetry summary to include all three model IDs. The S3 `noise-off-mid`
row had to be rerun for exactly this reason.

Final validation commands before commit:

```powershell
uv run --frozen --python 3.11 python -m py_compile tools\mirofish_headless.py backend\app\config.py backend\app\services\oasis_profile_generator.py backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py
uv run --frozen --python 3.11 pytest backtesting\ipc-trimodel-multiagent\scripts\test_run_ipc_trimodel_matrix.py -q
cd backend
uv run --frozen --python 3.11 pytest tests\test_model_router.py -q
```

The IPC runner validates required compact evidence before appending a
`completed` ledger row. Missing routing, telemetry summary, memory evidence,
report, eval result, run notes, or S3 scheduled-event evidence for conditions
that expect events becomes `failed_post_run`. The routing audit must contain
Qwen, Gemma, and Llama model IDs, not just exist as a file.
Before execution, the runner removes the selected row's raw output directory
under `runs/ipc_trimodel_multiagent/` so stale artifacts cannot satisfy the
evidence gate. For S3 rows with expected events, the scheduled-event JSONL line
count must equal `expected_events`.

## Result Hygiene

Raw artifacts:

```text
runs/ipc_trimodel_multiagent/
```

Committed artifacts:

```text
backtesting/ipc-trimodel-multiagent/evaluation/
```

Never commit raw DB files, backend logs, uploads, caches, or full `runs/`.

## Full Matrix Runner

After the smoke gate passes, execute one line at a time:

```powershell
uv run --frozen --python 3.11 python backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py --temporal --execute --start-backend
uv run --frozen --python 3.11 python backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py --line5 --execute --start-backend
uv run --frozen --python 3.11 python backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py --s3 --execute --start-backend
```

Use `--rows <row_id>` or `--conditions <condition>` to resume narrowly.
