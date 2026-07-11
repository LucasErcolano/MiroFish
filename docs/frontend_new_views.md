# Frontend Observability Surfaces

This document describes the Issue #32 frontend surfaces after the integrated UI pass.

## Primary UX

Observability is embedded in the workflow instead of being a separate debug-first screen.

- Preparation shows `Preparation Trace` with Deep Research, Deduplication, Wiki, Agent Profiles and Simulation Config.
- Simulation shows `Runtime Observability` with LLM calls, errors, tokens, latency, cost status, model details and routing details.
- Report shows `Evidence Command Center` with Deep Research trace, Wiki evidence, Runtime/Telemetry and Fusion.
- Wiki and Telemetry open as slide-over drawers so users do not leave or reset the active workflow.

## Debug Routes

The direct routes still exist for advanced inspection and sharing links:

- `/simulation/:simulationId/wiki`
- `/simulation/:simulationId/telemetry`

These routes are not the primary in-flow access pattern.

## Backend Endpoints

The frontend reads existing read-only artifact endpoints:

- `GET /api/simulation/:id/artifacts`
- `GET /api/simulation/:id/wiki`
- `GET /api/simulation/:id/wiki/page?path=...`
- `GET /api/simulation/:id/telemetry`
- `GET /api/simulation/:id/routing-audit`
- `GET /api/simulation/:id/deep-search`
- `GET /api/simulation/:id/fusion-verdicts`
- `GET /api/simulation/:id/fusion-verdict?path=...`

No backend simulation logic is changed by these surfaces.

## Interpretation

- Deep Research shows whether context came from Tavily, LLM fallback, or a failed trace, plus a few readable findings.
- Routing details show the post-run source of truth: which provider/model each agent actually used.
- Telemetry cost can be estimated, partial, not estimated, or unavailable depending on model pricing and provider usage data.
- Fusion is a final judge pass over the completed report and Wiki evidence. The current stable judge model is `openai/gpt-4o-mini`.

## Smoke Target

Use `sim_e1b184a97a57` for a full artifact smoke:

- Wiki: available.
- Telemetry: available.
- Routing audit: available.
- Deep Search: available.
- Fusion: completed.
