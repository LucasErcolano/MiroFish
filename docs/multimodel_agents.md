# Multi-model agents & observability

> Issue #21 (S2 Dev 2). Per-agent / per-role LLM routing for MiroFish
> simulations, plus per-call telemetry (tokens, latency, cost) so every agent
> action is traceable back to the model that produced it.

## What this is

By default a MiroFish simulation runs every OASIS agent on a single LLM (the one
in `LLM_*` env vars). This feature lets you assign **different models to
different agents** — e.g. a local 7B for the crowd and a stronger hosted model
for a few key actors — driven by a YAML *model map*, and records a telemetry
line for every LLM call.

Two modules implement it, both in `backend/app/services/`:

| Module | Responsibility |
|--------|----------------|
| `model_router.py` | Load + validate the model map, resolve a `ModelPolicy` per agent, build the CAMEL backend. |
| `llm_telemetry.py` | Wrap each backend instance to record per-call telemetry to JSONL, with cost estimation. |

The standalone `scripts/export_telemetry.py` turns the per-run JSONL into a flat
CSV plus an aggregated summary.

### Why the telemetry wraps the CAMEL backend, not `LLMClient`

OASIS simulation agents do **not** call `LLMClient` — they call the CAMEL model
backend created by `ModelFactory.create`, dispatched through
`ModelManager.current_model.run/arun`. `LLMClient` is only used for the
graph / profile / report paths. Instrumenting `LLMClient` would capture **zero**
agent responses. So `instrument_backend` monkeypatches the backend **instance**
(`run`/`arun`), which:

- keeps `isinstance(model, BaseModelBackend)` true (CAMEL's `ChatAgent` relies on it), and
- intercepts every call OASIS routes through the model manager.

## Canonical config file

Issue #21 lists **two** YAML deliverables that coexist by design:

| File | Role | Reuse? |
|------|------|--------|
| `configs/model_map_example.yaml` | Annotated **template** with every field documented. | Copy it — don't run it directly. |
| `agent_model_map.yaml` (user-provided, any path) | The **canonical runtime config** for a real run. Passed to the runner via `--model-map <path>`. | This is the file you author and edit per experiment. |
| `examples/multimodel-smoke-evidence/agent_model_map.yaml`, `agent_model_map.gemini.yaml` | **Frozen smoke evidence** for the 2-model run below. | Reference only — not a starting point. |

The runner takes the map **path as an argument**, so the canonical
`agent_model_map.yaml` lives wherever the researcher keeps it (alongside the
case config is the convention). Start by copying the example:

```bash
cp configs/model_map_example.yaml agent_model_map.yaml   # then edit
```

## Enabling it

Pass a model map to the simulation runner:

```bash
cd backend
uv run python scripts/run_reddit_simulation.py \
  --config <sim_dir>/simulation_config.json \
  --model-map ../configs/model_map_example.yaml \
  --max-rounds 1 --no-wait
```

Without `--model-map`, behavior is unchanged — single-model, no routing, no
per-call telemetry file. The feature is fully opt-in.

When enabled, the runner writes two artifacts into the simulation directory:

- **`model_routing_audit.jsonl`** — one line per agent: the resolved
  `model, provider, base_url, temperature, seed, source, api_key_env,
  api_key_set`. **Keys are never written** — only whether the named env var is set.
- **`llm_telemetry.jsonl`** — one line per LLM call (schema below).

## Model map schema

See `configs/model_map_example.yaml` for a complete annotated example.

```yaml
version: 1                    # required, must be 1

default:                      # required; applied to every agent unless overridden
  provider: openai            # OpenAI-compatible provider name
  model: gpt-4o-mini          # required
  base_url_env: LLM_BASE_URL  # env var naming the base URL (or use `base_url:` literal)
  api_key_env: LLM_API_KEY    # env var holding the key
  temperature: 0.7
  seed: null                  # int for reproducibility, null = non-deterministic

fallback:
  enabled: false              # see "Fallback semantics" below

by_role:                      # keyed by agent entity_type / role
  FinancialInstitution:
    provider: vllm
    model: qwen2.5-7b-instruct-awq
    base_url: http://127.0.0.1:8000/v1
    api_key_env: LOCAL_LLM_API_KEY

by_agent_id:                  # keyed by integer agent_id (most specific)
  0:
    provider: vllm
    model: mistral-7b-instruct-v0.3-awq
    base_url: http://127.0.0.1:8001/v1
    api_key_env: LOCAL_LLM_API_KEY
    temperature: 0.5
    seed: 42
```

### Per-layer fields

A layer (`default`, any `by_role.*`, any `by_agent_id.*`) accepts only these
fields — any other key is a validation error:

| Field | Meaning |
|-------|---------|
| `provider` | OpenAI-compatible provider name. Known: `openai`, `vllm`, `lmstudio`, `groq`. Unknown names are rejected by validation (add to `PROVIDERS` in `model_router.py` if intended). Defaults to `openai`. |
| `model` | Model identifier passed to the provider. Required on `default`. |
| `base_url` | Literal base URL. Takes precedence over `base_url_env`. |
| `base_url_env` | Name of an env var holding the base URL. Used when `base_url` is absent. |
| `api_key_env` | Name of the env var holding the API key. Falls back to the provider's conventional var, else `LLM_API_KEY`. |
| `temperature` | Number, optional. Threaded into the CAMEL `model_config_dict`. |
| `seed` | Integer or `null`, optional. Threaded into `model_config_dict` for reproducibility. |

## Resolution precedence

Each layer is **shallow-merged on top of `default`** — a `by_role` or
`by_agent_id` entry only needs to specify the fields that differ.

```
by_agent_id  >  by_role  >  default        (highest wins)
```

The merge starts from `default`, applies `by_role[role]` if the agent's role
matches, then `by_agent_id[agent_id]` if present. The resolved `ModelPolicy`
records which layer won in its `source` field (`"by_agent_id" | "by_role" |
"default"`), which is surfaced in the routing audit.

## Provider abstraction

All providers are routed through CAMEL's OpenAI-compatible backend
(`ModelFactory.create(model_platform=ModelPlatformType.OPENAI, ...)`). The
`provider` name is primarily for documentation, validation, and conventional
default env-var selection (see `PROVIDERS` in `model_router.py`). This means any
OpenAI-compatible server — hosted OpenAI, vLLM, LM Studio, Groq — works with the
same code path; you only change `base_url` / `model` / keys.

The CAMEL import is **lazy** (only in `build_backend`), so the map
loading / validation / resolution logic is unit-testable without the heavy
simulation dependency installed.

## Secrets policy

API keys are **never** written in the model map. `validate_model_map` rejects a
literal `api_key` field in any layer. Keys come exclusively from the environment,
named by `api_key_env`. `base_url` may be a literal (it is not a secret) or
resolved from `base_url_env`. The routing audit records `api_key_set: true|false`
but never the key value.

## Fallback semantics

`fallback.enabled` is **`false` by default** (an Issue #21 requirement): if a
per-agent backend fails to build (e.g. its `api_key_env` is unset), the routing
error is **loud**, not silently downgraded to the default model. Set
`fallback.enabled: true` only if you explicitly want missing per-agent backends
to fall back to `default`.

## Telemetry record schema

Each LLM call appends one JSON line to `<sim_dir>/llm_telemetry.jsonl`:

| Field | Type | Notes |
|-------|------|-------|
| `timestamp` | string | ISO-8601, call completion time. |
| `round` | int | Simulation round; set by the runner before each `env.step` (OASIS doesn't expose the round at the model-call layer). |
| `agent_id` | int | The agent that made the call. |
| `role` | string\|null | The agent's role / entity_type. |
| `provider` | string | Resolved provider. |
| `model` | string | Resolved model. |
| `temperature` | number\|null | From the backend's `model_config_dict`. |
| `prompt_hash` | string | SHA-256 of the request messages (content not stored). |
| `response_hash` | string\|null | SHA-256 of the response content, or null. |
| `tokens_in` | int | `prompt_tokens` from the response usage. |
| `tokens_out` | int | `completion_tokens` from the response usage. |
| `latency_ms` | number | Wall-clock latency of the call. |
| `cost_usd_est` | number | Estimated cost (see cost estimation). |
| `output_valid_json` | bool\|null | Whether the response content parses as JSON; null if no content. |
| `error` | string\|null | `repr(exc)` if the call raised (then re-raised); else null. |
| `leak_flags` | string[] | Audit flags, e.g. `cost_unknown_model`. |

Prompts and responses are stored as **hashes only** — the schema is auditable
without retaining message content.

### Issue #21 required-field coverage

Every telemetry field the issue mandates is present in `llm_telemetry.jsonl`
**and** carried through to `telemetry.csv` by `export_telemetry.py`:

| Issue #21 requirement | Field | Status |
|-----------------------|-------|--------|
| `agent_id` | `agent_id` | ✅ |
| `role` | `role` | ✅ |
| `provider` (exact) | `provider` | ✅ |
| `model` (exact) | `model` | ✅ |
| `prompt_hash` | `prompt_hash` | ✅ |
| `response_hash` | `response_hash` | ✅ (null when the provider response carries no extractable content) |
| Tokens in/out | `tokens_in`, `tokens_out` | ✅ |
| Latencia | `latency_ms` | ✅ |
| `round` | `round` | ✅ |
| Costo estimado | `cost_usd_est` | ✅ |
| Temperatura | `temperature` | ✅ |
| Validación de output JSON | `output_valid_json` | ✅ |
| Errores | `error` | ✅ |
| **Retries** | — | **Not a separate field by design** — SDK-internal retries happen below the instrumented call (see "Scope & limitations"). Stable: one row per top-level call; `latency_ms` includes retry time. |
| Leak flags | `leak_flags` | ✅ |
| Export a CSV/JSONL | `export_telemetry.py` | ✅ (CSV columns mirror the JSONL fields above) |

## Cost estimation

Costs are estimated from `configs/model_prices.yaml` (USD per **1,000** tokens,
`in` = prompt, `out` = completion):

```yaml
version: 1
prices:
  gpt-4o-mini: { in: 0.00015, out: 0.0006 }
  gpt-4o:      { in: 0.0025,  out: 0.01 }
  # local / self-hosted → no vendor cost
  qwen2.5-7b-instruct-awq: { in: 0.0, out: 0.0 }
```

Lookup order: exact model name → case-insensitive → prefix match. An unknown
model estimates `cost_usd_est: 0.0` **and** adds `cost_unknown_model` to
`leak_flags`, so a missing price entry is auditable rather than silently zero.

## Exporting telemetry

`scripts/export_telemetry.py` is standalone (stdlib only — it does **not** need
the #20 experiment harness). It reads one or more `llm_telemetry.jsonl` files
(or sim dirs, or globs) and writes a flat CSV plus a JSONL summary:

```bash
python scripts/export_telemetry.py \
  --input <sim_dir> \
  --out-csv results/telemetry.csv \
  --out-summary results/telemetry_summary.jsonl
```

`--input` accepts a simulation directory (resolved to its `llm_telemetry.jsonl`),
a JSONL file path, or a glob — and any number of them. The summary contains
overall totals (`calls, tokens_in, tokens_out, cost_usd_est, latency_sec,
mean_latency_ms, errors, parse_errors`) and a per-model breakdown.

## Smoke run

`examples/multimodel-smoke-evidence/` is the reproducible recipe **and the final S2 evidence**
for an end-to-end multi-agent / 2-model run against real OpenAI-compatible
endpoints. The real run was **executed** (2026-06-06) against the Gemini
OpenAI-compatible endpoint — two real models, **no GPU required**: 18 calls,
9 per model, every call traceable to `(model, provider, tokens, cost, round)`.

The committed artifacts are the auditable record of that run:

- `examples/multimodel-smoke-evidence/model_routing_audit.jsonl` — agent → model/provider/base_url.
- `examples/multimodel-smoke-evidence/llm_telemetry.jsonl` — one line per LLM call.
- `examples/multimodel-smoke-evidence/telemetry.csv` + `telemetry_summary.jsonl` — exported tables.

`cost_usd_est` is `0.0` with a `cost_unknown_model` leak flag for the Gemini
models (no entry in `configs/model_prices.yaml`) — the documented
auditable-not-silent behavior, not a bug. The unit suite (`test_model_routing.py`)
additionally covers the logic with mock providers. See
`examples/multimodel-smoke-evidence/README.md` for prerequisites, the run command (both the
local-GPU and no-GPU variants), and the acceptance check (agent 0 and agent 1
must use different models in `model_routing_audit.jsonl`).

## Scope & limitations

**Runner coverage.** Routing + telemetry are wired into
`backend/scripts/run_reddit_simulation.py` (the single-platform Reddit runner
used by the simulation pipeline). `backend/scripts/run_parallel_simulation.py`
(dual Twitter+Reddit) is **not** wired: it builds **one model per platform**
(`create_model`, optionally split via `LLM_BOOST_*` env vars) and runs both
platforms concurrently with `asyncio.gather` — a single shared
`sink.current_round` would be racy across platforms, so wiring it requires
per-platform sinks and round contexts. Until then, parallel runs are
single-model per platform and produce **no** `llm_telemetry.jsonl`.

**Retries.** Provider-SDK retries (e.g. the OpenAI client's internal retry
loop) happen **below** the instrumented `run()`/`arun()`. Telemetry records
one row per top-level call: the final usage on success, or the final exception
in `error` (then re-raised). Individual retry attempts are not separately
counted, and `latency_ms` includes time spent in internal retries.

## Testing

```bash
cd backend && env -u PYTHONPATH .venv/bin/python -m pytest tests/test_model_routing.py -v
```

> Run tests with `.venv/bin/python` directly, **not** `uv run` — `uv run` fails
> dependency resolution here, and an unrelated ROS `launch_testing` plugin leaks
> in via `PYTHONPATH` (hence `env -u PYTHONPATH`). 21 tests cover validation,
> precedence, secrets enforcement, cost estimation, and the telemetry wrapper.
