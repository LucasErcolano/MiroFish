# Results: Bolivia 2025 Runoff Temporal Backtest

## Case

- Case id: `bolivia_2025_runoff_s2`
- Event: Bolivia presidential runoff, October 19, 2025.
- Ground truth: Rodrigo Paz defeated Jorge "Tuto" Quiroga.
- Operational vote-share ground truth:
  - Rodrigo Paz: `54.53`
  - Jorge Quiroga: `45.47`
  - Otros / blanco / nulo: `0.00`
  - Paz - Quiroga margin: `9.06` points

## Temporal Design

- `T0`: pre-first-round context and final first-round polling context.
- `T1`: T0 plus first-round surprise and MAS collapse/runoff realignment.
- `T2`: T1 plus runoff platform contrast.
- `T3`: T2 plus late poll favoring Quiroga, US-relations signal, and football-noise source.

The model was given only the evidence package and `question.md`. It was not given `ground_truth_private.md`, rubrics, internal notes, outputs, or evaluation code.

## Score Summary

| Run | Evidence | Prediction | Winner score | MAE vote share | Margin abs error | Notes |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `T0_gemma_probe` | sources 01-02 | `null` | 0 | null | 5.06 | Failed to identify the actual runoff field; anchored on older/persistent Bolivian political figures. |
| `T1_gemma_probe` | sources 01-04 | `paz_gana` | 1 | 2.0 | 0.06 | Best run. First-round surprise and Doria Medina realignment supported Paz. |
| `T2_gemma_probe` | sources 01-05 | `quiroga_gana` | 0 | 7.02 | 18.06 | Platform contrast pushed the report toward Quiroga's pro-market / IMF-stabilization framing. |
| `T3_gemma_probe` | sources 01-08 | `quiroga_gana` | 0 | 7.687 | 18.06 | Late poll favoring Quiroga dominated the forecast; football noise did not appear to affect the final reasoning. |

## Main Findings

1. T0 lacked enough decisive context.
   The model saw Rodrigo Paz mentioned, but he was not yet the dominant pre-first-round figure. The run did not infer the correct Paz vs Quiroga runoff and instead drifted toward older or more familiar political names. This is a useful failure mode for temporal evaluation.

2. T1 was the strongest temporal package.
   Once the first-round result entered the evidence, the model identified the two finalists and forecast Paz correctly. The likely drivers were Paz finishing first, MAS falling out of the runoff, and Doria Medina endorsing Paz.

3. T2 and T3 show recency / salience bias toward Quiroga.
   Adding platform contrast and then a late poll favoring Quiroga caused the report to over-weight the case for Quiroga. The system treated the later pro-Quiroga information as more predictive than the first-round coalition signals that favored Paz.

4. The football noise source did not materially affect T3.
   T3 reasoning focused on the late poll, US engagement, economic crisis, MAS decline, and candidate platforms. The football source was not a meaningful factor in the structured forecast.

5. The report agent can produce inconsistent summaries.
   In T3, the title/summary said Paz, while the structured forecast sections predicted Quiroga. The evaluator uses the structured `Prediccion principal` line, which is the right choice for this benchmark.

## Risk Factors Identified By The Reports

- Economic crisis: inflation, fuel scarcity, foreign-currency pressure, and general economic insecurity were treated as the central voter drivers.
- MAS collapse: internal Arce/Morales fragmentation and the worst MAS defeat in decades opened the runoff to non-MAS candidates.
- Coalition transfer uncertainty: the key unknown was how voters from Doria Medina, MAS-linked candidates, protest options, and undecided voters would move in the runoff.
- Poll reliability: T2/T3 show that a late poll can dominate the forecast even when the earlier first-round surprise suggests polling error risk.
- Platform risk: Quiroga's IMF / pro-market stabilization message was read as credible by some agents, but also carried austerity and social-program backlash risk.
- Paz moderation risk: Paz's more moderate and decentralizing platform could attract a broader coalition, but reports sometimes treated it as less forceful than Quiroga's economic proposal.
- Social stability: several reports flagged fraud claims, post-election protests, polarization, and external interference as uncertainty factors.
- Foreign-relations signal: US engagement was interpreted as a diplomatic/institutional signal, not as direct winner evidence, but T3 still gave it some weight toward a more internationally aligned candidate.

## Leakage Check

Manual grep checks found no direct final-result leakage in the intended evidence packages:

- no final official vote shares (`54.53`, `45.47`, `9.06`);
- no final winner statement for Paz;
- no direct post-runoff result text.

T1 contains strong allowed signals, not leakage: Paz first in the first round, Quiroga second, MAS excluded from the runoff, and Doria Medina endorsing Paz.

## Code Fixes Needed For The Run

These local fixes should stay committed so the backtesting flow does not need to be repaired again:

- `backend/app/utils/llm_client.py`
  - Initialize the OpenAI-compatible client even when Prompture is installed.
  - Route JSON `response_format` calls through the OpenAI-compatible SDK instead of Prompture, so ontology/JSON generation is more stable.

- `backend/app/services/zep_tools.py`
  - Import `get_locale` along with `t`.
  - Increase dual-platform interview timeout from 180 seconds to 600 seconds.
  - Add fallback from dual-platform interviews to single-platform `reddit`, then `twitter`, if the batch call times out or returns failure.

- `backend/app/services/report_agent_quality_guards.py`
  - Make tool-call parsing tolerant of safe Python-style literals such as `True`, `False`, and `None` inside `<tool_call>` blocks.
  - This fixed the failure where Gemma emitted `"include_expired": True`, which looked like a tool call to humans but was rejected as invalid JSON by the parser.

- `backtesting/case-b-s2-bolivia-2025-runoff/eval_objective.py`
  - Interpret `margen ganador-segundo` as a signed Paz-minus-Quiroga margin based on the predicted winner.
  - Without this, wrong Quiroga predictions could appear to have low margin error.

## Setup Note

During local execution, report generation also required `chromadb` for `backend/app/services/experimental_memory.py`. The package is already listed in `backend/requirements.txt`, but not as a direct dependency in `backend/pyproject.toml`. In this local environment it was installed with `uv pip install 'chromadb>=0.4.0'`. If a fresh `uv --frozen` environment fails with `No module named 'chromadb'`, either install it into the backend venv or resolve the backend lockfile dependency conflict before adding it to `pyproject.toml`.
