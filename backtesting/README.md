# Backtesting research artefacts

This directory contains the S1/S2/S3 backtesting cases, evaluation
artefacts, and supporting configuration for the MiroFish research
project. It is a snapshot of the seven source PRs (#15, #16, #22, #24,
#25, #26, #29) collected into a single research branch.

## Index of cases

| Case | Topic | Source PR | Description |
|---|---|---|---|
| `case-a/` | Copa America 2024 final (ARG vs COL) | #15 | Simple self-verifiable event. Argentina won 1-0 (extra time). |
| `case-a-s2-positional-noise/` | Same case, V1 | #25 → #26 | Tests sensitivity to where the ground-truth evidence is placed in the input. |
| `case-a-s2-positional-noise-v2/` | Same case, V2 | #25 → #26 | V2 with 6 conditions: baseline, signal-early/mid/late, counter-signal-mid, noise-near/off-mid. |
| `case-b-s2-bolivia-2025-runoff/` | Bolivia 2025 presidential runoff | #24 → #29 | Temporal backtest: 4 evidence packages T0..T3, then evaluated after cutoff. Slim Llama line-5 results. |
| `case-c-s2-arg-ipc-line5-gemma/` | Argentina 2025 IPC forecast | #24 | Line-5 simulation with Gemma. |
| `case-d-s2-copa-america-line5-gemma/` | Copa America 2024 | #24 | Line-5 simulation with Gemma. |
| `case-b/` (via `cases/CASE-B1/2`) | BTC-ETF approval (Jan 2024) + ARG IPC 2025 | #22 → #29 | Quantitative backtesting cases. S1 backtest. |
| `s3-cross-topic-injection/` | 3 topics × 2 models × 7 conditions | #26 | S3 cross-topic scheduled injection benchmark. |

## Top-level files

- `OBJECTIVE.md` — overall research objective and methodology
- `LINE5_LLAMA_BOLIVIA_COPA.md` — final slim Llama line-5 results for Bolivia 2025 + Copa 2024
- `S2_TEMPORAL_RESULTS_MATRIX.md` — cross-case results matrix for S2

## Supporting files

- `configs/` — model and case configuration YAMLs
- `scripts/` — runbook and aggregation scripts (some executable)

## How to navigate

Each `case-*` directory typically contains:
- `README.md` — case description and methodology
- `question.md` — the prediction question
- `rubric.md` — evaluation rubric
- `input_pack_pre_x/` — input sources with manifest
- `answer_key_post_x/` — ground truth (post-cutoff)
- `evaluation/` — model outputs, summaries, scores
- `model_output_raw/` — raw API traces (request/response)

## Source PRs

- #15: `feat/issue-10-backtesting-case-a` (Closes #10)
- #16: `chore/pilot-arg-2025-q1-artifacts` (Closes #12)
- #22: `feat/case-b-backtesting` (Closes #11, Resolves #22)
- #24: `feat/issue-17-bolivia-runoff-backtesting-pr` (Closes #17)
- #25: `codex/s2-issue19-baseline` (Closes #19)
- #26: `codex/s3-cross-topic-injection` (DRAFT)
- #29: `feat/line5-llama-bolivia-copa-results` (Closes #28)

See also `../CHANGELOG-research.md` for what was NOT included and why.
