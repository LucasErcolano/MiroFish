# Issue Response: Bolivia 2025 Runoff Temporal Backtest

Implemented and ran a political-social S2 temporal backtesting case for the 2025 Bolivia presidential runoff. The case is designed to test whether MiroFish changes its forecast as new time-bounded evidence becomes available, without giving it the final result.

## Case Summary

- Case id: `bolivia_2025_runoff_s2`
- Event: Bolivia presidential runoff, October 19, 2025.
- Target question: predict who wins the runoff and estimate vote shares for the two competitive candidates plus other/blank/null.
- Ground truth, kept private from the input package: Rodrigo Paz defeated Jorge "Tuto" Quiroga.
- Operational ground truth used by the evaluator:
  - Rodrigo Paz: `54.53%`
  - Jorge "Tuto" Quiroga: `45.47%`
  - Otros / blanco / nulo: `0.00%`
  - Paz minus Quiroga margin: `9.06` points

The model was given only the temporal evidence package and `question.md`. It was not given `ground_truth_private.md`, `rubric.md`, `internal_notes.md`, `testing_protocol.md`, prior outputs, or evaluator code.

## What Changed In The Repo

- Added the case under `backtesting/case-b-s2-bolivia-2025-runoff/`.
- Curated neutral evidence sources under `input/`.
- Added temporal assembled packages:
  - `assembled_T0.md`
  - `assembled_T1.md`
  - `assembled_T2.md`
  - `assembled_T3.md`
- Added a structured `question.md` so the report must name the competitive candidates, choose one winner, estimate percentages, state a margin, justify the prediction, and list uncertainty.
- Added private ground truth and an objective evaluator.
- Saved completed run outputs for `T0`, `T1`, `T2`, and `T3`.
- Added `RESULTS.md` with the scored results.
- Added local robustness fixes required for the report flow to complete reliably.

## Temporal Design

The point of the case is not only whether the final answer is correct. The useful part is seeing how the forecast shifts when the information frontier moves forward.

| Package | Cutoff | Evidence Included | Intended Test |
| --- | --- | --- | --- |
| `T0` | `2025-08-16` | Sources `01-02`: pre-first-round context and polling context. | Can the model infer the eventual runoff field from weak early information? |
| `T1` | `2025-08-18` | Sources `01-04`: T0 plus first-round surprise and MAS collapse/runoff realignment. | Does the first-round shock correct the candidate set and improve the forecast? |
| `T2` | `2025-10-10` | Sources `01-05`: T1 plus runoff platform contrast. | Does issue/platform information change the model's view of the race? |
| `T3` | `2025-10-17` | Sources `01-08`: T2 plus late Quiroga poll, US-relations signal, and football-noise source. | Does late evidence dominate the earlier coalition signal, and does unrelated noise affect the forecast? |

## Run Results

| Run | Report id | Prediction | Winner score | MAE vote share | Margin abs error | Parse errors |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `T0_gemma_probe` | `report_c4f38b4b9b45` | no parseable Paz/Quiroga forecast | `0` | `null` | `5.06` | `2` |
| `T1_gemma_probe` | `report_69dabe8c4725` | `paz_gana` | `1` | `2.00` | `0.06` | `0` |
| `T2_gemma_probe` | `report_8b7869068e03` | `quiroga_gana` | `0` | `7.02` | `18.06` | `0` |
| `T3_gemma_probe` | `report_def4b871bbf2` | `quiroga_gana` | `0` | `7.687` | `18.06` | `0` |

## Issue #17 Acceptance Checklist

The core ask of issue #17 is answered, but there are two small presentation/configuration caveats worth calling out before closing it.

| Requirement from issue #17 | Status | Evidence / Notes |
| --- | --- | --- |
| `case_card.md` | Done | `case_card.md` documents event, hypotheses, cutoff, primary model target, and complexity gate. |
| `manifest.csv` with dates/sources | Done | `manifest.csv` lists all 8 sources with package, date, source, type, role, status, URL, and notes. |
| `seed_T0/T1/T2/T3` | Functionally done, naming differs | The package artifacts are `assembled_T0.md`, `assembled_T1.md`, `assembled_T2.md`, and `assembled_T3.md`. If strict naming is required, we should add alias files or rename/copy them to `seed_T0.md` through `seed_T3.md`. |
| `question.md` identical except available evidence | Done | One shared `question.md` is used across all T packages; only the uploaded evidence changes. |
| `ground_truth_private.md` | Done | Ground truth is separated from input and not uploaded to MiroFish. |
| `eval_objective.py` or `eval.md` | Done | `eval_objective.py` scores winner, vote shares, margin, parse errors, and leakage flags. |
| 1 pilot baseline run | Done | `T0_gemma_probe` is the baseline/early-evidence pilot; all four temporal runs were also completed. |
| 3 or 4 temporal evidence packages | Done | We produced and ran T0, T1, T2, and T3. |
| Measure whether MiroFish updates beliefs vs rewrites narratives | Done | The results show a real update from invalid T0 to correct T1, then degradation from T2/T3 due to late/salient pro-Quiroga evidence. |
| Complexity gate: minimum 6 docs | Done | 8 input documents. |
| Complexity gate: minimum 3 documentary dates | Done | Sources span August 15/16/18, October 8/13/15/17. |
| Complexity gate: minimum 3 source types | Done | Policy analysis, polling, wire/news, official statement, sports/noise. |
| Complexity gate: minimum 2 competing causal hypotheses | Done | Paz moderation/coalition vs Quiroga stabilization/anti-MAS hard-opposition path, plus polling/territorial-error hypothesis. |
| Complexity gate: 1 valid distractor/noise document | Done | `source-08-football-noise.md`. |
| Complexity gate: 20 extractable entities | Done in practice | Completed graphs/reports produced entity-rich runs; the T0 run notes alone show the report flow over a populated graph. |
| Ground truth outside input | Done | Ground truth was kept in `ground_truth_private.md`. |
| Event after model cutoff | Done | Event is October 19, 2025; target primary model cutoff in the case card is March 31, 2025. |
| Metric defined before execution | Done | Rubric/evaluator existed before scoring the saved reports. |
| Fixed primary model policy | Partially done / needs note | The case card targets `qwen/qwen3-8b`, but saved run folders are named `*_gemma_probe` and the run notes describe a Gemma probe setup. The evaluator metadata says `primary_fixed_qwen3_8b`, so before final closure we should either normalize the documentation or rerun one clean primary-policy pass if the issue owner requires strict model-policy evidence. |
| Model ladder | Not completed in this branch | Issue text says the model ladder is separate calibration. We focused on the temporal line with one completed run per T, not on Qwen vs Gemma vs Llama comparisons. |

Practical closure assessment: this branch answers the temporal-update experiment requested by the issue. The only items I would clean up before marking the issue fully closed are naming the seed artifacts exactly as requested (`seed_T0.md` etc., or documenting that `assembled_T*` are the seed packages) and resolving the model-policy naming ambiguity around `gemma_probe` vs `qwen/qwen3-8b`.

## What Happened In Each Temporal Package

### T0: Pre-First-Round Context

`T0` completed technically, but it failed as a forecast for the target runoff.

The report did not identify Rodrigo Paz and Jorge "Tuto" Quiroga as the two competitive runoff candidates. Instead, it anchored on older or more familiar Bolivian political figures, including Luis Arce and Samuel Doria Medina in the full report, and later Luis Arce / Carlos Mesa in report chat.

This is an important failure mode. With only early evidence, Rodrigo Paz existed in the context but was not salient enough for the system to reconstruct the eventual runoff. The evidence frontier was too early and too weak, so the model leaned on prior political familiarity rather than the actual 2025 runoff dynamics.

Main learning from T0:

- early packages can fail before the model even reaches the winner-prediction step;
- candidate identification should be evaluated separately from winner accuracy;
- if the competitive field is not explicit enough, MiroFish may fill gaps with high-salience historical actors;
- this makes T0 a useful baseline for measuring whether later evidence actually improves temporal reasoning.

### T1: First-Round Surprise And MAS Collapse

`T1` was the best run.

It identified the competitive candidates correctly:

- Rodrigo Paz
- Jorge "Tuto" Quiroga

It predicted Rodrigo Paz would win. The final forecast section estimated:

- Rodrigo Paz: `53%`
- Jorge "Tuto" Quiroga: `44%`
- Otros / blanco / nulo: `3%`
- Margin: `9` points

The evaluator parsed an earlier percentage block in the same report:

- Rodrigo Paz: `52%`
- Jorge "Tuto" Quiroga: `45%`
- Otros / blanco / nulo: `3%`

That still scored very well:

- winner score: `1`
- MAE vote share: `2.00`
- margin absolute error: `0.06`

Interpretation: adding the first-round result corrected the race. The model picked up that Paz had finished first, Quiroga second, MAS had collapsed out of the runoff, and Samuel Doria Medina's alignment with Paz mattered for coalition transfer. This is the cleanest evidence that the temporal setup works: after a major new event, MiroFish moved from an invalid early forecast to the correct winner.

Main learning from T1:

- the first-round surprise was the strongest predictive update in the whole case;
- MAS collapse mattered less as a simple anti-MAS signal and more as a voter-transfer / coalition-fragmentation problem;
- Doria Medina's endorsement of Paz was treated as a useful bridge to non-MAS and moderate voters;
- this package had strong signals but no direct final-result leakage.

### T2: Runoff Platform Contrast

`T2` completed and identified the right competitive candidates, but predicted the wrong winner: Jorge "Tuto" Quiroga.

Parsed forecast:

- Jorge "Tuto" Quiroga: `53%`
- Rodrigo Paz: `44%`
- Otros / blanco / nulo: `3%`
- Margin: `9` points for Quiroga

Score:

- winner score: `0`
- MAE vote share: `7.02`
- margin absolute error: `18.06`

Interpretation: adding the platform-contrast evidence moved the model away from the T1 coalition signal and toward Quiroga. The report gave substantial weight to Quiroga's pro-market / IMF-stabilization framing, treating it as a credible response to inflation, fuel scarcity, currency stress, and general economic anxiety.

This is not a technical failure; it is a forecasting failure mode. The system over-weighted a policy narrative that sounded economically coherent and under-weighted the electoral coalition signal from the first round.

Main learning from T2:

- later platform evidence can degrade performance if it is more vivid or structured than the prior electoral signal;
- economic-crisis framing can push the model toward the candidate with the clearest stabilization proposal;
- the model did not sufficiently discount the social backlash risk of austerity/IMF-style messaging;
- temporal recency is useful, but salience bias can override better electoral evidence.

### T3: Late Poll, US Signal, And Noise

`T3` completed and again identified the correct competitive candidates, but predicted Quiroga.

Parsed forecast:

- Jorge "Tuto" Quiroga: `52%`
- Rodrigo Paz: `43%`
- Otros / blanco / nulo: `5%`
- Margin: `9` points for Quiroga

Score:

- winner score: `0`
- MAE vote share: `7.687`
- margin absolute error: `18.06`

The report had an internal inconsistency: its title/summary mentioned a Paz victory, while the structured forecast sections predicted Quiroga. The evaluator correctly uses the structured `Prediccion principal` / vote-share block, so this is scored as `quiroga_gana`.

Interpretation: the late poll favoring Quiroga appears to have dominated the final forecast. The US-relations signal was treated as relevant context but not as direct winner evidence. The football source did not appear to materially affect the structured reasoning, which is a good sign: the system mostly ignored unrelated noise.

Main learning from T3:

- the late poll was the dominant new signal;
- the model did not sufficiently remember that the first-round result itself exposed polling/expectation error;
- unrelated sports noise did not meaningfully contaminate the final forecast;
- report generation can still produce inconsistent high-level summaries, so objective parsing should target the required structured answer section.

## Cross-Time Interpretation

The sequence shows a clear temporal pattern:

1. `T0` lacked enough decisive information and failed to identify the runoff correctly.
2. `T1` added the first-round surprise and produced the best forecast.
3. `T2` added platform contrast and shifted incorrectly toward Quiroga.
4. `T3` added a late Quiroga poll and preserved the same wrong direction.

So the main conclusion is not simply "more evidence is better." The better conclusion is:

> The most predictive evidence was the first-round shock and coalition realignment. Later evidence was more recent, but not necessarily more reliable. MiroFish over-weighted late/salient pro-Quiroga signals relative to the earlier but stronger voter-behavior signal.

That makes this a useful S2 case because it exposes both positive and negative temporal behavior:

- positive: the system updates strongly when a decisive event appears (`T1`);
- negative: the system can be pulled away by later but less robust signals (`T2`, `T3`);
- robust: unrelated noise did not visibly drive the forecast (`T3`);
- fragile: report summaries can contradict structured forecast sections.

## Leakage Review

No direct ground-truth leakage was found in the intended evidence packages.

Manual checks over the input sources found:

- no final official vote shares (`54.53`, `45.47`, `9.06`);
- no final runoff winner statement saying Paz won;
- no direct post-runoff result text;
- no ground truth file included in the uploaded evidence.

`T1` does contain strong information, but it is allowed information because it occurs before the runoff:

- Paz finished first in the first round;
- Quiroga finished second;
- MAS did not reach the runoff;
- Doria Medina endorsed Paz.

Those are legitimate temporal signals, not leakage.

## Risk Factors MiroFish Surfaced

The reports repeatedly identified a set of plausible election-risk factors:

- Economic crisis: inflation, fuel scarcity, foreign-currency pressure, and economic insecurity were the central voter drivers.
- MAS fragmentation: the Arce/Morales split and MAS's weak result changed the political map.
- Voter-transfer uncertainty: the key unknown was where MAS voters, Doria Medina voters, protest voters, blank/null voters, and undecideds would move.
- Poll reliability: T2/T3 show that late polls can dominate the model even when the case history suggests polling error risk.
- Platform backlash: Quiroga's IMF/pro-market plan looked credible to the model but carried austerity and social-program backlash risk.
- Paz coalition risk: Paz's moderation and decentralization could build a broad coalition, but the reports sometimes treated it as less forceful than Quiroga's economic plan.
- Post-election instability: fraud claims, protests, polarization, and legitimacy disputes were recurring uncertainty factors.
- Foreign-relations ambiguity: US engagement was treated as a diplomatic signal, not proof of a winner.
- Noise handling: the football-noise source was not materially used in the final structured forecast.

## Engineering Problems Found And Fixed

The backtesting work also exposed real stability problems in the MiroFish report flow. These were fixed locally and committed so future runs should not need the same manual repair.

### JSON / LLM Client Stability

File: `backend/app/utils/llm_client.py`

Problem:

- JSON-format calls could route through Prompture even when the OpenAI-compatible client was needed.
- This caused ontology/report stages to fail or return malformed/incomplete JSON with some providers.

Fix:

- Initialize the OpenAI-compatible client even when Prompture is installed.
- Route `response_format={"type":"json_object"}` calls through the OpenAI-compatible SDK.

### Report Tool Timeout And Fallback

File: `backend/app/services/zep_tools.py`

Problem:

- `interview_agents` could spend several minutes in the dual-platform API call and then fail.
- One run failed after the interview API returned because `get_locale` was not imported.

Fix:

- Import `get_locale` together with `t`.
- Increase the interview timeout to 600 seconds.
- If the dual-platform call fails or times out, retry with one platform at a time: first `reddit`, then `twitter`.

### Report Agent Tool Parsing

File: `backend/app/services/report_agent_quality_guards.py`

Problem:

- Gemma emitted tool calls with Python-style literals like `True`.
- The parser expected strict JSON only, rejected the tool call, and the report agent eventually hit max iterations without making the intended tool call.

Fix:

- Add a safe `ast.literal_eval` fallback for `<tool_call>` payloads.
- Normalize Python-style literals into ordinary dicts when safe.

### Objective Evaluator Margin Logic

File: `backtesting/case-b-s2-bolivia-2025-runoff/eval_objective.py`

Problem:

- Wrong Quiroga predictions could look artificially close if `margen ganador-segundo` was treated only as an absolute positive number.

Fix:

- Interpret the predicted margin as a signed Paz-minus-Quiroga margin based on the predicted winner.
- This makes `T2` and `T3` correctly show `18.06` points of margin error.

### Local Dependency Note

During execution, `backend/app/services/experimental_memory.py` required `chromadb`.

- `chromadb` is listed in `backend/requirements.txt`.
- It is not currently a direct dependency in `backend/pyproject.toml`.
- In this local environment it was installed with `uv pip install 'chromadb>=0.4.0'`.

I did not add it to `pyproject.toml` in this issue because the backend lockfile currently has a known dependency conflict around `camel-oasis` and `neo4j`. That should be handled as a separate dependency-cleanup issue.

## Verification

The code touched for the run was syntax-checked with:

```bash
python3 -m py_compile \
  backend/app/utils/llm_client.py \
  backend/app/services/zep_tools.py \
  backend/app/services/report_agent_quality_guards.py \
  backtesting/case-b-s2-bolivia-2025-runoff/eval_objective.py
```

The evaluator was run for all completed temporal outputs:

```bash
python3 backtesting/case-b-s2-bolivia-2025-runoff/eval_objective.py \
  --prediction backtesting/case-b-s2-bolivia-2025-runoff/output/T0_gemma_probe/full_report.md \
  --variant T0_gemma_probe

python3 backtesting/case-b-s2-bolivia-2025-runoff/eval_objective.py \
  --prediction backtesting/case-b-s2-bolivia-2025-runoff/output/T1_gemma_probe/full_report.md \
  --variant T1_gemma_probe

python3 backtesting/case-b-s2-bolivia-2025-runoff/eval_objective.py \
  --prediction backtesting/case-b-s2-bolivia-2025-runoff/output/T2_gemma_probe/full_report.md \
  --variant T2_gemma_probe

python3 backtesting/case-b-s2-bolivia-2025-runoff/eval_objective.py \
  --prediction backtesting/case-b-s2-bolivia-2025-runoff/output/T3_gemma_probe/full_report.md \
  --variant T3_gemma_probe
```

## Final Conclusion

This issue produced a complete temporal backtesting case and a useful first set of observations.

The most important result is that `T1` worked exactly as a temporal benchmark should: once the first-round surprise became available, MiroFish corrected the candidate field and predicted Paz with a near-perfect margin. The most important limitation is that later packages over-weighted pro-Quiroga information, especially platform framing and a late poll, even though the earlier first-round surprise was arguably the more reliable signal about voter behavior.

For future S2 cases, I would keep this structure:

- evaluate candidate identification separately from winner prediction;
- keep one package just before the main shock event;
- keep one package immediately after the shock event;
- add one later package with plausible but misleading high-salience evidence;
- add one irrelevant-noise source to test robustness;
- use structured answer parsing rather than trusting report titles or summaries.

This Bolivia runoff case is useful precisely because it is not a trivial "more context means better answer" example. It shows improvement, degradation, salience bias, and noise handling in the same controlled setup.
