# IPC Tri-Model TODO

## 0. Preparation

- [x] Move to branch `codex/ipc-trimodel-multiagent`.
- [x] Merge final multimodel baseline files into this branch.
- [x] Create durable state/docs package.
- [x] Create root `AGENTS.md` for future threads.
- [x] Fetch and inspect `origin/backtesting-feature-augmented` as teammate
      source branch for the complete simulation system.
- [x] Verify backend dependency sync on Python 3.11.
- [x] Verify API key presence in the execution shell.

## 1. Code Readiness

- [x] Reimport or rebuild `backend/app/services/model_router.py` and
      `backend/app/services/llm_telemetry.py` from
      `origin/backtesting-feature-augmented` (fallback reference: `a6e0ae6`).
- [x] Decide whether to keep/adapt the test-only files already created by the
      paused helper thread:
      `backend/tests/test_model_router.py`,
      `backend/tests/test_graphiti_dedup_bypass.py`, and the edit in
      `backend/tests/test_s2_scheduled_injection.py`.
- [x] Import or adapt `configs/model_prices.yaml`.
- [x] Fix provider handling so `openrouter` and `deepinfra` routes validate, or
      normalize all hosted routes to `provider: openai` plus `base_url_env`.
- [x] Reconnect `backend/scripts/run_reddit_simulation.py` to `--model-map`
      using `origin/backtesting-feature-augmented` as reference, while
      preserving the current branch's scheduled-event support.
- [x] Add env-controlled Graphiti dedup bypass.
- [x] Add a unit or smoke-level check for the dedup bypass branch.
- [x] Confirm `run_reddit_simulation.py --model-map` is reachable through the
      headless/runners used by IPC.
- [x] Add or adapt an IPC tri-model runner that can run one variant at a time.
- [x] Ensure runner is prepared to write compact evidence to `evaluation/` and raw artifacts
      to `runs/ipc_trimodel_multiagent/`.
- [x] Validate the compact-evidence copy path with the first paid smoke.

## 2. Smoke Gate

- [x] Compile touched Python files.
- [x] Validate `model_map_ipc_trimodel.yaml`.
- [x] Run graph build smoke for IPC T0 with dedup bypass enabled.
- [x] Run one short multi-agent IPC smoke:
      `ipc_trimodel_smoke_T0_R12_D2`.
- [x] Verify `model_routing_audit.jsonl` contains Qwen, Gemma, and Llama.
- [x] Verify experimental memory initialized or fallback is documented.
- [x] Verify `eval_objective.py` returns parseable result.

## 3. Temporal Matrix

- [x] Run IPC T0 R40-D2 multi-agent.
- [x] Run IPC T1 R40-D2 multi-agent.
- [x] Run IPC T2 R40-D2 multi-agent.
- [x] Run IPC T3 R40-D2 multi-agent. First retry graph completed, then
      profile generation stalled at 0/37; second retry passed after
      timeout/stale guardrails.
- [x] Summarize MAE/parse_errors/score by T in `RESULTS_ANALYSIS.md`.
- [ ] Compare against Gemma/Qwen/Llama single-agent baselines where available.

## 4. Line 5 Depth

- [x] Run IPC T3 R10-D2 multi-agent. First attempt failed post-run because
      telemetry only exercised Qwen; final run passed after role-based routing
      and `SIMILARITY_THRESHOLD=0`.
- [x] Run IPC T3 R20-D2 multi-agent.
- [x] Run IPC T3 R40-D2 multi-agent.
- [x] Run IPC T3 R80-D2 multi-agent.
- [x] Summarize multi-agent R10/R20/R40/R80 by MAE, score, parse errors, and
      tokens in `RESULTS_ANALYSIS.md`.
- [ ] Compare multi-agent R40 against single-agent R80 by MAE and tokens/cost
      once the single-agent baseline table is selected.

## 5. S3 Noise/Signal

- [x] Run baseline-control. First attempt failed post-run; rerun passed with
      Qwen, Gemma, and Llama in telemetry.
- [x] Run signal-early.
- [x] Run signal-mid.
- [x] Run signal-late.
- [x] Run counter-signal-mid.
- [x] Run noise-near-mid.
- [x] Run noise-off-mid. First attempt failed post-run because Llama did not
      make telemetry calls; rerun passed with all three models.
- [x] Summarize delta MAE vs baseline and event firing validity in
      `RESULTS_ANALYSIS.md`.

## 6. Finalization

- [x] Write final IPC tri-model report: `RESULTS_ANALYSIS.md`.
- [ ] Validate no secrets in committed files.
- [ ] Validate no raw `runs/` artifacts are staged.
- [ ] Commit.
- [ ] Push if authorized.
