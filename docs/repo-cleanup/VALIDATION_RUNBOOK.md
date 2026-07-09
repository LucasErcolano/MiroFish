# Validation Runbook

Run from:

```powershell
cd C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish-stable-cleanup
```

## Preflight

```powershell
git status --short --branch
git rev-parse --abbrev-ref HEAD
git fetch origin --prune
git branch --all --list "*feat/ui-observability-dock*" "*backtesting-feature-augmented*" "*backtesting-baseline*" "*feat/issue-28-linea6-entropia*"
```

Expected:

- Branch is `codex/stable-fork-cleanup`.
- Source branches exist.
- Worktree is clean except intentional prep docs or active changes.
- Current full-suite baseline: `322 passed`.

## Branch Relationship Checks

```powershell
git merge-base --is-ancestor origin/backtesting-baseline origin/backtesting-feature-augmented
git merge-base --is-ancestor origin/main origin/feat/ui-observability-dock
```

Expected exit code 0 for both based on prep-time state.

## Backend Checks

Use Python 3.11 through `uv`.

```powershell
cd backend
uv run --frozen --python 3.11 python -m py_compile app\config.py app\services\experimental_memory.py app\services\model_router.py app\services\simulation_runner.py app\services\simulation_config_generator.py app\graph\graphiti_backend.py scripts\run_reddit_simulation.py
cd ..
npm test
```

If dependency resolution fails because of the known `camel-oasis` /
`neo4j` metadata conflict, document the exact failure and use the repo's
documented no-deps workaround only after deciding whether Docker or local
validation is the source of truth.

## Frontend Checks

```powershell
npm install
cd frontend
npm install
npm run build
```

## Smoke / Example Checks

Final target commands to make true:

```powershell
npm run smoke-test
npm run run-example
npm test
npm run hygiene
npm run check
docker compose config --quiet
```

Optional Linea 6 tri-model dry-run, no provider keys:

```powershell
cd backend
uv run --frozen --python 3.11 python ../scripts/run_linea6_trimodel_model_map.py --out-root ../outputs/linea6_trimodel_dry_run
cd ..
```

If `make` is not available on Windows, provide npm or PowerShell equivalents
and document them in README.

## Docker Checks

Before and after any Docker command, record a memory snapshot:

```powershell
$os = Get-CimInstance Win32_OperatingSystem
(Get-Counter '\Memory\Pool Nonpaged Bytes','\Memory\Pool Paged Bytes').CounterSamples
```

If pool usage climbs abnormally, stop Docker/WSL validation and document the
counters. A previous Neo4j default-stack run caused excessive kernel-pool usage
until reboot.

Minimum expected behavior for the default, lower-memory stack:

```powershell
docker compose up --build --wait
npm run docker-test
npm run docker-down
```

Then verify either:

- UI/API path: backend health endpoint returns OK and frontend is reachable.
- Batch path: `docker compose run --rm <service> <smoke command>` generates
  documented outputs.

Neo4j/Graphiti is optional and should only be started explicitly:

```powershell
docker compose --profile graphiti up --build
```

## Final Git Checks

```powershell
git diff --check
git status --short --untracked-files=all
git diff --stat
```

Before commit, inspect for accidental raw artifacts:

```powershell
rg --files | rg "(^runs/|node_modules|\\.venv|\\.db$|\\.sqlite|request_trace\\.json|worldbuilding_trace\\.json)"
npm run hygiene
```
