# ReportAgent Artifact-Only Evaluation

Date: 2026-06-07

This folder contains the Issue 19 V2 ReportAgent follow-up.

The goal is not to replace the deterministic summaries or evaluator scores. The goal is to verify that ReportAgent can be run per condition without reading shared graph/tool state.

## Method

Each run uses `ReportAgent` with:

- `artifact_only=True`
- one condition-specific `artifact_context`
- no Zep/graph tools
- unique `report_id`
- one model/provider at a time

The artifact context is built from:

- the condition summary markdown;
- the condition metrics CSV row;
- the narrative score CSV row.

No simulation is rerun. No SQLite database is committed here.

## Models

| model_slug | provider | model |
|---|---|---|
| qwen | OpenRouter | `qwen/qwen3-8b` |
| gemma | DeepInfra | `google/gemma-3-27b-it` |
| llama | DeepInfra | `meta-llama/Llama-3.3-70B-Instruct-Turbo` |

## Result

All 18 ReportAgent artifact-only reports completed:

```text
3 models x 6 V2 conditions = 18 reports
```

See `report_agent_manifest.csv` for the full status table.

Each condition folder contains:

- `full_report.md`
- `outline.json`
- `meta.json`
- `report_agent_run.json`

## Reproduce

Run from `backend/` so the backend `uv` environment is used:

```powershell
uv run --frozen python ../backtesting/case-a-s2-positional-noise-v2/evaluation_report_agent/run_report_agent_from_artifacts.py --models qwen,gemma,llama --force
```

The runner reads `OPENROUTER_API_KEY` and `DEEPINFRA_API_KEY` from process env or Windows User env.

To refresh only the manifest from existing folders without new model calls:

```powershell
uv run --frozen python ../backtesting/case-a-s2-positional-noise-v2/evaluation_report_agent/run_report_agent_from_artifacts.py --models qwen,gemma,llama
```

## Evidence Boundary

Committed evidence:

- `report_agent_manifest.csv`
- per-condition `full_report.md`
- per-condition `report_agent_run.json`
- per-condition compact report files

Local reproducibility evidence remains separate:

- `runs/s2_issue19_v2/*`
- `runs/s2_issue19_deepinfra/*`

Those local run artifacts are not committed because they contain copied SQLite databases and logs.
