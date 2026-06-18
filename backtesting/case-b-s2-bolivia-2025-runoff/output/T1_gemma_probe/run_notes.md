# T1 Gemma Probe Run Notes

## Run identity

- Case: `bolivia_2025_runoff_s2`
- Temporal package: `T1`
- Evidence cutoff: `2025-08-18`
- Intended uploaded evidence: sources `01` through `04` plus `question.md`
- Report id: `report_69dabe8c4725`
- Simulation id: `sim_7c53f3ac28f0`
- Graph id: `mirofish_7c5c84b3698a47da`
- Local completion time: `2026-06-02 19:38`

## Model/config note

This run used the local Gemma probe setup. It is useful as a completed T1 probe, but the final benchmark policy still needs to distinguish this from the intended Qwen primary model policy.

## Outcome

The report completed successfully and produced a full markdown report. It identified the competitive runoff candidates as Rodrigo Paz and Jorge "Tuto" Quiroga, then predicted a Rodrigo Paz victory.

Final forecast section:

- Rodrigo Paz: `53%`
- Jorge "Tuto" Quiroga: `44%`
- Otros / blanco / nulo: `3%`
- Margin: `9` points

The evaluator currently parses the first percentage block in the report, which is:

- Rodrigo Paz: `52%`
- Jorge "Tuto" Quiroga: `45%`
- Otros / blanco / nulo: `3%`

## Evaluation

- Ground truth: Rodrigo Paz wins.
- Parsed prediction: `paz_gana`
- Winner score: `1`
- MAE vote share: `2.0`
- Margin absolute error: `0.06`
- Parse errors: `0`
- Leakage flags: none detected by the evaluator.

## Leakage note

A manual check of sources `01` through `04` found no direct runoff-result leakage: no final winner text, no final official vote shares, and no final margin. T1 does include strong allowed signals: Paz first in the first round, Quiroga second, MAS excluded from the runoff, and Doria Medina endorsing Paz.
