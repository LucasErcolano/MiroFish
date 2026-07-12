# S3 Smoke Summary

Rows valid: 12/12

Scope: 3 topics x 2 models x 2 conditions (`baseline-control`, `signal-mid`).

Technical validity requires a completed manifest, real MiroFish/OASIS evidence, and scheduled event count matching the condition.

| topic | model | condition | valid | events | posts | comments | traces | sim |
|---|---|---|---:|---:|---:|---:|---:|---|
| football | gemma | baseline-control | True | 0/0 | 7 | 2 | 31 | sim_0d64742b0523 |
| football | gemma | signal-mid | True | 1/1 | 8 | 2 | 30 | sim_0d64742b0523 |
| football | llama | baseline-control | True | 0/0 | 5 | 3 | 20 | sim_2903c2fffa71 |
| football | llama | signal-mid | True | 1/1 | 5 | 2 | 19 | sim_2903c2fffa71 |
| bolivia | gemma | baseline-control | True | 0/0 | 6 | 6 | 33 | sim_97ea1fdbe89c |
| bolivia | gemma | signal-mid | True | 1/1 | 6 | 5 | 34 | sim_97ea1fdbe89c |
| bolivia | llama | baseline-control | True | 0/0 | 3 | 3 | 18 | sim_3e3386657572 |
| bolivia | llama | signal-mid | True | 1/1 | 5 | 3 | 23 | sim_3e3386657572 |
| ipc | gemma | baseline-control | True | 0/0 | 3 | 1 | 6 | sim_d381ccba64dc |
| ipc | gemma | signal-mid | True | 1/1 | 4 | 4 | 10 | sim_d381ccba64dc |
| ipc | llama | baseline-control | True | 0/0 | 2 | 1 | 5 | sim_1e1dccf3fd15 |
| ipc | llama | signal-mid | True | 1/1 | 3 | 2 | 10 | sim_1e1dccf3fd15 |

Notes:

- `runs/` remains local and is not intended to be committed.
- Backend round counters can remain zero for DeepInfra/OASIS runs; the audit uses manifest status, DB counts, and `scheduled_events_fired.jsonl`.
- Llama rows use Llama for the simulation LLM and Gemma for Graphiti extraction, as declared in `matrix.yaml`.
