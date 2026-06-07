# Narrative Scores

Generated from deterministic condition summaries using the configured evaluator model.

| condition | predicted_winner | confidence | used_injected_document | noise_contamination |
|---|---|---:|---|---|
| v2-baseline-control | Argentina | 0.70 | False | none |
| v2-signal-strong-mid | Argentina | 1.00 | True | none |
| v2-signal-weak-mid | Argentina | 0.00 | True | none |
| v2-counter-colombia-mid | Argentina | 0.60 | True | none |
| v2-noise-near-mid | Argentina | 0.70 | True | medium |
| v2-noise-off-mid | Argentina | 0.80 | False | low |

## Evidence

### v2-baseline-control

- Predicted winner: `Argentina`
- Confidence: `0.70`
- Used injected document: `False`
- Noise contamination: `none`
- Difference vs baseline: n/a
- Notes: The simulation leans towards Argentina as the winner, but acknowledges Colombia's potential to cause an upset, largely due to James Rodriguez.

Main evidence:
- Argentina is analyzed as the favorite due to experience and squad depth.
- Argentina trusts its history of victories and solid defense.
- Colombia could surprise Argentina, but Argentina is still favored.

### v2-signal-strong-mid

- Predicted winner: `Argentina`
- Confidence: `1.00`
- Used injected document: `True`
- Noise contamination: `none`
- Difference vs baseline: The injected document strongly favored Argentina, increasing the frequency of 'Argentina' mentions from 4 to 16 and introducing specific win probabilities (50.9%, 63.0%) not present in the baseline. The baseline discussion acknowledged Argentina as a favorite, but the injected signal amplified this prediction and provided quantitative support.
- Notes: The injected document provided a clear signal favoring Argentina, and the discussion reflects this shift. The baseline acknowledged Argentina as a favorite, but the injected signal provided specific probabilities and context.

Main evidence:
- Argentina was the model favorite.
- Argentina had a 50.9 percent chance of winning in 90 minutes and a 63.0 percent chance of lifting the trophy overall.
- Argentina entered as defending Copa America champion and 2022 World Cup champion.

### v2-signal-weak-mid

- Predicted winner: `Argentina`
- Confidence: `0.00`
- Used injected document: `True`
- Noise contamination: `none`
- Difference vs baseline: The injected document explicitly leaned the prediction towards Argentina, reinforcing the baseline's initial assessment of Argentina as favored, but emphasizing a 'modest' advantage and preserving uncertainty. Keyword counts show an increase in mentions of 'Argentina' (from 4 to 13) and 'James' (from 6 to 8).
- Notes: The injected document provided a 'weak' signal, aiming for a gentle lean towards Argentina while acknowledging Colombia's competitiveness. The simulation still reflects a degree of uncertainty.

Main evidence:
- Argentina is favored due to experience and depth of squad.
- Argentina has recent title experience (Copa America 2021, World Cup 2022).
- Argentina has extensive experience in high-pressure knockout matches.

### v2-counter-colombia-mid

- Predicted winner: `Argentina`
- Confidence: `0.60`
- Used injected document: `True`
- Noise contamination: `none`
- Difference vs baseline: The injected document shifted the narrative to highlight Colombia's strong form (28 matches without defeat, 22 wins and 6 draws) and James Rodriguez's performance (6 assists). While Argentina was still initially favored, the injected document increased discussion of Colombia's capabilities.
- Notes: The injected document provided strong counter-evidence for Colombia, but the initial posts still favored Argentina. The final prediction leans towards Argentina due to the initial framing, but the injected document clearly altered the discussion.

Main evidence:
- Argentina is analyzed as the favorite with experience and depth.
- Argentina trusts its history of victories and solid defense.
- Colombia could surprise Argentina, but Argentina depends on its experience.

### v2-noise-near-mid

- Predicted winner: `Argentina`
- Confidence: `0.70`
- Used injected document: `True`
- Noise contamination: `medium`
- Difference vs baseline: The injected document introduces noise related to fan engagement, media attention, and logistical issues surrounding the match. Keyword counts show an increase in 'football_noise' to 6, and 'messi' appears 1 time, compared to 0 in the baseline. The number of posts increased from 4 to 6.
- Notes: The injected document explicitly states the noise is *not* predictive of match outcome, but the increased discussion of fan engagement and media attention may subtly shift focus away from purely tactical considerations.

Main evidence:
- Argentina is analyzed as the favorite with experience and depth.
- Argentina confides in its history of victories and solid defense.
- Colombia could surprise Argentina, but Argentina relies on experience.

### v2-noise-off-mid

- Predicted winner: `Argentina`
- Confidence: `0.80`
- Used injected document: `False`
- Noise contamination: `low`
- Difference vs baseline: The injected document contained off-topic sports news. Keyword counts show an increase in 'football_noise' from 0 to 4, but the core narrative remains focused on Argentina as the favorite.
- Notes: The injected noise document appears to have had minimal impact on the prediction, as the top discussed posts are consistent with the baseline condition. The narrative still favors Argentina.

Main evidence:
- Argentina is analyzed as the favorite with experience and depth.
- Argentina confides in its history of victories and solid defense.
- Colombia could surprise Argentina, but Argentina relies on its experience.
