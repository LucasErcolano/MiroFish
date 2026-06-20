# T0 Gemma Probe Run Notes

## Run identity

- Case: `bolivia_2025_runoff_s2`
- Temporal package: `T0`
- Evidence cutoff: `2025-08-16`
- Uploaded evidence: `assembled_T0.md` and `question.md`
- Report id: `report_c4f38b4b9b45`
- Simulation id: `sim_9b6b7d536856`
- Graph id: `mirofish_fe18700ad334405d`
- Local completion time: `2026-06-01 13:07`

## Model/config note

This run used the Gemma probe configuration in the local environment, not the intended final Qwen primary policy. It is still useful as a system/protocol check because the full MiroFish flow completed end to end.

## Outcome

The report completed technically, but the forecast is invalid for the target runoff. It identified Luis Arce and Samuel Doria Medina as the competitive candidates, and the report chat later gave a different incorrect pair, Luis Arce and Carlos Mesa.

The official scored artifact is `full_report.md`, not the later chat answer. The evaluator gives `winner_score = 0` because it cannot parse a Paz or Quiroga win prediction from the report.

## Evaluation

- Ground truth: Rodrigo Paz wins.
- Parsed prediction: `null`
- Winner score: `0`
- Parsed vote shares: only `otros = 20.0`
- Parse errors: `2`
- Margin absolute error: `5.06`

## Interpretation

This T0 result is a useful failure mode: with only early evidence, the model appears to anchor on older Bolivian political figures instead of reconstructing the actual 2025 runoff field. T1, T2, and T3 should test whether later evidence corrects the candidate set and winner prediction.
