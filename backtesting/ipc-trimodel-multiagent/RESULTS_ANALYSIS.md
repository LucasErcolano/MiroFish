# IPC Tri-Model Results Analysis

Last updated: 2026-06-28 15:10 America/Buenos_Aires.

## Scope

This run evaluates the IPC 2025 case with one MiroFish simulation using three
hosted model families in the same agent population:

- Qwen: `qwen/qwen3-8b` via OpenRouter.
- Gemma: `google/gemma-3-27b-it` via DeepInfra.
- Llama: `meta-llama/Llama-3.3-70B-Instruct-Turbo` via DeepInfra.

All canonical rows below passed the compact evidence gate:

- `model_routing_audit.jsonl` includes all three models.
- `llm_telemetry_summary.json` includes all three models.
- `experimental_memory_evidence.json` exists and reports memory artifacts.
- `structured_answer.json` was scored by `eval_objective.py`.
- S3 rows with injections fired exactly one scheduled event.

Raw evidence remains local under `runs/ipc_trimodel_multiagent/`. Committable
evidence is under `backtesting/ipc-trimodel-multiagent/evaluation/`.

## Temporal Line

Question: does the tri-model multi-agent setup reduce IPC error faster and more
stably as temporal packets add information from T0 to T3?

| Row | Score | Feb abs error | Dec abs error | Eval parse errors | LLM calls | Telemetry parse errors | Total tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| T0 R40-D2 | 1/5 | 0.4 | 8.2 | 0 | 78 | 12 | 1,917,733 |
| T1 R40-D2 | 1/5 | 0.1 | 0.65 | 0 | 116 | 9 | 2,777,867 |
| T2 R40-D2 | 2/5 | 0.1 | 0.3 | 0 | 115 | 7 | 2,964,385 |
| T3 R40-D2 | 2/5 | 0.1 | 0.65 | 0 | 167 | 4 | 4,195,688 |

Interpretation:

- The February point forecast improved immediately from T0 to T1
  (`0.4 -> 0.1` absolute error) and stayed stable through T3.
- The December forecast improved strongly once temporal evidence was added:
  T0 was far off (`8.2`), while T1/T2/T3 stayed near the answer key.
- T2 was the strongest temporal packet by score and December error. T3 added
  more tokens and more comments, but did not improve the objective score.
- Structured report evaluation had zero parse errors in every temporal row.
  Telemetry still recorded non-JSON action outputs, so the improvement is not
  "models never emit malformed JSON"; it is "the structured/report/eval path
  survives malformed intermediate actions."

Conclusion: temporal evidence helps, but the best IPC temporal point in this
run is T2, not necessarily the deepest T3 packet.

## Line 5 Depth

Question: does more discussion depth help IPC precision, and can a shallower
multi-agent row justify itself economically versus deeper single-agent baselines?

| Row | Score | Feb abs error | Dec abs error | Eval parse errors | LLM calls | Telemetry errors | Telemetry parse errors | Total tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| T3 R10-D2 | 3/5 | 0.1 | 0.7 | 0 | 13 | 0 | 2 | 50,231 |
| T3 R20-D2 | 2/5 | 0.1 | 22.2 | 0 | 101 | 0 | 12 | 1,101,055 |
| T3 R40-D2 | 2/5 | 0.1 | 22.2 | 0 | 191 | 0 | 20 | 3,764,018 |
| T3 R80-D2 | 1/5 | 0.1 | 0.65 | 0 | 174 | 11 | 39 | 5,546,655 |

Interpretation:

- Depth was not monotonic. R10 was the best objective row in this trimodel
  line despite being much cheaper.
- R20 and R40 preserved the February point forecast but collapsed badly on the
  December target.
- R80 spent the most tokens and produced the most telemetry problems
  (`11` errors, `39` parse errors). It did not improve objective score.
- This line does not by itself prove the economic claim that multi-agent R40
  beats a single-agent R80, because that requires the external single-agent
  R80 baseline table. What it does show is that for the tri-model setup, more
  rounds past R10 were not automatically better.

Conclusion: for IPC, "more rounds" is a weak lever. The strongest cost/quality
candidate in the tri-model depth line is R10, while R80 is expensive and noisy.

## S3 Noise And Signal Line

Question: is a tri-model consensus harder to mislead with injected signals or
irrelevant noise?

| Condition | Score | Feb abs error | Dec abs error | Eval parse errors | Events fired | LLM calls | Telemetry parse errors | Total tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline-control | 4/5 | 1.1 | 1.2 | 0 | 0 | 27 | 2 | 213,793 |
| signal-early | 0/5 | 2.8 | 3.7 | 0 | 1 | 39 | 6 | 340,493 |
| signal-mid | 2/5 | 1.2 | 0.7 | 0 | 1 | 35 | 10 | 291,433 |
| signal-late | 1/5 | 2.8 | 4.0 | 0 | 1 | 36 | 2 | 370,504 |
| counter-signal-mid | 0/5 | 2.8 | 9.0 | 0 | 1 | 26 | 0 | 277,444 |
| noise-near-mid | 1/5 | 1.1 | 2.7 | 0 | 1 | 38 | 0 | 295,532 |
| noise-off-mid | 0/5 | 2.8 | 4.0 | 0 | 1 | 37 | 7 | 315,491 |

Interpretation:

- Baseline-control was the best S3 row at `4/5`.
- Relevant signal timing mattered. `signal-mid` preserved the best December
  answer in S3 (`0.7` error), but early and late signal injections degraded the
  final score.
- The counter-signal was highly damaging (`0/5`, December error `9.0`).
- The two noise rows did not demonstrate robustness. `noise-near-mid` kept the
  February error equal to baseline (`1.1`) but lost score on other targets.
  `noise-off-mid` degraded both score and February error after a valid rerun.
- Every injected condition fired exactly one scheduled event, so the result is
  a real simulation response to the injection plan, not a missed-injection
  artifact.

Conclusion: this S3 run is a negative/nuanced result for the robustness
hypothesis. The tri-model consensus was not reliably harder to mislead; it was
sensitive to both counter-signals and irrelevant noise.

## Discarded Attempts

The runner intentionally records failed attempts in `RUN_LEDGER.csv`; these are
not canonical results.

- Initial S3 `baseline-control` failed post-run validation because Llama was
  missing from telemetry/routing evidence. The IPC context was then enriched
  and the model map anchored by early agent IDs plus roles.
- Initial S3 `noise-off-mid` finished an eval but failed post-run validation
  because Llama did not make any telemetry calls. It was rerun and the final
  completed row includes Qwen, Gemma, and Llama in telemetry.
- Initial low-depth Line5 attempts also caught the same class of issue:
  assigned routes are not enough; effective telemetry must prove all three
  models acted in the row.

## Bottom Line

The infrastructure objective was met: IPC can now be run as a hosted tri-model
multi-agent benchmark with experimental memory, Graphiti dedup bypass,
scheduled S3 injection, structured IPC reporting, and compact evidence gates.

The research outcome is mixed:

- Temporal evidence helps, especially by T1/T2.
- More depth is not automatically better; R10 was the best Line 5 trimodel row.
- Structured IPC output avoided final JSON parse collapse across all canonical
  rows.
- S3 did not support a strong robustness claim; injected signals and noise
  often degraded the consensus.
