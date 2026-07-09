# Upstream PR Candidates

This fork is intentionally organized as a stable integration branch plus a set
of feature candidates that could be proposed independently to upstream
MiroFish.

## 1. Simulation Observability Dock

Problem: simulation artifacts, telemetry, reports, and wiki memory are hard to
inspect from the browser UI.

Change: add backend artifact endpoints and frontend views for run artifacts,
telemetry, report output, and wiki/memory navigation.

Main files:

- `backend/app/api/simulation.py`
- `backend/app/services/simulation_manager.py`
- `backend/app/services/capture_artifacts.py`
- `frontend/src/`
- `docs/frontend_observability_issue_32.md`

Usage: run `npm run dev`, open the frontend, and inspect a prepared/completed
simulation through the observability UI.

Dependencies: existing Flask backend and Vue frontend.

Upstream review: verify endpoint schema stability, UI naming, and behavior when
artifacts are missing.

## 2. Multi-Model Routing And Telemetry

Problem: single-provider simulations cannot audit which model produced each
agent action or compare heterogeneous providers.

Change: add YAML model maps, per-agent/per-role routing, provider defaults for
OpenRouter and DeepInfra, route audits, and per-call telemetry summaries.

Main files:

- `backend/app/services/model_router.py`
- `backend/app/services/llm_telemetry.py`
- `backend/scripts/run_reddit_simulation.py`
- `backend/app/services/simulation_runner.py`
- `configs/model_map_example.yaml`
- `configs/model_map_s2.yaml`
- `configs/model_prices.yaml`

Usage: pass `--model-map <path>` to the Reddit runner or call
`SimulationRunner.start_simulation(..., platform="reddit", model_map_path=...)`.

Dependencies: provider API keys in environment variables such as
`OPENROUTER_API_KEY` and `DEEPINFRA_API_KEY`.

Upstream review: decide public schema for model maps and whether provider
defaults should live in config, code, or docs.

## 3. Scheduled Injection Backtesting

Problem: preassembled input bundles do not test whether the simulation reacts to
signals/noise injected during specific rounds.

Change: add `event_config.scheduled_events` support in the Reddit runner,
headless plan application, compact S2 positional-noise artifacts, and focused
tests.

Main files:

- `backend/scripts/run_reddit_simulation.py`
- `tools/mirofish_headless.py`
- `backtesting/case-a-s2-positional-noise/`
- `backtesting/case-a-s2-positional-noise-v2/`
- `backend/tests/test_s2_scheduled_injection.py`

Usage: apply an injection plan with
`apply_injection_plan_to_simulation_config(...)`, then run the Reddit
simulation. Fired events are audited in `scheduled_events_fired.jsonl`.

Dependencies: OASIS/CAMEL runtime for real simulations.

Upstream review: decide whether scheduled events belong in the public simulation
config schema or in a separate experiment harness.

## 4. Wiki-Backed Report Memory

Problem: report generation needs compact, inspectable memory without dumping
raw traces into prompts.

Change: add a local wiki compiler/store and experimental memory provider with
ChromaDB when embeddings are configured and JSON fallback for offline tests.

Main files:

- `backend/app/services/wiki_memory/`
- `backend/app/services/experimental_memory.py`
- `backend/app/services/memory_factory.py`
- `backend/app/services/memory_provider.py`
- `tests/test_wiki_*.py`
- `backend/tests/test_experimental_memory.py`

Usage: enable experimental memory or compile wiki artifacts during/report after
a simulation; offline tests use JSON fallback and do not require embedding API
calls.

Dependencies: optional ChromaDB and embedding provider settings.

Upstream review: settle storage lifecycle, prompt-size budget, and stale-memory
handling.

## 5. S2/S3 Research Backtesting Packages

Problem: research findings need reproducible case data, matrices, and compact
result summaries without committing raw run directories.

Change: add curated backtesting packages for football, Bolivia, IPC, S3
cross-topic injections, IPC tri-model multi-agent, and final multi-model
summaries.

Main files:

- `backtesting/README.md`
- `backtesting/case-b-s2-bolivia-2025-runoff/`
- `backtesting/s3-cross-topic-injection/`
- `backtesting/ipc-trimodel-multiagent/`
- `backtesting/final-multimodel/`
- `backtesting/scripts/`

Usage: follow the runbooks in each backtesting folder. Committed artifacts are
summaries, matrices, ledgers, and compact JSON/CSV/MD evidence.

Dependencies: paid model/provider keys for full reproduction.

Upstream review: decide which research artifacts belong upstream versus an
external benchmark repository.

## 6. Entropy / Linea 6 Analysis

Problem: agreement rate does not capture response diversity, collapse, or useful
variation across providers and checkpoints.

Change: add entropy metrics, checkpoint/persona analysis, simulation DB
readers, run-bundle export, and Linea 6 comparison docs.

Main files:

- `backend/app/research/entropy/`
- `backend/app/research/dataset/run_bundle.py`
- `backend/scripts/entropy_*.py`
- `backend/scripts/export_run_bundle.py`
- `scripts/run_linea6_multiprovider_parallel.py`
- `docs/linea6_*.md`
- `tests/test_entropy_metrics.py`
- `tests/test_checkpoints_temporal.py`
- `tests/test_run_bundle.py`
- `tests/test_simulation_db.py`

Usage: export a run bundle, then run the entropy scripts against checkpoints,
personas, or generated responses.

Dependencies: standard Python test/runtime dependencies; provider calls only
for new data generation.

Upstream review: keep research utilities isolated under `backend/app/research`
and document cost controls for provider-based scripts.

## 7. Stable Fork Runtime And Smoke Harness

Problem: reviewers need a reproducible way to verify that the fork installs,
loads a minimal case, and writes expected outputs without private API keys.

Change: add `.env.example`, `Makefile`, root npm commands, a minimal example,
offline smoke/run-example scripts, and local-build Docker Compose.

Main files:

- `.env.example`
- `Makefile`
- `package.json`
- `Dockerfile`
- `docker-compose.yml`
- `examples/minimal_case/`
- `scripts/smoke_test.py`
- `scripts/run_example.py`

Usage:

```bash
cp .env.example .env
npm run setup:all
npm run smoke-test
npm run run-example
npm test
```

Dependencies: Node 18+, Python 3.11, uv, and Docker for Compose.

Upstream review: decide whether upstream wants the offline smoke harness or a
smaller CI-only version.
