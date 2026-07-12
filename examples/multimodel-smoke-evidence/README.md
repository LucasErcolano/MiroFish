# Smoke run: 2 agents, 2 real models

Validates the multi-model feature end-to-end against two real OpenAI-compatible
endpoints, producing an auditable `model_routing_audit.jsonl` and per-call
`llm_telemetry.jsonl`.

> Status: **DONE** (2026-06-06). Executed against the Gemini OpenAI-compatible
> endpoint with two real models — no GPU needed (see "Variant: no GPU" below).
> Committed artifacts: `llm_telemetry.jsonl`, `model_routing_audit.jsonl`,
> `telemetry.csv`, `telemetry_summary.jsonl`. Result: 18 calls, 9 per model,
> agents 0–9 → `gemini-2.5-flash-lite` (by_agent_id), default →
> `gemini-3.1-flash-lite`, every call traceable to (model, provider, tokens,
> cost, round). `cost_usd_est` is 0.0 + `cost_unknown_model` flag because the
> gemini models have no entry in `configs/model_prices.yaml` — the documented
> auditable-not-silent behavior.

## Variant: no GPU (any multi-model OpenAI-compatible endpoint)

A single OpenAI-compatible endpoint that serves several models (Gemini,
OpenRouter, Groq, ...) satisfies the "2 real models" requirement without local
servers. Use `agent_model_map.gemini.yaml` (resolves `LLM_BASE_URL` /
`LLM_API_KEY` from env):

```bash
cd backend
env -u PYTHONPATH .venv/bin/python scripts/run_reddit_simulation.py \
  --config <sim_dir>/simulation_config.json \
  --model-map ../examples/multimodel-smoke-evidence/agent_model_map.gemini.yaml \
  --max-rounds 12 --no-wait
```

> Use enough rounds to reach the agents' `active_hours` (1 round = 1 simulated
> hour with `minutes_per_round: 60`; agents are typically active from hour 8).

## Prerequisites (original local-GPU variant)

Two OpenAI-compatible servers, e.g. vLLM on a single RTX 3090:

- `qwen2.5-7b-instruct-awq`  → `http://127.0.0.1:8000/v1`
- `mistral-7b-instruct-v0.3-awq` → `http://127.0.0.1:8001/v1`

```bash
export LOCAL_LLM_API_KEY=dummy        # vLLM accepts any non-empty key
```

You also need a prepared simulation directory with a `simulation_config.json`
and `reddit_profiles.json` (produced by the normal MiroFish graph→profile flow)
with **at least 2 agents** (agent_id 0 and 1).

## Run

```bash
cd backend
uv run python scripts/run_reddit_simulation.py \
  --config <sim_dir>/simulation_config.json \
  --model-map ../examples/multimodel-smoke-evidence/agent_model_map.yaml \
  --max-rounds 1 --no-wait
```

## Expected artifacts (written into `<sim_dir>/`)

- `model_routing_audit.jsonl` — one line per agent: model, provider, base_url,
  `api_key_set`, `source`. Keys are redacted (never written).
- `llm_telemetry.jsonl` — one line per LLM call with `agent_id, role, provider,
  model, prompt_hash, response_hash, tokens_in, tokens_out, latency_ms, round,
  cost_usd_est, temperature, output_valid_json, error, leak_flags`.

## Export the telemetry

```bash
python scripts/export_telemetry.py \
  --input <sim_dir> \
  --out-csv ../outputs/multimodel-smoke/telemetry.csv \
  --out-summary ../outputs/multimodel-smoke/telemetry_summary.jsonl
```

## Acceptance check

Confirm each agent action is traceable to (model, provider, tokens, cost,
round) in `llm_telemetry.jsonl`, and that agent 0 and agent 1 used **different**
models in `model_routing_audit.jsonl`.
