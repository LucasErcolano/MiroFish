# Upstream PR Candidates Draft

This planning draft is superseded by `docs/upstream_pr_candidates.md`. All
candidates below are integrated on `codex/stable-fork-cleanup`; use the final
document for current files, usage, dependencies, and upstream review notes.

## Candidate 1: Simulation Observability Dock

- Source branch: `origin/feat/ui-observability-dock`
- Status: already in base branch.
- Problem: simulation runs generate artifacts and telemetry that are hard to
  inspect from the UI.
- Change: add observability endpoints, frontend dock, telemetry views, wiki and
  report artifact navigation.
- Files to review: backend simulation API/services, frontend observability
  components/views, observability tests, `docs/frontend_observability_issue_32.md`.
- Upstream concerns: UI polish, endpoint stability, artifact schema stability.

## Candidate 2: Multi-Model Routing And LLM Telemetry

- Source branch: `origin/backtesting-feature-augmented`
- Status: integrated selectively.
- Problem: single-model simulations cannot compare heterogeneous providers or
  audit which model produced each agent action.
- Change: per-agent/role model map, model routing audit, telemetry JSONL/CSV,
  provider cost metadata.
- Upstream concerns: provider abstraction, secret hygiene, tests for backwards
  compatibility.

## Candidate 3: Wiki-Backed Report Memory

- Source branch: `origin/backtesting-feature-augmented`
- Status: integrated selectively.
- Problem: ReportAgent needs compact, auditable context from simulation memory
  and evidence without replacing the existing graph/memory stack.
- Change: local wiki store/compiler, report prompt integration, graceful
  fallback when wiki context is missing.
- Upstream concerns: prompt size, stale memory handling, optional behavior.

## Candidate 4: Scheduled Injection / Backtesting Harness

- Source branch: `origin/backtesting-feature-augmented`
- Status: integrated selectively.
- Problem: static input packages do not test whether simulations react to
  signals/noise injected during rounds.
- Change: scheduled events, temporal packages, condition matrices, compact
  evaluation summaries.
- Upstream concerns: runner API design, deterministic examples, artifact size.

## Candidate 5: Entropy / Linea 6 Analysis

- Source branch: `origin/feat/issue-28-linea6-entropia`
- Status: integrated surgically.
- Problem: agreement rate alone does not measure useful variation or collapse
  across multi-model predictions.
- Change: entropy metrics, checkpoint interviews, persona/run bundle analysis,
  multi-provider comparison scripts.
- Upstream concerns: dependency surface, runtime cost, keeping research code
  isolated under `backend/app/research/`.

## Candidate 6: Stable Fork Runtime And Smoke Harness

- Source branch: cleanup branch.
- Status: implemented and validated.
- Problem: the fork needs reproducible install/run/test commands for external
  users and evaluators.
- Change: README quick start, `.env.example`, Docker/Compose path, `make`
  targets or equivalents, minimal example, smoke test.
- Upstream concerns: avoid overfitting to local Windows paths, keep API-key
  usage optional for offline smoke.
