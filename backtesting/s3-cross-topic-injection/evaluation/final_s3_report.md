# Final S3 Report - Cross-Topic Scheduled Injection

Date: 2026-06-18

## Scope

S3 extends the S2 Issue 19 scheduled-injection design from one football case to three prediction topics:

- football: Argentina vs Colombia, Copa America 2024 final;
- bolivia: Bolivia 2025 presidential runoff;
- ipc: Argentina IPC 2025 forecast.

Models:

- DeepInfra `google/gemma-3-27b-it`;
- DeepInfra `meta-llama/Llama-3.3-70B-Instruct-Turbo`.

Conditions per topic/model:

- `baseline-control`;
- `signal-early`;
- `signal-mid`;
- `signal-late`;
- `counter-signal-mid`;
- `noise-near-mid`;
- `noise-off-mid`.

Full matrix size: 42 runs.

## Technical Result

All 42 rows are technically valid.

- 6/6 baselines fired zero scheduled events.
- 36/36 injected conditions fired exactly one scheduled event.
- Each topic/model pair reused one prepared simulation across its seven conditions.
- Raw `runs/` outputs remain local and uncommitted.
- Committed evidence is in `evaluation/full_summary.*`, `evaluation/condition_summary_metrics.*`, and `RUN_LEDGER.csv`.

Important runtime note: DeepInfra/OASIS runs can leave backend progress counters at zero even when the run is complete. This report treats `run_manifest.json`, `reddit_simulation.db`, `simulation.log`, and `scheduled_events_fired.jsonl` as the technical audit surface.

## Design Notes

Graphiti extraction uses Gemma for both Gemma and Llama rows. The simulation LLM still uses the row model. This avoids a Llama schema failure observed during graph construction, where Graphiti expected `extracted_entities` and received `entities`.

IPC scoring uses `topics/ipc/ground_truth_decision.md`; PR #22 has conflicting ground-truth artifacts, and the richer answer-key markdown is treated as canonical for S3.

## Deterministic Metrics

The deterministic metrics in `condition_summary_metrics.*` count Reddit post/comment keywords. They are useful for directional pressure and contamination checks, but they are not a semantic ReportAgent judgment.

### Football

Gemma stayed Argentina across all seven conditions. Llama stayed Argentina except `counter-signal-mid`, where the heuristic flips to Colombia. Noise conditions introduced expected noise terms but did not flip the heuristic prediction.

### Bolivia

Signal conditions shift toward Paz for both models. Counter-signal flips both models to Quiroga. Near/off noise is mixed: Gemma remains unclear for both noise controls; Llama moves to Quiroga on near-topic noise and unclear on off-topic noise.

### IPC

Both models mostly stay on the lower/disinflation side. Counter-signal weakens that: Gemma becomes unclear and Llama flips to higher/rebound. Off-topic noise registers as noise but does not flip the heuristic prediction.

## Artifacts

- `matrix.yaml`: V3 design and model/provider metadata.
- `RUN_LEDGER.csv`: run attempts and final valid rows.
- `evaluation/smoke_summary.*`: 12-row smoke result, all valid.
- `evaluation/full_summary.*`: 42-row technical result, all valid.
- `evaluation/condition_summary_metrics.*`: deterministic keyword/axis metrics.
- `evaluation/results_analysis.md`: detailed interpretation and S2/V2 comparison.
- `scripts/run_s3_matrix.py`: resumable runner with prepared-simulation reuse.
- `scripts/summarize_s3_smoke.py`: smoke/full technical summarizer.
- `scripts/extract_s3_metrics.py`: deterministic metrics extractor.

## Remaining Optional Work

Artifact-only ReportAgent scoring can be added later for semantic interpretation. It should read only committed summaries plus local run artifacts for one condition at a time, with no shared graph/Zep state.
