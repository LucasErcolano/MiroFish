# S3 Results Analysis - Cross-Topic Scheduled Injection

Date: 2026-06-18

## What Was Tested

S3 extends the S2 Issue 19 scheduled-injection experiment from one football case to three prediction topics:

- football: Argentina vs Colombia, Copa America 2024 final;
- bolivia: Bolivia 2025 presidential runoff;
- ipc: Argentina IPC 2025 forecast.

The full matrix contains:

- 3 topics;
- 2 DeepInfra simulation models: `google/gemma-3-27b-it` and `meta-llama/Llama-3.3-70B-Instruct-Turbo`;
- 7 conditions per topic/model pair.

The seven conditions were:

- `baseline-control`: no scheduled document;
- `signal-early`: pro-ground-truth signal injected early;
- `signal-mid`: pro-ground-truth signal injected mid-run;
- `signal-late`: pro-ground-truth signal injected late;
- `counter-signal-mid`: relevant contrary signal injected mid-run;
- `noise-near-mid`: plausible near-topic distractor injected mid-run;
- `noise-off-mid`: off-topic distractor injected mid-run.

Total full matrix size: 42 runs.

## Technical Validity

All 42 rows are technically valid.

| check | result |
|---|---:|
| Full matrix rows valid | 42/42 |
| Baselines with zero fired events | 6/6 |
| Injected rows with exactly one fired event | 36/36 |
| Topic/model pairs using prepared simulation reuse | 6/6 |

Technical validity was audited from the local MiroFish/OASIS artifacts: run manifests, SQLite artifacts, logs, and `scheduled_events_fired.jsonl`. Backend progress counters were not treated as authoritative because DeepInfra/OASIS runs can leave those counters at zero after a completed run.

## Directional Results

The deterministic scoring counts topic-axis keywords in posts/comments. It is useful for directional pressure and contamination checks, but it is not a semantic ReportAgent judgment.

### Football

Football reproduces the most important S2/V2 pattern.

| model | baseline | signal behavior | counter behavior | noise behavior |
|---|---|---|---|---|
| Gemma | Argentina, 12 vs 6 | stays Argentina, signal raises Argentina mentions | stays Argentina, but narrows to 10 vs 9 | stays Argentina; noise terms appear |
| Llama | Argentina, 11 vs 6 | stays Argentina | flips weakly to Colombia, 14 vs 15 | stays Argentina; noise terms appear |

Interpretation:

- Gemma is sticky toward Argentina, matching the S2/V2 DeepInfra finding.
- Llama is more sensitive to relevant counter-evidence and flips to Colombia under `counter-signal-mid`.
- Near-topic and off-topic noise introduce expected noise markers but do not flip the football heuristic.

### Bolivia

Bolivia is the cleanest cross-topic injection result.

| model | baseline | signal behavior | counter behavior | noise behavior |
|---|---|---|---|---|
| Gemma | unclear, 2 vs 2 | shifts to Paz, 8 vs 2 across early/mid/late | flips to Quiroga, 2 vs 10 | remains unclear under both noise controls |
| Llama | Paz, 4 vs 2 | reinforces Paz, up to 12 vs 2 | flips to Quiroga, 2 vs 10 | near-topic noise shifts to Quiroga; off-topic noise becomes unclear |

Interpretation:

- Both models respond strongly to pro-Paz signal injections.
- Both models respond strongly to the contrary Quiroga signal.
- Bolivia appears more vulnerable to near-topic noise than football or IPC, especially with Llama.

### IPC

IPC is stable toward the lower/disinflation side except under contrary evidence.

| model | baseline | signal behavior | counter behavior | noise behavior |
|---|---|---|---|---|
| Gemma | lower/disinflation, 5 vs 0 | reinforces lower/disinflation, up to 12 vs 0 | becomes unclear, 5 vs 5 | stays lower/disinflation |
| Llama | lower/disinflation, 1 vs 0 | reinforces lower/disinflation, up to 6 vs 0 | flips to higher/rebound, 2 vs 5 | stays lower/disinflation |

Interpretation:

- Signal injections reinforce the baseline lower/disinflation direction.
- Counter-signal weakens or reverses the result depending on model.
- Off-topic noise is detected by the keyword metric but does not flip the heuristic.

## Comparison With S2/V2

S2/V2 tested scheduled injection on one football case. V2 improved the design by using richer variable injected documents while keeping timing fixed at mid-run:

- baseline;
- strong Argentina signal;
- weak Argentina signal;
- Colombia counter-signal;
- near-topic noise;
- off-topic noise.

V2's strongest result was that richer injected content produced interpretable variation:

- strong/weak signal shifted toward Argentina;
- Colombia counter-signal could flip the result for Qwen and Llama;
- near-topic noise contaminated more than off-topic noise;
- Gemma remained more Argentina-biased.

S3 keeps the scheduled-injection idea but changes the research question from "does variable football content matter?" to "does the scheduled-injection effect transfer across topics and models?"

| aspect | S2/V2 | S3 |
|---|---|---|
| Topics | one football case | football, Bolivia, IPC |
| Models emphasized | Qwen, plus Gemma/Llama DeepInfra extension | Gemma and Llama |
| Conditions | 6, all mid-run | 7, including early/mid/late signal timing |
| Runs | 6 original V2, 12 DeepInfra extension | 42 full matrix |
| Scoring | deterministic summaries plus narrative scores and ReportAgent follow-up | deterministic keyword/axis metrics; ReportAgent still optional |
| Strongest finding | injected content changes football narratives | injection behavior transfers across topics, with topic/model-specific sensitivity |

## Main Conclusions

1. The scheduled-injection mechanism is robust.
   All baselines fired zero events, and every injected row fired exactly one scheduled event.

2. The S2/V2 football pattern mostly replicates.
   Llama remains sensitive to counter-evidence; Gemma remains more biased toward Argentina.

3. Cross-topic transfer is real but not uniform.
   Bolivia reacts strongly to both signal and counter-signal. IPC is more stable and only weakens or flips under direct contrary evidence.

4. Noise sensitivity is topic-dependent.
   Off-topic noise is generally ignored. Near-topic noise is more dangerous, especially in Bolivia.

5. S3 should be interpreted as a technical and directional benchmark, not a final semantic evaluation.
   The next optional step is artifact-only ReportAgent scoring, using one condition evidence bundle at a time and no shared graph/Zep state.

## Evidence Files

Committed evidence:

- `evaluation/full_summary.csv`
- `evaluation/full_summary.json`
- `evaluation/full_summary.md`
- `evaluation/condition_summary_metrics.csv`
- `evaluation/condition_summary_metrics.json`
- `evaluation/condition_summary_metrics.md`
- `evaluation/final_s3_report.md`
- `RUN_LEDGER.csv`

Local reproducibility evidence:

- `runs/s3_cross_topic/*/run_manifest.json`
- `runs/s3_cross_topic/*/simulation_artifacts/reddit_simulation.db`
- `runs/s3_cross_topic/*/simulation_artifacts/scheduled_events_fired.jsonl`
- `runs/s3_cross_topic/*/simulation_artifacts/simulation.log`

The local `runs/` artifacts are intentionally not committed because they contain SQLite/log outputs.
