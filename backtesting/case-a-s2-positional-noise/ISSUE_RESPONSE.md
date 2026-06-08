# Issue #19 Response

Date: 2026-06-07

## Issue

S2 - Investigador 3: Sensibilidad posicional (Linea 3) + Ruido temporal (Linea 4) combinados

## Acceptance Checklist

| requirement | status | evidence |
|---|---|---|
| `case_card.md` | done | `case_card.md` |
| `rubric.md` | done | `rubric.md` |
| `signal_doc.md` | done | `signal_doc.md` |
| `noise_doc.md` | done | `noise_doc.md` |
| `injection_plan.yaml` | done | `injection_plan.yaml` |
| Outputs por condicion | done | `evaluation/condition_summaries/*.md`, `evaluation/narrative_scores.md` |
| Tabla de impacto narrativo | done | `evaluation/impact_table.md`, `evaluation/narrative_scores.csv` |
| 2 evaluadores humanos o plan ciego para S3 | done as S3 plan | see `S3 Blind Evaluation Plan` below |

## What Was Implemented

The Reddit simulation runner now supports scheduled intra-run injection through `event_config.scheduled_events`.

Supported schedule fields:

- `round`
- `round_index`
- `round_pct`

Supported action:

- `target_platform=reddit`
- `action=create_post`

Each scheduled event fires once and is audited in `scheduled_events_fired.jsonl`.

## S2 Matrix

The S2 acceptance matrix was run with one baseline and six injected conditions:

| condition | injected document | position |
|---|---|---|
| baseline | none | none |
| signal-early | signal | early |
| signal-mid | signal | mid |
| signal-late | signal | late |
| noise-early | noise | early |
| noise-mid | noise | mid |
| noise-late | noise | late |

The run used a prepared Reddit simulation (`sim_4bab3075239e`) and 40 rounds.

## Main Result

Scheduled injection is measurable and auditable.

Observed narrative pattern:

- baseline remained ambiguous;
- signal early/mid/late shifted the narrative toward Argentina;
- noise early/mid/late did not flip the winner, but produced medium narrative contamination;
- timing changed discussion volume/traces, but did not change the evaluator-selected winner in this matrix.

This measures output/narrative variation, not agreement rate.

## Model Ladder / Robustness

The issue asked to keep one model fixed for the primary comparison and use the model ladder separately as calibration.

Primary matrix:

- Qwen3 8B through OpenRouter.

Additional robustness runs:

- richer V2 variable-injection matrix with Qwen;
- DeepInfra Gemma 3 27B IT;
- DeepInfra Llama 3.3 70B Instruct Turbo.

The DeepInfra extension confirmed the technical scheduled-injection behavior across both additional models. Llama reproduced the intended V2 narrative pattern more closely than Gemma.

ReportAgent follow-up:

- `ReportAgent` now has an explicit artifact-only mode for condition-isolated reporting;
- the V2 matrix was rendered through ReportAgent for Qwen, Gemma, and Llama;
- all 18 ReportAgent artifact-only reports completed without shared graph/tool reads.

See:

- `../case-a-s2-positional-noise-v2/evaluation/final_v2_report.md`
- `../case-a-s2-positional-noise-v2/evaluation_deepinfra/final_deepinfra_report.md`
- `../case-a-s2-positional-noise-v2/evaluation_report_agent/README.md`

## S3 Blind Evaluation Plan

The S2 run does not include two human evaluators. Instead, this PR provides the blind-evaluation plan requested as the S3 alternative.

### Packet Preparation

For each condition, create an anonymized packet containing only:

- condition summary text;
- top posts/comments;
- final narrative score fields with condition name removed;
- no file path, run directory, or injected-document label.

Randomize packet order and assign opaque IDs:

```text
P01, P02, P03, ...
```

Keep the mapping from packet ID to true condition in a private key file not shown to evaluators.

### Evaluators

Use two human evaluators who do not know:

- which condition is baseline/signal/noise;
- whether the injection was early/mid/late;
- which model generated the run.

### Blind Rubric

Each evaluator scores:

- predicted winner: Argentina / Colombia / unclear;
- confidence: 0.0-1.0;
- whether a new document appears to influence discussion;
- narrative impact: 0-3;
- noise contamination: none / low / medium / high;
- evidence discipline: 0-3;
- short rationale with quoted evidence from the anonymized packet.

### Agreement And Resolution

After both evaluators submit scores:

- compute exact agreement on predicted winner;
- compute absolute confidence difference;
- compare narrative-impact and contamination ratings;
- resolve large disagreements through a third adjudication pass.

Recommended disagreement thresholds:

- winner mismatch;
- confidence difference greater than `0.30`;
- narrative-impact difference greater than `1`;
- contamination difference greater than one level.

### S3 Output

The S3 output should include:

- anonymized packets;
- private condition key;
- evaluator score sheets;
- agreement table;
- adjudicated final table;
- comparison against automated narrative scoring.

## Evidence Policy

Committed evidence:

- `evaluation/impact_table.md`
- `evaluation/impact_table.csv`
- `evaluation/condition_summary_metrics.csv`
- `evaluation/condition_summary_metrics.json`
- `evaluation/condition_summaries/*.md`
- `evaluation/narrative_scores.csv`
- `evaluation/narrative_scores.md`
- `evaluation/narrative_score_raw/*.json`
- `evaluation/final_issue_report.md`

Local reproducibility evidence:

- `runs/s2_issue19/*/simulation_artifacts/scheduled_events_fired.jsonl`
- `runs/s2_issue19/*/simulation_artifacts/reddit_simulation.db`

The `runs/` directory is intentionally not committed because it contains copied SQLite databases and run logs. The committed summaries and metrics are the compact PR evidence; local run artifacts can be regenerated with the commands in `README.md`.

## ReportAgent Follow-Up Status

ReportAgent was not used as the original primary scorer. That decision remains methodologically clean because the acceptance evidence is based on deterministic summaries and evaluator scoring.

The follow-up is now complete: `ReportAgent` can run in artifact-only mode, receiving one condition-specific evidence bundle and avoiding shared graph/Zep tools. The completed V2 ReportAgent evidence is in `../case-a-s2-positional-noise-v2/evaluation_report_agent/`.
