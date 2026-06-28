# Handoff Prompt

Use this prompt for a fresh Codex thread if final validation or follow-up work
is needed.

```text
The IPC 2025 tri-model multi-agent benchmark in MiroFish is complete. Continue
only with validation, documentation consistency, commit/push, or an explicit
follow-up from the user.

Work in:
C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish

Use branch:
codex/ipc-trimodel-multiagent

First read:
AGENTS.md
backtesting/ipc-trimodel-multiagent/AGENT_STATE.md
backtesting/ipc-trimodel-multiagent/TODO.md
backtesting/ipc-trimodel-multiagent/RUNBOOK.md
backtesting/ipc-trimodel-multiagent/DECISIONS.md
backtesting/ipc-trimodel-multiagent/PRE_SMOKE_CHECKLIST.md
backtesting/ipc-trimodel-multiagent/RUN_LEDGER.csv
backtesting/ipc-trimodel-multiagent/RESULTS_ANALYSIS.md
docs/superpowers/plans/2026-06-27-ipc-trimodel-multiagent.md

Goal:
Validate and deliver the completed IPC tri-model multi-agent experiments.
Temporal T0-T3, Line 5 R10/R20/R40/R80, and S3 seven conditions have canonical
compact evidence under backtesting/ipc-trimodel-multiagent/evaluation/.
RESULTS_ANALYSIS.md is the canonical summary.

Current prepared state:
backend/app/services/model_router.py, backend/app/services/llm_telemetry.py,
and configs/model_prices.yaml were selectively imported from
origin/backtesting-feature-augmented. Provider handling for openrouter and
deepinfra is fixed. run_reddit_simulation.py accepts --model-map and writes
model_routing_audit.jsonl and llm_telemetry.jsonl while preserving scheduled
events. The headless/API/SimulationRunner path propagates model_map_path.
Headless also captures experimental_memory_evidence.json from backend/data.

Do not rerun paid simulations unless the user asks. If a rerun is necessary,
use run_ipc_trimodel_matrix.py with --rows or --conditions to target only the
failed row. Do not commit raw runs, backend logs, uploads, caches, or secrets.
```
