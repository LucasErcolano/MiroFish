# Case A S2 Positional Noise V2

This is an extension of `backtesting/case-a-s2-positional-noise/`.

V1 proved scheduled injection and tested signal/noise timing. V2 tests richer variable injected documents while keeping timing fixed.

## Files

- `plan.md`: objective, design, run policy, expected outcome.
- `injection_plan_v2.yaml`: condition schedule.
- `injections/*.md`: variable documents injected during the run.
- `run_map_v2.yaml`: mapping from conditions to artifact directories.
- `evaluation/`: generated summaries, metrics, and reports.
- `evaluation_report_agent/`: artifact-only ReportAgent follow-up across Qwen, Gemma, and Llama.

## Important Rule

Do not overwrite V1 results. V2 outputs go to:

```text
runs/s2_issue19_v2/
```

## Pilot Matrix

Conditions:

- `v2-baseline-control`
- `v2-signal-strong-mid`
- `v2-signal-weak-mid`
- `v2-counter-colombia-mid`
- `v2-noise-near-mid`
- `v2-noise-off-mid`

All injections use `round_pct=0.50` so content is the variable under test.

## Generated Outputs

Current V2 pilot outputs:

- `runs/s2_issue19_v2/*`: copied per-condition run artifacts.
- `evaluation/condition_summaries/*.md`: deterministic summaries from run artifacts.
- `evaluation/condition_summary_metrics.csv`: compact technical metrics.
- `evaluation/narrative_scores.csv`: evaluator scoring by condition.
- `evaluation/final_v2_report.md`: final interpretation and next-run recommendation.
- `evaluation_report_agent/report_agent_manifest.csv`: ReportAgent artifact-only status table.

## Rebuild Summaries

From repo root:

```powershell
python backtesting/case-a-s2-positional-noise/evaluation/summarize_condition_artifacts.py `
  --runs-root runs/s2_issue19_v2 `
  --run-map backtesting/case-a-s2-positional-noise-v2/run_map_v2.yaml `
  --output-dir backtesting/case-a-s2-positional-noise-v2/evaluation/condition_summaries `
  --metrics-csv backtesting/case-a-s2-positional-noise-v2/evaluation/condition_summary_metrics.csv `
  --metrics-json backtesting/case-a-s2-positional-noise-v2/evaluation/condition_summary_metrics.json
```

## Rebuild Narrative Scores From Raw

Use this when raw evaluator outputs already exist and you do not want to spend API credits:

```powershell
cd backend
uv run --frozen python ../backtesting/case-a-s2-positional-noise/evaluation/score_narratives.py `
  --from-raw `
  --summary-dir backtesting/case-a-s2-positional-noise-v2/evaluation/condition_summaries `
  --output-csv backtesting/case-a-s2-positional-noise-v2/evaluation/narrative_scores.csv `
  --output-md backtesting/case-a-s2-positional-noise-v2/evaluation/narrative_scores.md `
  --raw-dir backtesting/case-a-s2-positional-noise-v2/evaluation/narrative_score_raw `
  --conditions v2-baseline-control,v2-signal-strong-mid,v2-signal-weak-mid,v2-counter-colombia-mid,v2-noise-near-mid,v2-noise-off-mid `
  --baseline-condition v2-baseline-control
```

## Current Finding

The richer variable documents produce more interpretable variation than V1:

- strong Argentina signal shifts confidently to Argentina;
- weak Argentina signal shifts to Argentina with lower confidence;
- Colombia counter-signal can flip the predicted winner at low confidence;
- near-topic noise creates medium contamination;
- off-topic noise is mostly ignored.

The main caveat is that simulated agents can generate unsupported numeric claims during discussion. Future scoring should track those as a separate hallucination/unsupported-claim category.

## DeepInfra Extension

The V2 matrix was also run with the two remaining S2 DeepInfra models:

- `google/gemma-3-27b-it`
- `meta-llama/Llama-3.3-70B-Instruct-Turbo`

Artifacts:

- `runs/s2_issue19_deepinfra/`
- `evaluation_deepinfra/final_deepinfra_report.md`
- `evaluation_deepinfra/combined_deepinfra_scores.csv`

## ReportAgent Follow-Up

The V2 summaries, metrics, and narrative scores were also rendered through ReportAgent in artifact-only mode. This avoids shared graph/tool state by giving ReportAgent one condition-specific evidence bundle at a time.

Run from `backend/`:

```powershell
uv run --frozen python ../backtesting/case-a-s2-positional-noise-v2/evaluation_report_agent/run_report_agent_from_artifacts.py --models qwen,gemma,llama
```

Outputs:

- `evaluation_report_agent/report_agent_manifest.csv`
- `evaluation_report_agent/qwen/*/full_report.md`
- `evaluation_report_agent/gemma/*/full_report.md`
- `evaluation_report_agent/llama/*/full_report.md`
