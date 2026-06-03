# T2 Gemma Probe Run Notes

## Run identity

- Case: `bolivia_2025_runoff_s2`
- Temporal package: `T2`
- Evidence cutoff: `2025-10-10`
- Intended uploaded evidence: sources `01` through `05` plus `question.md`
- Report id: `report_8b7869068e03`
- Simulation id: `sim_bbda52725c33`
- Graph id: `mirofish_fc33987528ad4fdc`
- Local completion time: `2026-06-02 23:10`

## Model/config note

This run used the local Gemma probe setup. It is a completed T2 probe, but should be reported separately from the intended Qwen primary model policy.

## Outcome

The report completed successfully and produced a full markdown report. It identified the competitive runoff candidates as Rodrigo Paz and Jorge "Tuto" Quiroga, but predicted a Jorge Quiroga victory.

Parsed forecast:

- Jorge "Tuto" Quiroga: `53%`
- Rodrigo Paz: `44%`
- Otros / blanco / nulo: `3%`
- Margin: `9` points for Quiroga

## Evaluation

- Ground truth: Rodrigo Paz wins.
- Parsed prediction: `quiroga_gana`
- Winner score: `0`
- MAE vote share: `7.02`
- Margin absolute error: `18.06`
- Parse errors: `0`
- Leakage flags: none detected by the evaluator.

## Leakage note

A manual grep check over sources `01` through `05` found no direct runoff-result leakage: no final winner text, no final official vote shares, and no final margin. T2 adds platform-contrast evidence relative to T1, which appears to have pushed the report toward Quiroga's pro-market economic framing.
