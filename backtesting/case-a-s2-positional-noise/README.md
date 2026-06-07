# Case A S2 Positional Noise

This folder is the working packet for S2 Issue #19.

Status as of 2026-06-07:

- S1 Case A files are available in `backtesting/case-a/`.
- Hosted-model routing support is prepared in `configs/model_map_s2.yaml`.
- Scheduled Reddit injection is implemented in `backend/scripts/run_reddit_simulation.py`.
- Qwen JSON handling is hardened by avoiding forced `response_format={"type":"json_object"}`.
- OpenRouter chat and embeddings were validated for the matrix path.
- A prepared Reddit simulation was reused for the 7-condition matrix: `sim_4bab3075239e`.
- The 7 technical 40-round condition runs are available under `runs/s2_issue19/`.
- Deterministic per-condition summaries are generated in `evaluation/condition_summaries/`.

## Conditions

Run one baseline and six injection conditions:

- `baseline`
- `signal-early`
- `signal-mid`
- `signal-late`
- `noise-early`
- `noise-mid`
- `noise-late`

The goal is to measure whether final narrative/output changes depending on whether useful signal or distracting noise is introduced early, mid, or late in the simulated discussion.

## Required Technical Work

The required scheduled-injection implementation is now present.

`backend/scripts/run_reddit_simulation.py` processes `event_config.initial_posts` before the loop and `event_config.scheduled_events` during each round.

Implemented behavior:

- reads `event_config.scheduled_events`;
- resolves each event by `round`, `round_index`, or `round_pct`;
- before normal round actions, calls `env.step()` with `ManualAction(ActionType.CREATE_POST, ...)`;
- writes `scheduled_events_fired.jsonl`;
- never fires the same event twice;
- keeps `scheduled_events: []` behavior unchanged.

## Files

- `case_card.md`: case definition and cutoff.
- `question.md`: target prediction prompt.
- `rubric.md`: scoring rubric.
- `signal_doc.md`: injected relevant signal.
- `noise_doc.md`: injected irrelevant but plausible noise.
- `injection_plan.yaml`: condition-to-event schedule.
- `model_policy.md`: model/provider policy for S2.
- `complexity_gate.md`: why the S1 case needs S2 hardening.
- `configs/*.yaml`: one config stub per condition.
- `evaluation/condition_summaries/*.md`: deterministic summaries extracted from run SQLite artifacts.
- `evaluation/condition_summary_metrics.csv`: compact condition metrics.
- `evaluation/condition_summary_metrics.json`: machine-readable condition metrics.
- `evaluation/summarize_condition_artifacts.py`: reproducible artifact summarizer.
- `evaluation/score_narratives.py`: hosted evaluator scoring script.
- `evaluation/evaluator_prompt.md`: prompt for optional narrative scoring.
- `evaluation/narrative_scores.csv`: final narrative scoring table.
- `evaluation/narrative_scores.md`: readable narrative scoring report.
- `evaluation/narrative_score_raw/*.json`: normalized per-condition evaluator outputs.
- `evaluation/technical_report.md`: concise technical report for the current matrix.
- `evaluation/final_issue_report.md`: final issue-level interpretation.

## Rebuild Evaluation Summaries

From the repo root:

```powershell
python backtesting/case-a-s2-positional-noise/evaluation/summarize_condition_artifacts.py
```

This reads the copied artifacts in `runs/s2_issue19/` and rewrites:

- `evaluation/condition_summaries/*.md`
- `evaluation/condition_summary_metrics.csv`
- `evaluation/condition_summary_metrics.json`

## Narrative Scoring

The final narrative output per condition is generated. To rebuild it with model calls, run:

```powershell
$env:OPENROUTER_API_KEY=[Environment]::GetEnvironmentVariable("OPENROUTER_API_KEY","User")
$env:LLM_API_KEY=$env:OPENROUTER_API_KEY
$env:OPENAI_API_KEY=$env:LLM_API_KEY
$env:LLM_BASE_URL="https://openrouter.ai/api/v1"
$env:LLM_MODEL_NAME="qwen/qwen3-8b"
cd backend
uv run --frozen python ../backtesting/case-a-s2-positional-noise/evaluation/score_narratives.py
```

To rebuild from existing raw model outputs without spending more model calls:

```powershell
cd backend
uv run --frozen python ../backtesting/case-a-s2-positional-noise/evaluation/score_narratives.py --from-raw
```

## Remaining Work

Only optional polish remains:

- verify and use ReportAgent per condition if the issue explicitly requires ReportAgent output;
- rerun the matrix with a second model/provider for robustness;
- commit and open PR.
