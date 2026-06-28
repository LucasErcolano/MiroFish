# IPC Tri-Model Agent State

Last updated: 2026-06-28

## Read First

Current objective: complete the IPC 2025 tri-model multi-agent benchmark.

Current branch: `codex/ipc-trimodel-multiagent`.

Base state:

- Started from `origin/backtesting-baseline` at `bbb48e0`.
- Merged `origin/codex/final-multimodel-baseline` locally at merge commit `e73bffb`.
- The original local changes from `codex/s3-cross-topic-injection` were stashed as:
  `codex-temp-before-bringing-merged-final-multimodel`.

## Current Status

Smoke gate, temporal IPC matrix, Line5 depth, and S3 noise/signal matrix are
complete. Canonical analysis lives in `RESULTS_ANALYSIS.md`; compact evidence
lives under `evaluation/`; raw evidence remains local under
`runs/ipc_trimodel_multiagent/`.

Latest canonical results:

- Temporal T0-T3 completed with zero objective eval parse errors. T1/T2/T3
  improved the February absolute error to `0.1`; T2 was the best temporal
  packet by score and December error.
- Line5 R10/R20/R40/R80 completed. R10 was the best trimodel depth row
  (`3/5`, about 50k tokens). R80 was expensive and noisy (`1/5`, 11 telemetry
  errors, 39 telemetry parse errors).
- S3 7/7 canonical rows completed. Baseline-control was strongest (`4/5`);
  signals/noise mostly degraded results, so this is not strong evidence of
  noise robustness.
- The final S3 `noise-off-mid` row was rerun because the first completed eval
  lacked Llama telemetry. The rerun passed with Qwen, Gemma, and Llama in
  `llm_telemetry_summary.json` and is the canonical row.

Current remaining action: run final validation, stage only intended compact
code/docs/evidence, commit, and push. Do not open a PR.

Latest execution notes:

- 2026-06-28T09:38-03:00: temporal T3 retry completed after profile-generation
  guardrails. Raw DB evidence for `ipc_trimodel_T3_R40_D2` included 26 posts,
  136 comments, 367 traces, and 35 users. Compact evidence was copied with
  `score=2/5`, `delta_1.abs_error=0.1`, and `parse_errors=0`.
- 2026-06-28T10:07-03:00: first Line5 R10 attempt produced real DB/eval
  evidence but failed post-run validation. `model_routing_audit.jsonl` included
  Qwen, Gemma, and Llama by fixed IDs, but `llm_telemetry_summary.json` showed
  only Qwen because the first 10 rounds activated different agent IDs. The
  failed ledger row is intentional evidence that the gate caught a non-trimodel
  effective run.
- 2026-06-28T10:10-03:00: changed
  `backtesting/ipc-trimodel-multiagent/model_map_ipc_trimodel.yaml` from
  fixed `by_agent_id` overrides to stable `by_role` routing:
  `Organization -> Gemma`, `MediaOutlet`/`FiscalConsultancy -> Llama`, default
  `Qwen`. Verified with backend `test_model_router.py`, runner tests, and a
  direct resolver check. Relaunched Line5 from R10 with `--line5 --execute
  --start-backend`.
- 2026-06-28T10:34-03:00: stopped that Line5 rerun during preparation because
  it reached the separate simulation semantic dedup path
  (`SIMILARITY_THRESHOLD=0.85`) and stayed in `[1/4] deduplication`. This is
  the half-finished dedup path the team said to bypass. Runner env now sets
  `SIMILARITY_THRESHOLD=0` in addition to `GRAPHITI_BYPASS_NODE_DEDUP=true`.
- 2026-06-28T11:13-03:00: Line5 `ipc_trimodel_T3_R10_D2` completed valid
  after role-based routing and `SIMILARITY_THRESHOLD=0`. Effective telemetry:
  Qwen, Gemma, and Llama all appeared in `llm_telemetry_summary.json`.
  Objective result: `score=3/5`, `delta_1.abs_error=0.1`, `parse_errors=0`.
  Runner automatically advanced to `ipc_trimodel_T3_R20_D2`.
- 2026-06-28T11:45-03:00: Line5 `ipc_trimodel_T3_R20_D2` completed valid.
  Objective result: `score=2/5`, `delta_1.abs_error=0.1`, `parse_errors=0`;
  telemetry included all three models with about 1.10M total tokens. Runner
  automatically advanced to `ipc_trimodel_T3_R40_D2`.

Current attempt:

- 2026-06-28T01:53:50-03:00: pre-smoke validation passed in this thread.
  Backend health at `http://127.0.0.1:5001/health` returned OK, so the paid
  smoke will run without `--start-backend`. Neo4j is running, backend
  dependencies/py_compile pass from `backend/`, the IPC model map validates,
  and `--smoke --dry-run` selected only `ipc_trimodel_smoke_T0_R2_D2`.
- 2026-06-28T01:55:33-03:00: revalidated in this thread before paid smoke.
  Current branch is `codex/ipc-trimodel-multiagent`, Neo4j exposes `7474` and
  `7687`, backend `/health` and `/api/graph/project/list` returned HTTP 200,
  both required API keys are present, and `--smoke --dry-run` again selected
  only `ipc_trimodel_smoke_T0_R2_D2`. Starting paid smoke without
  `--start-backend`.
- 2026-06-28T02:20:36-03:00: paid smoke failed during report generation.
  The first launch path briefly produced a duplicate smoke process because the
  shell hook rewrote a command while a `Start-Process` monitor also launched
  one; the older process tree was stopped and only the newer monitored run was
  kept. The kept run reached graph build, simulation preparation, simulation,
  and report generation, then `/api/report/generate/status` returned
  `failed` with `No module named 'chromadb'`. Raw
  `model_routing_audit.jsonl` included Qwen, Gemma, and Llama in the same
  simulation, but `llm_telemetry.jsonl` was empty and
  `experimental_memory_evidence.json` reported no memory dir, no core memory,
  and no Chroma DB. `backend` uv env check showed `chromadb_spec False`, and
  `chromadb` was not found in `backend/pyproject.toml` or lock search.
- 2026-06-28T02:24:00-03:00: added `chromadb>=0.5.0` to the backend
  dependency set with `uv add --python 3.11`, stopped the stale backend, and
  verified `uv run --frozen --python 3.11 python -c "import chromadb"` from
  `backend/` prints `chromadb_ok 1.5.9`. Next paid smoke retry will use
  `--start-backend` so the runner launches a backend from the corrected
  environment.
- 2026-06-28T02:38:18-03:00: paid smoke retry failed during report generation
  after the `chromadb` dependency was fixed. The backend error was
  `'ExperimentalMemoryService' object has no attribute 'core_memory'`. Root
  cause: `_load_core_memory()` called `save_core_memory()` before
  `self.core_memory` existed when initializing from generated profiles.
- 2026-06-28T02:43:16-03:00: fixed experimental memory initialization by
  writing initial profile-derived core memory directly and making
  `save_core_memory()` robust before `self.core_memory` exists. Verified:
  `uv run --frozen --python 3.11 pytest tests\test_spike_integration.py -q`
  from `backend/` passed with 5 tests. Next paid smoke retry will again use
  `--start-backend` and no matrix rows will run unless the smoke gate passes.
- 2026-06-28T02:25:23-03:00: main monitor verified the corrected backend
  environment imports `chromadb` with `uv run --frozen --python 3.11`. The
  old manually-started backend was still listening on port `5001`, so stop it
  before retrying the smoke with `--start-backend`.
- 2026-06-28T03:03:22-03:00: third paid smoke attempt got past Graphiti
  updater initialization and Report Agent initialization, but failed during
  Report Agent planning/statistics with
  `'NoneType' object has no attribute 'get_all_nodes'`. Root cause:
  `ZepToolsService` used the experimental-memory provider for simulation
  memory, but left `self.backend=None`; Report Agent still needs the graph
  backend for `get_graph_statistics`, `get_all_nodes`, and `get_all_edges`.
- 2026-06-28T03:07:20-03:00: fixed `ZepToolsService` to fall back to
  `get_graph_backend(api_key=...)` when the selected memory provider has no
  `backend` attribute. Verified with
  `uv run --frozen --python 3.11 pytest tests\test_zep_tools_backend_fallback.py tests\test_spike_integration.py::test_core_memory_initializes_from_profiles_without_existing_attribute -q`
  and `uv run --frozen --python 3.11 python -m py_compile
  app\services\zep_tools.py app\services\experimental_memory.py`.
- 2026-06-28T03:08:45-03:00: starting a fourth paid smoke retry in the
  foreground with `--start-backend` after the `ZepToolsService.backend`
  fallback fix. Do not start another smoke while this command is running.
- 2026-06-28T03:28:39-03:00: fourth paid smoke returned exit code 0 and wrote
  compact artifacts, but it is invalid evidence. `run_manifest.json` shows
  `num_rounds_or_epochs=0`, `final_run_status.current_round=0`,
  `reddit_actions_count=0`, and `llm_telemetry_summary.json` shows
  `llm_calls=0`. Root cause: the R2 smoke only reaches simulated hours with no
  active agents, so the backend loop can mark the run completed without real
  agent activity. Do not count `ipc_trimodel_smoke_T0_R2_D2` as a valid smoke.
- 2026-06-28: smoke gate hardened in
  `backtesting/ipc-trimodel-multiagent/scripts/run_ipc_trimodel_matrix.py`.
  `validate_committed_evidence()` now rejects completed artifacts when
  `run_manifest.json` shows no completed rounds/current round/simulated hours
  or when `llm_telemetry_summary.json` has `llm_calls=0`. Verified with
  `uv run --frozen --python 3.11 pytest backtesting\ipc-trimodel-multiagent\scripts\test_run_ipc_trimodel_matrix.py -q`
  passing 10 tests.
- 2026-06-28T05:40:08-03:00: final smoke gate passed on
  `ipc_trimodel_smoke_T0_R12_D2` using the production matrix path:
  headless simulation with `--no-report`, then `StructuredReportAgent` for
  `structured_answer.json`. Compact evidence includes Qwen, Gemma, and Llama
  in telemetry, experimental memory evidence, structured answer JSON,
  `eval_result.json` with `score=1/5`, and `parse_errors=0`.
- 2026-06-28T05:43-03:00: temporal T0-T3 run started with
  `--temporal --execute --start-backend`.
- 2026-06-28T08:00-03:00: temporal T2 rerun completed with real simulation
  artifacts. Graph task `38eea118-5147-46a1-914c-32712dd358f7` completed with
  51 nodes and 31 edges; simulation `sim_94a103a18abe` produced 10 posts,
  95 comments, 245 traces, and 24 users. Compact evidence was copied to
  `backtesting/ipc-trimodel-multiagent/evaluation/temporal/ipc_trimodel_T2_R40_D2`.
- 2026-06-28T08:39-03:00: temporal T3 first retry was stopped as stale.
  Graph task `a3ec68ad-6781-4889-8f95-8febbd7732a8` completed with 73 nodes
  and 51 edges, but preparation for simulation `sim_4c1eb8946a9c` stayed at
  `[2/4] generating_profiles: 0/37` with task `updated_at` stuck at
  `08:11:58`. No `reddit_profiles.json` or `run_manifest.json` was written.
  Root cause category: profile-generation LLM calls had no explicit short
  timeout and the headless prepare polling only failed at the full poll timeout.
- 2026-06-28T08:42-03:00: added bounded profile-generation guardrails:
  `LLM_REQUEST_TIMEOUT`, `OASIS_PROFILE_MAX_TOKENS`,
  `OASIS_PROFILE_MAX_ATTEMPTS`, and
  `MIROFISH_PREPARE_STALE_AFTER_SECONDS`. Verified with
  `uv run --frozen --python 3.11 python -m py_compile tools\mirofish_headless.py backend\app\config.py backend\app\services\oasis_profile_generator.py backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py`
  and
  `uv run --frozen --python 3.11 pytest backtesting\ipc-trimodel-multiagent\scripts\test_run_ipc_trimodel_matrix.py -q`
  passing 12 tests. Next action is to rerun only T3.
- 2026-06-28T03:03:22-03:00: paid smoke retry reached graph build,
  simulation preparation, simulation execution, and report generation, then
  failed in `/api/report/generate/status` with
  `'NoneType' object has no attribute 'get_all_nodes'`. This attempt produced
  partial raw evidence: graph id `mirofish_e934c2c5575347f2`, simulation id
  `sim_1e939736a8f0`, routing audit with Qwen+Gemma+Llama in the same
  simulation, and experimental memory evidence with `memory_dir_exists=true`,
  `core_memory_exists=true`, and `chroma_db_exists=true`. It did not produce a
  valid report, eval result, completed compact evidence set, or non-empty
  telemetry. Per smoke-gate rules, temporal/line5/S3 were not run.

Completed setup:

- Created durable planning directory: `backtesting/ipc-trimodel-multiagent/`.
- Created root `AGENTS.md` for future threads.
- Confirmed API keys are present in environment without printing values:
  `OPENROUTER_API_KEY`, `DEEPINFRA_API_KEY`.
- Confirmed Neo4j Docker container is running on ports `7474` and `7687`.
- Confirmed `matrix.yaml` and `model_map_ipc_trimodel.yaml` parse as YAML.
- Discovered the current branch does not contain
  `backend/app/services/model_router.py` or `backend/app/services/llm_telemetry.py`.
  Those files exist in prior commit `a6e0ae6 feat(sim): per-agent multi-model routing + LLM telemetry (#21)`.
  The execution thread must reimport or reimplement that routing layer before
  validating `model_map_ipc_trimodel.yaml`.
- Refreshed remotes and verified the teammate branch is named
  `origin/backtesting-feature-augmented` at `ad3e4f9`, not
  `backtesting-augmented-feature`.
- `origin/backtesting-feature-augmented` is now the preferred source for the
  completed S2/S3 system pieces because it already includes the multi-model
  routing services, telemetry, wiki-backed report memory, model-map configs,
  model prices, and smoke artifacts. Use it as a selective source, not as a
  full branch merge.
- Current branch already has `experimental_memory.py`, `memory_factory.py`, and
  `memory_provider.py`.
- Do not copy `backend/scripts/run_reddit_simulation.py` wholesale from
  `origin/backtesting-feature-augmented`: that branch has the routing/telemetry
  integration, but the current branch has the more complete scheduled-event
  implementation used by S3.
- `configs/model_map_s2.yaml` from `origin/backtesting-feature-augmented` uses
  `provider: openrouter` and `provider: deepinfra`, while the source
  `model_router.py` validates a smaller provider allowlist. Fix provider
  validation or normalize the IPC model map before paid smoke runs.
- Selectively imported `backend/app/services/model_router.py`,
  `backend/app/services/llm_telemetry.py`, and `configs/model_prices.yaml` from
  `origin/backtesting-feature-augmented`.
- Kept/adapted the paused helper thread tests for router precedence, Graphiti
  dedup bypass, and CLI-over-config `model_map_path` precedence.
- Added OpenRouter and DeepInfra provider support to `model_router.py` so
  `model_map_ipc_trimodel.yaml` validates without normalizing provider names.
- Added `GRAPHITI_BYPASS_NODE_DEDUP` support in
  `backend/app/graph/graphiti_backend.py`.
- Integrated `--model-map`, `model_routing_audit.jsonl`, and
  `llm_telemetry.jsonl` support into `backend/scripts/run_reddit_simulation.py`
  while preserving the current branch's scheduled-event logic.
- Added `model_map_path` propagation through:
  `tools/mirofish_headless.py` -> `/api/simulation/start` ->
  `SimulationRunner.start_simulation(...)` ->
  `backend/scripts/run_reddit_simulation.py --model-map`.
- Updated headless artifact capture so completed runs can persist
  `mirofish_report_raw.md`, `report_meta.json`,
  `simulation_artifacts/model_routing_audit.jsonl`, and
  `simulation_artifacts/llm_telemetry.jsonl`.
- Updated headless memory capture so completed runs persist
  `simulation_artifacts/experimental_memory_evidence.json` and copy
  `core_memory.json` when present.
- Added IPC trimodel runner:
  `backtesting/ipc-trimodel-multiagent/scripts/run_ipc_trimodel_matrix.py`.
  It requires explicit `--dry-run` or `--execute`, supports `--smoke`,
  `--temporal`, `--line5`, `--s3`, `--rows`, and `--conditions`, and writes
  compact evidence under `backtesting/ipc-trimodel-multiagent/evaluation/`.
- Added pre-smoke checklist:
  `backtesting/ipc-trimodel-multiagent/PRE_SMOKE_CHECKLIST.md`.
- Generated current dry-run plan:
  `backtesting/ipc-trimodel-multiagent/evaluation/pre_smoke_plan.json`.
- Generated current full matrix dry-run plan:
  `backtesting/ipc-trimodel-multiagent/evaluation/full_matrix_plan.json`.
- Runner env now pins Graphiti embeddings to OpenRouter
  `qwen/qwen3-embedding-8b` with dimension `4096`, matching the existing S3
  hosted-run pattern instead of falling through to the local default
  `qwen3-embedding:8b`.
- Verified:
  `uv run --frozen --python 3.11 pytest tests/test_model_router.py tests/test_graphiti_dedup_bypass.py tests/test_s2_scheduled_injection.py`
  passed with 10 tests.
- Verified touched Python compilation and IPC model-map validation.
- Verified headless/model-map tests:
  `uv run --frozen --python 3.11 pytest tests\test_mirofish_headless.py`
  passed with 5 tests after memory evidence capture was added.
- Verified backend routing/injection tests:
  `uv run --frozen --python 3.11 pytest tests/test_model_router.py tests/test_graphiti_dedup_bypass.py tests/test_s2_scheduled_injection.py tests/test_simulation_runner_model_map.py`
  passed with 12 tests.
- Verified runner dry-runs:
  `--temporal --dry-run --limit 1`,
  `--s3 --dry-run --conditions baseline-control --limit 1`,
  `--all --dry-run --write-plan`, and `--smoke --dry-run`.
- Review fix verification:
  `uv run --frozen --python 3.11 pytest tests/test_graphiti_dedup_bypass.py`
  passed with 2 tests after switching Graphiti bypass uuid map to `uuid -> uuid`.
- Added required compact-evidence validation to the IPC runner. A row is not
  ledged as `completed` unless report, eval result, run notes, manifest,
  routing audit, telemetry summary, and experimental memory evidence exist.
- Evidence validation now also checks that routing audit includes all three
  required model IDs, S3 event logs match `expected_events`, and baseline
  zero-event controls do not require an event log.
- The runner removes a selected row's raw output directory before execution,
  guarded to stay under `runs/ipc_trimodel_multiagent/`, so stale artifacts
  cannot satisfy evidence validation.
- Runner evidence tests:
  `uv run --frozen --python 3.11 pytest backtesting\ipc-trimodel-multiagent\scripts\test_run_ipc_trimodel_matrix.py`
  passed with 8 tests.
- Structured IPC reporting is now the benchmark evidence path. The runner
  passes `--no-report` to the generic web ReportAgent and then calls
  `StructuredReportAgent` from the backend uv environment to write
  `structured_answer.json`, `structured_report.md`, and
  `structured_report_meta.json`. Objective evaluation uses
  `eval_objective.py --structured-answer`.
- `DEEPINFRA_BASE_URL` was not set in the environment at inspection time; set it
  in runner env to `https://api.deepinfra.com/v1/openai`.
- `USE_EXPERIMENTAL_MEMORY` was not set in the environment at inspection time;
  set it to `true` for benchmark runs.

## Required Benchmark Lines

1. Temporal:
   - IPC T0, T1, T2, T3.
   - Multi-agent Qwen+Gemma+Llama in each simulation.
   - Fixed R40-D2 unless matrix changes are explicitly documented.
2. Line 5 depth:
   - IPC T3.
   - R10-D2, R20-D2, R40-D2, R80-D2.
   - Core comparison: multi-agent R40 vs single-agent R80.
3. S3 noise/signals:
   - IPC baseline-control.
   - signal-early, signal-mid, signal-late.
   - counter-signal-mid.
   - noise-near-mid.
   - noise-off-mid.

## Must-Have Validity Checks

- Multi-agent rows must produce `model_routing_audit.jsonl` showing all three
  models inside the same simulation.
- Experimental memory rows must produce or log the experimental memory path:
  `core_memory.json`, `chroma_db`, or documented keyword fallback.
- IPC graph build must use the dedup bypass before the graph is built.
- Structured output must be evaluated by IPC `eval_objective.py`.
- Results must record MAE, parse errors, score, leak flags, and telemetry cost
  when available.

## Next Action

Next engineering action:

1. Run final validation:
   `uv run --frozen --python 3.11 python -m py_compile tools\mirofish_headless.py backend\app\config.py backend\app\services\oasis_profile_generator.py backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py`
2. Run runner tests:
   `uv run --frozen --python 3.11 pytest backtesting\ipc-trimodel-multiagent\scripts\test_run_ipc_trimodel_matrix.py -q`
3. Run backend routing tests from `backend/`:
   `uv run --frozen --python 3.11 pytest tests\test_model_router.py -q`
4. Inspect `git status --short` and stage only code/docs/compact evidence.
   Never stage raw `runs/`, `backend/uploads`, local DBs, caches, logs, or
   secrets.
5. Commit and push `codex/ipc-trimodel-multiagent`. Do not create a PR.
