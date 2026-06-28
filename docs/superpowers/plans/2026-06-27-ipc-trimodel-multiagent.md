# IPC Tri-Model Multi-Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete a reproducible IPC 2025 benchmark where one MiroFish simulation routes agents across Qwen, Gemma, and Llama, then evaluates temporal depth, simulation depth, and S3 noise resistance.

**Execution status (2026-06-28):** The benchmark matrix has been executed. The
canonical result summary is
`backtesting/ipc-trimodel-multiagent/RESULTS_ANALYSIS.md`; compact evidence is
under `backtesting/ipc-trimodel-multiagent/evaluation/`. The remaining work for
this branch is final validation, selective staging, commit, and push unless the
user asks for additional experiments.

**Architecture:** Keep benchmark-specific orchestration, state, and evidence under `backtesting/ipc-trimodel-multiagent/`. Reuse existing MiroFish backend, Graphiti, ReportAgent, IPC evaluator, and S3 runners where possible. Add only the minimal runner/code seams needed for model-map propagation, experimental memory, and a Graphiti dedup bypass.

**Tech Stack:** Python 3.11 via `uv`, MiroFish backend APIs, Graphiti/Neo4j, OASIS/CAMEL, OpenRouter Qwen, DeepInfra Gemma/Llama, Chroma-backed experimental memory, CSV/JSON/Markdown evidence.

---

### Task 1: Verify Workspace And Environment

**Files:**
- Modify: `backtesting/ipc-trimodel-multiagent/AGENT_STATE.md`
- Modify: `backtesting/ipc-trimodel-multiagent/TODO.md`
- Modify: `backtesting/ipc-trimodel-multiagent/RUNBOOK.md`

- [x] **Step 1: Verify branch and cleanliness**

Run:

```powershell
git status -sb
git branch --show-current
```

Expected:

```text
## codex/ipc-trimodel-multiagent
codex/ipc-trimodel-multiagent
```

- [x] **Step 2: Verify key presence without printing secrets**

Run:

```powershell
$names='OPENROUTER_API_KEY','DEEPINFRA_API_KEY'
foreach($n in $names){
  $v=[Environment]::GetEnvironmentVariable($n,'Process')
  $u=[Environment]::GetEnvironmentVariable($n,'User')
  [pscustomobject]@{Name=$n; ProcessPresent=[bool]$v; UserPresent=[bool]$u}
}
```

Expected: both keys present in either Process or User scope.

- [x] **Step 3: Set required non-secret env**

Run:

```powershell
$env:OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
$env:DEEPINFRA_BASE_URL = "https://api.deepinfra.com/v1/openai"
$env:USE_EXPERIMENTAL_MEMORY = "true"
$env:GRAPHITI_BYPASS_NODE_DEDUP = "true"
$env:PYTHONIOENCODING = "utf-8"
```

Expected: no output.

### Task 2: Implement Graphiti Dedup Bypass

**Files:**
- Modify: `backend/app/graph/graphiti_backend.py`
- Modify: `backtesting/ipc-trimodel-multiagent/RUNBOOK.md`
- Modify: `backtesting/ipc-trimodel-multiagent/LESSONS.md`

- [x] **Step 1: Locate node resolution block**

Read `backend/app/graph/graphiti_backend.py` around `_add_text_async`.

Expected: find the call to `resolve_extracted_nodes(...)`.

- [x] **Step 2: Add env-controlled bypass**

Implementation target:

```python
bypass_node_dedup = os.getenv("GRAPHITI_BYPASS_NODE_DEDUP", "").lower() in {
    "1",
    "true",
    "yes",
}
if bypass_node_dedup:
    nodes = extracted_nodes
    uuid_map = {node.name: node.uuid for node in nodes if getattr(node, "name", None)}
else:
    nodes, uuid_map, _ = await resolve_extracted_nodes(
        self._graphiti.clients,
        extracted_nodes,
        episode,
        previous_episodes,
        entity_types,
    )
```

If Graphiti node objects do not expose `name`/`uuid`, inspect with a one-row smoke and adjust to the minimum shape required by `_extract_and_resolve_edges`.

- [x] **Step 3: Compile**

Run:

```powershell
cd backend
uv run --frozen --python 3.11 python -m py_compile app\graph\graphiti_backend.py
```

Expected: exit code 0.

### Task 3: Restore Per-Agent Model Routing

**Files:**
- Create: `backend/app/services/model_router.py`
- Create: `backend/app/services/llm_telemetry.py`
- Create: `configs/model_prices.yaml`
- Modify: `backend/scripts/run_reddit_simulation.py`

- [x] **Step 1: Inspect source branch**

Run:

```powershell
git fetch origin --prune
git log --oneline -n 20 origin/backtesting-feature-augmented
git show origin/backtesting-feature-augmented:backend/app/services/model_router.py
git show origin/backtesting-feature-augmented:backend/app/services/llm_telemetry.py
git show origin/backtesting-feature-augmented:configs/model_prices.yaml
```

Expected: routing, telemetry, and model prices exist in
`origin/backtesting-feature-augmented`.

- [x] **Step 2: Reimport routing files and model prices**

Restore the needed files from `origin/backtesting-feature-augmented`, then
inspect the diff rather than blindly committing.

Run:

```powershell
git checkout origin/backtesting-feature-augmented -- backend/app/services/model_router.py backend/app/services/llm_telemetry.py configs/model_prices.yaml
git diff -- backend/app/services/model_router.py backend/app/services/llm_telemetry.py configs/model_prices.yaml
```

Expected: two new service files plus model prices in the working tree only
after review.

- [x] **Step 3: Fix hosted provider validation**

The source branch has a known mismatch: hosted maps use `openrouter` and
`deepinfra`, while `model_router.py` validates a smaller provider allowlist.
Either add those providers with env defaults or normalize the IPC model map to
`provider: openai` plus provider-specific `base_url_env`.

- [x] **Step 4: Reconnect runner integration**

Patch `backend/scripts/run_reddit_simulation.py` so it accepts `--model-map`,
builds routed per-agent backends, writes `model_routing_audit.jsonl`, and writes
telemetry to `llm_telemetry.jsonl`.

Use `origin/backtesting-feature-augmented:backend/scripts/run_reddit_simulation.py`
as the reference implementation, but preserve scheduled-injection changes from
the current branch. Do not copy the whole file.

- [x] **Step 5: Compile routing files**

Run:

```powershell
cd backend
uv run --frozen --python 3.11 python -m py_compile app\services\model_router.py app\services\llm_telemetry.py scripts\run_reddit_simulation.py
```

Expected: exit code 0.

### Task 4: Add IPC Tri-Model Runner

**Files:**
- Create: `backtesting/ipc-trimodel-multiagent/scripts/run_ipc_trimodel_matrix.py`
- Modify if needed: `tools/mirofish_headless.py`
- Modify if needed: `backtesting/scripts/run_final_temporal_optimum.py`
- Modify if needed: `backtesting/scripts/run_final_line5_matrix.py`

- [x] **Step 1: Start from existing runner patterns**

Read:

```text
backtesting/scripts/run_final_temporal_optimum.py
backtesting/scripts/run_final_line5_matrix.py
backtesting/s3-cross-topic-injection/scripts/run_s3_matrix.py
```

Expected: identify how they start backend, upload case files, generate report,
evaluate, and write compact evidence.

- [x] **Step 2: Ensure `--model-map` reaches simulation**

Trace command path:

```text
runner -> tools/mirofish_headless.py -> backend API -> backend/scripts/run_reddit_simulation.py
```

The final simulation invocation must pass:

```text
--model-map backtesting/ipc-trimodel-multiagent/model_map_ipc_trimodel.yaml
```

- [x] **Step 3: Runner outputs**

Each row must write raw artifacts under:

```text
runs/ipc_trimodel_multiagent/<line>/<variant>/
```

Each row must copy compact evidence under:

```text
backtesting/ipc-trimodel-multiagent/evaluation/<line>/<variant>/
```

Required compact files:

```text
report.md
eval_result.json
run_notes.md
model_routing_audit.jsonl
llm_telemetry_summary.json
```

### Task 5: Smoke Gate

**Files:**
- Modify: `backtesting/ipc-trimodel-multiagent/RUN_LEDGER.csv`
- Modify: `backtesting/ipc-trimodel-multiagent/AGENT_STATE.md`
- Modify: `backtesting/ipc-trimodel-multiagent/TODO.md`

- [x] **Step 1: Validate model map**

Run:

```powershell
cd backend
uv run --frozen --python 3.11 python -c "from app.services.model_router import load_model_map; m=load_model_map('..\backtesting\ipc-trimodel-multiagent\model_map_ipc_trimodel.yaml'); print('model_map_ok')"
```

Expected:

```text
model_map_ok
```

- [ ] **Step 2: Run one tiny smoke**

Run only one short IPC row after the runner exists, for example T0 with a small
round limit.

Expected artifacts:

```text
model_routing_audit.jsonl
llm_telemetry.jsonl or llm_telemetry_summary.json
eval_result.json
```

- [ ] **Step 3: Verify three models**

Parse `model_routing_audit.jsonl` and confirm it includes:

```text
qwen/qwen3-8b
google/gemma-3-27b-it
meta-llama/Llama-3.3-70B-Instruct-Turbo
```

### Task 6: Execute Temporal Matrix

**Files:**
- Modify: `backtesting/ipc-trimodel-multiagent/RUN_LEDGER.csv`
- Create: `backtesting/ipc-trimodel-multiagent/evaluation/temporal_summary.csv`
- Create: `backtesting/ipc-trimodel-multiagent/evaluation/temporal_summary.json`
- Create: `backtesting/ipc-trimodel-multiagent/evaluation/temporal_summary.md`

- [ ] **Step 1: Run T0**
- [ ] **Step 2: Run T1**
- [ ] **Step 3: Run T2**
- [ ] **Step 4: Run T3**
- [ ] **Step 5: Summarize**

For each row, record score, parse_errors, MAE, total tokens, estimated cost,
and whether experimental memory initialized.

### Task 7: Execute Line 5 Depth Matrix

**Files:**
- Modify: `backtesting/ipc-trimodel-multiagent/RUN_LEDGER.csv`
- Create: `backtesting/ipc-trimodel-multiagent/evaluation/line5_summary.csv`
- Create: `backtesting/ipc-trimodel-multiagent/evaluation/line5_summary.json`
- Create: `backtesting/ipc-trimodel-multiagent/evaluation/line5_summary.md`

- [ ] **Step 1: Run R10-D2**
- [ ] **Step 2: Run R20-D2**
- [ ] **Step 3: Run R40-D2**
- [ ] **Step 4: Run R80-D2**
- [ ] **Step 5: Compare R40 multi-agent vs R80 single-agent**

Use prior single-agent evidence where available and cite exact source files.

### Task 8: Execute S3 IPC Noise Matrix

**Files:**
- Modify: `backtesting/ipc-trimodel-multiagent/RUN_LEDGER.csv`
- Create: `backtesting/ipc-trimodel-multiagent/evaluation/s3_summary.csv`
- Create: `backtesting/ipc-trimodel-multiagent/evaluation/s3_summary.json`
- Create: `backtesting/ipc-trimodel-multiagent/evaluation/s3_summary.md`

- [ ] **Step 1: Run baseline-control**
- [ ] **Step 2: Run signal-early**
- [ ] **Step 3: Run signal-mid**
- [ ] **Step 4: Run signal-late**
- [ ] **Step 5: Run counter-signal-mid**
- [ ] **Step 6: Run noise-near-mid**
- [ ] **Step 7: Run noise-off-mid**
- [ ] **Step 8: Summarize delta MAE vs baseline**

Every injected condition must show expected scheduled event count.

### Task 9: Final Report And Delivery

**Files:**
- Create: `backtesting/ipc-trimodel-multiagent/evaluation/final_ipc_trimodel_report.md`
- Modify: `backtesting/ipc-trimodel-multiagent/README.md`
- Modify: `backtesting/ipc-trimodel-multiagent/AGENT_STATE.md`

- [ ] **Step 1: Write final report**

Include:

- temporal results;
- Line 5 economic comparison;
- S3 noise robustness;
- parse error reduction;
- model routing audit evidence;
- experimental memory evidence;
- caveats and failed rows.

- [ ] **Step 2: Validate**

Run:

```powershell
git diff --check
cd backend
uv run --frozen --python 3.11 python -m py_compile app\graph\graphiti_backend.py ..\backtesting\ipc-trimodel-multiagent\scripts\run_ipc_trimodel_matrix.py
```

- [ ] **Step 3: Secret and raw artifact scan**

Run:

```powershell
git diff --cached -G"<secret-prefix-regex>" --name-only
git diff --cached --name-only | Select-String -Pattern '^runs/|^backend/uploads|\\.sqlite3$|\\.log$'
git status --short
```

Expected: no live secrets and no raw `runs/` staged.

## Self-Review

Spec coverage:

- Temporal T0-T3: Task 5.
- Line 5 R10-R80 and R40 vs R80 economic claim: Task 6.
- S3 seven conditions: Task 7.
- Three models in one simulation: Tasks 3 and 4.
- Experimental memory: Tasks 1, 4, and report caveats.
- Dedup bypass before graph build: Task 2.
- Durable post-compaction state: `AGENTS.md`, `AGENT_STATE.md`, `TODO.md`,
  `RUNBOOK.md`, `RUN_LEDGER.csv`, `DECISIONS.md`, `LESSONS.md`,
  `THREAD_CONTEXT_DUMP.md`, and `HANDOFF_PROMPT.md`.
