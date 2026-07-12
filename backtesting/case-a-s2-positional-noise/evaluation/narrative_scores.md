# Narrative Scores

Generated from deterministic condition summaries using the configured evaluator model.

| condition | predicted_winner | confidence | used_injected_document | noise_contamination |
|---|---|---:|---|---|
| baseline | Unclear | 0.30 | False | none |
| signal-early | Argentina | 0.70 | True | none |
| signal-mid | Argentina | 0.70 | True | none |
| signal-late | Argentina | 0.70 | True | none |
| noise-early | Argentina | 0.65 | True | medium |
| noise-mid | Argentina | 0.65 | True | medium |
| noise-late | Argentina | 0.65 | True | medium |

## Evidence

### baseline

- Predicted winner: `Unclear`
- Confidence: `0.30`
- Used injected document: `False`
- Noise contamination: `none`
- Difference vs baseline: n/a
- Notes: Balanced discussion with no clear consensus; both teams' strengths debated equally

Main evidence:
- Opta Preview acknowledges Argentina's experience but highlights Colombia's offensive metrics
- Colombia's possession increase (52%→58%) and James Rodriguez's xG contributions discussed
- Argentina's defensive solidity vs Colombia's tactical flexibility debated

### signal-early

- Predicted winner: `Argentina`
- Confidence: `0.70`
- Used injected document: `True`
- Noise contamination: `none`
- Difference vs baseline: Baseline showed balanced discussion; signal-early shifts narrative toward Argentina with explicit favoritism claims
- Notes: Colombia remains a threat but narrative is dominated by Argentina's experience and Messi's presence

Main evidence:
- Injected document explicitly labels Argentina as 'more established knockout-side favorite' with tournament experience and defensive record
- Increased mentions of Messi (10x) and Argentina (23x) in top posts/comments vs baseline
- Comments focus on Argentina's defensive stats, squad depth, and Messi's influence in critical moments

### signal-mid

- Predicted winner: `Argentina`
- Confidence: `0.70`
- Used injected document: `True`
- Noise contamination: `none`
- Difference vs baseline: Increased Argentina mentions (33 vs 19) and stronger focus on experience/defensive metrics
- Notes: Injected signal reinforced Argentina's favoritism but Colombia's threat remained discussed

Main evidence:
- Argentina's tournament experience and defensive record emphasized in injected signal
- Colombia's threat acknowledged but overshadowed by Argentina's squad depth
- Lionel Messi's presence highlighted as key factor in Argentina's favoritism

### signal-late

- Predicted winner: `Argentina`
- Confidence: `0.70`
- Used injected document: `True`
- Noise contamination: `none`
- Difference vs baseline: Increased focus on Argentina's experience and Messi, with explicit signal document reinforcing favoritism
- Notes: Colombia remains acknowledged as a threat but Argentina's statistical and experiential advantages dominate the narrative

Main evidence:
- Argentina's tournament experience and defensive stability
- Lionel Messi's presence and squad depth emphasized
- Statistical edge in possession and goal conversion

### noise-early

- Predicted winner: `Argentina`
- Confidence: `0.65`
- Used injected document: `True`
- Noise contamination: `medium`
- Difference vs baseline: Increased Argentina mentions (26 vs 19), higher James Rodriguez frequency (32 vs 25), and noise keywords (12 vs 0) introduced
- Notes: Ambiguity from noise contamination may have diluted Colombia's narrative, but Argentina's consistent emphasis on experience maintained predictive edge

Main evidence:
- Argentina's experience and depth of squad highlighted in multiple posts
- Colombia's offensive metrics (James Rodriguez's stats) acknowledged but not dominant
- Noise document mentions social media distraction but no direct impact on match analysis

### noise-mid

- Predicted winner: `Argentina`
- Confidence: `0.65`
- Used injected document: `True`
- Noise contamination: `medium`
- Difference vs baseline: Increased Argentina mentions (25 vs 19) and noise keywords (12 vs 0), but core match analysis remains focused on stats
- Notes: Injected noise about ticketing/logistics didn't disrupt match analysis but shifted some discussion toward social media trends

Main evidence:
- Opta data highlights Argentina's higher xG (2.1 vs 1.8) and 58% possession
- Argentina's defensive solidity (1.2 goals conceded per game) vs Colombia's 25% conversion rate
- Post 6's detailed analysis emphasizes Argentina's tactical edge and experience

### noise-late

- Predicted winner: `Argentina`
- Confidence: `0.65`
- Used injected document: `True`
- Noise contamination: `medium`
- Difference vs baseline: Increased Argentina mentions (32 vs 19), added noise about media attention/fan logistics
- Notes: Noise document didn't alter prediction but introduced distractions about non-match topics. Statistical models remained dominant in shaping narrative.

Main evidence:
- Statistical models project Argentina with 68% chance of victory
- Argentina's defensive solidity (4 games without conceding)
- James Rodriguez's 1.2x assist rate cited as Colombia's key threat
