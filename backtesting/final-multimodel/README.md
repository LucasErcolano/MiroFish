# Final Multimodel Baseline

This directory contains the final multimodel research layer built on top of `origin/backtesting-baseline`.

Scope:

- Temporal optimum cross-model validation for Llama and Qwen.
- S3 scheduled-injection Qwen extension for Bolivia and IPC.
- Line 5 Bolivia depth check for Gemma and Qwen on R10-D2 and R80-D2.

Durable state:

- `AGENT_STATE.md`: current run context and resume point.
- `RUN_LEDGER.csv`: append-only run ledger.
- `evaluation/`: generated summaries and final report.

Committed result index:

- `evaluation/final_multimodel_report.md`: consolidated interpretation and caveats.
- `evaluation/s3_qwen_bolivia_ipc_full_summary.{csv,json,md}`: Qwen S3 scheduled-injection extension for Bolivia and IPC.
- `evaluation/temporal_optimum_summary.{csv,json,md}`: Llama and Qwen cross-model validation at the selected temporal optimum for each case.
- `evaluation/line5_bolivia_summary.{csv,json,md}`: Bolivia Line 5 depth/density check for Gemma and Qwen.

Raw local evidence:

- `runs/s3_cross_topic/`
- `runs/final_multimodel/raw_temporal/`
- `runs/final_multimodel/raw_line5/`

The `runs/` tree is intentionally not committed. Committed evidence is limited to summaries, reports, run notes, generated configs, and evaluator JSON.

No pull request should be created from this work unless explicitly requested later.
