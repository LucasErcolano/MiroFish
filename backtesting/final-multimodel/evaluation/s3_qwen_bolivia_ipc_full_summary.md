# S3 Full Matrix Summary

Rows valid: 14/14

Scope: the full S3 matrix schema is 3 topics x 3 models x 7 conditions. This run filters to topics `bolivia,ipc` and model `qwen`, for 14 executed rows.

Technical validity requires a completed manifest, real MiroFish/OASIS evidence, and scheduled event count matching the condition.

| topic | model | condition | valid | events | posts | comments | traces | sim |
|---|---|---|---:|---:|---:|---:|---:|---|
| bolivia | qwen | baseline-control | True | 0/0 | 2 | 2 | 8 | sim_337e5cb85369 |
| bolivia | qwen | signal-early | True | 1/1 | 5 | 1 | 9 | sim_58a7ec2d73ea |
| bolivia | qwen | signal-mid | True | 1/1 | 10 | 2 | 21 | sim_58a7ec2d73ea |
| bolivia | qwen | signal-late | True | 1/1 | 7 | 1 | 13 | sim_58a7ec2d73ea |
| bolivia | qwen | counter-signal-mid | True | 1/1 | 6 | 1 | 11 | sim_58a7ec2d73ea |
| bolivia | qwen | noise-near-mid | True | 1/1 | 6 | 3 | 15 | sim_58a7ec2d73ea |
| bolivia | qwen | noise-off-mid | True | 1/1 | 7 | 1 | 13 | sim_58a7ec2d73ea |
| ipc | qwen | baseline-control | True | 0/0 | 4 | 1 | 7 | sim_0840565dbdd7 |
| ipc | qwen | signal-early | True | 1/1 | 5 | 1 | 8 | sim_0840565dbdd7 |
| ipc | qwen | signal-mid | True | 1/1 | 5 | 1 | 8 | sim_0840565dbdd7 |
| ipc | qwen | signal-late | True | 1/1 | 5 | 1 | 8 | sim_0840565dbdd7 |
| ipc | qwen | counter-signal-mid | True | 1/1 | 5 | 2 | 10 | sim_0840565dbdd7 |
| ipc | qwen | noise-near-mid | True | 1/1 | 6 | 1 | 10 | sim_0840565dbdd7 |
| ipc | qwen | noise-off-mid | True | 1/1 | 5 | 5 | 16 | sim_0840565dbdd7 |

Notes:

- `runs/` remains local and is not intended to be committed.
- Backend round counters can remain zero for DeepInfra/OASIS runs; the audit uses manifest status, DB counts, and `scheduled_events_fired.jsonl`.
- Qwen rows use `qwen/qwen3-8b` through OpenRouter for simulation and `google/gemma-3-27b-it` through DeepInfra for Graphiti extraction, as declared in `matrix.yaml`.
