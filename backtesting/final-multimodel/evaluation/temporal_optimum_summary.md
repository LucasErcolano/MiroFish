# Temporal Optimum Cross-Model Summary

Rows completed: 6/6

| topic | model | package | status | score | parse errors | rounds | key result |
|---|---|---|---:|---:|---:|---:|---|
| bolivia | llama | T1 | completed | 1/None | 0 | 40/40 | paz_gana mae=28.0 |
| bolivia | qwen | T1 | completed | 0/None | 0 | 40/40 | quiroga_gana mae=8.667 |
| copa | llama | T2 | completed | 5/5 | 0 | 40/40 | Argentina p=0.504 |
| copa | qwen | T2 | completed | 5/5 | 0 | 40/40 | Argentina p=0.504 |
| ipc | llama | T3 | completed | 0/5 | 5 | 40/40 | d1=None err=None |
| ipc | qwen | T3 | completed | 2/5 | 0 | 40/40 | d1=25.9 err=23.5 |

Notes:

- Raw simulation artifacts are local under `runs/final_multimodel/raw_temporal/`.
- Committed evidence keeps only report, structured answer when present, eval result, and run notes.
