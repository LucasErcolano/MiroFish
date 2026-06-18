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
| Bolivia runoff | `backtesting/case-b-s2-bolivia-2025-runoff/config_line5_llama.yaml` | `seed_T3.md` | report markdown evaluator |
| Copa America | `backtesting/case-d-s2-copa-america-line5-gemma/config_line5_llama.yaml` | `seed_T3.md` | structured JSON evaluator |

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

## Execute Full Matrices

```bash
python3 backtesting/scripts/run_line5_llama_matrix.py \
  --case-dir backtesting/case-b-s2-bolivia-2025-runoff \
  --force

python3 backtesting/scripts/run_line5_llama_matrix.py \
  --case-dir backtesting/case-d-s2-copa-america-line5-gemma \
  --force
```

Outputs are written under each case's `output_llama_line5/` directory. Each run
keeps `worldbuilding_trace.json`, `worldbuilding_artifacts/llm_calls`,
`simulation_config.json`, `run_state.json`, report artifacts and `eval_result.json`.

Note: as in PR #22, `density` is recorded as an experimental condition. The
current backend enforces the round count through `max_rounds`; density is not yet
a separate first-class runtime control.
