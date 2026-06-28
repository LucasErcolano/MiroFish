# Bolivia Line 5 Final Multimodel Summary

Rows completed: 4/4

| model | variant | status | actual/target rounds | density | prediction | winner | mae | margin error | parse errors |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|
| gemma | gemma_T3_slim_R10_D2 | completed | 10/10 | 2 | quiroga_gana | 0 | 6.353 | 16.06 | 0 |
| gemma | gemma_T3_slim_R80_D2 | completed | 80/80 | 2 | quiroga_gana | 0 | None | None | 2 |
| qwen | qwen_T3_slim_R10_D2 | completed | 10/10 | 2 | quiroga_gana | 0 | 9.687 | 21.06 | 0 |
| qwen | qwen_T3_slim_R80_D2 | completed | 72/80 | 2 | quiroga_gana | 0 | 13.02 | 29.06 | 0 |

Notes:

- Uses `seed_T3_line5_slim.md`, matching the slim Llama Line 5 setup.
- Raw simulation artifacts are local under `runs/final_multimodel/raw_line5/`.
- Committed evidence keeps report, eval result, run notes, and generated simulation config.
- `qwen_T3_slim_R80_D2` is labelled by its target variant R80, but the backend-generated run completed at 72 actual rounds; this is preserved in `run_notes.md` and the CSV.
