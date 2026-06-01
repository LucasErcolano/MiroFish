# Smoke run: 2 agents, 2 real models

Validates the multi-model feature end-to-end against two real OpenAI-compatible
endpoints, producing an auditable `model_routing_audit.jsonl` and per-call
`llm_telemetry.jsonl`.

> Status: the real 2-model run is **deferred** (no GPU/endpoints in CI). This
> directory is the reproducible recipe; the unit suite
> (`backend/tests/test_model_routing.py`) covers the logic with mock providers.

## Prerequisites

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
  --model-map ../runs/smoke_multimodel/agent_model_map.yaml \
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
  --out-csv runs/smoke_multimodel/telemetry.csv \
  --out-summary runs/smoke_multimodel/telemetry_summary.jsonl
```

## Acceptance check

Confirm each agent action is traceable to (model, provider, tokens, cost,
round) in `llm_telemetry.jsonl`, and that agent 0 and agent 1 used **different**
models in `model_routing_audit.jsonl`.
