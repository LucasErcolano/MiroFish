# S3 Lessons

- Do not conflate prepared-input backtests with real scheduled injection. S3 must use `event_config.scheduled_events` and audit fired events.
- Do not call an output DB "committed primary evidence" when `runs/` is local. Committed evidence should be summaries, metrics, configs, and reports.
- For Qwen-style JSON issues, avoid forced `response_format={"type":"json_object"}` when the model breaks; repair malformed JSON through the existing fixer if needed.
- Keep smoke small. The first useful run is 12 rows: 3 topics x 2 models x baseline/signal-mid.
- Baseline validity is technical: no scheduled events fired. Injection validity is technical: exactly one scheduled event fired.
- IPC must not be scored until the answer-key conflict is explicitly resolved or documented.
- Avoid re-running expensive rows that already have valid output unless the run is marked invalid.
- Pass `--no-wait-after-run` by default for S3 autonomous runs. Without it, OASIS can wait for IPC commands and never advance rounds.
- For DeepInfra/OASIS runs, `run_manifest.json` may report `num_rounds_or_epochs=0` while `simulation.log` and `reddit_simulation.db` prove the run completed. Audit DB/log plus scheduled event files.
- Do not use Llama as the Graphiti extraction model by default. It returned `entities` instead of Graphiti's expected `extracted_entities`; keep Graphiti on Gemma while Llama remains the simulation model.
