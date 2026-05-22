# Local Qwen vLLM Smoke Runbook

This runbook documents the validated local path for MiroFish issue #8 style work: one local model, one OASIS Reddit agent, one minimal simulation round.

Validated on:

- Windows PowerShell host.
- WSL distribution: `Ubuntu-22.04`.
- GPU: `NVIDIA GeForce RTX 3090`, 24 GB VRAM.
- Backend Python: 3.11 via `uv`.
- Local server: vLLM OpenAI-compatible API.

Do not use this runbook to implement multi-model routing. First prove this one-model path, then design multi-model routing separately.

## Key Architecture Facts

MiroFish does not load Hugging Face model paths directly in simulation code. It talks to LLMs through OpenAI-compatible APIs:

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL_NAME`

Relevant backend files:

- `backend/app/config.py`
- `backend/app/utils/llm_client.py`
- `backend/app/services/simulation_config_generator.py`
- `backend/scripts/run_reddit_simulation.py`
- `backend/scripts/run_twitter_simulation.py`
- `backend/scripts/run_parallel_simulation.py`

The validated model name/base URL are:

```text
LLM_MODEL_NAME=qwen2.5-7b-instruct
LLM_BASE_URL=http://127.0.0.1:8000/v1
LLM_API_KEY=local-dev
```

Local model snapshot:

```text
C:\Users\joaco\.cache\huggingface\hub\models--Qwen--Qwen2.5-7B-Instruct\snapshots\a09a35458c702b33eeacc393d103063234e8bc28
```

WSL path for the same snapshot:

```text
/mnt/c/Users/joaco/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28
```

## 1. Confirm Machine State

From repo root:

```powershell
cd C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish
rtk git status --short
nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,driver_version --format=csv,noheader
py -0p
uv python list --only-installed
```

Proceed only if Python 3.11 is available and the RTX 3090 has enough free VRAM. The previous successful run used around 20 GB VRAM while serving.

Check port `8000`:

```powershell
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
  Where-Object { $_.LocalPort -eq 8000 } |
  Select-Object LocalAddress,LocalPort,OwningProcess
```

If port `8000` is already used, choose another port and update every later command consistently.

## 2. Sync Backend Dependencies

```powershell
cd C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish\backend
uv sync --python 3.11 --frozen
uv run --frozen python -c "import openai, flask, camel; print('backend imports ok')"
```

Use `uv run --frozen`. A plain `uv run` can try to resolve dependency groups for other Python versions and fail because `camel-oasis==0.2.5` pins `neo4j==5.23.0` while the project requires `neo4j>=5.26.0`.

## 3. Install vLLM In WSL

Use WSL Ubuntu 22.04:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "python3 --version && nvidia-smi"
```

If `python3 -m venv` fails with missing `ensurepip`, install venv support:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "sudo -n apt-get update && sudo -n apt-get install -y python3.10-venv"
```

Create the vLLM env outside the repo:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "python3 -m venv --clear ~/venvs/mirofish-vllm && source ~/venvs/mirofish-vllm/bin/activate && pip install -U pip && pip install vllm"
```

## 4. Start Qwen vLLM Server

Start the server from PowerShell. This uses `Start-Process` so the WSL process stays alive outside the Codex shell command.

```powershell
$inner = 'rm -f /home/joaco/mirofish-vllm-qwen.log; export VLLM_USE_FLASHINFER_SAMPLER=0; exec /home/joaco/venvs/mirofish-vllm/bin/python -m vllm.entrypoints.openai.api_server --model /mnt/c/Users/joaco/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28 --served-model-name qwen2.5-7b-instruct --host 127.0.0.1 --port 8000 --api-key local-dev --gpu-memory-utilization 0.80 --max-model-len 4096 --safetensors-load-strategy prefetch --enable-auto-tool-choice --tool-call-parser hermes > /home/joaco/mirofish-vllm-qwen.log 2>&1'
$args = '-d Ubuntu-22.04 -- bash -lc "' + $inner + '"'
$p = Start-Process -FilePath wsl.exe -ArgumentList $args -WindowStyle Hidden -PassThru
Write-Output "started-vllm-wsl-pid=$($p.Id)"
```

Why these flags matter:

- `VLLM_USE_FLASHINFER_SAMPLER=0`: avoids FlashInfer sampler JIT requiring `nvcc` and `/usr/local/cuda`.
- `--safetensors-load-strategy prefetch`: helps when loading the Hugging Face snapshot from `/mnt/c` over WSL 9P.
- `--enable-auto-tool-choice --tool-call-parser hermes`: required because OASIS/CAMEL sends `tool_choice="auto"`; vLLM rejects that without tool calling enabled. vLLM documents Hermes parser support for Qwen2.5 at <https://docs.vllm.ai/en/latest/features/tool_calling.html>.

Expect first startup to take several minutes. Watch logs:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "tail -n 120 /home/joaco/mirofish-vllm-qwen.log"
```

Stop the server:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "pkill -f 'vllm.entrypoints.openai.api_server|api_server' || true"
```

## 5. Verify Endpoint Contract

Check model list:

```powershell
Invoke-RestMethod -Headers @{ Authorization = "Bearer local-dev" } `
  -Uri "http://127.0.0.1:8000/v1/models" `
  -Method Get
```

Expected model id:

```text
qwen2.5-7b-instruct
```

Plain chat smoke:

```powershell
cd C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish\backend
@'
from openai import OpenAI
client = OpenAI(api_key="local-dev", base_url="http://127.0.0.1:8000/v1")
resp = client.chat.completions.create(
    model="qwen2.5-7b-instruct",
    messages=[{"role": "user", "content": "Reply with exactly: ok"}],
    temperature=0,
    max_tokens=8,
)
print(resp.choices[0].message.content)
'@ | .\.venv\Scripts\python.exe -
```

Expected:

```text
ok
```

JSON smoke:

```powershell
@'
from openai import OpenAI
client = OpenAI(api_key="local-dev", base_url="http://127.0.0.1:8000/v1")
resp = client.chat.completions.create(
    model="qwen2.5-7b-instruct",
    messages=[
        {"role": "system", "content": "Return only a JSON object."},
        {"role": "user", "content": "Return {\"status\":\"ok\"}."},
    ],
    response_format={"type": "json_object"},
    temperature=0,
    max_tokens=32,
)
print(resp.choices[0].message.content)
'@ | .\.venv\Scripts\python.exe -
```

Expected:

```json
{"status":"ok"}
```

Tool-choice smoke:

```powershell
@'
from openai import OpenAI
client = OpenAI(api_key="local-dev", base_url="http://127.0.0.1:8000/v1")
resp = client.chat.completions.create(
    model="qwen2.5-7b-instruct",
    messages=[{"role": "user", "content": "Use the tool."}],
    tools=[{"type":"function","function":{"name":"noop","description":"No-op test","parameters":{"type":"object","properties":{},"additionalProperties":False}}}],
    tool_choice="auto",
    temperature=0,
    max_tokens=32,
)
print(resp.choices[0].finish_reason)
print(resp.choices[0].message.tool_calls or resp.choices[0].message.content)
'@ | .\.venv\Scripts\python.exe -
```

Expected first line:

```text
tool_calls
```

## 6. Verify MiroFish Client

```powershell
cd C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish\backend
$env:LLM_API_KEY="local-dev"
$env:LLM_BASE_URL="http://127.0.0.1:8000/v1"
$env:LLM_MODEL_NAME="qwen2.5-7b-instruct"

uv run --frozen python -c "from app.utils.llm_client import LLMClient; print(LLMClient().chat([{'role':'user','content':'Reply with exactly: ok'}], temperature=0, max_tokens=8))"
uv run --frozen python -c "from app.services.simulation_config_generator import SimulationConfigGenerator; g=SimulationConfigGenerator(); print(g.model_name, g.base_url)"
```

Expected:

```text
ok
qwen2.5-7b-instruct http://127.0.0.1:8000/v1
```

## 7. Create Minimal Reddit Fixture

`backend/uploads/` is gitignored, so a fresh checkout must recreate these files.

```powershell
cd C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish
New-Item -ItemType Directory -Force -Path "backend\uploads\simulations\smoke_local_qwen_1agent" | Out-Null
```

Create `backend\uploads\simulations\smoke_local_qwen_1agent\reddit_profiles.json`:

```json
[
  {
    "user_id": 0,
    "username": "smoke_agent_0",
    "realname": "Smoke Agent Zero",
    "name": "Smoke Agent Zero",
    "bio": "A single local LLM smoke-test participant.",
    "persona": "You are a concise participant in a minimal Reddit-like simulation. Write short, direct posts and comments.",
    "karma": 100,
    "created_at": "2026-05-22",
    "age": 30,
    "gender": "unspecified",
    "mbti": "ISTJ",
    "country": "Argentina",
    "profession": "Test participant",
    "interested_topics": ["local LLM smoke test"]
  }
]
```

`mbti` is required by `oasis.social_agent.agents_generator.generate_reddit_agent_graph`; omitting it causes `KeyError: 'mbti'`.

Create `backend\uploads\simulations\smoke_local_qwen_1agent\simulation_config.json`:

```json
{
  "simulation_id": "smoke_local_qwen_1agent",
  "project_id": "local_smoke",
  "graph_id": "local_smoke_graph",
  "simulation_requirement": "Minimal local LLM smoke test with one Reddit agent and one round.",
  "time_config": {
    "total_simulation_hours": 1,
    "minutes_per_round": 60,
    "agents_per_hour_min": 1,
    "agents_per_hour_max": 1,
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
      "entity_uuid": "smoke-agent-0",
      "entity_name": "Smoke Agent Zero",
      "entity_type": "person",
      "activity_level": 1.0,
      "posts_per_hour": 1.0,
      "comments_per_hour": 0.0,
      "active_hours": [0],
      "response_delay_min": 0,
      "response_delay_max": 0,
      "sentiment_bias": 0.0,
      "stance": "neutral",
      "influence_weight": 1.0
    }
  ],
  "event_config": {
    "initial_posts": [],
    "scheduled_events": [],
    "hot_topics": ["local LLM smoke test"],
    "narrative_direction": "Validate that one local OpenAI-compatible model can drive one simulation agent."
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
  "llm_model": "qwen2.5-7b-instruct",
  "llm_base_url": "http://127.0.0.1:8000/v1",
  "generated_at": "2026-05-22T00:00:00",
  "generation_reasoning": "Manual minimal fixture for local LLM smoke test."
}
```

Validate JSON:

```powershell
python -m json.tool "backend\uploads\simulations\smoke_local_qwen_1agent\reddit_profiles.json" > $null
python -m json.tool "backend\uploads\simulations\smoke_local_qwen_1agent\simulation_config.json" > $null
```

## 8. Run One-Agent Reddit Simulation

Use UTF-8 console output on Windows:

```powershell
cd C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish\backend
$env:LLM_API_KEY="local-dev"
$env:LLM_BASE_URL="http://127.0.0.1:8000/v1"
$env:LLM_MODEL_NAME="qwen2.5-7b-instruct"
$env:PYTHONIOENCODING="utf-8"

uv run --frozen python scripts\run_reddit_simulation.py --config "uploads\simulations\smoke_local_qwen_1agent\simulation_config.json" --max-rounds 1 --no-wait
```

Success criteria:

- Script exits with code 0.
- It initializes the LLM model.
- It loads one Reddit profile.
- It creates OASIS environment.
- It runs one round without traceback.
- It writes `reddit_simulation.db` under `backend\uploads\simulations\smoke_local_qwen_1agent`.

Inspect outputs:

```powershell
cd C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish
Get-ChildItem "backend\uploads\simulations\smoke_local_qwen_1agent" -Recurse |
  Select-Object FullName,Length,LastWriteTime
```

Optional DB sanity check:

```powershell
@'
import sqlite3
from pathlib import Path
p = Path("backend/uploads/simulations/smoke_local_qwen_1agent/reddit_simulation.db")
print(p.exists(), p.stat().st_size if p.exists() else 0)
con = sqlite3.connect(p)
print([row[0] for row in con.execute("select name from sqlite_master where type='table' order by name")])
con.close()
'@ | python -
```

## Known Failure Modes

### `python3 -m venv` fails in WSL

Install:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "sudo -n apt-get update && sudo -n apt-get install -y python3.10-venv"
```

### vLLM fails with missing `nvcc`

Symptom:

```text
RuntimeError: Could not find nvcc and default cuda_home='/usr/local/cuda' doesn't exist
```

Use:

```bash
export VLLM_USE_FLASHINFER_SAMPLER=0
```

Do this before starting vLLM.

### vLLM rejects `tool_choice="auto"`

Symptom:

```text
"auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set
```

Start vLLM with:

```text
--enable-auto-tool-choice --tool-call-parser hermes
```

### Reddit profile fails with `KeyError: 'mbti'`

Add `"mbti": "ISTJ"` to each Reddit profile object.

### Windows console crashes with `UnicodeEncodeError`

Set:

```powershell
$env:PYTHONIOENCODING="utf-8"
```

### `pytest` fails against LM Studio

`backend/scripts/test_lmstudio.py` hard-codes:

```text
LLM_MODEL_NAME=lmstudio/deepseek/deepseek-r1-0528-qwen3-8b
LLM_BASE_URL=http://localhost:1234/v1
LLM_API_KEY=lm-studio
```

Those tests fail if LM Studio is not running. That is separate from the validated Qwen/vLLM smoke.

## Validated Outcome

The validated base is:

```text
One MiroFish/OASIS Reddit agent can call one local Qwen2.5-7B-Instruct model through an OpenAI-compatible vLLM endpoint.
```

Next separate step:

```text
Introduce per-agent model metadata in simulation config, then route agent LLM calls to the correct OpenAI-compatible client. Start with two local endpoints: Qwen on port 8000 and Gemma or Mistral on port 8001. Keep default behavior unchanged when per-agent config is absent.
```

