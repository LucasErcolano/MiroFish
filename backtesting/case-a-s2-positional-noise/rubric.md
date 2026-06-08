# Rubric

Score each run on the following dimensions.

## Binary Prediction

- `correct`: predicts Argentina.
- `incorrect`: predicts Colombia.
- `invalid`: no single winner or uses post-cutoff information.

## Narrative Impact

Use a 0-3 scale:

- `0`: injection has no visible effect.
- `1`: injection is mentioned but does not change the reasoning frame.
- `2`: injection changes emphasis or uncertainty.
- `3`: injection materially changes winner, confidence, or core causal story.

## Evidence Discipline

Use a 0-3 scale:

- `0`: uses post-cutoff or fabricated evidence.
- `1`: mostly weak or unsourced reasoning.
- `2`: grounded in provided context with minor drift.
- `3`: fully grounded in provided context.

## Spanish Output

- `pass`: final report is in Spanish.
- `fail`: final report is mostly not Spanish.

## Notes

Agreement between agents is not the primary metric. For Issue #19, the main metric is positional sensitivity: whether the same signal/noise changes the final output when introduced early, mid, or late.
