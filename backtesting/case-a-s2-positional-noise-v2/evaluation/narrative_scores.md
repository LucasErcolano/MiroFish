# Narrative Scores

Generated from deterministic condition summaries using the configured evaluator model.

| condition | predicted_winner | confidence | used_injected_document | noise_contamination |
|---|---|---:|---|---|
| v2-baseline-control | Unclear | 0.30 | False | none |
| v2-signal-strong-mid | Argentina | 0.90 | True | none |
| v2-signal-weak-mid | Argentina | 0.68 | True | none |
| v2-counter-colombia-mid | Colombia | 0.50 | True | none |
| v2-noise-near-mid | Argentina | 0.70 | True | medium |
| v2-noise-off-mid | Argentina | 0.50 | False | low |

## Evidence

### v2-baseline-control

- Predicted winner: `Unclear`
- Confidence: `0.30`
- Used injected document: `False`
- Noise contamination: `none`
- Difference vs baseline: n/a
- Notes: Ambiguous prediction due to equal emphasis on both teams' strengths without decisive evidence

Main evidence:
- Argentina's experience and defensive strength (1.2 blocked shots per game)
- Colombia's offensive threat via James Rodriguez's creativity
- Balanced discussion with no clear consensus between teams

### v2-signal-strong-mid

- Predicted winner: `Argentina`
- Confidence: `0.90`
- Used injected document: `True`
- Noise contamination: `none`
- Difference vs baseline: Injected document increased Argentina mentions (15 vs 7) and added explicit probability metrics
- Notes: Prediction stabilized by injected signal document containing explicit probability weights

Main evidence:
- Opta Preview assigned Argentina 50.9% chance to win in 90 minutes
- Argentina was model favorite with 63.0% chance of lifting trophy
- Colombia had 25.4% chance to win in 90 minutes

### v2-signal-weak-mid

- Predicted winner: `Argentina`
- Confidence: `0.68`
- Used injected document: `True`
- Noise contamination: `none`
- Difference vs baseline: Increased Argentina mentions (14 vs 7), explicit 68% probability in comments
- Notes: Balanced signal preserves uncertainty but assigns measurable probability to Argentina

Main evidence:
- Argentina's recent titles (Copa America 2021, World Cup 2022) and tournament experience
- Colombia's long unbeaten run and attacking confidence
- 68% probability assigned to Argentina in comment analysis

### v2-counter-colombia-mid

- Predicted winner: `Colombia`
- Confidence: `0.50`
- Used injected document: `True`
- Noise contamination: `none`
- Difference vs baseline: Colombia mentions increased from 5 to 13, Argentina mentions increased from 7 to 8; injected document shifted focus to Colombia's form and James Rodriguez's impact
- Notes: Ambiguity persists between Argentina's experience and Colombia's recent form; injected document provided specific statistical evidence altering narrative from baseline

Main evidence:
- Colombia's 28-match unbeaten streak (22 wins, 6 draws)
- James Rodriguez's 6 assists (most in Copa America since 2011)
- Colombia's defensive stability (0.25 goals conceded per game)

### v2-noise-near-mid

- Predicted winner: `Argentina`
- Confidence: `0.70`
- Used injected document: `True`
- Noise contamination: `medium`
- Difference vs baseline: Increased focus on Messi's global following and fan discourse metrics
- Notes: Injected document introduced celebrity/media attention signals but did not override performance-based analysis

Main evidence:
- Argentina's defensive solidity and squad depth highlighted in Opta Preview Summary
- Colombia's offensive threat via James Rodriguez acknowledged but not prioritized
- Comments emphasize tactical execution over social media narratives

### v2-noise-off-mid

- Predicted winner: `Argentina`
- Confidence: `0.50`
- Used injected document: `False`
- Noise contamination: `low`
- Difference vs baseline: argentina keyword count increased (8 vs 7), colombia decreased (4 vs 5), football_noise introduced
- Notes: Noise document did not influence top discussions; prediction remains aligned with baseline

Main evidence:
- Argentina's experience and defensive solidity highlighted in multiple posts
- Colombia's offensive threat with James Rodriguez acknowledged but not dominant
- Noise document about unrelated sports topics included but not referenced in top discussions
