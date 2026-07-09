# IPC Tri-Model Decisions

## Branching

- Work branch: `codex/ipc-trimodel-multiagent`.
- Base: `origin/backtesting-baseline`.
- Merged locally: `origin/codex/final-multimodel-baseline`.

## IPC Ground Truth

Use the answer-key markdown values already documented by S3 IPC:

- February: 2.4%.
- April: 3.7%.
- July: about 3.0%.
- December: 2.8%.
- Annual accumulated: 31.5%.

Keep the mismatch with `ground_truth.json` visible in final reports.

## Multi-Agent Definition

A row is multi-agent only if one simulation uses all three routed models:

- Qwen: `qwen/qwen3-8b` via OpenRouter.
- Gemma: `google/gemma-3-27b-it` via DeepInfra.
- Llama: `meta-llama/Llama-3.3-70B-Instruct-Turbo` via DeepInfra.

Evidence: `model_routing_audit.jsonl` and `llm_telemetry_summary.json` must
both show all three model IDs. Assigned routes are not enough if a routed model
never acts in the simulation.

## Memory

Use `USE_EXPERIMENTAL_MEMORY=true` for benchmark rows. This activates the
Karpathy/MemGPT-inspired experimental memory service when the simulation memory
factory is reached.

If ChromaDB embeddings fail, keyword fallback is acceptable only if documented
in `RUN_LEDGER.csv` notes and final report caveats.

## Graphiti Dedup

IPC graph build must bypass the half-finished dedup path before graph creation.
The bypass should be controlled by an explicit env var:

```text
GRAPHITI_BYPASS_NODE_DEDUP=true
```

Do not run full matrix rows until this has passed a smoke check.

## Graphiti Extraction Model

Use Gemma/DeepInfra for Graphiti extraction by default. This keeps extraction
stable while Qwen/Gemma/Llama vary inside the simulation agents.

## Economic Claim

The main Line 5 economic comparison is:

```text
multi-agent IPC T3 R40-D2 vs best available single-agent IPC T3 R80-D2
```

The comparison must include MAE and token/cost telemetry when available.

## Runner Contract

Use `backtesting/ipc-trimodel-multiagent/scripts/run_ipc_trimodel_matrix.py`
as the single entrypoint for this benchmark. It requires either `--dry-run` or
`--execute` so accidental paid runs are harder.

The first smoke is a dedicated non-matrix row:

```text
ipc_trimodel_smoke_T0_R2_D2
```

Full temporal, Line 5, and S3 row IDs remain reserved for actual benchmark
depths.
