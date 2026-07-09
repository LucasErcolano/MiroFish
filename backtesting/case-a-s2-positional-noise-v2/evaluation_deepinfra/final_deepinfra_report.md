# Final DeepInfra Report - S2 Issue 19 V2

Date: 2026-06-07

## Scope

This report extends the V2 variable-injected-information experiment with the two S2 DeepInfra models that had not been tested yet.

The objective was provider/model robustness. The injection design did not change.

## Models

Both model IDs passed a minimal DeepInfra OpenAI-compatible chat-completions smoke test before running the matrix.

| provider | model | smoke |
|---|---|---|
| DeepInfra | `google/gemma-3-27b-it` | OK |
| DeepInfra | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | OK |

## Design

Fixed elements:

- prepared simulation: `sim_4bab3075239e`;
- platform: Reddit;
- base seed/context: unchanged from V2;
- injection plan: `backtesting/case-a-s2-positional-noise-v2/injection_plan_v2.yaml`;
- injection timing: `round_pct=0.50`;
- pilot length: 12 rounds;
- ReportAgent: disabled in the original simulation/scoring pass, then run as artifact-only follow-up;
- graph memory update: disabled.

Variable element:

- DeepInfra simulation model.

Output isolation:

- previous V1 artifacts remain under `runs/s2_issue19/`;
- previous V2/Qwen artifacts remain under `runs/s2_issue19_v2/`;
- new DeepInfra artifacts are under `runs/s2_issue19_deepinfra/`;
- DeepInfra evaluation artifacts are under `backtesting/case-a-s2-positional-noise-v2/evaluation_deepinfra/`.

## Technical Results

All 12 DeepInfra runs completed: 6 conditions for Gemma and 6 conditions for Llama.

For both models:

- baseline fired zero scheduled events;
- every injected condition fired exactly one scheduled event;
- all injected events fired at round 6.

### Gemma

| condition | injected_doc | scheduled_events | fired_round | posts | comments | traces | football_noise_mentions |
|---|---|---:|---:|---:|---:|---:|---:|
| v2-baseline-control | none | 0 | - | 4 | 0 | 11 | 0 |
| v2-signal-strong-mid | signal-strong | 1 | 6 | 5 | 2 | 17 | 0 |
| v2-signal-weak-mid | signal-weak | 1 | 6 | 6 | 0 | 14 | 0 |
| v2-counter-colombia-mid | counter-colombia | 1 | 6 | 6 | 0 | 12 | 0 |
| v2-noise-near-mid | noise-near | 1 | 6 | 6 | 0 | 14 | 6 |
| v2-noise-off-mid | noise-off | 1 | 6 | 5 | 0 | 13 | 4 |

### Llama

| condition | injected_doc | scheduled_events | fired_round | posts | comments | traces | football_noise_mentions |
|---|---|---:|---:|---:|---:|---:|---:|
| v2-baseline-control | none | 0 | - | 4 | 3 | 16 | 0 |
| v2-signal-strong-mid | signal-strong | 1 | 6 | 5 | 2 | 17 | 0 |
| v2-signal-weak-mid | signal-weak | 1 | 6 | 5 | 1 | 13 | 0 |
| v2-counter-colombia-mid | counter-colombia | 1 | 6 | 5 | 2 | 16 | 0 |
| v2-noise-near-mid | noise-near | 1 | 6 | 5 | 1 | 13 | 6 |
| v2-noise-off-mid | noise-off | 1 | 6 | 5 | 2 | 17 | 4 |

## Narrative Scores

Narrative scoring was generated separately per model using the same DeepInfra model as evaluator for its own condition summaries.

### Gemma

| condition | predicted_winner | confidence | used_injected_document | noise_contamination |
|---|---|---:|---|---|
| v2-baseline-control | Argentina | 0.70 | false | none |
| v2-signal-strong-mid | Argentina | 1.00 | true | none |
| v2-signal-weak-mid | Argentina | 0.00 | true | none |
| v2-counter-colombia-mid | Argentina | 0.60 | true | none |
| v2-noise-near-mid | Argentina | 0.70 | true | medium |
| v2-noise-off-mid | Argentina | 0.80 | false | low |

### Llama

| condition | predicted_winner | confidence | used_injected_document | noise_contamination |
|---|---|---:|---|---|
| v2-baseline-control | Unclear | 0.00 | false | none |
| v2-signal-strong-mid | Argentina | 0.63 | true | none |
| v2-signal-weak-mid | Argentina | 0.60 | true | none |
| v2-counter-colombia-mid | Colombia | 0.60 | true | none |
| v2-noise-near-mid | Argentina | 0.50 | false | medium |
| v2-noise-off-mid | Argentina | 0.50 | false | none |

## Interpretation

The scheduled-injection mechanism is robust across the two DeepInfra models tested. The event scheduling part is the strongest finding:

- 12/12 runs completed;
- 10/10 injected conditions fired exactly one event;
- 2/2 baselines fired zero events;
- all injected events fired at the intended mid-run point.

The narrative effect differs by model.

Gemma:

- baseline already leaned Argentina, so the signal conditions did not produce a clean baseline-to-signal flip;
- strong signal raised confidence to `1.00`;
- counter-Colombia did not flip the winner away from Argentina;
- near-topic noise produced medium contamination;
- off-topic noise was mostly ignored;
- one evaluator output is internally odd: `v2-signal-weak-mid` returned `Argentina` with `confidence=0.00`. This was preserved as raw model output, not manually corrected.

Llama:

- baseline stayed `Unclear`, matching the desired control behavior more closely;
- strong and weak Argentina signal shifted toward Argentina;
- Colombia counter-signal flipped the predicted winner to Colombia at `0.60`;
- near-topic noise did not become a main cited injected source, but still produced medium contamination through fan/social framing;
- off-topic noise was ignored with no contamination.

## Comparison To Prior V2 Qwen Run

The prior V2 Qwen/OpenRouter pilot showed:

- baseline: `Unclear`;
- strong signal: `Argentina`;
- weak signal: `Argentina`;
- counter-Colombia: `Colombia`;
- near-topic noise: medium contamination;
- off-topic noise: low contamination or mostly ignored.

Llama matches this pattern most closely. Gemma preserves the technical injection behavior but is more Argentina-biased in the narrative scoring, including baseline and counter-signal.

## Caveats

- The backend Reddit `run_status` still reports `current_round=0` after runs, so round completion is not reliable from that field. The reliable evidence is the copied SQLite DB, traces, and `scheduled_events_fired.jsonl`.
- ReportAgent was disabled during the original scoring pass. A later artifact-only ReportAgent pass keeps isolation by using one condition-specific evidence bundle and no shared graph/Zep tools.
- The same model was used to score its own summaries. This is useful for model-specific behavior, but a cross-model evaluator pass could be added later.
- Gemma produced one inconsistent evaluator confidence value. The raw output is retained in `evaluation_deepinfra/gemma/narrative_score_raw/v2-signal-weak-mid.txt`.

## Evidence

Local run artifacts, not committed:

- `runs/s2_issue19_deepinfra/gemma/*/simulation_artifacts/`
- `runs/s2_issue19_deepinfra/llama/*/simulation_artifacts/`
- `runs/s2_issue19_deepinfra/gemma/_model_metadata.json`
- `runs/s2_issue19_deepinfra/llama/_model_metadata.json`

Committed evaluation artifacts:

- `backtesting/case-a-s2-positional-noise-v2/evaluation_deepinfra/gemma/condition_summary_metrics.csv`
- `backtesting/case-a-s2-positional-noise-v2/evaluation_deepinfra/gemma/narrative_scores.csv`
- `backtesting/case-a-s2-positional-noise-v2/evaluation_deepinfra/llama/condition_summary_metrics.csv`
- `backtesting/case-a-s2-positional-noise-v2/evaluation_deepinfra/llama/narrative_scores.csv`
- `backtesting/case-a-s2-positional-noise-v2/evaluation_deepinfra/combined_deepinfra_scores.csv`

The committed evaluation artifacts are derived from the local run artifacts. The `runs/` directory is intentionally not committed because it contains copied SQLite databases and logs.

ReportAgent artifact-only evidence:

- `backtesting/case-a-s2-positional-noise-v2/evaluation_report_agent/gemma/*/full_report.md`
- `backtesting/case-a-s2-positional-noise-v2/evaluation_report_agent/llama/*/full_report.md`
- `backtesting/case-a-s2-positional-noise-v2/evaluation_report_agent/report_agent_manifest.csv`

## Conclusion

The DeepInfra extension is complete.

The issue's scheduled-injection behavior is confirmed on:

- OpenRouter/Qwen from the prior V2 run;
- DeepInfra/Gemma;
- DeepInfra/Llama.

The strongest cross-model result is technical: scheduled mid-run injection reliably fires and is auditable. The strongest narrative result is with Llama, which reproduces the intended V2 pattern most closely.

The ReportAgent follow-up is also complete across the three requested models: Qwen, Gemma, and Llama all produced six artifact-only condition reports.
