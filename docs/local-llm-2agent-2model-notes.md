# Local 2-Agent / 2-Model Spike Notes

Date: 2026-05-22

This note captures the current state of the phase 2 issue #8 spike: two Reddit
agents pinned to two local OpenAI-compatible vLLM endpoints, preserving default
single-model behavior when no per-agent LLM config is present.

## Code Changes

Touched file:

```text
backend/scripts/run_reddit_simulation.py
```

Implemented:

- Per-agent LLM routing is enabled only when an `agent_configs[]` entry contains
  one of:
  - `llm_model`
  - `llm_base_url`
  - `llm_api_key`
- If no per-agent LLM fields exist, the runner still uses the previous global
  `generate_reddit_agent_graph(profile_path, model, available_actions)` path.
- When per-agent routing is active, the runner creates one CAMEL OpenAI model
  backend per `agent_id`.
- The runner writes:

```text
backend/uploads/simulations/<simulation_id>/model_routing_audit.jsonl
```

Each audit row contains:

```json
{
  "timestamp": "...",
  "agent_id": 0,
  "model": "qwen2.5-7b-instruct",
  "base_url": "http://127.0.0.1:8000/v1",
  "api_key_set": true,
  "source": "agent_configs"
}
```

## OASIS / CAMEL Finding

Installed OASIS/CAMEL does not expose clean per-agent model routing through
`generate_reddit_agent_graph`.

Observed in `backend/.venv/Lib/site-packages/oasis/social_agent/agents_generator.py`:

- `generate_reddit_agent_graph(profile_path, model, available_actions)` accepts
  one `model` argument.
- It passes that same `model` object into every `SocialAgent`.

Observed in `backend/.venv/Lib/site-packages/oasis/social_agent/agent.py`:

- `SocialAgent` subclasses CAMEL `ChatAgent`.
- It calls `super().__init__(..., model=model, scheduling_strategy="random_model", ...)`.

Observed in CAMEL:

- Passing a list of models is not deterministic per agent.
- CAMEL wraps the list in `ModelManager` and `random_model()` randomly chooses
  a backend per call.

Therefore, pinning `agent_id -> model` required a local copy of OASIS' Reddit
graph construction inside the runner, with the only behavioral change being:

```text
SocialAgent(..., model=agent_models[i], ...)
```

S2 cleanup candidate:

- Add or upstream a small OASIS extension point:
  `generate_reddit_agent_graph(..., model_by_agent_id=None)` or similar.
- Then remove the local copy from MiroFish.

## Local Endpoints Tried

### Qwen on port 8000

Model:

```text
qwen2.5-7b-instruct
```

Snapshot:

```text
/mnt/c/Users/joaco/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28
```

Working vLLM flags for two-model coexistence:

```text
--served-model-name qwen2.5-7b-instruct
--host 127.0.0.1
--port 8000
--api-key local-dev
--gpu-memory-utilization 0.68
--kv-cache-memory-bytes 512M
--max-model-len 2048
--max-num-seqs 2
--safetensors-load-strategy prefetch
--enforce-eager
--enable-auto-tool-choice
--tool-call-parser hermes
```

Also required:

```text
VLLM_USE_FLASHINFER_SAMPLER=0
```

### Gemma on port 8001

Tried:

```text
gemma-3-4b-it
```

Snapshot:

```text
/mnt/c/Users/joaco/.cache/huggingface/hub/models--google--gemma-3-4b-it/snapshots/093f9f388b31de276ce2de164bdc2081324b9767
```

Result:

```text
FAILED before serving.
```

Reason:

```text
OSError: Can't load image processor ... missing preprocessor_config.json
```

vLLM resolved the architecture as `Gemma3ForConditionalGeneration`, which uses
multimodal processor loading. The cached snapshot has model/tokenizer files but
does not have the required image processor metadata for that vLLM path.

### Mistral on port 8001

Model:

```text
mistral-7b-instruct-v0.3
```

Snapshot:

```text
/mnt/c/Users/joaco/.cache/huggingface/hub/models--mistralai--Mistral-7B-Instruct-v0.3/snapshots/c170c708c41dac9275d15a8fff4eca08d52bab71
```

Working vLLM flags:

```text
--served-model-name mistral-7b-instruct-v0.3
--host 127.0.0.1
--port 8001
--api-key local-dev
--gpu-memory-utilization 0.30
--kv-cache-memory-bytes 256M
--cpu-offload-gb 10
--max-model-len 2048
--max-num-seqs 1
--safetensors-load-strategy prefetch
--enforce-eager
--enable-auto-tool-choice
--tool-call-parser mistral
```

Also required:

```text
VLLM_USE_FLASHINFER_SAMPLER=0
```

## Smoke Fixture

Created ignored local fixture:

```text
backend/uploads/simulations/smoke_local_2agents_2models/reddit_profiles.json
backend/uploads/simulations/smoke_local_2agents_2models/simulation_config.json
```

Routing:

```text
agent_id=0 -> qwen2.5-7b-instruct-awq -> http://127.0.0.1:8000/v1
agent_id=1 -> mistral-7b-instruct-v0.3-awq -> http://127.0.0.1:8001/v1
```

Because `backend/uploads/` is ignored, a clean checkout must recreate this
fixture before running the smoke. The copy-pasteable PowerShell block that
writes both JSON files is in:

```text
docs/s1-heterogeneous-llm-agents-evidence.md
```

See section:

```text
Recreate Ignored 2-Agent Fixture
```

## Historical Non-AWQ Verification Attempt

This section records the earlier non-quantized two-model attempt. It is kept as
debugging context only. The validated reproducible path is the later
`Validated AWQ Runtime Outcome` section.

Passing checks:

```text
uv run --frozen python -m py_compile scripts\run_reddit_simulation.py
```

Per-agent routing helper test passed:

```text
per-agent routing helper ok
```

Both endpoints passed plain chat and tool-call smoke after using
`--max-model-len 2048`:

```text
qwen2.5-7b-instruct plain ok
qwen2.5-7b-instruct tool_finish tool_calls tool_calls True
mistral-7b-instruct-v0.3 plain Ok.
mistral-7b-instruct-v0.3 tool_finish tool_calls tool_calls True
```

First Reddit run with `--max-model-len 1024`:

```text
FAILED as a smoke.
```

Reason:

```text
This model's maximum context length is 1024 tokens. However, you requested
0 output tokens and your prompt contains at least 1025 input tokens.
```

Second Reddit run with `--max-model-len 2048`:

```text
Ran to script exit code 0, wrote audit and DB, but Mistral timed out inside
CAMEL/OpenAI during the round.
```

Observed timeout:

```text
openai.APITimeoutError: Request timed out.
```

Round elapsed:

```text
723.9s
```

Historical interpretation:

- Routing works: both agents were assigned their intended model/base URL and the
  audit file was written.
- This non-AWQ attempt was not a clean success because Mistral timed out during
  the OASIS action call.

## Why It Is Slow

Main causes observed:

- Both models are loaded from Hugging Face snapshots under `/mnt/c/...`.
  In WSL this goes through the Windows filesystem bridge; vLLM logs report
  filesystem type `9P`, and loading Qwen shards took several minutes.
- Running Qwen 7B and Mistral 7B simultaneously on a 24 GB RTX 3090 is tight.
- Mistral was started with `--cpu-offload-gb 10` to make it coexist with Qwen.
  That means Mistral is not fully GPU-resident.
- CPU offload makes inference much slower and likely contributed to the CAMEL
  `APITimeoutError`.
- `--enforce-eager` disables some vLLM optimizations, but was kept to reduce
  memory pressure and avoid compile overhead/instability during the spike.

## GPU / Quantization Assessment

Not everything is running purely on GPU in the two-model attempt.

- Qwen is effectively GPU-resident.
- Mistral was intentionally run with `--cpu-offload-gb 10`, so part of its
  weights are offloaded through CPU memory.

Quantization would likely be the right next performance lever, but it was not
done in this spike. Better next options:

- Use a quantized Mistral/Gemma checkpoint for the second model.
- Use a smaller text-only second model.
- Move model snapshots into WSL native storage instead of `/mnt/c` to reduce
  startup time.
- Increase OpenAI/CAMEL request timeout only after model throughput is improved;
  timeout changes alone would hide the performance issue.

## AWQ Models Installed For Next Test

Installed on 2026-05-22 with `hf download`.

Qwen AWQ:

```text
repo: Qwen/Qwen2.5-7B-Instruct-AWQ
revision: b25037543e9394b818fdfca67ab2a00ecc7dd641
Windows path: C:\Users\joaco\.cache\huggingface\hub\models--Qwen--Qwen2.5-7B-Instruct-AWQ\snapshots\b25037543e9394b818fdfca67ab2a00ecc7dd641
WSL path: /mnt/c/Users/joaco/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct-AWQ/snapshots/b25037543e9394b818fdfca67ab2a00ecc7dd641
served model name: qwen2.5-7b-instruct-awq
quantization: AWQ 4-bit, group_size=128, version=gemm
safetensors size: 5.19 GiB
verified files: 12
```

Mistral AWQ:

```text
repo: solidrust/Mistral-7B-Instruct-v0.3-AWQ
revision: 95b1295ddd1a8673117cdc7bd2a4da2a457bb3f7
Windows path: C:\Users\joaco\.cache\huggingface\hub\models--solidrust--Mistral-7B-Instruct-v0.3-AWQ\snapshots\95b1295ddd1a8673117cdc7bd2a4da2a457bb3f7
WSL path: /mnt/c/Users/joaco/.cache/huggingface/hub/models--solidrust--Mistral-7B-Instruct-v0.3-AWQ/snapshots/95b1295ddd1a8673117cdc7bd2a4da2a457bb3f7
served model name: mistral-7b-instruct-v0.3-awq
quantization: AWQ 4-bit, group_size=128, version=gemm
safetensors size: 3.88 GiB
verified files: 10
```

Verification commands already passed:

```powershell
$env:PYTHONIOENCODING='utf-8'
hf cache verify Qwen/Qwen2.5-7B-Instruct-AWQ --fail-on-missing-files
hf cache verify solidrust/Mistral-7B-Instruct-v0.3-AWQ --fail-on-missing-files
```

Candidate vLLM start commands for the next run:

```powershell
$inner = 'rm -f /home/joaco/mirofish-vllm-qwen-awq-8000.log; export VLLM_USE_FLASHINFER_SAMPLER=0; exec /home/joaco/venvs/mirofish-vllm/bin/python -m vllm.entrypoints.openai.api_server --model /mnt/c/Users/joaco/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct-AWQ/snapshots/b25037543e9394b818fdfca67ab2a00ecc7dd641 --served-model-name qwen2.5-7b-instruct-awq --host 127.0.0.1 --port 8000 --api-key local-dev --gpu-memory-utilization 0.45 --kv-cache-memory-bytes 512M --max-model-len 2048 --max-num-seqs 2 --safetensors-load-strategy prefetch --enforce-eager --enable-auto-tool-choice --tool-call-parser hermes > /home/joaco/mirofish-vllm-qwen-awq-8000.log 2>&1'
$args = '-d Ubuntu-22.04 -- bash -lc "' + $inner + '"'
$p = Start-Process -FilePath wsl.exe -ArgumentList $args -WindowStyle Hidden -PassThru
```

```powershell
$inner = 'rm -f /home/joaco/mirofish-vllm-mistral-awq-8001.log; export VLLM_USE_FLASHINFER_SAMPLER=0; exec /home/joaco/venvs/mirofish-vllm/bin/python -m vllm.entrypoints.openai.api_server --model /mnt/c/Users/joaco/.cache/huggingface/hub/models--solidrust--Mistral-7B-Instruct-v0.3-AWQ/snapshots/95b1295ddd1a8673117cdc7bd2a4da2a457bb3f7 --tokenizer /mnt/c/Users/joaco/.cache/huggingface/hub/models--mistralai--Mistral-7B-Instruct-v0.3/snapshots/c170c708c41dac9275d15a8fff4eca08d52bab71 --served-model-name mistral-7b-instruct-v0.3-awq --host 127.0.0.1 --port 8001 --api-key local-dev --gpu-memory-utilization 0.35 --kv-cache-memory-bytes 512M --max-model-len 2048 --max-num-seqs 2 --safetensors-load-strategy prefetch --enforce-eager --enable-auto-tool-choice --tool-call-parser mistral > /home/joaco/mirofish-vllm-mistral-awq-8001.log 2>&1'
$args = '-d Ubuntu-22.04 -- bash -lc "' + $inner + '"'
$p = Start-Process -FilePath wsl.exe -ArgumentList $args -WindowStyle Hidden -PassThru
```

Important:

- Serve Mistral AWQ with `--tokenizer` pointing to the original BF16
  `mistralai/Mistral-7B-Instruct-v0.3` snapshot.
- The `solidrust` AWQ tokenizer template is too old for OASIS/CAMEL because it
  only supports alternating `user/assistant` messages and rejects `system` /
  tool-call messages.
- The original Mistral v0.3 tokenizer template supports the system/tool message
  shape that OASIS sends.

## Validated AWQ Runtime Outcome

Validated on 2026-05-22:

```text
Qwen AWQ on http://127.0.0.1:8000/v1
Mistral AWQ on http://127.0.0.1:8001/v1
No --cpu-offload-gb
max_model_len=2048
```

Observed vLLM memory:

```text
Qwen AWQ model loading took 5.29 GiB GPU memory.
Mistral AWQ model loading took 3.89 GiB GPU memory.
Both servers together used about 12.4 GiB VRAM, leaving about 11.9 GiB free.
```

Endpoint checks passed:

```text
qwen2.5-7b-instruct-awq plain 'ok'
qwen2.5-7b-instruct-awq tool_finish tool_calls tool_calls True
mistral-7b-instruct-v0.3-awq plain ' Ok.'
mistral-7b-instruct-v0.3-awq tool_finish tool_calls tool_calls True
```

The ignored local fixture was updated to AWQ model names:

```text
backend/uploads/simulations/smoke_local_2agents_2models/simulation_config.json
```

Validated Reddit smoke:

```powershell
cd C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish\backend
$env:LLM_API_KEY="local-dev"
$env:LLM_BASE_URL="http://127.0.0.1:8000/v1"
$env:LLM_MODEL_NAME="qwen2.5-7b-instruct-awq"
$env:PYTHONIOENCODING="utf-8"
uv run --frozen python scripts\run_reddit_simulation.py --config "uploads\simulations\smoke_local_2agents_2models\simulation_config.json" --max-rounds 1 --no-wait
```

Result:

```text
Exit code: 0
Round elapsed: 2.1s
No timeout
No OASIS/CAMEL model error
DB: backend/uploads/simulations/smoke_local_2agents_2models/reddit_simulation.db
DB size: 94208 bytes
```

Audit file:

```text
backend/uploads/simulations/smoke_local_2agents_2models/model_routing_audit.jsonl
```

Audit content:

```json
{"agent_id": 0, "model": "qwen2.5-7b-instruct-awq", "base_url": "http://127.0.0.1:8000/v1", "api_key_set": true, "source": "agent_configs"}
{"agent_id": 1, "model": "mistral-7b-instruct-v0.3-awq", "base_url": "http://127.0.0.1:8001/v1", "api_key_set": true, "source": "agent_configs"}
```

Conclusion:

```text
The local 2-agent / 2-model Reddit smoke path is validated with AWQ models.
The previous blocker was runtime performance and Mistral CPU offload, not the
per-agent routing implementation.
```
