# S3 Runbook

Run all commands from repo root unless noted.

## 1. Validate package

```powershell
cd backend
uv run --frozen python ../backtesting/s3-cross-topic-injection/scripts/validate_s3_package.py
```

Expected: prints the number of topics, models, conditions, and planned smoke/full rows.

## 2. Check smoke plan without API calls

```powershell
cd backend
uv run --frozen python ../backtesting/s3-cross-topic-injection/scripts/run_s3_matrix.py --smoke --dry-run
```

Expected: prints 12 planned rows and writes nothing to `runs/`.

## 3. Real smoke with managed backend

Prereq: set the key in the user environment or current shell:

```powershell
$env:DEEPINFRA_API_KEY="..."
```

Then:

```powershell
cd backend
uv run --frozen python ../backtesting/s3-cross-topic-injection/scripts/run_s3_matrix.py --smoke --execute --start-backend
```

Stop any already-running backend first. With `--start-backend`, the script aborts if `http://127.0.0.1:5001` is already reachable, because an old backend may be configured with the wrong model.

The script runs one model group at a time, starts the backend with that model env, appends rows to `RUN_LEDGER.csv`, writes backend logs under `runs/s3_cross_topic/_backend_logs/`, and stores local outputs under:

```text
runs/s3_cross_topic/<topic>/<model>/<condition>-r20/
```

## 4. Manual backend mode

If the backend is already running, start it with the target model env first:

```powershell
$env:LLM_API_KEY=$env:DEEPINFRA_API_KEY
$env:OPENAI_API_KEY=$env:DEEPINFRA_API_KEY
$env:LLM_BASE_URL="https://api.deepinfra.com/v1/openai"
$env:LLM_MODEL_NAME="google/gemma-3-27b-it"
$env:PYTHONIOENCODING="utf-8"
npm run backend
```

Then in a second terminal:

```powershell
cd backend
uv run --frozen python ../backtesting/s3-cross-topic-injection/scripts/run_s3_matrix.py --smoke --execute --models gemma
```

Repeat for `llama` with:

```powershell
$env:LLM_MODEL_NAME="meta-llama/Llama-3.3-70B-Instruct-Turbo"
```

## 5. Full matrix

Only after smoke validates:

```powershell
cd backend
uv run --frozen python ../backtesting/s3-cross-topic-injection/scripts/run_s3_matrix.py --full --execute --start-backend
```
