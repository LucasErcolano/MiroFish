# Technical Report - S2 Issue 19

Date: 2026-06-07

## Objective

Evaluate scheduled information injection in a MiroFish Reddit simulation for the Copa America 2024 final prediction case: Argentina vs Colombia.

The experiment compares a baseline run against useful signal and plausible noise injected at three positions in the simulated discussion:

- early: round 4 of 40;
- mid: round 20 of 40;
- late: round 36 of 40.

## Implementation Summary

The Reddit runner now supports `event_config.scheduled_events` inside the round loop.

Implemented behavior:

- `round`, `round_index`, and `round_pct` scheduling;
- one-shot event firing;
- Reddit `create_post` via `ManualAction(ActionType.CREATE_POST, ...)`;
- audit artifact `scheduled_events_fired.jsonl`;
- unchanged baseline behavior when no scheduled events are configured.

The headless runner can also apply `injection_plan.yaml` to a prepared simulation and preserve physical artifacts for each condition.

## Matrix

Prepared simulation:

- `sim_4bab3075239e`

Run mode:

- Reddit only;
- 40 rounds per condition;
- existing prepared simulation reused;
- no ReportAgent generation in this pass;
- no graph-memory update after simulation.

Conditions:

- `baseline`
- `signal-early`
- `signal-mid`
- `signal-late`
- `noise-early`
- `noise-mid`
- `noise-late`

## Evidence

The strongest evidence is in copied artifacts under `runs/s2_issue19/<condition>/simulation_artifacts/`:

- `reddit_simulation.db`: posts, comments, traces;
- `scheduled_events_fired.jsonl`: fired scheduled event audit;
- `run_state.json`: subprocess runner status.

The compact technical table is maintained in:

- `impact_table.md`
- `impact_table.csv`
- `condition_summary_metrics.csv`
- `condition_summary_metrics.json`

Per-condition readable summaries are in:

- `condition_summaries/*.md`

## Result Highlights

All 7 conditions completed. Baseline fired no scheduled events. Each signal/noise condition fired exactly one scheduled event at the expected round.

Round resolution over 40 rounds:

- `round_pct=0.10` -> round 4, index 3;
- `round_pct=0.50` -> round 20, index 19;
- `round_pct=0.90` -> round 36, index 35.

Signal runs produced no detected noise-keyword contamination. Noise runs all include 12 detected noise-topic mentions from the injected document content.

## Narrative Scoring

Narrative scoring has been generated from deterministic condition summaries:

- `narrative_scores.csv`
- `narrative_scores.md`
- `narrative_score_raw/*.json`

Summary:

- baseline: `Unclear`, confidence `0.30`;
- signal early/mid/late: `Argentina`, confidence `0.70`, no noise contamination;
- noise early/mid/late: `Argentina`, confidence `0.65`, medium noise contamination.

## Final Report

Final issue-level interpretation is in:

- `final_issue_report.md`

ReportAgent was intentionally not used as the per-condition scorer because it has not been verified to isolate each copied SQLite artifact. The final scoring path is summary-based and reproducible.
