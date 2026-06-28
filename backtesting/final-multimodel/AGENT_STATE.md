# Final Multimodel Agent State

Last updated: 2026-06-24

## Goal

Complete the final multimodel research layer on top of `origin/backtesting-baseline`, then commit and push. Do not create a PR.

## Current Workspace

- Worktree: `C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish-final-multimodel`
- Branch: `codex/final-multimodel-baseline`
- Base: `origin/backtesting-baseline`
- User authorized API credit spend.
- User authorized commit and push.
- User explicitly requested no PR.

## Required Lines

1. Temporal optimum cross-model:
   - Bolivia T1: Llama + Qwen.
   - Copa America T2: Llama + Qwen.
   - IPC T3/deepest selected IPC packet: Llama + Qwen.
2. S3 injection:
   - Qwen across 7 S3 conditions for Bolivia and IPC.
3. Line 5:
   - Bolivia Gemma + Qwen for R10-D2 and R80-D2.

## Important Prior Findings

- `origin/backtesting-baseline` already imports PRs #15, #16, #22, #24, #25, #26, and #29.
- Existing S3 Gemma/Llama full matrix is valid: 42/42 rows, 6/6 baselines with 0 events, 36/36 injected rows with 1 event.
- Existing temporal matrix says:
  - Bolivia optimal package: T1.
  - Copa America selected optimal package: T2.
  - IPC optimal package: T3.
- Existing Line 5 Llama Bolivia/Copa results live in `backtesting/LINE5_LLAMA_BOLIVIA_COPA.md`.

## Operational Constraints

- Never print API keys.
- Keep Qwen as simulation model where required, but avoid using Qwen for Graphiti extraction if a stable Gemma/DeepInfra extraction model is available.
- Restart backend per model group; do not rely on hot-swapping model env in an already-running backend.
- Preserve raw outputs and mark rows failed/partial instead of deleting evidence.
- Update this file after every long run, failure, or methodological decision.

## Current Resume Point

Plan has been written to `docs/superpowers/plans/2026-06-24-final-multimodel-baseline.md`.

Completed:

- Created isolated worktree and branch from `origin/backtesting-baseline`.
- Wrote persistent plan, README, state file, and run ledger.
- Added Qwen to S3 matrix.
- Patched S3 runner so Graphiti credentials/model can differ from simulation credentials/model.
- Relaxed S3 validator to allow model extensions beyond Gemma/Llama.
- Updated S3 summary scope to use the actual number of models.
- Diagnosed first S3 backend startup failure: `npm run backend` respected `backend/.python-version=3.12`, which makes `uv` resolve the unsatisfiable `camel-oasis==0.2.5` / `neo4j>=5.26.0` split. Patched S3 backend startup to call `uv run --frozen --python 3.11 python run.py` directly from `backend`.
- Restored the minimum scheduled-injection execution path that `backtesting-baseline` was missing: `tools/mirofish_headless.py` now supports `--existing-simulation-id`, `--injection-plan`, `--condition`, `--no-wait-after-run`; `/api/simulation/start` and `SimulationRunner.start_simulation` propagate `no_wait`; `backend/scripts/run_reddit_simulation.py` fires Reddit `CREATE_POST` scheduled events during the round loop and logs `scheduled_events_fired.jsonl`. This was applied surgically without importing the old S1/S2 `model_router` / telemetry stack.
- Diagnosed second S3 blocker: `backend/uv.lock` omitted `graphiti-core` despite `pyproject.toml` declaring it. Added `uv` override to keep `neo4j==5.23.0` for `camel-oasis==0.2.5`, regenerated `uv.lock`, and verified `graphiti_core` imports under `uv run --frozen --python 3.11`.
- Diagnosed third S3 blocker: simulation prepare calls `OasisProfileGenerator.deduplicate_entities`, missing from this branch. Restored the implementation from `origin/main`. Also disabled forced `response_format={"type":"json_object"}` only for Qwen profile generation, preserving the existing `_try_fix_json` repair pipeline.

Next steps:

1. Revalidate S3 package after backend/headless injection patches.
2. Smoke execute S3 Qwen for Bolivia and IPC on `baseline-control` + `signal-mid`.
3. Execute full S3 Qwen subset if smoke passes.

## 2026-06-24 Resume Notes

- Latest S3 smoke failed during `generating_config`, after Graphiti and Qwen profile generation succeeded.
- Root cause: `SimulationConfigGenerator._call_llm_with_retry` still forced `response_format={"type":"json_object"}` and returned `json.loads(content)` without verifying the result was a JSON object. Qwen/OpenRouter produced a JSON string/non-object shape, causing `_parse_time_config` to crash with `'str' object has no attribute 'get'`.
- Applied fix in `backend/app/services/simulation_config_generator.py`: skip forced `response_format` for model names containing `qwen`, normalize double-encoded JSON strings via `_ensure_json_object`, and defensively default non-dict time/event configs.
- `uv run --frozen --python 3.11 python -m py_compile app\services\simulation_config_generator.py` passed.
- S3 Qwen smoke after the fix completed 3/4 rows: `bolivia/baseline-control` 0/0 events, `bolivia/signal-mid` 1/1 events, `ipc/baseline-control` 0/0 events. `ipc/signal-mid` failed because a newly forced IPC prepare wrote `prepared_manifest.status=prepared` even though `prepare_status.result.status=failed`, `config_generated=false`, and no `simulation_config.json` existed.
- Patched `backtesting/s3-cross-topic-injection/scripts/run_s3_matrix.py` so prepare is considered invalid unless `simulation_config.json` exists and the prepare result did not fail.
- Reran `ipc/qwen/signal-mid` with `--force` but without `--force-prepare`; the runner discovered the valid IPC prepared simulation from `ipc/qwen/baseline-control-r20` and completed `events=1/1`.
- S3 Qwen smoke now valid: 4/4 rows.
- Full S3 Qwen Bolivia+IPC completed with `valid=14/14`.
- Committable summary written to `backtesting/final-multimodel/evaluation/s3_qwen_bolivia_ipc_full_summary.{csv,json,md}`.

Next resume point:

1. Run temporal optimum Llama+Qwen rows with `backtesting/scripts/run_final_temporal_optimum.py --start-backend`.
2. Implement/run Line 5 Bolivia Gemma+Qwen rows.
3. Write final report, validate, commit, push.

Temporal runner notes:

- Added `backtesting/final-multimodel/temporal_optimum_matrix.yaml`.
- Added `backtesting/scripts/run_final_temporal_optimum.py`.
- The runner executes full 40-round simulations via the existing generic matrix runner path and writes raw artifacts under `runs/final_multimodel/raw_temporal/`.
- The committable summary/evidence target is `backtesting/final-multimodel/evaluation/temporal_optimum/` plus `temporal_optimum_summary.{csv,json,md}`.

## 2026-06-24 Temporal Graph-Build Diagnosis

- `llama_bolivia_T1_R40_D2` completed before compaction and produced committed evidence under `backtesting/final-multimodel/evaluation/temporal_optimum/bolivia/llama/`.
- The first resumed full temporal run skipped Bolivia/Llama but got stuck rebuilding Copa T2 at Graphiti task `442cfc86-8b2e-4c89-a992-5e64150a4336`, progress `24`, message `sending batch 1/5`.
- Querying Neo4j by `group_id` showed only the current Bolivia graph exists locally:
  - present: `mirofish_d4ed97d1a3a3455e`.
  - absent: previous Copa T2 `mirofish_eeb30a71652a4bdd`, previous IPC T3 `mirofish_84d7ae07d55846d9`.
- Therefore old Copa/IPCi `run_notes.md` IDs cannot be reused without rebuilding the graph. Restoring only `project.json` would be misleading because the graph data is absent.
- Patched `backend/app/api/graph.py` so graph build batch size defaults to `GRAPH_BUILD_BATCH_SIZE=1` instead of batching 3 chunks. This is intended to reduce long Graphiti extraction hangs.
- Patched `backtesting/scripts/run_line5_llama_matrix.py` to reuse a graph from a `run_notes.md` only if both `project_id` and `graph_id` are present and the backend validates it.
- Patched `backtesting/scripts/run_final_temporal_optimum.py` to skip already completed raw outputs and merge existing/new temporal summary rows.

## 2026-06-24 Line 5 Prep And Temporal Watch

- Added final Bolivia Line 5 slim configs for Gemma and Qwen:
  - `backtesting/case-b-s2-bolivia-2025-runoff/config_line5_gemma_slim.yaml`
  - `backtesting/case-b-s2-bolivia-2025-runoff/config_line5_qwen_slim.yaml`
- Added `backtesting/scripts/run_final_line5_matrix.py`.
- Line 5 dry-run verified exactly four target rows:
  - `gemma_T3_slim_R10_D2`
  - `gemma_T3_slim_R80_D2`
  - `qwen_T3_slim_R10_D2`
  - `qwen_T3_slim_R80_D2`
- Raw Line 5 artifacts are configured under `runs/final_multimodel/raw_line5/`; committable evidence will be copied under `backtesting/final-multimodel/evaluation/line5_bolivia/`.
- Patched `backtesting/scripts/run_line5_llama_matrix.py` so structured evaluators can recover from missing `structured_answer.json` by extracting a fenced JSON block from `report.md`.
- This matters for `llama_copa_T2_R40_D2`: the backend report completed and contains a fenced JSON answer, but did not save `structured_answer.json`.
- The running temporal process is still `uv run --frozen --python 3.11 python ..\backtesting\scripts\run_final_temporal_optimum.py --start-backend`.
- As of the latest check, IPC/Llama is still in report generation, section 3/5. It has hit `interview_agents` IPC timeouts, but the ReportAgent continued generating sections afterwards.

## 2026-06-24 Temporal Llama Completion

- `llama_ipc_T3_R40_D2` completed the 40/40 simulation with 130 actions and generated report `report_1a275975b0b5`.
- ReportAgent generated all five IPC sections. `interview_agents` repeatedly timed out, but with `MIROFISH_INTERVIEW_AGENTS_TIMEOUT=45` the report continued instead of hanging.
- The backend did not save `structured_answer.json` for IPC/Llama and the markdown report did not include a JSON code block. I patched `backtesting/scripts/run_line5_llama_matrix.py` so structured evaluators fall back to `report.md` when a case evaluator supports it.
- IPC/Llama was finalized from the existing output without rerunning simulation or report:
  - `artifact_kind=report_markdown`
  - `score=0/5`
  - `parse_errors=5`
  - `leak_flags=[]`
- Temporal Llama summary is now complete: Bolivia, Copa, and IPC all have committed evidence under `backtesting/final-multimodel/evaluation/temporal_optimum/*/llama/`.
- Updated `backtesting/final-multimodel/temporal_optimum_matrix.yaml` so Qwen reuses the freshly validated Llama graph run notes for Bolivia, Copa, and IPC.

Next resume point:

1. Run Qwen temporal:
   `uv run --frozen --python 3.11 python ..\backtesting\scripts\run_final_temporal_optimum.py --models qwen --start-backend`
2. Then run Line 5:
   `uv run --frozen --python 3.11 python ..\backtesting\scripts\run_final_line5_matrix.py --case-dir ..\backtesting\case-b-s2-bolivia-2025-runoff --models gemma,qwen --start-backend`

## 2026-06-24 Temporal Qwen Progress

- Launched Qwen temporal batch with:
  `uv run --frozen --python 3.11 python ..\backtesting\scripts\run_final_temporal_optimum.py --models qwen --start-backend`
- `qwen_bolivia_T1_R40_D2` completed 40/40 with 280 total platform actions.
- Bolivia/Qwen committed evidence currently exists under `backtesting/final-multimodel/evaluation/temporal_optimum/bolivia/qwen/`.
- Bolivia/Qwen evaluation:
  - prediction: `quiroga_gana`
  - ground truth: `paz_gana`
  - score: `0`
  - winner_score: `0`
  - mae_vote_share: `8.667`
  - margin_abs_error: `7.94`
  - parse_errors: `0`
  - leak_flags: `[]`
- Runner advanced automatically to `qwen_copa_T2_R40_D2`.
- Current active simulation prepare is Copa/Qwen, simulation id `sim_e9c606198740`, generating profiles for the Copa America T2 package.
- `qwen_copa_T2_R40_D2` completed 40/40 with 234 total platform actions.
- Copa/Qwen committed evidence exists under `backtesting/final-multimodel/evaluation/temporal_optimum/copa/qwen/`.
- Copa/Qwen evaluation:
  - predicted_winner: `Argentina`
  - score: `5/5`
  - confidence: `0.55`
  - winner_probability_point: `0.504`
  - parse_errors: `0`
  - leak_flags: `[]`
  - caveat: evaluator reports `winner_range_width_valid=false`, but existing score logic still awards 5/5.
- Runner advanced automatically to `qwen_ipc_T3_R40_D2`.
- Current active simulation prepare is IPC/Qwen, simulation id `sim_979e61ea7e1f`, generating profiles for the IPC T3 package.
- `qwen_ipc_T3_R40_D2` completed 40/40 with 102 total platform actions.
- IPC/Qwen committed evidence exists under `backtesting/final-multimodel/evaluation/temporal_optimum/ipc/qwen/`.
- IPC/Qwen evaluation:
  - artifact_kind: `report_markdown`
  - score: `2/5`
  - delta_1_prediction: `25.9`
  - delta_1_abs_error: `23.5`
  - parse_errors: `0`
  - leak_flags: `[]`
- Temporal optimum summary is complete at `backtesting/final-multimodel/evaluation/temporal_optimum_summary.csv` with 6/6 rows:
  Llama+Qwen for Bolivia T1, Copa T2, and IPC T3.

Next resume point:

1. Run Line 5:
   `uv run --frozen --python 3.11 python ..\backtesting\scripts\run_final_line5_matrix.py --case-dir ..\backtesting\case-b-s2-bolivia-2025-runoff --models gemma,qwen --start-backend`

## 2026-06-24 Line 5 Execution Progress

- Started final Line 5 runner:
  `uv run --frozen --python 3.11 python ..\backtesting\scripts\run_final_line5_matrix.py --case-dir ..\backtesting\case-b-s2-bolivia-2025-runoff --models gemma,qwen --start-backend`
- `gemma_T3_slim_R10_D2` completed and committed evidence exists under:
  `backtesting/final-multimodel/evaluation/line5_bolivia/gemma/gemma_T3_slim_R10_D2/`
- `gemma_T3_slim_R10_D2` evaluation:
  - prediction: `quiroga_gana`
  - ground truth: `paz_gana`
  - score: `0`
  - winner_score: `0`
  - mae_vote_share: `6.353`
  - margin_abs_error: `16.06`
  - parse_errors: `0`
  - leak_flags: `[]`
- ReportAgent hit one `interview_agents` timeout during the R10 report, but continued and completed all three sections. Treat this as a methodological caveat, not a failed run.
- Current active row is `gemma_T3_slim_R80_D2`, simulation id `sim_defecff3a523`, in prepare/config generation under the same Gemma backend log:
  `runs/s3_cross_topic/_backend_logs/backend-final-line5-gemma-2026-06-24T150228Z0000.log`.

## 2026-06-24 Line 5 Gemma Completion

- `gemma_T3_slim_R80_D2` completed and committed evidence exists under:
  `backtesting/final-multimodel/evaluation/line5_bolivia/gemma/gemma_T3_slim_R80_D2/`
- `gemma_T3_slim_R80_D2` evaluation:
  - prediction: `quiroga_gana`
  - ground truth: `paz_gana`
  - score: `0`
  - winner_score: `0`
  - mae_vote_share: `null`
  - margin_abs_error: `null`
  - parse_errors: `2`
  - leak_flags: `[]`
- Gemma Line 5 result so far: both R10 and R80 predict the wrong winner (`quiroga_gana`), with R80 parsing worse than R10.
- Qwen backend started with log:
  `runs/s3_cross_topic/_backend_logs/backend-final-line5-qwen-2026-06-24T154313Z0000.log`
- Qwen graph build completed for the Line 5 package:
  - project_id: `proj_da8e4263af54`
  - graph_id: `mirofish_c489d9b4ae344aba`
  - graph_task_id: `802f813f-8cdf-4476-ac54-2c84b61a33bb`
  - graph stats: 9 nodes, 12 edges
- Current active Qwen row is `qwen_T3_slim_R10_D2`, simulation id `sim_09d185416aa0`, in prepare/profile generation.

## 2026-06-24 Final Completion Notes

- `qwen_T3_slim_R10_D2` completed and committed evidence exists under:
  `backtesting/final-multimodel/evaluation/line5_bolivia/qwen/qwen_T3_slim_R10_D2/`
- `qwen_T3_slim_R10_D2` evaluation:
  - prediction: `quiroga_gana`
  - ground truth: `paz_gana`
  - score: `0`
  - winner_score: `0`
  - mae_vote_share: `9.687`
  - margin_abs_error: `21.06`
  - parse_errors: `0`
  - leak_flags: `[]`
- `qwen_T3_slim_R80_D2` completed and committed evidence exists under:
  `backtesting/final-multimodel/evaluation/line5_bolivia/qwen/qwen_T3_slim_R80_D2/`
- `qwen_T3_slim_R80_D2` evaluation:
  - prediction: `quiroga_gana`
  - ground truth: `paz_gana`
  - score: `0`
  - winner_score: `0`
  - mae_vote_share: `13.02`
  - margin_abs_error: `29.06`
  - parse_errors: `0`
  - leak_flags: `[]`
  - caveat: target variant is R80 but the backend-generated run ended at 72 actual rounds.
- All required research lines are complete:
  - S3 Qwen Bolivia+IPC: `14/14` valid rows.
  - Temporal optimum Llama+Qwen: `6/6` completed rows.
  - Bolivia Line 5 Gemma+Qwen: `4/4` completed rows.
- Consolidated report written to:
  `backtesting/final-multimodel/evaluation/final_multimodel_report.md`
- No backend or runner process is intentionally left running.
- Fresh validation before commit:
  - Python compile passed for touched backend services and backtesting/headless runners.
  - S3 package validator passed: `topics=3`, `models=3`, `conditions=7`, `full_rows=63`.
  - Final multimodel JSON artifacts parsed successfully: `19`.
  - Secret scan found only documented placeholders and grep patterns, not live keys.
- Next steps are narrow staging, commit, and push. Do not create a PR.
