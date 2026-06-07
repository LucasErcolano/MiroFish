# Final Issue Report - S2 Issue 19

Date: 2026-06-07

## Scope

This report closes the S2 Issue 19 experiment for scheduled Reddit injection on the Copa America 2024 final case: Argentina vs Colombia.

The experiment tested whether injecting useful signal or plausible sports-news noise at different positions in a Reddit simulation changes the final narrative output.

## Implementation Status

Scheduled injection is implemented and verified in the Reddit simulation loop.

Supported event scheduling:

- `round`
- `round_index`
- `round_pct`

Implemented event behavior:

- `target_platform=reddit`
- `action=create_post`
- one-shot firing
- audit log in `scheduled_events_fired.jsonl`
- unchanged baseline behavior when no scheduled event exists

## Experimental Matrix

Prepared simulation:

- `sim_4bab3075239e`

Conditions:

| condition | injected_doc | fired_round | posts | comments | traces |
|---|---|---:|---:|---:|---:|
| baseline | none | - | 6 | 16 | 48 |
| signal-early | signal | 4 | 5 | 15 | 55 |
| signal-mid | signal | 20 | 5 | 18 | 47 |
| signal-late | signal | 36 | 7 | 17 | 53 |
| noise-early | noise | 4 | 9 | 15 | 47 |
| noise-mid | noise | 20 | 6 | 15 | 56 |
| noise-late | noise | 36 | 7 | 17 | 51 |

All six injection conditions fired exactly one scheduled event. Baseline fired zero scheduled events.

Round resolution over 40 rounds:

- early: `round_pct=0.10` -> round 4, index 3
- mid: `round_pct=0.50` -> round 20, index 19
- late: `round_pct=0.90` -> round 36, index 35

## Narrative Scores

The final narrative scoring used deterministic condition summaries plus a hosted evaluator model. It did not call ReportAgent because ReportAgent appears graph/tool-centric and has not been verified to isolate each copied SQLite condition artifact.

| condition | predicted_winner | confidence | used_injected_document | noise_contamination |
|---|---|---:|---|---|
| baseline | Unclear | 0.30 | false | none |
| signal-early | Argentina | 0.70 | true | none |
| signal-mid | Argentina | 0.70 | true | none |
| signal-late | Argentina | 0.70 | true | none |
| noise-early | Argentina | 0.65 | true | medium |
| noise-mid | Argentina | 0.65 | true | medium |
| noise-late | Argentina | 0.65 | true | medium |

## Interpretation

Baseline remained ambiguous. The simulated discussion balanced Argentina's tournament experience and defensive solidity against Colombia's form and James Rodriguez's influence.

Signal injection shifted the output toward Argentina in all positions. The exact timing did not change the final predicted winner, but it changed the narrative from `Unclear` to `Argentina` with higher confidence. The signal was strongest as an interpretive anchor rather than as a source of extra activity volume.

Noise injection introduced medium contamination in all positions. The final predicted winner still became Argentina, but the narrative picked up non-match distractions and additional media/fan-attention language. This means the noise did not flip the winner, but it did contaminate the rationale.

## Answer To The Issue

The scheduled-injection feature works and is measurable.

Observed effect:

- baseline: no stable winner;
- signal early/mid/late: stable Argentina prediction;
- noise early/mid/late: Argentina prediction with medium narrative contamination;
- timing affected discussion traces/counts, but not the winner selected by the evaluator in this matrix.

This is not an agreement-rate measurement. It measures output/narrative variation caused by injecting documents at different positions in the multi-agent discussion.

## Evidence Files

Committed evidence:

- `impact_table.md`
- `impact_table.csv`
- `condition_summary_metrics.csv`
- `condition_summary_metrics.json`
- `condition_summaries/*.md`
- `narrative_scores.csv`
- `narrative_scores.md`
- `narrative_score_raw/*.json`

Local reproducibility evidence, not committed:

- `runs/s2_issue19/*/simulation_artifacts/scheduled_events_fired.jsonl`
- `runs/s2_issue19/*/simulation_artifacts/reddit_simulation.db`

The `runs/` artifacts contain copied SQLite databases and logs. They were used to generate the committed summaries and metrics, but are intentionally kept local.

## S3 Blind Evaluation Plan

The issue accepts either two human evaluators or a blind plan for S3. This S2 PR provides the blind plan.

Plan:

- anonymize each condition summary and remove condition names, run paths, and injected-document labels;
- randomize packet order using opaque IDs such as `P01`, `P02`, `P03`;
- keep a private key mapping packet ID to condition;
- have two human evaluators score predicted winner, confidence, narrative impact, noise contamination, evidence discipline, and rationale;
- compute agreement on winner, confidence deltas, narrative-impact deltas, and contamination deltas;
- adjudicate any winner mismatch, confidence delta greater than `0.30`, narrative-impact delta greater than `1`, or contamination delta greater than one level.

The full checklist and blind-evaluation protocol are in `../ISSUE_RESPONSE.md`.

Reproducible commands:

```powershell
python backtesting/case-a-s2-positional-noise/evaluation/summarize_condition_artifacts.py

$env:OPENROUTER_API_KEY=[Environment]::GetEnvironmentVariable("OPENROUTER_API_KEY","User")
$env:LLM_API_KEY=$env:OPENROUTER_API_KEY
$env:OPENAI_API_KEY=$env:LLM_API_KEY
$env:LLM_BASE_URL="https://openrouter.ai/api/v1"
$env:LLM_MODEL_NAME="qwen/qwen3-8b"
cd backend
uv run --frozen python ../backtesting/case-a-s2-positional-noise/evaluation/score_narratives.py
```

Rebuild scores without spending model calls:

```powershell
cd backend
uv run --frozen python ../backtesting/case-a-s2-positional-noise/evaluation/score_narratives.py --from-raw
```

## Remaining Optional Work

Only optional polish remains:

- run ReportAgent per condition after verifying it reads the intended condition state;
- run the S3 blind human evaluation plan.

The issue's core implementation, matrix evidence, and narrative scoring are complete.
