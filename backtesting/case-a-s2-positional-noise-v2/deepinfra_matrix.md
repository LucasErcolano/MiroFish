# DeepInfra Model Matrix

Date: 2026-06-07

## Objective

Repeat the V2 variable-injected-information matrix with the two S2 DeepInfra models that were not previously tested.

The goal is provider/model robustness, not a new injection design.

## Fixed Elements

- Case: Copa America 2024 final, Argentina vs Colombia.
- Platform: Reddit.
- Prepared simulation: `sim_4bab3075239e`.
- Injection plan: `backtesting/case-a-s2-positional-noise-v2/injection_plan_v2.yaml`.
- Conditions: same six V2 conditions.
- Rounds per run: 12.
- ReportAgent: disabled during the simulation/scoring pass; artifact-only ReportAgent reports are generated separately in `evaluation_report_agent/`.
- Graph memory update: disabled.

## Variable Element

The simulation LLM provider/model:

| provider | model |
|---|---|
| DeepInfra | `google/gemma-3-27b-it` |
| DeepInfra | `meta-llama/Llama-3.3-70B-Instruct-Turbo` |

## Output Rule

Do not overwrite previous runs.

New run artifacts must go under:

```text
runs/s2_issue19_deepinfra/
```

Model-specific summaries and reports must go under:

```text
backtesting/case-a-s2-positional-noise-v2/evaluation_deepinfra/
```

## Conditions

- `v2-baseline-control`
- `v2-signal-strong-mid`
- `v2-signal-weak-mid`
- `v2-counter-colombia-mid`
- `v2-noise-near-mid`
- `v2-noise-off-mid`

## Verification Gates

- Each model answers a minimal DeepInfra chat-completions smoke request.
- Each condition completes or is recorded as blocked with artifacts.
- Baseline fires zero scheduled events.
- Each injected condition fires exactly one scheduled event at round 6.
- Deterministic summaries and metrics are generated per model.
- Narrative scores are generated per model.
- A final comparative report is written without modifying V1/V2 reports.
