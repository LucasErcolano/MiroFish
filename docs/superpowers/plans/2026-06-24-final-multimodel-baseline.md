# Final Multimodel Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the final research layer on top of `origin/backtesting-baseline`: temporal optimum cross-model runs, S3 Qwen Bolivia/IPC runs, and Line 5 Bolivia Gemma/Qwen R10-D2/R80-D2 runs.

**Final status:** Complete as of 2026-06-24. The executed scope is documented in `backtesting/final-multimodel/evaluation/final_multimodel_report.md`. Validation passed for Python compile, S3 package validation, JSON parsing, and secret scan. Commit and push are authorized; PR creation is explicitly out of scope.

**Architecture:** Keep the work in a separate worktree and branch, with all new code/configuration under `backtesting/final-multimodel/` or adjacent existing backtesting case folders when runner compatibility requires it. Reuse existing S3 and Line 5 runners where possible, add thin wrappers/config generators only where the current scripts are model-specific. Persist state after every meaningful discovery or long-running run in `backtesting/final-multimodel/AGENT_STATE.md`.

**Tech Stack:** Python 3 via `uv`, MiroFish backend APIs, existing `tools/mirofish_headless.py`, OpenRouter Qwen, DeepInfra Gemma/Llama, local Git/GitHub CLI for commit/push only.

---

## Scope

The authorized deliverable is commit + push, no PR.

Target branch:

```powershell
codex/final-multimodel-baseline
```

Target base:

```powershell
origin/backtesting-baseline
```

No files from the original dirty checkout should be staged. The active worktree is:

```text
C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish-final-multimodel
```

## File Map

- Create `backtesting/final-multimodel/AGENT_STATE.md`: durable context, decisions, commands, current blockers, and resume point.
- Create `backtesting/final-multimodel/RUN_LEDGER.csv`: append-only planned/started/completed/failed run ledger.
- Create `backtesting/final-multimodel/README.md`: final runbook and result index.
- Create `backtesting/final-multimodel/evaluation/final_multimodel_report.md`: final interpretation after all available runs.
- Create `backtesting/final-multimodel/evaluation/*.csv|*.json|*.md`: summary tables for each line.
- Modify `backtesting/s3-cross-topic-injection/matrix.yaml`: add Qwen model entry if missing.
- Modify or create `backtesting/s3-cross-topic-injection/evaluation/*qwen*`: generated Qwen summaries for Bolivia and IPC.
- Create `backtesting/scripts/run_final_temporal_optimum.py`: thin, case-aware runner for the six temporal-optimum runs if no existing generic runner is sufficient.
- Create `backtesting/scripts/run_final_line5_matrix.py` or extend `run_line5_llama_matrix.py` carefully if model-specific naming blocks Gemma/Qwen runs.
- Create Line 5 configs under `backtesting/case-b-s2-bolivia-2025-runoff/` for Gemma/Qwen R10-D2 and R80-D2 only.

## Task 1: Verify Workspace And Record State

**Files:**
- Create: `backtesting/final-multimodel/AGENT_STATE.md`
- Create: `backtesting/final-multimodel/RUN_LEDGER.csv`
- Create: `backtesting/final-multimodel/README.md`

- [ ] **Step 1: Verify clean worktree**

Run:

```powershell
rtk git status --short
rtk git branch --show-current
```

Expected:

```text
ok
codex/final-multimodel-baseline
```

- [ ] **Step 2: Verify API keys without printing them**

Run:

```powershell
$names='OPENROUTER_API_KEY','DEEPINFRA_API_KEY','LLM_API_KEY'
foreach($n in $names){
  $v=[Environment]::GetEnvironmentVariable($n,'Process')
  $u=[Environment]::GetEnvironmentVariable($n,'User')
  [pscustomobject]@{Name=$n; ProcessPresent=[bool]$v; UserPresent=[bool]$u}
}
```

Expected:

```text
OPENROUTER_API_KEY present
DEEPINFRA_API_KEY present
```

- [ ] **Step 3: Write durable state**

Add the current goal, base branch, known existing artifacts, and next command to `AGENT_STATE.md`.

- [ ] **Step 4: Initialize ledger**

Create CSV with columns:

```csv
line,topic,model,condition_or_variant,status,output_path,started_at,completed_at,notes
```

## Task 2: S3 Qwen Bolivia And IPC

**Files:**
- Modify: `backtesting/s3-cross-topic-injection/matrix.yaml`
- Possibly modify: `backtesting/s3-cross-topic-injection/scripts/run_s3_matrix.py`
- Generate: `backtesting/s3-cross-topic-injection/evaluation/qwen_*`
- Update: `backtesting/final-multimodel/AGENT_STATE.md`
- Update: `backtesting/final-multimodel/RUN_LEDGER.csv`

- [ ] **Step 1: Add Qwen model spec**

Add:

```yaml
  qwen:
    provider: openrouter
    model: qwen/qwen3-8b
    graphiti_llm_model: google/gemma-3-27b-it
    graphiti_key_env: DEEPINFRA_API_KEY
    graphiti_base_url: https://api.deepinfra.com/v1/openai
    base_url: https://openrouter.ai/api/v1
    key_env: OPENROUTER_API_KEY
```

If the runner only supports one `key_env` for both simulation and Graphiti, update the runner so simulation key/base URL come from `key_env/base_url`, while Graphiti can use `graphiti_key_env/graphiti_base_url/graphiti_llm_model`.

- [ ] **Step 2: Validate package**

Run from `backend/`:

```powershell
uv run --frozen python ../backtesting/s3-cross-topic-injection/scripts/validate_s3_package.py
```

Expected:

```text
topics=3 models=3 conditions=7
```

- [ ] **Step 3: Dry-run Qwen subset**

Run from `backend/`:

```powershell
uv run --frozen python ../backtesting/s3-cross-topic-injection/scripts/run_s3_matrix.py --full --dry-run --models qwen --topics bolivia,ipc
```

Expected: 14 planned rows, no missing API key.

- [ ] **Step 4: Execute Qwen subset**

Run from `backend/`:

```powershell
uv run --frozen python ../backtesting/s3-cross-topic-injection/scripts/run_s3_matrix.py --full --execute --start-backend --models qwen --topics bolivia,ipc
```

Expected:

```text
2 baselines fire 0 scheduled events
12 injected rows fire 1 scheduled event
```

- [ ] **Step 5: Summarize Qwen subset**

Run existing S3 summarizers or add a subset summarizer if needed. Update `AGENT_STATE.md` with exact valid count and failures.

## Task 3: Temporal Optimum Llama/Qwen

**Files:**
- Create: `backtesting/scripts/run_final_temporal_optimum.py`
- Create: `backtesting/final-multimodel/temporal_optimum_matrix.yaml`
- Generate: `backtesting/final-multimodel/evaluation/temporal_optimum_summary.*`
- Update: `backtesting/final-multimodel/AGENT_STATE.md`
- Update: `backtesting/final-multimodel/RUN_LEDGER.csv`

- [ ] **Step 1: Define six-row matrix**

Rows:

```yaml
- topic: bolivia
  package: T1
  input_file: backtesting/case-b-s2-bolivia-2025-runoff/seed_T1.md
  models: [llama, qwen]
- topic: copa
  package: T2
  input_file: backtesting/case-d-s2-copa-america-line5-gemma/seed_T2.md
  models: [llama, qwen]
- topic: ipc
  package: T3
  input_file: cases/CASE-B2-ARG-IPC-2025/input_pack_pre_x/seed_bundle.md
  models: [llama, qwen]
```

If IPC lacks T0-T3 packet files, document that IPC's selected optimum is the existing deepest available pre-cutoff packet and do not fabricate temporal files without source support.

- [ ] **Step 2: Implement thin runner**

The runner should:

- read matrix YAML;
- start/use backend with the selected model environment;
- upload only the selected evidence packet and question;
- generate report;
- run the existing case evaluator where available;
- write run artifacts under `backtesting/final-multimodel/output_temporal_optimum/<topic>/<model>/`.

- [ ] **Step 3: Dry-run**

Run:

```powershell
uv run --frozen python ../backtesting/scripts/run_final_temporal_optimum.py --dry-run
```

Expected: six planned rows.

- [ ] **Step 4: Execute rows**

Run:

```powershell
uv run --frozen python ../backtesting/scripts/run_final_temporal_optimum.py --execute --start-backend
```

If a row fails due to missing evaluator/schema, preserve raw report and mark `needs_manual_eval` in summaries.

## Task 4: Line 5 Bolivia Gemma/Qwen R10-D2 And R80-D2

**Files:**
- Create: `backtesting/case-b-s2-bolivia-2025-runoff/config_line5_gemma_slim.yaml`
- Create: `backtesting/case-b-s2-bolivia-2025-runoff/config_line5_qwen_slim.yaml`
- Create or modify: `backtesting/scripts/run_final_line5_matrix.py`
- Generate: `backtesting/final-multimodel/evaluation/line5_bolivia_summary.*`
- Update: `backtesting/final-multimodel/AGENT_STATE.md`
- Update: `backtesting/final-multimodel/RUN_LEDGER.csv`

- [ ] **Step 1: Create Gemma/Qwen slim configs**

Each config should include only:

```yaml
run_matrix:
  - id: "<model>_T3_slim_R10_D2"
    rounds: 10
    density: 2
  - id: "<model>_T3_slim_R80_D2"
    rounds: 80
    density: 2
```

Use `seed_T3_line5_slim.md` to stay comparable with existing Llama Line 5 results unless a later result proves T1 Line 5 is explicitly required.

- [ ] **Step 2: Dry-run Gemma/Qwen**

Run:

```powershell
uv run --frozen python ../backtesting/scripts/run_final_line5_matrix.py --case-dir ../backtesting/case-b-s2-bolivia-2025-runoff --models gemma,qwen --dry-run
```

Expected: four planned rows.

- [ ] **Step 3: Execute**

Run:

```powershell
uv run --frozen python ../backtesting/scripts/run_final_line5_matrix.py --case-dir ../backtesting/case-b-s2-bolivia-2025-runoff --models gemma,qwen --execute --start-backend
```

Expected: four `eval_result.json` files.

## Task 5: Final Report, Validation, Commit, Push

**Files:**
- Create: `backtesting/final-multimodel/evaluation/final_multimodel_report.md`
- Update: `backtesting/README.md`
- Update: `CHANGELOG-research.md`

- [ ] **Step 1: Write final report**

Include:

- what was run;
- what failed or was skipped;
- exact model/provider IDs;
- result tables;
- comparison to previous Gemma/Llama/Qwen baselines;
- methodological caveats.

- [ ] **Step 2: Validate scripts**

Run from `backend/`:

```powershell
uv run --frozen python -m py_compile ../backtesting/s3-cross-topic-injection/scripts/run_s3_matrix.py ../backtesting/scripts/run_final_temporal_optimum.py ../backtesting/scripts/run_final_line5_matrix.py
uv run --frozen python ../backtesting/s3-cross-topic-injection/scripts/validate_s3_package.py
```

- [ ] **Step 3: Secret scan**

Run:

```powershell
rtk grep -n "sk-or-|OPENROUTER_API_KEY=|DEEPINFRA_API_KEY=|gho_" backtesting/final-multimodel backtesting/s3-cross-topic-injection backtesting/scripts
```

Expected: no secrets.

- [ ] **Step 4: Stage only intended files**

Run:

```powershell
rtk git status --short
rtk git diff --stat
```

Stage only final multimodel files, modified S3 matrix/runner/evaluation, generated summaries, and doc index changes.

- [ ] **Step 5: Commit and push**

Run:

```powershell
git commit -m "research: add final multimodel baseline runs"
git push -u origin codex/final-multimodel-baseline
```

Do not create PR.

## Self-Review

Spec coverage:

- User authorized API credit spend: covered by execution tasks.
- User authorized branch/worktree work: covered by Task 1.
- User asked for durable context before compaction: covered by `AGENT_STATE.md`, plan, and ledger.
- User requested commit and push but no PR: covered by Task 5.
- Required research lines: S3 Qwen, temporal optimum Llama/Qwen, Line 5 Bolivia Gemma/Qwen.

Known risks:

- Qwen may break JSON/schema output. Mitigation: avoid forcing Qwen as Graphiti model; use Gemma/DeepInfra for Graphiti extraction where possible and preserve raw output on failures.
- Backend model hot-swap is not reliable. Mitigation: restart backend per model group.
- IPC may not have explicit T0-T3 temporal packet files. Mitigation: use the deepest existing IPC packet only if source support exists, and document the limitation clearly.
