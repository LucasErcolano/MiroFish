# Issue #33 Context - Market Baseline Benchmark

Source issue: https://github.com/LucasErcolano/MiroFish/issues/33

Status read on 2026-06-22: assigned to `BrunoDC-dev`, open, label `type:spike`.

Note: GitHub was not reachable from the current sandbox when this note was created, so this file preserves the issue context previously fetched from GitHub during this thread.

## Goal

Build a benchmark that compares MiroFish predictions against market-implied probabilities available at each cutoff, instead of comparing only against a naive 50/50 baseline or only against ground truth.

Primary idea:

- For each benchmark question, identify the best available market/proxy at cutoff `x`.
- Convert that market signal into an implied probability.
- Compare MiroFish probability against market probability and final ground truth.
- Main metric: `Brier(MiroFish) - Brier(Market)`.
- If delta is negative, MiroFish improves over the market; if positive, it underperforms.

The issue explicitly says not to pre-assign the market source per question during planning. Choosing the correct market/proxy is part of Phase 2.

## Branch / Work Scope

Original issue plan mentions:

- Target branch: `backtesting-baseline`.
- Suggested implementation branch: `feat/market-baseline-bench`.

Current local branch at time of this note:

- `feat/line5-llama-bolivia-copa-results`.

Before implementation, decide whether to:

1. branch from `backtesting-baseline` if available locally/remotely, or
2. branch from the current backtesting branch if the goal is to reuse the latest generated outputs.

Do not touch backend/frontend simulation logic for this spike unless a parser needs a tiny helper. This benchmark should mostly read existing artifacts.

## Available MiroFish Result Groups

The issue identified these candidate groups:

| # | Case | Path | Question type | Cutoff |
|---|---|---|---|---|
| 1 | Copa America 2024 final | `backtesting/case-a/` | binary winner | 2024-07-13 23:59 UTC |
| 2 | Bolivia 2025 runoff T0-T3 | `backtesting/case-b-s2-bolivia-2025-runoff/` | 3-way + margin | T0-T3 |
| 3 | BTC ETF Jan 2024 | `cases/CASE-B1-BTC-ETF-JAN2024/` | BTC price/direction deltas | 2024-01-09 |
| 4 | ARG IPC 2025 | `cases/CASE-B2-ARG-IPC-2025/` | monthly IPC deltas | 2025-01-31 |
| 5 | ARG Q1 2025 pilot | `cases/PILOT-ARG-2025-Q1/` | vote share + inflation scenarios | 2025-01-31 |
| 6 | S2 positional noise | `backtesting/case-a-s2-positional-noise*/` | binary, same base as Copa | 2024-07-13 23:59 UTC |
| 7 | S2 Bolivia Line5 slim | `backtesting/case-b-s2-bolivia-2025-runoff/output_llama_line5_slim/` | Bolivia T3 slim variants | 2025-08 approx |
| 8 | S3 cross-topic injection | `backtesting/s3-cross-topic-injection/` | internal robustness topics | N/A |

Local outputs already known from recent work:

- Bolivia temporal T0-T3 matrix: `backtesting/S2_TEMPORAL_RESULTS_MATRIX.md`.
- IPC temporal T0-T3 outputs:
  - `backtesting/case-c-s2-arg-ipc-line5-gemma/output/gemma_T0_R40_D2/`
  - `backtesting/case-c-s2-arg-ipc-line5-gemma/output/gemma_T1_R40_D2/`
  - `backtesting/case-c-s2-arg-ipc-line5-gemma/output/gemma_T2_R40_D2/`
  - `backtesting/case-c-s2-arg-ipc-line5-gemma/output/gemma_T3_R40_D2/`
- Copa temporal T0-T3 outputs:
  - `backtesting/case-d-s2-copa-america-line5-gemma/output/gemma_T0_R40_D2/`
  - `backtesting/case-d-s2-copa-america-line5-gemma/output/gemma_T1_R40_D2/`
  - `backtesting/case-d-s2-copa-america-line5-gemma/output/gemma_T2_R40_D2/`
  - `backtesting/case-d-s2-copa-america-line5-gemma/output/gemma_T3_R40_D2/`
- Bolivia/Copa Line5 Llama slim outputs:
  - `backtesting/case-b-s2-bolivia-2025-runoff/output_llama_line5_slim/`
  - `backtesting/case-d-s2-copa-america-line5-gemma/output_llama_line5_slim/`
- Summary of Line5 Llama slim results:
  - `backtesting/LINE5_LLAMA_BOLIVIA_COPA.md`.

## Methodology Fixed by the Issue

Use these as defaults unless the user changes scope:

- Primary metric: Brier score per question.
- Main comparison: `delta_brier = brier_mirofish - brier_market`.
- Secondary metric: log-loss.
- Tertiary metric: directional agreement / same side.
- Odds timestamp: cutoff day at 23:59 UTC, or closest available snapshot if exact timestamp is unavailable.
- Market probability should be normalized to the same event contract as the MiroFish answer.
- If no reasonable market exists within the accepted window, mark `NONE_AVAILABLE`; do not invent odds.
- If using a proxy, mark it explicitly, e.g. `PROXY_SURVEY`, `PROXY_ODDS`, `PROXY_EXPECTATIONS`, etc.
- Separate liquid markets from proxies in the final report.

## Proposed Directory

All new benchmark work should live under:

```text
backtesting/benchmarks/market_baseline/
```

Expected files from the issue plan:

```text
README.md
OBJECTIVE.md
SCHEMA.md
NON_COMPARABLE.md
market_research_plan.md
mirofish_predictions.csv
market_odds.csv
metrics_per_question.csv
MARKET_BASELINE_REPORT.md
VALIDATION.md
_inventory.txt
market_odds/
scripts/
  extract_mirofish_predictions.py
  build_market_odds_csv.py
  normalize.py
  compute_metrics.py
  build_report.py
tests/
  test_normalize.py
```

## Phase 1 - Consolidate MiroFish Outputs

Output: `mirofish_predictions.csv`.

Tasks:

1. Inventory available outputs:

```bash
find backtesting cases \
  \( -name 'eval_result.json' -o -name 'structured_answer.json' -o -name 'verdict.json' -o -name 'verdict_raw.json' -o -name 'evaluation.md' -o -name 'first_eval.md' \) \
  | sort
```

2. Define canonical schema in `SCHEMA.md`.
3. Implement `scripts/extract_mirofish_predictions.py`.
4. Generate and manually check `mirofish_predictions.csv`.
5. Mark internal/noisy variants in `NON_COMPARABLE.md`.

Important caveat:

- S2/S3 variants are often internal robustness tests. They may share the same market baseline as the base question, but should not necessarily count as independent market benchmark questions.

## Phase 2 - Research Market Odds

Output: `market_research_plan.md`, `market_odds/*.json`, `market_odds.csv`.

For each comparable question, decide:

- best market/proxy type;
- why that source is appropriate;
- alternatives considered and rejected;
- quality flag: `HIGH`, `MEDIUM`, `LOW`, `UNAVAILABLE`.

Possible source types:

- prediction market exchange;
- betting odds / sportsbook;
- financial derivative or traded instrument;
- survey/expectations proxy;
- none available.

Gate:

- Stop after Phase 2 and let the user review sources before computing final metrics.

## Phase 3 - Compute Metrics and Report

Output:

- `metrics_per_question.csv`
- `MARKET_BASELINE_REPORT.md`
- `VALIDATION.md`

Core functions:

- `brier(p_pred, p_real)`
- `log_loss(p_pred, p_real)`
- implied probability from decimal odds / market price / proxy survey
- range-to-point conversion for MiroFish ranges

Report sections:

1. Executive summary.
2. Per-question liquid-market table.
3. Per-question proxy table.
4. By-case aggregate.
5. By-horizon aggregate.
6. Internal robustness variants.
7. Caveats and unavailable markets.

## Recommended MVP

Because full market research can be large, start with a minimum viable set:

1. Copa America final base / T3.
2. Bolivia T3 or Line5 slim T3.
3. IPC Argentina T3.
4. BTC ETF one horizon.
5. Pilot ARG one headline target.

After validating the schema and metric pipeline on the MVP, expand to all comparable rows.

## Immediate Next Steps

1. Create or switch to the implementation branch.
2. Build Phase 1 inventory and schema.
3. Write extractor for the local outputs we already generated:
   - Bolivia temporal;
   - IPC temporal;
   - Copa temporal;
   - Bolivia/Copa Line5 slim.
4. Produce first `mirofish_predictions.csv`.
5. Review which rows are genuinely market-comparable before researching odds.

## Do Not Commit

Avoid committing local/private artifacts:

- `.env`
- `frontend/.env`
- `backend/uploads/`
- `backend/data/`
- `backend/logs/`
- `node_modules/`
- `__pycache__/`
- `Backtesting.pdf`
- `prueba-comedor.txt`

