# Narrative Scores

Generated from deterministic condition summaries using the configured evaluator model.

| condition | predicted_winner | confidence | used_injected_document | noise_contamination |
|---|---|---:|---|---|
| v2-baseline-control | Unclear | 0.00 | False | none |
| v2-signal-strong-mid | Argentina | 0.63 | True | none |
| v2-signal-weak-mid | Argentina | 0.60 | True | none |
| v2-counter-colombia-mid | Colombia | 0.60 | True | none |
| v2-noise-near-mid | Argentina | 0.50 | False | medium |
| v2-noise-off-mid | Argentina | 0.50 | False | none |

## Evidence

### v2-baseline-control

- Predicted winner: `Unclear`
- Confidence: `0.00`
- Used injected document: `False`
- Noise contamination: `none`
- Difference vs baseline: n/a
- Notes: The discussion presents balanced views on both teams, making it difficult to determine a clear winner.

Main evidence:
- Argentina favored due to experience and depth
- Colombia's offense and James Rodriguez' influence
- Discussion acknowledges both teams' strengths

### v2-signal-strong-mid

- Predicted winner: `Argentina`
- Confidence: `0.63`
- Used injected document: `True`
- Noise contamination: `none`
- Difference vs baseline: Increased discussion of Argentina's chances and history
- Notes: Injected post provided strong evidence for Argentina's favoritism

Main evidence:
- Argentina assigned a 63.0 percent chance of lifting the trophy overall
- Defending Copa America champion and 2022 World Cup champion
- Colombia had only one win in its last 12 meetings with Argentina

### v2-signal-weak-mid

- Predicted winner: `Argentina`
- Confidence: `0.60`
- Used injected document: `True`
- Noise contamination: `none`
- Difference vs baseline: Increased discussion of Argentina's experience and Colombia's attacking confidence
- Notes: The injected document leaned the prediction toward Argentina, but preserved uncertainty

Main evidence:
- Argentina's recent title experience
- defensive organization and elite individual quality
- Colombia's long unbeaten run and strong attacking confidence

### v2-counter-colombia-mid

- Predicted winner: `Colombia`
- Confidence: `0.60`
- Used injected document: `True`
- Noise contamination: `none`
- Difference vs baseline: Increased discussion of Colombia's strengths and James Rodriguez's influence
- Notes: The injected document highlighting Colombia's unbeaten streak and James Rodriguez's performance appears to have shifted the discussion in favor of Colombia

Main evidence:
- Colombia's 28 matches without defeat
- James Rodriguez's creativity and 6 assists
- Colombia's above-expectation attacking efficiency

### v2-noise-near-mid

- Predicted winner: `Argentina`
- Confidence: `0.50`
- Used injected document: `False`
- Noise contamination: `medium`
- Difference vs baseline: Reduced discussion of Messi, increased focus on social media and fan discourse
- Notes: The injected document introduced noise related to fan discourse and social media attention, but did not directly influence the top-discussed posts or comments.

Main evidence:
- Opta Preview Summary analysis
- Argentina's experience and depth
- James Rodriguez's influence on Colombia

### v2-noise-off-mid

- Predicted winner: `Argentina`
- Confidence: `0.50`
- Used injected document: `False`
- Noise contamination: `none`
- Difference vs baseline: Similar discussion themes, but with an additional off-topic post
- Notes: The injected document did not appear to influence the discussion, as the top-discussed posts still focused on the match prediction

Main evidence:
- Opta Preview Summary analysis
- Argentina's experience and depth
- Colombia's reliance on James Rodriguez
