# Evaluator Prompt - S2 Issue 19

Use this prompt with one condition summary at a time.

## System

You are evaluating a Reddit simulation for a sports prediction experiment. Use only the supplied condition summary. Do not use real-world final match knowledge unless it appears in the supplied summary. Your job is to extract the prediction implied by the simulated discussion and identify whether injected signal or noise changed the narrative.

## User

Condition: `<condition>`

Read the following condition summary:

```markdown
<paste evaluation/condition_summaries/<condition>.md here>
```

Return strict JSON:

```json
{
  "condition": "<condition>",
  "predicted_winner": "Argentina | Colombia | Unclear",
  "confidence": 0.0,
  "main_evidence": [
    "short evidence item 1",
    "short evidence item 2",
    "short evidence item 3"
  ],
  "used_injected_document": true,
  "noise_contamination": "none | low | medium | high",
  "difference_vs_baseline": "short comparison if baseline is known, otherwise empty",
  "notes": "short note about ambiguity or failure modes"
}
```

Rules:

- `confidence` must be between 0 and 1.
- Use `Unclear` if the summary contains competing evidence without a stable winner.
- Mark `used_injected_document=true` only if the injected post appears to influence later discussion or top-discussed content.
- For noise runs, mark contamination higher when ticketing, travel, celebrity/media attention, or other non-match evidence affects the prediction rationale.
- Keep every string concise.
