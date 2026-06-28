# IPC Tri-Model Lessons

Append lessons here while working.

## Existing Lessons To Respect

- Qwen can fail when strict `response_format={"type":"json_object"}` is forced.
  Keep Qwen generation paths on the repair/normalization pipeline.
- Backend hot-swapping model env is unreliable. Restart backend between model
  groups when not using per-agent model routing.
- Graphiti extraction is more stable with Gemma than with Llama/Qwen for this
  repo's hosted setup.
- Do not call a row multi-agent unless `model_routing_audit.jsonl` proves three
  models participated in the same simulation.
- Do not run full matrices before the smoke gate passes.
- Use `origin/backtesting-feature-augmented` as the source for routing/telemetry
  pieces, but never copy its `run_reddit_simulation.py` wholesale over this
  branch because that would weaken the S3 scheduled-event implementation.
- Do not set hosted model prices to `0.0` just to silence telemetry warnings.
  Leave unknown hosted prices out of `configs/model_prices.yaml` until verified;
  telemetry will mark `cost_unknown_model` while still recording tokens.
- Keep the paid smoke as its own row (`ipc_trimodel_smoke_T0_R2_D2`) instead of
  running a real matrix row with fewer rounds. Otherwise the output path and
  row id lie about the actual depth.
- The headless runner must persist the fetched report markdown. Calling
  `/api/report/<id>` is not enough for objective evaluation unless
  `mirofish_report_raw.md` is written.
- Capture routing and telemetry from `backend/uploads/simulations/<id>/` into
  `simulation_artifacts/`; those files are the proof that one simulation used
  all three models.
- Experimental memory writes outside `backend/uploads`, under
  `backend/data/simulations/<id>`. Headless artifact capture must summarize
  that directory separately or the smoke can pass without memory evidence.
- Every paid row attempt must append `RUN_LEDGER.csv` even when the run itself
  finishes but evaluation or compact artifact copy fails afterward.
- Remove a row's raw output directory before rerun execution; deterministic
  output paths plus optional artifact copying can otherwise let stale evidence
  pass validation.
- For S3, scheduled-event evidence is valid only when the JSONL line count
  matches `expected_events`. The baseline-control row expects zero and should
  not require the file.
- Report generation and experimental-memory evidence can fail late if the
  backend runtime lacks `chromadb`. Before the next paid smoke, verify from
  `backend/` with `uv run --frozen --python 3.11 python -c "import chromadb"`
  and restart the backend after fixing the dependency.
- In `USE_EXPERIMENTAL_MEMORY=true`, the memory provider and graph backend are
  separate responsibilities. `ExperimentalMemoryService` has no `.backend`,
  but Report Agent still calls graph tools such as `get_graph_statistics`.
  Keep `ZepToolsService.backend` populated from `get_graph_backend(...)` even
  when `self.exp_memory` is active.
- Experimental memory can also fail late when `core_memory.json` is created
  from generated profiles: `_load_core_memory()` must not call
  `save_core_memory()` before `self.core_memory` exists. Keep the regression
  covered by `backend/tests/test_spike_integration.py`.
- A smoke that exits 0 is not necessarily valid. `ipc_trimodel_smoke_T0_R2_D2`
  completed with report/eval artifacts but had zero completed rounds, zero
  actions, and zero LLM telemetry because the first simulated hours had no
  active agents. Keep the runner gate checking both `run_manifest.json` and
  `llm_telemetry_summary.json`, and use a deeper smoke such as R12 before the
  full matrix.
- IPC generated agent IDs are not stable enough for tri-model routing. A Line5
  R10 run routed Gemma/Llama in `model_routing_audit.jsonl` by fixed IDs, but
  the agents that actually spoke in the first 10 rounds were different IDs, so
  `llm_telemetry_summary.json` collapsed to Qwen only and the row correctly
  failed post-run validation. Prefer stable `by_role` coverage for IPC:
  `Organization -> Gemma`, `MediaOutlet`/`FiscalConsultancy -> Llama`, and
  default `Qwen`. Keep the telemetry gate requiring all three models.
- A graph task can complete cleanly and the next failure can still be a
  preparation hang. Temporal T3 reached 73 graph nodes and 51 edges, then
  stalled at profile generation `0/37` with no `reddit_profiles.json`. Keep
  hosted profile generation bounded with `LLM_REQUEST_TIMEOUT`,
  `OASIS_PROFILE_MAX_TOKENS`, `OASIS_PROFILE_MAX_ATTEMPTS`, and
  `MIROFISH_PREPARE_STALE_AFTER_SECONDS`; otherwise `as_completed()` plus
  OpenAI-compatible calls can burn the full poll timeout without a useful
  failure.
- There are two dedup paths. `GRAPHITI_BYPASS_NODE_DEDUP=true` only bypasses
  node dedup inside Graphiti graph construction. Simulation preparation has a
  separate semantic agent dedup controlled by `SIMILARITY_THRESHOLD`; for IPC
  benchmark rows keep `SIMILARITY_THRESHOLD=0`, matching the teammate warning
  that the dedup system is half-finished and should be bypassed.
- Effective tri-model participation must be checked in telemetry, not only in
  the routing audit. S3 `noise-off-mid` produced an objective eval on the first
  attempt, but Llama never made an LLM call, so the runner correctly marked it
  `failed_post_run`. The canonical rerun is the one where
  `llm_telemetry_summary.json.models` includes Qwen, Gemma, and Llama.
- Negative research results are still deliverable results. The IPC S3 matrix
  did not show strong robustness to noise/counter-signals; document that
  directly instead of hiding it behind implementation success.
