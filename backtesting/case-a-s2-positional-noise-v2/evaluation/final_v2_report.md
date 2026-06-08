# Final V2 Report - Variable Injection Content

Date: 2026-06-07

## Objective

V1 tested scheduled injection timing with one signal document and one noise document. V2 tests richer variable injected information while keeping timing fixed at mid-run.

The purpose is to answer the concern that the original injected information was too small.

## Design

Fixed elements:

- prepared simulation: `sim_4bab3075239e`;
- platform: Reddit;
- base seed/context: unchanged from V1;
- injection timing: `round_pct=0.50`;
- pilot length: 12 rounds;
- no ReportAgent in the original scoring pass;
- no graph-memory update.

Variable element:

- injected document content.

## Conditions

| condition | injected document | intent |
|---|---|---|
| v2-baseline-control | none | control |
| v2-signal-strong-mid | strong Argentina signal | dense probability/history evidence |
| v2-signal-weak-mid | weak Argentina lean | balanced favorite signal |
| v2-counter-colombia-mid | Colombia counter-signal | relevant evidence for upset narrative |
| v2-noise-near-mid | near-topic social narrative | plausible fandom/media contamination |
| v2-noise-off-mid | off-topic sports distraction | easier-to-ignore irrelevant sports noise |

## Technical Results

All six V2 pilot conditions completed. Each injected condition fired exactly one scheduled event at round 6 (`round_index=5`) over 12 rounds. The baseline fired zero events.

| condition | injected_doc | fired_round | posts | comments | traces | football_noise_mentions |
|---|---|---:|---:|---:|---:|---:|
| v2-baseline-control | none | - | 4 | 3 | 14 | 0 |
| v2-signal-strong-mid | signal-strong | 6 | 6 | 0 | 13 | 0 |
| v2-signal-weak-mid | signal-weak | 6 | 5 | 1 | 13 | 0 |
| v2-counter-colombia-mid | counter-colombia | 6 | 5 | 2 | 17 | 0 |
| v2-noise-near-mid | noise-near | 6 | 5 | 4 | 17 | 6 |
| v2-noise-off-mid | noise-off | 6 | 5 | 2 | 13 | 4 |

## Narrative Scores

| condition | predicted_winner | confidence | used_injected_document | noise_contamination |
|---|---|---:|---|---|
| v2-baseline-control | Unclear | 0.30 | false | none |
| v2-signal-strong-mid | Argentina | 0.90 | true | none |
| v2-signal-weak-mid | Argentina | 0.68 | true | none |
| v2-counter-colombia-mid | Colombia | 0.50 | true | none |
| v2-noise-near-mid | Argentina | 0.70 | true | medium |
| v2-noise-off-mid | Argentina | 0.50 | false | low |

## Interpretation

The richer injected documents produced clearer variation than V1.

Strong Argentina signal:

- shifted the narrative strongly toward Argentina;
- raised confidence to `0.90`;
- evaluator used explicit Opta probability evidence from the injected document.

Weak Argentina signal:

- still shifted toward Argentina;
- confidence was lower than strong signal (`0.68`);
- preserved uncertainty more than the strong signal.

Colombia counter-signal:

- flipped the evaluator-selected winner to Colombia, but only at `0.50` confidence;
- increased Colombia and James Rodriguez emphasis;
- shows that relevant counter-evidence can change output direction when injected mid-run.

Near-topic noise:

- did not flip the winner;
- introduced medium contamination through fan/media/social-attention framing;
- was partly used in the narrative.

Off-topic noise:

- did not flip the winner;
- had low contamination;
- evaluator marked `used_injected_document=false`, meaning the irrelevant sports noise was mostly ignored.

## Methodological Finding

V2 confirms the user's concern: one signal and one noise document were enough for a technical pilot, but richer variable injected content gives a more informative experiment.

Important caveat:

- generated agents can invent or extrapolate numerical claims during discussion;
- for example, the `v2-signal-weak-mid` summary contains a generated comment with a `68% probability` claim that was not present in the injected weak-signal document;
- therefore final scoring should distinguish between source-provided evidence and agent-generated claims.

This caveat is useful: it suggests future evaluators should flag unsupported numerical claims as a separate contamination or hallucination category.

## Answer

Yes, V2 is a better test of variable injected information.

Compared with V1, it separates:

- strong signal;
- weak signal;
- relevant counter-signal;
- near-topic noise;
- off-topic noise.

That makes the experiment more interpretable than simply repeating the original signal/noise pair.

## Next Robust Run

The pilot is complete. A stronger matrix would run:

```text
6 conditions x 3 seeds x 40 rounds = 18 runs
```

or, for timing plus content:

```text
5 injected document types x 3 timings + baseline = 16 conditions
```

The recommended next robust design is not to expand timing yet. First repeat this V2 content matrix with multiple seeds.

## Evidence

Committed V2 artifacts:

- `backtesting/case-a-s2-positional-noise-v2/injection_plan_v2.yaml`
- `backtesting/case-a-s2-positional-noise-v2/injections/*.md`
- `backtesting/case-a-s2-positional-noise-v2/evaluation/condition_summary_metrics.csv`
- `backtesting/case-a-s2-positional-noise-v2/evaluation/narrative_scores.csv`
- `backtesting/case-a-s2-positional-noise-v2/evaluation/condition_summaries/*.md`

Local reproducibility artifacts, not committed:

- `runs/s2_issue19_v2/*/simulation_artifacts/scheduled_events_fired.jsonl`
- `runs/s2_issue19_v2/*/simulation_artifacts/reddit_simulation.db`

## ReportAgent Follow-Up

After the deterministic/evaluator scoring pass, the V2 conditions were also rendered with ReportAgent in artifact-only mode.

This follow-up used one condition-specific evidence bundle per report and disabled shared graph/Zep tool reads. The completed outputs are in:

- `../evaluation_report_agent/qwen/*/full_report.md`
- `../evaluation_report_agent/report_agent_manifest.csv`

The same artifact-only runner also covers the DeepInfra Gemma and Llama runs documented in `../evaluation_deepinfra/final_deepinfra_report.md`.
