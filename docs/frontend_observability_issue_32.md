# Frontend Observability Issue 32

This branch exposes PR #31 artifacts through read-only backend endpoints and frontend inspection screens.

## Backend endpoints

- `GET /api/simulation/<simulation_id>/artifacts`
- `GET /api/simulation/<simulation_id>/wiki`
- `GET /api/simulation/<simulation_id>/wiki/page?path=...`
- `GET /api/simulation/<simulation_id>/telemetry`
- `GET /api/simulation/<simulation_id>/routing-audit`
- `GET /api/simulation/<simulation_id>/fusion-verdicts`
- `GET /api/simulation/<simulation_id>/fusion-verdict?path=...`

Missing artifacts return empty usable payloads instead of `500`.
`wiki/page` and `fusion-verdict` reject path traversal.

## Frontend surfaces

- `/simulation/:simulationId/wiki`: browses wiki memory pages and renders Markdown.
- `/simulation/:simulationId/telemetry`: shows telemetry KPIs, lazy Chart.js charts and per-model table.
- `Step3Simulation`: shows routing audit rows after simulation artifacts exist.
- `Step4Report`: shows wiki stats, latest Fusion verdict, `marked` Markdown rendering and a collapsible Deep Search trace in console logs.

## Checkpoint

Validated backend artifacts API:

```bash
cd backend
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests/test_api_artifacts.py -v
```

Result: `6 passed`.

Validated traversal behavior with the dev server:

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  "http://localhost:5001/api/simulation/nonexistent/wiki/page?path=../../../../etc/passwd"
```

Result: `400`.

Validated frontend build:

```bash
cd frontend
npm run build
```

Result: build completed. Vite still reports the pre-existing large chunk warning.
