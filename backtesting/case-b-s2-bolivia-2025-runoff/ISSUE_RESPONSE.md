# Issue Response Draft

Implemented and ran a temporal S2 backtesting case for the 2025 Bolivia presidential runoff.

## What Changed

- Added a curated political-social backtesting case under `backtesting/case-b-s2-bolivia-2025-runoff/`.
- Built neutral input sources for four temporal evidence packages:
  - `T0`: pre-first-round context.
  - `T1`: first-round surprise and MAS collapse.
  - `T2`: runoff platform contrast.
  - `T3`: late Quiroga poll, US-relations signal, and football-noise source.
- Added private ground truth and objective evaluator.
- Saved completed outputs for `T0`, `T1`, `T2`, and `T3`.
- Added local report-agent robustness fixes needed to complete the runs.

## Run Results

| Run | Prediction | Winner score | Main interpretation |
| --- | --- | ---: | --- |
| `T0` | no parseable Paz/Quiroga forecast | 0 | Too little context; model failed to infer the actual runoff field. |
| `T1` | Paz wins | 1 | Best run; first-round surprise and Doria Medina alignment pushed toward Paz. |
| `T2` | Quiroga wins | 0 | Platform contrast over-weighted Quiroga's pro-market stabilization frame. |
| `T3` | Quiroga wins | 0 | Late poll favoring Quiroga dominated the forecast; noise source did not materially affect reasoning. |

## Conclusions

- The temporal update behavior is visible: adding the first-round result in `T1` materially improves the forecast.
- Later evidence can also degrade performance: `T2` and `T3` show recency/salience bias toward Quiroga, especially once the late poll is included.
- The model correctly ignored the football-noise source in T3.
- No direct ground-truth leakage was detected in the intended input packages.
- The most important forecast-risk factors surfaced by MiroFish were economic distress, MAS fragmentation, coalition transfer uncertainty, late-poll reliability, platform backlash, and post-election unrest.

## Engineering Notes

The following fixes were needed for stable execution:

- JSON-format LLM calls now bypass Prompture and use the OpenAI-compatible client.
- `interview_agents` now has a 600-second timeout and single-platform fallback.
- Report-agent tool parsing now accepts safe Python-style literals like `True` in tool-call payloads.
- The objective evaluator now signs margins correctly when the predicted winner is Quiroga.

