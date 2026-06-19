# S2 Line 5 Llama Extension - Bolivia and Copa America

This extends the Issue #18 / PR #22 Line 5 design to the Bolivia runoff and
Copa America cases already prepared in this branch.

## Source Pattern

The imported design is the reduced S2 matrix from PR #22:

| Condition | Rounds | Density |
|---|---:|---:|
| R10-D2 | 10 | 2 |
| R40-D2 | 40 | 2 |
| R80-D2 | 80 | 2 |
| R40-D1 | 40 | 1 |
| R40-D3 | 40 | 3 |

The model policy follows PR #22:

- Model label: `Llama 3.3 70B Instruct`
- Provider id: `meta-llama/Llama-3.3-70B-Instruct`
- Expected backend base URL: `https://api.deepinfra.com/v1/openai`

## Cases

| Case | Config | Evidence package | Evaluator |
|---|---|---|---|
| Bolivia runoff | `backtesting/case-b-s2-bolivia-2025-runoff/config_line5_llama.yaml` | `seed_T3_clean.md` | report markdown evaluator |
| Copa America | `backtesting/case-d-s2-copa-america-line5-gemma/config_line5_llama.yaml` | `seed_T3.md` | structured JSON evaluator |

For Bolivia, `seed_T3_clean.md` keeps the full pre-cutoff electoral evidence
package and removes the football-noise block from `seed_T3.md`.

## Slim Mode

The slim mode mirrors the practical setup used in PR #22 more closely: it keeps
the same R/D matrix, but uses a short fixed evidence packet and reuses one graph
project across all variants in a single runner execution.

| Case | Config | Evidence package | Output directory |
|---|---|---|---|
| Bolivia runoff slim | `config_line5_llama_slim.yaml` | `seed_T3_line5_slim.md` | `output_llama_line5_slim/` |
| Copa America slim | `config_line5_llama_slim.yaml` | `seed_T3_line5_slim.md` | `output_llama_line5_slim/` |

## Backend Requirement

The runner cannot hot-swap the model of an already-running backend. Start the
backend with the Llama/DeepInfra configuration first, for example:

```bash
export LLM_API_KEY="$DEEPINFRA_API_KEY"
export LLM_BASE_URL="https://api.deepinfra.com/v1/openai"
export LLM_MODEL_NAME="meta-llama/Llama-3.3-70B-Instruct"
export GRAPHITI_LLM_BASE_URL="https://api.deepinfra.com/v1/openai"
export GRAPHITI_LLM_MODEL="meta-llama/Llama-3.3-70B-Instruct"
export GRAPHITI_MAX_COROUTINES=1
npm run backend
```

## Dry Run

```bash
python3 backtesting/scripts/run_line5_llama_matrix.py \
  --case-dir backtesting/case-b-s2-bolivia-2025-runoff \
  --dry-run

python3 backtesting/scripts/run_line5_llama_matrix.py \
  --case-dir backtesting/case-d-s2-copa-america-line5-gemma \
  --dry-run
```

Slim dry runs:

```bash
python3 backtesting/scripts/run_line5_llama_matrix.py \
  --case-dir backtesting/case-b-s2-bolivia-2025-runoff \
  --config config_line5_llama_slim.yaml \
  --dry-run

python3 backtesting/scripts/run_line5_llama_matrix.py \
  --case-dir backtesting/case-d-s2-copa-america-line5-gemma \
  --config config_line5_llama_slim.yaml \
  --dry-run
```

## Execute One Smoke Variant

```bash
python3 backtesting/scripts/run_line5_llama_matrix.py \
  --case-dir backtesting/case-b-s2-bolivia-2025-runoff \
  --variant llama_T3_R10_D2 \
  --force

python3 backtesting/scripts/run_line5_llama_matrix.py \
  --case-dir backtesting/case-d-s2-copa-america-line5-gemma \
  --variant llama_T3_R10_D2 \
  --force
```

Slim smoke variants:

```bash
python3 backtesting/scripts/run_line5_llama_matrix.py \
  --case-dir backtesting/case-b-s2-bolivia-2025-runoff \
  --config config_line5_llama_slim.yaml \
  --variant llama_T3_slim_R10_D2 \
  --force

python3 backtesting/scripts/run_line5_llama_matrix.py \
  --case-dir backtesting/case-d-s2-copa-america-line5-gemma \
  --config config_line5_llama_slim.yaml \
  --variant llama_T3_slim_R10_D2 \
  --force
```

## Execute Full Matrices

```bash
python3 backtesting/scripts/run_line5_llama_matrix.py \
  --case-dir backtesting/case-b-s2-bolivia-2025-runoff \
  --force

python3 backtesting/scripts/run_line5_llama_matrix.py \
  --case-dir backtesting/case-d-s2-copa-america-line5-gemma \
  --force
```

Slim full matrices:

```bash
python3 backtesting/scripts/run_line5_llama_matrix.py \
  --case-dir backtesting/case-b-s2-bolivia-2025-runoff \
  --config config_line5_llama_slim.yaml \
  --force

python3 backtesting/scripts/run_line5_llama_matrix.py \
  --case-dir backtesting/case-d-s2-copa-america-line5-gemma \
  --config config_line5_llama_slim.yaml \
  --force
```

Outputs are written under each case's `output_llama_line5/` directory. Each run
keeps `worldbuilding_trace.json`, `worldbuilding_artifacts/llm_calls`,
`simulation_config.json`, `run_state.json`, report artifacts and `eval_result.json`.
Slim outputs use `output_llama_line5_slim/` and additionally write a
`_shared_graph_T3_slim.json` cache when the shared graph build completes.

Note: as in PR #22, `density` is recorded as an experimental condition. The
current backend enforces the round count through `max_rounds`; density is not yet
a separate first-class runtime control.

## Slim Results

The completed slim matrices use the same five Line 5 conditions as PR #22 and
reuse one graph build per case. All rows below include `worldbuilding_trace.json`,
`simulation_config.json`, `run_state.json`, `state.json`, report artifacts and
`eval_result.json`.

### Bolivia Runoff

Ground truth: `paz_gana`, with Paz 54.53%, Quiroga 45.47%, margin +9.06.

| Variant | Prediction | Winner score | Paz | Quiroga | Otros | MAE vote share | Predicted margin | Margin abs error | Parse errors |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `llama_T3_slim_R10_D2` | `quiroga_gana` | 0 | 43.0 | 52.0 | 5.0 | 7.687 | -9.0 | 18.06 | 0 |
| `llama_T3_slim_R40_D1` | `quiroga_gana` | 0 | 40.0 | 45.0 | 15.0 | 10.000 | -5.0 | 14.06 | 0 |
| `llama_T3_slim_R40_D2` | `quiroga_gana` | 0 | 42.8 | 51.2 | 6.0 | 7.820 | -8.4 | 17.46 | 0 |
| `llama_T3_slim_R40_D3` | `quiroga_gana` | 0 | 42.8 | 51.2 | 6.0 | 7.820 | -8.4 | 17.46 | 0 |
| `llama_T3_slim_R80_D2` | `quiroga_gana` | 0 | 43.0 | 52.0 | 5.0 | 7.687 | -9.0 | 18.06 | 0 |

In this case, increasing rounds or density did not reverse the dominant polling
signal in the evidence packet. The model remained anchored on a Quiroga win even
though the post-event ground truth was a Paz win.

### Copa America Final

Ground truth: Argentina won the 2024 Copa America final.

| Variant | Prediction | Score | Confidence | Winner probability | Winner range | Goal margin | Parse errors |
|---|---|---:|---:|---:|---|---|---:|
| `llama_T3_slim_R10_D2` | Argentina | 4/5 | 0.70 | 0.475 | 0.45-0.50 | 1.0 [0.0, 2.0] | 0 |
| `llama_T3_slim_R40_D1` | Argentina | 5/5 | 0.70 | 0.475 | 0.45-0.50 | 1.0 [0.0, 2.0] | 0 |
| `llama_T3_slim_R40_D2` | Argentina | 5/5 | 0.70 | 0.475 | 0.45-0.50 | 1.0 [0.0, 2.0] | 0 |
| `llama_T3_slim_R40_D3` | Argentina | 5/5 | 0.70 | 0.475 | 0.45-0.50 | 1.0 [0.0, 2.0] | 0 |
| `llama_T3_slim_R80_D2` | Argentina | 5/5 | 0.70 | 0.475 | 0.45-0.50 | 1.0 [0.0, 2.0] | 0 |

The Copa America matrix is almost invariant across conditions. All variants
predict Argentina with the same probability and margin, which suggests that
additional rounds do not add much when the evidence packet already contains a
strong and consistent pre-event favorite.

## Cross-Case Interpretation

The IPC results from PR #22 show one meaningful depth effect: `R80-D2` moved to a
more explicit disinflation path while most other conditions stayed close to each
other. Bolivia and Copa America show the opposite pattern: when evidence includes
a strong prior signal, such as polls or market/model odds, the simulation tends
to preserve that signal instead of exploring a contrary outcome.

This suggests a useful follow-up experiment for the multi-agent setting: split
evidence across agents instead of giving all agents the same packet. Some agents
could receive poll/market signals, others qualitative context, institutional
risks or counterevidence. Under that setup, extra rounds may matter more because
agents would need to negotiate between partially different evidence views instead
of converging immediately on the same dominant prior.
