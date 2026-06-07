# MiroFish Headless Runner Guide for AI Agents

This file is for AI agents and automation tools that need to run MiroFish without using the browser UI.

The headless runner is not a direct LLM shortcut. It replays the same backend API flow used by the frontend, so a successful run is still a real MiroFish/OASIS system run.

## What to use

- Runner: `tools/mirofish_headless.py`
- Frontend parity guard: `tools/mirofish_frontend_parity_check.py`
- Main artifact directory: `runs/headless/<run-id>/`

Do not commit `runs/`; it contains per-case artifacts and generated reports.

## Required backend state

The runner talks to the Flask backend, normally at `http://localhost:5001`.

You can either:

1. start the backend yourself, then run the runner; or
2. pass `--start-backend` and let the runner launch `npm run backend`.

For Graphiti-backed runs, Neo4j must be reachable before the backend starts. Example local container:

```bash
docker run -d --name mirofish-neo4j-headless \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/mirofishpassword \
  neo4j:5
```

Wait until Neo4j accepts Cypher:

```bash
docker exec mirofish-neo4j-headless \
  cypher-shell -u neo4j -p mirofishpassword 'RETURN 1;'
```

## Required environment variables

Never write real API keys into files, command logs, manifests, or docs. Export them in the shell that starts the backend/runner.

Minimum Gemini/OpenAI-compatible setup:

```bash
export MIROFISH_GEMINI_API_KEYS='<primary-key>[,<optional-backup-key>]'
export LLM_API_KEY='<primary-key>'
export OPENAI_API_KEY='<primary-key>'
export LLM_BASE_URL='https://generativelanguage.googleapis.com/v1beta/openai/'
export LLM_MODEL_NAME='gemini-2.5-flash-lite'
```

Graphiti setup used by successful headless runs:

```bash
export GRAPH_BACKEND='graphiti'
export GRAPHITI_URI='bolt://localhost:7687'
export GRAPHITI_USER='neo4j'
export GRAPHITI_PASSWORD='mirofishpassword'
export GRAPHITI_DATABASE='neo4j'

export GRAPHITI_LLM_API_KEY="$LLM_API_KEY"
export GRAPHITI_LLM_BASE_URL='https://generativelanguage.googleapis.com/v1beta/openai/'
export GRAPHITI_LLM_MODEL='gemini-2.5-flash-lite'
export GRAPHITI_LLM_CLIENT_MODE='generic'

export GRAPHITI_EMBEDDER_API_KEY="$LLM_API_KEY"
export GRAPHITI_EMBEDDER_BASE_URL='https://generativelanguage.googleapis.com/v1beta/openai/'
export GRAPHITI_EMBEDDER_MODEL='gemini-embedding-001'
export GRAPHITI_EMBEDDER_DIM='3072'

export GRAPHITI_RERANKER_API_KEY="$LLM_API_KEY"
export GRAPHITI_RERANKER_BASE_URL='https://generativelanguage.googleapis.com/v1beta/openai/'
export GRAPHITI_RERANKER_MODEL='gemini-2.5-flash-lite'
```

If using `uv` and an already-prepared virtualenv, `UV_NO_SYNC=1` can prevent `uv` from removing locally installed optional packages while debugging:

```bash
export UV_NO_SYNC=1
```

## Backend readiness check

Before spending model credits, verify the backend in the same shell/environment:

```bash
npm run backend
```

In another terminal:

```bash
python - <<'PY'
from urllib.request import urlopen
r = urlopen('http://localhost:5001/api/graph/project/list', timeout=5)
print(r.status)
print(r.read().decode()[:500])
PY
```

Expected: HTTP 200 with JSON.

## Basic runner command

Use one or more seed files and the same natural-language requirement that the frontend would receive.

```bash
python tools/mirofish_headless.py \
  --base-url http://localhost:5001 \
  --file /absolute/path/to/seed_bundle.md \
  --requirement "Predict the requested scenario using only the supplied seed material." \
  --project-name "Headless Benchmark" \
  --platform parallel \
  --max-rounds 1 \
  --output-dir runs/headless/my-run-id
```

For multiple input files, repeat `--file`:

```bash
python tools/mirofish_headless.py \
  --file input-a.md \
  --file input-b.pdf \
  --requirement "..." \
  --max-rounds 1
```

To skip downstream report generation and only validate the simulation:

```bash
python tools/mirofish_headless.py \
  --file input.md \
  --requirement "..." \
  --max-rounds 1 \
  --no-report
```

To let the runner start the backend:

```bash
python tools/mirofish_headless.py \
  --start-backend \
  --file input.md \
  --requirement "..." \
  --max-rounds 1
```

`--start-backend` still requires Neo4j/Graphiti and model environment variables to be set first.

## Important CLI flags

- `--base-url`: backend URL. Default: `http://localhost:5001`.
- `--file`: seed file to upload. Repeatable. Required.
- `--requirement`: simulation requirement/prompt. Required.
- `--project-name`: name shown in MiroFish project state.
- `--max-rounds`: requested MiroFish/OASIS rounds/epochs. Use `1` for smoke tests.
- `--platform`: `parallel`, `twitter`, or `reddit`. Default: `parallel`.
- `--output-dir`: artifact directory. Default: timestamp under `runs/headless/`.
- `--poll-timeout`: timeout in seconds for graph/simulation/report polling.
- `--no-report`: skip Report Agent after the simulation completes.
- `--no-graph-memory-update`: pass `enable_graph_memory_update=false` to simulation start.
- `--no-force`: do not force restart if a simulation already exists.
- `--accept-language`: backend locale header. Default: `zh`.

## What the runner does

The runner mirrors the frontend/backend sequence:

1. `POST /api/graph/ontology/generate` with seed file(s) and requirement.
2. `POST /api/graph/build`.
3. Poll `GET /api/graph/task/{task_id}`.
4. Read `GET /api/graph/project/{project_id}` and `GET /api/graph/data/{graph_id}`.
5. `POST /api/simulation/create`.
6. `POST /api/simulation/prepare`.
7. Poll `POST /api/simulation/prepare/status`.
8. `POST /api/simulation/start` with `platform`, `max_rounds`, `force`, and graph-memory flag.
9. Poll `GET /api/simulation/{simulation_id}/run-status`.
10. Capture simulation detail endpoints.
11. Optionally `POST /api/report/generate`, poll `POST /api/report/generate/status`, then fetch `GET /api/report/{report_id}`.

Known parity warning: the frontend wrapper currently declares report status as GET while the backend route is POST. The runner uses backend POST so the headless run is executable.

## Artifacts produced

Typical files in `--output-dir`:

- `run_config.json`: sanitized run configuration and input hashes.
- `request_trace.json`: sanitized request/response trace for every API call.
- `run_manifest.json`: final status, IDs, epoch accounting, and provenance.
- `verdict_raw.json`: written for blocked runs.
- `mirofish_report_raw.md`: placeholder for blocked runs.
- `backend_env_sanitized.json`: only when `--start-backend` is used.
- `run_hashes.json`: hashes for files in the run directory.

If the simulation completes but Report Agent fails, do not say the MiroFish run failed before checking `run_manifest.json` and the simulation status. Count completed MiroFish/OASIS epochs separately from downstream report generation.

## Interpreting success vs blocked

A successful real run has:

- `flow_provenance: frontend_replay_backend_api`
- `real_mirofish_flow_invoked: true`
- `is_real_mirofish_system: true`
- `num_rounds_or_epochs > 0`
- backend `runner_status: completed`

A blocked run has:

- `status: BLOCKED`
- `is_model_output: false`
- `num_rounds_or_epochs: 0`
- exact blocker in `reason`

Do not replace a blocked real-system run with a direct LLM call unless the user explicitly asks for an adapted/direct-LLM fallback.

## Parity check

Run this after changing frontend API wrappers or the headless runner:

```bash
python tools/mirofish_frontend_parity_check.py
```

Expected output:

```text
OK
Warning: frontend/src/api/report.js declares getReportStatus as GET, but backend route is POST; runner uses backend POST to avoid a 405.
```

Use JSON output for CI or agents:

```bash
python tools/mirofish_frontend_parity_check.py --json
```

## Tests

From repository root:

```bash
python -m py_compile tools/mirofish_headless.py tools/mirofish_frontend_parity_check.py tests/test_mirofish_headless.py
python -m unittest tests.test_mirofish_headless -v
```

For backend Report Agent resilience tests, run inside the backend environment:

```bash
cd backend
UV_NO_SYNC=1 uv run python ../tests/test_report_agent_resilience.py -v
```

## Cleanup after a run

Stop local services when done:

```bash
# backend if manually started: Ctrl-C in the backend terminal
# or locate and stop it carefully
ss -ltnp | grep ':5001\b' || true

docker stop mirofish-neo4j-headless
```

Before committing, verify that case artifacts and secrets are not staged:

```bash
git status --short
git diff --cached --name-only
```

Do not stage `runs/`, generated reports, uploaded input bundles, or API keys.
