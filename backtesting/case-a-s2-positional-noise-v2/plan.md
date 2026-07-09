# S2 Issue 19 V2 Plan - Variable Injection Content

## Objective

The first S2 matrix proved that scheduled Reddit injection works, but the injected content was too small: one signal document and one noise document. V2 tests whether richer and more varied injected information produces clearer output variation.

This extension keeps the original S2 results intact and writes all new artifacts to separate V2 paths.

## What Changes

V1 varied:

- injection type: signal vs noise;
- injection timing: early/mid/late.

V2 varies:

- injected document content.

V2 keeps timing fixed at `round_pct=0.50` so the experiment isolates content type before reintroducing timing.

## Conditions

| condition | injected document | purpose |
|---|---|---|
| v2-baseline-control | none | control run using same prepared simulation |
| v2-signal-strong-mid | strong Argentina signal | high-density pro-Argentina evidence |
| v2-signal-weak-mid | weak/balanced Argentina signal | modest favorite signal with uncertainty |
| v2-counter-colombia-mid | Colombia upside counter-signal | relevant evidence pushing toward Colombia |
| v2-noise-near-mid | near-topic narrative noise | plausible social/media noise close to match discourse |
| v2-noise-off-mid | off-topic sports noise | less relevant sports-news distraction |

## Design Rationale

The seed bundle remains fixed. The variable component is only the scheduled injected document. This preserves the core experimental contract:

- same base world;
- same prepared simulation;
- same platform;
- same injection timing;
- different injected content.

## Run Policy

Pilot run:

- platform: Reddit;
- prepared simulation: `sim_4bab3075239e`;
- max rounds: 12;
- no ReportAgent;
- no graph-memory update;
- output root: `runs/s2_issue19_v2/`.

This is a content-variation pilot, not a statistically robust final matrix. If results are promising, the next robust run should be:

- 6 V2 conditions x 3 seeds x 40 rounds.

## Stop Criteria

Stop instead of burning credits if:

- backend is unavailable;
- scheduled event audit is missing;
- any condition fails to complete;
- the injected post is absent from `reddit_simulation.db`;
- all conditions produce identical summary/evaluator output.

## Expected Outcome

The strong Argentina signal should push the narrative toward Argentina more clearly than baseline.

The weak signal should be less forceful than the strong signal.

The Colombia counter-signal should increase uncertainty or push the narrative toward Colombia.

Near-topic noise should contaminate the rationale more than off-topic noise.

Off-topic noise should be easier for the evaluator to ignore.
