# S3 Condition Summary Metrics

These deterministic metrics are extracted from local Reddit SQLite artifacts. They are not a ReportAgent/narrative judgment.

| topic | model | condition | valid | events | axis A | A mentions | axis B | B mentions | heuristic | noise | posts | comments | traces |
|---|---|---|---:|---:|---|---:|---|---:|---|---:|---:|---:|---:|
| football | gemma | baseline-control | True | 0/0 | Argentina | 12 | Colombia | 6 | Argentina | 0 | 7 | 2 | 31 |
| football | gemma | signal-early | True | 1/1 | Argentina | 17 | Colombia | 5 | Argentina | 0 | 9 | 2 | 31 |
| football | gemma | signal-mid | True | 1/1 | Argentina | 16 | Colombia | 3 | Argentina | 0 | 8 | 2 | 30 |
| football | gemma | signal-late | True | 1/1 | Argentina | 13 | Colombia | 4 | Argentina | 0 | 7 | 3 | 34 |
| football | gemma | counter-signal-mid | True | 1/1 | Argentina | 10 | Colombia | 9 | Argentina | 0 | 8 | 1 | 33 |
| football | gemma | noise-near-mid | True | 1/1 | Argentina | 10 | Colombia | 3 | Argentina | 2 | 10 | 1 | 34 |
| football | gemma | noise-off-mid | True | 1/1 | Argentina | 8 | Colombia | 4 | Argentina | 4 | 8 | 2 | 35 |
| football | llama | baseline-control | True | 0/0 | Argentina | 11 | Colombia | 6 | Argentina | 0 | 5 | 3 | 20 |
| football | llama | signal-early | True | 1/1 | Argentina | 19 | Colombia | 8 | Argentina | 0 | 5 | 5 | 27 |
| football | llama | signal-mid | True | 1/1 | Argentina | 11 | Colombia | 5 | Argentina | 0 | 5 | 2 | 19 |
| football | llama | signal-late | True | 1/1 | Argentina | 20 | Colombia | 4 | Argentina | 0 | 5 | 4 | 20 |
| football | llama | counter-signal-mid | True | 1/1 | Argentina | 14 | Colombia | 15 | Colombia | 0 | 5 | 4 | 20 |
| football | llama | noise-near-mid | True | 1/1 | Argentina | 14 | Colombia | 10 | Argentina | 2 | 6 | 4 | 20 |
| football | llama | noise-off-mid | True | 1/1 | Argentina | 8 | Colombia | 5 | Argentina | 4 | 5 | 3 | 16 |
| bolivia | gemma | baseline-control | True | 0/0 | Paz | 2 | Quiroga | 2 | Unclear | 0 | 6 | 6 | 33 |
| bolivia | gemma | signal-early | True | 1/1 | Paz | 8 | Quiroga | 2 | Paz | 0 | 6 | 2 | 28 |
| bolivia | gemma | signal-mid | True | 1/1 | Paz | 8 | Quiroga | 2 | Paz | 0 | 6 | 5 | 34 |
| bolivia | gemma | signal-late | True | 1/1 | Paz | 8 | Quiroga | 2 | Paz | 0 | 9 | 4 | 43 |
| bolivia | gemma | counter-signal-mid | True | 1/1 | Paz | 2 | Quiroga | 10 | Quiroga | 0 | 5 | 1 | 20 |
| bolivia | gemma | noise-near-mid | True | 1/1 | Paz | 2 | Quiroga | 2 | Unclear | 2 | 6 | 3 | 31 |
| bolivia | gemma | noise-off-mid | True | 1/1 | Paz | 2 | Quiroga | 2 | Unclear | 3 | 6 | 6 | 29 |
| bolivia | llama | baseline-control | True | 0/0 | Paz | 4 | Quiroga | 2 | Paz | 0 | 3 | 3 | 18 |
| bolivia | llama | signal-early | True | 1/1 | Paz | 8 | Quiroga | 2 | Paz | 0 | 4 | 3 | 23 |
| bolivia | llama | signal-mid | True | 1/1 | Paz | 10 | Quiroga | 2 | Paz | 0 | 5 | 3 | 23 |
| bolivia | llama | signal-late | True | 1/1 | Paz | 12 | Quiroga | 2 | Paz | 0 | 4 | 5 | 22 |
| bolivia | llama | counter-signal-mid | True | 1/1 | Paz | 2 | Quiroga | 10 | Quiroga | 0 | 5 | 4 | 26 |
| bolivia | llama | noise-near-mid | True | 1/1 | Paz | 2 | Quiroga | 6 | Quiroga | 2 | 7 | 6 | 31 |
| bolivia | llama | noise-off-mid | True | 1/1 | Paz | 2 | Quiroga | 2 | Unclear | 3 | 4 | 3 | 23 |
| ipc | gemma | baseline-control | True | 0/0 | Lower/disinflation | 5 | Higher/rebound | 0 | Lower/disinflation | 0 | 3 | 1 | 6 |
| ipc | gemma | signal-early | True | 1/1 | Lower/disinflation | 8 | Higher/rebound | 0 | Lower/disinflation | 0 | 4 | 0 | 5 |
| ipc | gemma | signal-mid | True | 1/1 | Lower/disinflation | 12 | Higher/rebound | 0 | Lower/disinflation | 0 | 4 | 4 | 10 |
| ipc | gemma | signal-late | True | 1/1 | Lower/disinflation | 9 | Higher/rebound | 0 | Lower/disinflation | 0 | 4 | 2 | 12 |
| ipc | gemma | counter-signal-mid | True | 1/1 | Lower/disinflation | 5 | Higher/rebound | 5 | Unclear | 0 | 4 | 0 | 5 |
| ipc | gemma | noise-near-mid | True | 1/1 | Lower/disinflation | 6 | Higher/rebound | 0 | Lower/disinflation | 0 | 4 | 2 | 10 |
| ipc | gemma | noise-off-mid | True | 1/1 | Lower/disinflation | 6 | Higher/rebound | 0 | Lower/disinflation | 5 | 4 | 3 | 13 |
| ipc | llama | baseline-control | True | 0/0 | Lower/disinflation | 1 | Higher/rebound | 0 | Lower/disinflation | 0 | 2 | 1 | 5 |
| ipc | llama | signal-early | True | 1/1 | Lower/disinflation | 6 | Higher/rebound | 0 | Lower/disinflation | 0 | 3 | 2 | 10 |
| ipc | llama | signal-mid | True | 1/1 | Lower/disinflation | 6 | Higher/rebound | 0 | Lower/disinflation | 0 | 3 | 2 | 10 |
| ipc | llama | signal-late | True | 1/1 | Lower/disinflation | 5 | Higher/rebound | 0 | Lower/disinflation | 0 | 3 | 1 | 6 |
| ipc | llama | counter-signal-mid | True | 1/1 | Lower/disinflation | 2 | Higher/rebound | 5 | Higher/rebound | 0 | 3 | 0 | 4 |
| ipc | llama | noise-near-mid | True | 1/1 | Lower/disinflation | 1 | Higher/rebound | 0 | Lower/disinflation | 0 | 3 | 1 | 6 |
| ipc | llama | noise-off-mid | True | 1/1 | Lower/disinflation | 1 | Higher/rebound | 0 | Lower/disinflation | 5 | 3 | 1 | 8 |

Caveat: the heuristic counts injected documents themselves when they are posted. Use it to audit directional pressure and contamination, not as a final semantic evaluator.
