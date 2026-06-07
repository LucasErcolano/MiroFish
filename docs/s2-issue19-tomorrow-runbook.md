# S2 Issue 19 Runbook

Use this to resume the S2 Issue 19 work or rerun the matrix with a fresh hosted token.

## Current State

Ready:

- branch: `codex/s2-issue19-baseline`
- S2 packet: `backtesting/case-a-s2-positional-noise/`
- model map: `configs/model_map_s2.yaml`
- scheduled Reddit injection implemented in `backend/scripts/run_reddit_simulation.py`
- Qwen JSON hardening implemented for profile/config generation
- Graphiti/Neo4j attribute sanitization implemented
- 7-condition Reddit matrix completed with hosted OpenRouter path
- technical artifacts and summaries generated

Useful prepared simulation:

- `simulation_id=sim_4bab3075239e`
- artifact root: `runs/s2_issue19/`

## API Setup

In PowerShell:

```powershell
Get-Content scripts/set-s2-hosted-env.example.ps1
```

Then paste the same commands manually with real tokens. Do not save tokens.

For OpenRouter Qwen:

```powershell
$env:LLM_BASE_URL="https://openrouter.ai/api/v1"
$env:LLM_MODEL_NAME="qwen/qwen3-8b"
$env:LLM_API_KEY="PASTE_OPENROUTER_API_KEY"
$env:OPENAI_API_KEY=$env:LLM_API_KEY

$env:GRAPHITI_EMBEDDER_BASE_URL=$env:LLM_BASE_URL
$env:GRAPHITI_EMBEDDER_API_KEY=$env:LLM_API_KEY
$env:GRAPHITI_EMBEDDER_MODEL="qwen/qwen3-embedding-8b"
$env:GRAPHITI_EMBEDDER_DIM="4096"
```

## First Smoke

Before running MiroFish, verify the provider with one tiny request through `LLMClient`:

```powershell
cd backend
uv run --frozen python - <<'PY'
from app.utils.llm_client import LLMClient
print(LLMClient().chat("Reply with OK only.", max_tokens=8))
PY
```

If that fails, fix provider/token/base URL before touching simulation code.

## Already Implemented

Scheduled injection is implemented in:

```text
backend/scripts/run_reddit_simulation.py
```

Implemented behavior:

- load `event_config.scheduled_events`;
- support `round`, `round_index`, and `round_pct`;
- resolve `round_pct` against `total_rounds`;
- fire a `ManualAction(ActionType.CREATE_POST, ...)` exactly once;
- write `scheduled_events_fired.jsonl` in the simulation directory;
- keep `scheduled_events: []` identical to current behavior.

Focused tests already cover round resolution, one-shot event firing, model routing, and Qwen JSON routing.

## Run Matrix

Use these conditions:

```text
baseline
signal-early
signal-mid
signal-late
noise-early
noise-mid
noise-late
```

Fast path using the already prepared simulation:

```powershell
cd backend
uv run --frozen python ../tools/mirofish_headless.py `
  --base-url http://127.0.0.1:5001 `
  --existing-simulation-id sim_4bab3075239e `
  --platform reddit `
  --max-rounds 40 `
  --accept-language es `
  --output-dir ../runs/s2_issue19/<run-dir> `
  --poll-timeout 1800 `
  --no-report `
  --no-graph-memory-update `
  --injection-plan ../backtesting/case-a-s2-positional-noise/injection_plan.yaml `
  --condition <condition> `
  --no-wait-after-run
```

Replace `<condition>` with one of the seven condition names and `<run-dir>` with the matching artifact directory.

## Evaluation Artifacts

Already filled:

- `backtesting/case-a-s2-positional-noise/evaluation/impact_table.md`
- `backtesting/case-a-s2-positional-noise/evaluation/impact_table.csv`
- `backtesting/case-a-s2-positional-noise/evaluation/condition_summaries/*.md`
- `backtesting/case-a-s2-positional-noise/evaluation/condition_summary_metrics.csv`
- `backtesting/case-a-s2-positional-noise/evaluation/condition_summary_metrics.json`
- `backtesting/case-a-s2-positional-noise/evaluation/evaluator_prompt.md`
- `backtesting/case-a-s2-positional-noise/evaluation/narrative_scores.csv`
- `backtesting/case-a-s2-positional-noise/evaluation/narrative_scores.md`
- `backtesting/case-a-s2-positional-noise/evaluation/narrative_score_raw/*.json`
- `backtesting/case-a-s2-positional-noise/evaluation/technical_report.md`
- `backtesting/case-a-s2-positional-noise/evaluation/final_issue_report.md`

Regenerate deterministic summaries:

```powershell
python backtesting/case-a-s2-positional-noise/evaluation/summarize_condition_artifacts.py
```

## Narrative Scoring

The 40-round matrix was run with `--no-report`, so ReportAgent narrative outputs were intentionally not generated. Instead, narrative scoring was generated from deterministic condition summaries using `score_narratives.py`.

Rebuild with hosted evaluator calls:

```powershell
cd backend
uv run --frozen python ../backtesting/case-a-s2-positional-noise/evaluation/score_narratives.py
```

Rebuild without spending model calls:

```powershell
cd backend
uv run --frozen python ../backtesting/case-a-s2-positional-noise/evaluation/score_narratives.py --from-raw
```

Optional remaining work:

- verify ReportAgent reads condition-specific SQLite artifacts before using it per condition;
- rerun matrix with another provider/model for robustness;
- commit/open PR.

## Stop Criteria

Stop and report instead of burning credits if any of these happen:

- provider smoke fails;
- first hosted prepare step returns malformed JSON repeatedly;
- scheduled event artifact is missing after a condition run;
- baseline and all injected runs produce no actions.
