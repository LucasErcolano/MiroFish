# S1 Heterogeneous LLM Agents Evidence

Date: 2026-05-22

Issue: #8, "S1 - Spike: heterogeneous LLM agents in one simulation run".

## Objective

Validate the minimum Reddit simulation path where two agents are pinned to two
different local OpenAI-compatible LLM endpoints, while preserving the previous
single-model behavior when no per-agent LLM metadata is present.

## Files Touched

Tracked code:

```text
backend/scripts/run_reddit_simulation.py
```

Docs:

```text
docs/local-llm-qwen-smoke.md
docs/local-llm-2agent-2model-notes.md
docs/s1-heterogeneous-llm-agents-evidence.md
```

Ignored local fixtures and outputs:

```text
backend/uploads/simulations/smoke_local_qwen_1agent/
backend/uploads/simulations/smoke_local_2agents_2models/
```

## Implementation Summary

Default behavior remains unchanged unless at least one `agent_configs[]` entry
contains one of:

```text
llm_model
llm_base_url
llm_api_key
```

Without those fields, the runner still calls the original OASIS path:

```text
generate_reddit_agent_graph(profile_path=profile_path, model=model, available_actions=...)
```

With those fields, the runner builds a deterministic `agent_id -> CAMEL model`
map, writes a redacted routing audit, and constructs the Reddit agent graph with
the same OASIS logic except for:

```text
SocialAgent(..., model=agent_models[i], ...)
```

This local copy is necessary for S1 because installed OASIS/CAMEL exposes one
global `model` argument in `generate_reddit_agent_graph`. Passing a list is not
per-agent routing: `SocialAgent` uses CAMEL `ChatAgent` with
`scheduling_strategy="random_model"`, so a list can randomly select a backend
per call.

## Runtime Setup

Validated local endpoints:

```text
agent 0 -> qwen2.5-7b-instruct-awq -> http://127.0.0.1:8000/v1
agent 1 -> mistral-7b-instruct-v0.3-awq -> http://127.0.0.1:8001/v1
```

Both AWQ servers were started without `--cpu-offload-gb`.

Important runtime note:

```text
Mistral AWQ must be served with --tokenizer pointing to the original
mistralai/Mistral-7B-Instruct-v0.3 snapshot. The solidrust AWQ tokenizer
template rejects system/tool messages.
```

Observed GPU state after both servers were running:

```text
RTX 3090: about 12.6 GiB used, about 11.7 GiB free.
Qwen AWQ model loading took 5.29 GiB GPU memory.
Mistral AWQ model loading took 3.89 GiB GPU memory.
```

## Verification Commands

Syntax check:

```powershell
cd C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish\backend
uv run --frozen python -m py_compile scripts\run_reddit_simulation.py
```

Routing gate helper:

```powershell
cd C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish\backend
@'
from pathlib import Path
from scripts.run_reddit_simulation import RedditSimulationRunner

single = Path("uploads/simulations/smoke_local_qwen_1agent/simulation_config.json")
two = Path("uploads/simulations/smoke_local_2agents_2models/simulation_config.json")

single_runner = RedditSimulationRunner(str(single))
two_runner = RedditSimulationRunner(str(two))

assert not single_runner._has_per_agent_llm_config()
assert two_runner._has_per_agent_llm_config()
print("routing gate helper ok")
'@ | uv run --frozen python -
```

Single-model regression smoke:

```powershell
cd C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish\backend
$env:LLM_API_KEY="local-dev"
$env:LLM_BASE_URL="http://127.0.0.1:8000/v1"
$env:LLM_MODEL_NAME="qwen2.5-7b-instruct-awq"
$env:PYTHONIOENCODING="utf-8"
uv run --frozen python scripts\run_reddit_simulation.py --config "uploads\simulations\smoke_local_qwen_1agent\simulation_config.json" --max-rounds 1 --no-wait
```

Two-agent / two-model smoke:

```powershell
cd C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish\backend
$env:LLM_API_KEY="local-dev"
$env:LLM_BASE_URL="http://127.0.0.1:8000/v1"
$env:LLM_MODEL_NAME="qwen2.5-7b-instruct-awq"
$env:PYTHONIOENCODING="utf-8"
uv run --frozen python scripts\run_reddit_simulation.py --config "uploads\simulations\smoke_local_2agents_2models\simulation_config.json" --max-rounds 1 --no-wait
```

## Results

Syntax check:

```text
Exit code: 0
```

Routing gate helper:

```text
Exit code: 0
routing gate helper ok
```

Single-model regression:

```text
Exit code: 0
Round elapsed: 1.5s
DB created: backend/uploads/simulations/smoke_local_qwen_1agent/reddit_simulation.db
DB size: 94208 bytes
model_routing_audit.jsonl created: false
```

The single-model output printed the global path marker:

```text
LLM config: model=qwen2.5-7b-instruct-awq, base_url=http://127.0.0.1:8000/v1...
```

It did not print `Model routing audit`, which confirms it did not take the
per-agent routing path.

Two-agent / two-model smoke:

```text
Exit code: 0
Round elapsed: 2.0s
DB created: backend/uploads/simulations/smoke_local_2agents_2models/reddit_simulation.db
DB size: 94208 bytes
No timeout observed
No CAMEL/OASIS model error observed
```

Audit file:

```text
backend/uploads/simulations/smoke_local_2agents_2models/model_routing_audit.jsonl
```

Relevant audit content, redacted:

```json
{"agent_id": 0, "model": "qwen2.5-7b-instruct-awq", "base_url": "http://127.0.0.1:8000/v1", "api_key_set": true, "source": "agent_configs"}
{"agent_id": 1, "model": "mistral-7b-instruct-v0.3-awq", "base_url": "http://127.0.0.1:8001/v1", "api_key_set": true, "source": "agent_configs"}
```

## Limitations

- This is an S1 spike, not the final S2 architecture.
- Per-agent routing is implemented only for the Reddit runner.
- The implementation intentionally does not add fallback behavior.
- The implementation intentionally does not add dynamic routing.
- The local graph construction duplicates OASIS Reddit graph creation because
  OASIS does not expose a per-agent model hook.
- The smoke fixtures live under `backend/uploads/`, which is ignored local
  runtime data.

## Recreate Ignored 2-Agent Fixture

`backend/uploads/` is ignored, so a clean checkout must recreate the local smoke
fixture before running the two-agent verification.

From repo root in PowerShell:

```powershell
cd C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish
New-Item -ItemType Directory -Force -Path "backend\uploads\simulations\smoke_local_2agents_2models" | Out-Null

@'
[
  {
    "user_id": 0,
    "username": "smoke_agent_qwen",
    "realname": "Smoke Agent Qwen",
    "name": "Smoke Agent Qwen",
    "bio": "A local LLM smoke-test participant routed to Qwen.",
    "persona": "You are a concise participant in a minimal Reddit-like simulation. Write short, direct posts and comments.",
    "karma": 100,
    "created_at": "2026-05-22",
    "age": 30,
    "gender": "unspecified",
    "mbti": "ISTJ",
    "country": "Argentina",
    "profession": "Test participant",
    "interested_topics": ["local LLM smoke test", "routing"]
  },
  {
    "user_id": 1,
    "username": "smoke_agent_mistral",
    "realname": "Smoke Agent Mistral",
    "name": "Smoke Agent Mistral",
    "bio": "A local LLM smoke-test participant routed to Mistral.",
    "persona": "You are a concise participant in a minimal Reddit-like simulation. Write short, direct posts and comments.",
    "karma": 90,
    "created_at": "2026-05-22",
    "age": 31,
    "gender": "unspecified",
    "mbti": "INTJ",
    "country": "Argentina",
    "profession": "Test participant",
    "interested_topics": ["local LLM smoke test", "multi model routing"]
  }
]
'@ | Set-Content -LiteralPath "backend\uploads\simulations\smoke_local_2agents_2models\reddit_profiles.json" -Encoding UTF8

@'
{
  "simulation_id": "smoke_local_2agents_2models",
  "project_id": "local_smoke",
  "graph_id": "local_smoke_graph",
  "simulation_requirement": "Minimal local LLM smoke test with two Reddit agents pinned to two OpenAI-compatible local endpoints.",
  "time_config": {
    "total_simulation_hours": 1,
    "minutes_per_round": 60,
    "agents_per_hour_min": 2,
    "agents_per_hour_max": 2,
    "peak_hours": [0],
    "peak_activity_multiplier": 1.0,
    "off_peak_hours": [],
    "off_peak_activity_multiplier": 1.0,
    "morning_hours": [],
    "morning_activity_multiplier": 1.0,
    "work_hours": [],
    "work_activity_multiplier": 1.0
  },
  "agent_configs": [
    {
      "agent_id": 0,
      "entity_uuid": "smoke-agent-qwen",
      "entity_name": "Smoke Agent Qwen",
      "entity_type": "person",
      "activity_level": 1.0,
      "posts_per_hour": 1.0,
      "comments_per_hour": 0.0,
      "active_hours": [0],
      "response_delay_min": 0,
      "response_delay_max": 0,
      "sentiment_bias": 0.0,
      "stance": "neutral",
      "influence_weight": 1.0,
      "llm_model": "qwen2.5-7b-instruct-awq",
      "llm_base_url": "http://127.0.0.1:8000/v1",
      "llm_api_key": "local-dev"
    },
    {
      "agent_id": 1,
      "entity_uuid": "smoke-agent-mistral",
      "entity_name": "Smoke Agent Mistral",
      "entity_type": "person",
      "activity_level": 1.0,
      "posts_per_hour": 1.0,
      "comments_per_hour": 0.0,
      "active_hours": [0],
      "response_delay_min": 0,
      "response_delay_max": 0,
      "sentiment_bias": 0.0,
      "stance": "neutral",
      "influence_weight": 1.0,
      "llm_model": "mistral-7b-instruct-v0.3-awq",
      "llm_base_url": "http://127.0.0.1:8001/v1",
      "llm_api_key": "local-dev"
    }
  ],
  "event_config": {
    "initial_posts": [],
    "scheduled_events": [],
    "hot_topics": ["local LLM smoke test", "multi model routing"],
    "narrative_direction": "Validate that two local OpenAI-compatible models can drive two pinned Reddit agents."
  },
  "twitter_config": null,
  "reddit_config": {
    "platform": "reddit",
    "recency_weight": 0.4,
    "popularity_weight": 0.3,
    "relevance_weight": 0.3,
    "viral_threshold": 10,
    "echo_chamber_strength": 0.1
  },
  "llm_model": "qwen2.5-7b-instruct-awq",
  "llm_base_url": "http://127.0.0.1:8000/v1",
  "generated_at": "2026-05-22T00:00:00",
  "generation_reasoning": "Manual minimal fixture for local two-agent/two-model smoke test."
}
'@ | Set-Content -LiteralPath "backend\uploads\simulations\smoke_local_2agents_2models\simulation_config.json" -Encoding UTF8

python -m json.tool "backend\uploads\simulations\smoke_local_2agents_2models\reddit_profiles.json" > $null
python -m json.tool "backend\uploads\simulations\smoke_local_2agents_2models\simulation_config.json" > $null
```

`local-dev` is the dummy local vLLM API key used by the smoke servers, not a
secret.

## S2 Follow-Up

- Add or upstream an OASIS extension point such as
  `generate_reddit_agent_graph(..., model_by_agent_id=None)`.
- Remove the local copied graph construction after OASIS supports per-agent
  model assignment.
- Decide whether `agent_configs[]` is the permanent API for model routing or
  whether this metadata should move into a dedicated simulation/runtime schema.
- Add proper automated tests around per-agent routing once the API shape is
  accepted.
