# T3 Gemma Probe Run Notes

## Run identity

- Case: `bolivia_2025_runoff_s2`
- Temporal package: `T3`
- Evidence cutoff: `2025-10-17`
- Intended uploaded evidence: sources `01` through `08` plus `question.md`
- Report id: `report_def4b871bbf2`
- Simulation id: `sim_f01997f5c8ba`
- Graph id: `mirofish_762dc745bf614b0c`
- Local completion time: `2026-06-03 14:03`

## Outcome

The report completed successfully and produced a full markdown report. It identified Rodrigo Paz and Jorge "Tuto" Quiroga as the competitive runoff candidates, but predicted a Jorge Quiroga victory.

Parsed forecast:

- Jorge "Tuto" Quiroga: `52%`
- Rodrigo Paz: `43%`
- Otros / blanco / nulo: `5%`
- Margin: `9` points for Quiroga

The report title/summary are internally inconsistent because they mention a Paz victory, while the actual structured forecast sections predict Quiroga. The evaluator correctly uses the structured prediction line and scores this as `quiroga_gana`.

## Evaluation

- Ground truth: Rodrigo Paz wins.
- Parsed prediction: `quiroga_gana`
- Winner score: `0`
- MAE vote share: `7.687`
- Margin absolute error: `18.06`
- Parse errors: `0`
- Leakage flags: none detected by the evaluator.

## Leakage note

A manual grep check over sources `01` through `08` found no direct runoff-result leakage: no final winner text, no final official vote shares, and no final margin. T3 adds a late poll showing Quiroga ahead, a US-relations signal, and one football-noise source. The late poll appears to have pushed the report strongly toward Quiroga.

## Evaluation note

`eval_objective.py` was corrected after this run to treat "margen ganador-segundo" as a signed Paz-minus-Quiroga margin based on the predicted winner. Without that correction, a wrong Quiroga forecast could appear to have a small margin error.
