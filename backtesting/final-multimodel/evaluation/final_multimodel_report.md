# Final Multimodel Baseline Report

Date: 2026-06-24

Branch: `codex/final-multimodel-baseline`

Base: `origin/backtesting-baseline`

## Scope

This run closes the final multimodel research layer requested on top of the merged S2 baseline. It extends the existing football/Copa America work across the other S2 topics and models:

1. Temporal optimum cross-model validation:
   - Bolivia runoff: selected temporal package `T1`.
   - Copa America: selected temporal package `T2`.
   - Argentina IPC: selected temporal package `T3`.
   - Models: Llama and Qwen.
2. S3 scheduled injection:
   - Topics: Bolivia and IPC.
   - Model: Qwen.
   - Conditions: baseline-control, signal-early, signal-mid, signal-late, counter-signal-mid, noise-near-mid, noise-off-mid.
3. Line 5 depth/density:
   - Topic: Bolivia.
   - Models: Gemma and Qwen.
   - Variants: R10-D2 and R80-D2.

The prior S3 work already had Gemma/Llama coverage for the 3-topic x 2-model x 7-condition matrix. This branch adds the missing Qwen evidence for Bolivia and IPC, plus the temporal and Line 5 cross-model checks requested by the team.

## Models And Providers

| label | provider | model id | usage |
|---|---|---|---|
| gemma | DeepInfra | `google/gemma-3-27b-it` | Line 5 simulation and stable Graphiti extraction |
| llama | DeepInfra | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | Temporal optimum simulation |
| qwen | OpenRouter | `qwen/qwen3-8b` | Temporal optimum, S3 injection, and Line 5 simulation |

For Qwen S3 and Qwen Line 5, Graphiti extraction intentionally uses Gemma/DeepInfra instead of Qwen. The reason is operational: Qwen is useful as the simulation model, but it had already shown brittle behavior around structured JSON and extraction-style calls.

## Evidence Layout

Committed evidence:

- `backtesting/final-multimodel/evaluation/s3_qwen_bolivia_ipc_full_summary.{csv,json,md}`
- `backtesting/final-multimodel/evaluation/temporal_optimum_summary.{csv,json,md}`
- `backtesting/final-multimodel/evaluation/line5_bolivia_summary.{csv,json,md}`
- Per-row `report.md`, `eval_result.json`, `run_notes.md`, `simulation_config.json` where applicable.

Local reproducible evidence, intentionally not committed:

- `runs/s3_cross_topic/`
- `runs/final_multimodel/raw_temporal/`
- `runs/final_multimodel/raw_line5/`

## Result 1: Temporal Optimum Cross-Model

Summary file: `temporal_optimum_summary.csv`

| topic | optimum package | model | result |
|---|---|---|---|
| Bolivia | T1 | Llama | Winner correct: `paz_gana`; MAE 28.0; margin error 3.06 |
| Bolivia | T1 | Qwen | Winner wrong: `quiroga_gana`; MAE 8.667; margin error 7.94 |
| Copa America | T2 | Llama | Score 5/5; predicted `Argentina`; probability point 0.504 |
| Copa America | T2 | Qwen | Score 5/5; predicted `Argentina`; probability point 0.504 |
| IPC | T3 | Llama | Score 0/5; parse errors 5 |
| IPC | T3 | Qwen | Score 2/5; delta_1 prediction 25.9; delta_1 absolute error 23.5 |

Interpretation:

- Copa America is the most stable case. Both Llama and Qwen converge to the same correct winner at T2 with a 5/5 score.
- Bolivia remains model-sensitive. Llama gets the winner but with very poor vote-share MAE; Qwen has better numeric vote-share MAE but predicts the wrong winner. This means T1 is not a reliable cross-model optimum for the final answer quality, even if it was empirically selected by the prior temporal sweep.
- IPC remains hard. Qwen is materially more evaluable than Llama in this setup because it produced parseable structured content and scored 2/5, but its numerical error is still large.

## Result 2: S3 Qwen Injection For Bolivia And IPC

Summary file: `s3_qwen_bolivia_ipc_full_summary.csv`

| topic | rows | valid rows | baseline event check | injected event check |
|---|---:|---:|---:|---:|
| Bolivia | 7 | 7 | 0/0 | 6 rows at 1/1 |
| IPC | 7 | 7 | 0/0 | 6 rows at 1/1 |
| Total | 14 | 14 | 2 rows at 0/0 | 12 rows at 1/1 |

Interpretation:

- The scheduled-injection mechanism is technically valid for Qwen on Bolivia and IPC.
- The control rows have no fired scheduled events.
- Every injected condition fires exactly one scheduled event.
- The evidence is real MiroFish/OASIS output: each row has a completed manifest, posts/comments/traces, and `scheduled_events_fired.jsonl` evidence.

This S3 line mainly validates instrumentation and experimental control. It should not be read as a final model-quality claim by itself because the summary checks event delivery and evidence provenance, not forecast accuracy.

## Result 3: Line 5 Bolivia Depth/Density

Summary file: `line5_bolivia_summary.csv`

| model | variant | actual/target rounds | prediction | winner score | MAE | margin error | parse errors |
|---|---|---:|---|---:|---:|---:|---:|
| Gemma | R10-D2 | 10/10 | `quiroga_gana` | 0 | 6.353 | 16.06 | 0 |
| Gemma | R80-D2 | 80/80 | `quiroga_gana` | 0 | null | null | 2 |
| Qwen | R10-D2 | 10/10 | `quiroga_gana` | 0 | 9.687 | 21.06 | 0 |
| Qwen | R80-D2 | 72/80 | `quiroga_gana` | 0 | 13.02 | 29.06 | 0 |

Interpretation:

- More depth does not solve Bolivia. Every Gemma/Qwen Line 5 row predicts `quiroga_gana`, while the ground truth is `paz_gana`.
- R80 is not better than R10 in the available evidence. Gemma R80 becomes less parseable, and Qwen R80 has worse MAE and margin error than Qwen R10.
- The Qwen R80 row is labelled by its target variant, but the backend-generated simulation completed at 72 actual rounds. The committed CSV and run notes preserve this caveat.

## Comparison To The Prior V2/S2 Work

- Prior football/Copa America V2 evidence already suggested this topic was robust to variants. The new temporal run supports that: Llama and Qwen both hit 5/5 at T2.
- Prior S3 Gemma/Llama coverage had already validated the 7-condition injection design for all three topics. The new Qwen rows extend that technical validation to the missing Bolivia and IPC model/topic pairs.
- Bolivia continues to be the weakest topic. The new temporal and Line 5 runs both show contradictory or incorrect model behavior. Cross-model agreement should not be used as the main success criterion here.
- IPC improves when Qwen is used compared with Llama in the temporal optimum row, mainly because Qwen yields parseable output. It still does not produce an accurate forecast.

## Implementation Notes

The branch includes a few backend/backtesting fixes needed to make the research reproducible:

- Scheduled-event execution is wired through headless runs into the round loop.
- Qwen profile/config generation avoids forced `response_format={"type":"json_object"}` and keeps the existing JSON repair path.
- Graphiti extraction can use a stable model/key/base URL that differs from the simulation model.
- `uv` is pinned to Python 3.11 for backend starts, avoiding the known `camel-oasis` / `neo4j` resolver conflict under Python 3.12.
- `graphiti-core` lockfile consistency and `neo4j==5.23.0` override are preserved for `camel-oasis==0.2.5`.

## Caveats

- ReportAgent `interview_agents` calls occasionally timed out. The runner uses a bounded timeout and reports continued to completion.
- Copa America structured eval has a `winner_range_width_valid=false` field, but the existing evaluator still awards 5/5 because the core winner/probability/evidence checks pass.
- Qwen remains brittle around strict JSON constraints. This branch handles it by not forcing strict JSON response format for Qwen generation paths and by normalizing double-encoded JSON where needed.
- The committed artifacts are enough to review conclusions, but the full databases and backend logs remain local under `runs/`.

## Conclusion

The requested final multimodel extension is covered:

- Temporal optimum: 6/6 rows completed.
- S3 Qwen Bolivia/IPC injection: 14/14 rows valid.
- Bolivia Line 5 Gemma/Qwen: 4/4 rows completed.

Substantively, the evidence supports three different conclusions by topic:

- Copa America is robust and converges across models at T2.
- IPC is technically evaluable with Qwen but still inaccurate.
- Bolivia remains unstable; more rounds or density did not improve the answer and cross-model behavior is contradictory.
