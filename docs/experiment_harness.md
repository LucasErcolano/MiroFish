# S2 Experiment Harness

Deterministic, reproducible experiment runner for baseline vs experimental memory mode comparisons in MiroFish.

## Overview

The experiment harness provides:

- **Deterministic run IDs** — `{case_id}__{variant}__s{seed}` format ensures reproducible identification
- **Config YAML loading** — validate and load experiment configurations from YAML files
- **SHA-256 hashing** — seeds, prompts, and seed documents are hashed for integrity verification
- **Config snapshots** — full config is captured at run time with API keys redacted
- **Structured output directories** — `runs/<case_id>/<variant>/s<seed>/` containing all artifacts
- **Comparison tooling** — compare baseline vs experimental results across seeds

## Quick Start

### Validate a config

```bash
python scripts/run_experiment.py --validate configs/experiments/example_case.yaml
```

### Dry run (no simulation, just artifact creation)

```bash
python scripts/run_experiment.py --dry-run configs/experiments/example_case.yaml
```

### Dry run with seed override

```bash
python scripts/run_experiment.py --dry-run configs/memory_baseline.yaml --seeds 1 2 3
```

### Compare two variants

```bash
python scripts/run_experiment.py --compare \
  --case memory_smoke_test \
  --runs-root /path/to/runs
```

## Output Structure

Each run produces a directory under `runs/<case_id>/<variant>/s<seed>/` containing:

```
runs/
└── <case_id>/
    ├── baseline/
    │   └── s1/
    │       ├── config_snapshot.yaml   # Full config with API keys redacted
    │       ├── results.json           # Run outcome (tokens, rounds, status)
    │       ├── seed_hashes.json       # SHA-256 hashes of seed documents
    │       ├── prompt_hashes.json     # SHA-256 hashes of prompts
    │       └── run_manifest.json       # Run metadata (run_id, timestamps, status)
    └── experimental/
        └── s1/
            ├── config_snapshot.yaml
            ├── results.json
            ├── seed_hashes.json
            ├── prompt_hashes.json
            └── run_manifest.json
```

## Config YAML Format

### Experiment Case Config

Full experiment definition with multiple variants:

```yaml
case_id: example_case
description: "Example experiment comparing baseline vs experimental memory"

variants:
  - name: baseline
    memory_mode: baseline
    seeds: [1, 2, 3]

  - name: experimental
    memory_mode: experimental
    seeds: [1, 2, 3]

common:
  num_rounds: 5
  model: gemini-2.0-flash

seed_documents:
  - path: seeds/context.md
    alias: context

prompts:
  - path: prompts/system.txt
    alias: system
  - path: prompts/user.txt
    alias: user
```

### Single-Variant Config

Simpler config for running one variant at a time (used for baseline/experimental pair configs):

```yaml
case_id: memory_smoke_test
variant: baseline
memory_mode: baseline
seeds: [1]

num_rounds: 3
model: gemini-2.0-flash

seed_documents:
  - path: seeds/context.md

prompts:
  - path: prompts/system.txt
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `case_id` | string | Experiment case identifier (lowercase, hyphens, underscores) |
| `variant` | string | Variant name (lowercase, hyphens, underscores) |
| `memory_mode` | string | One of: `baseline`, `experimental` |
| `seeds` | list[int] | List of seed integers |

### Optional Fields

| Field | Type | Default | Description |
|------|------|---------|-------------|
| `num_rounds` | int | — | Number of simulation rounds |
| `model` | string | — | LLM model override |
| `description` | string | — | Human-readable description |
| `seed_documents` | list | [] | Seed document paths with optional aliases |
| `prompts` | list | [] | Prompt file paths with optional aliases |
| `runs_root` | string | `runs` | Output directory root |
| `project_root` | string | auto | Project root for resolving relative paths |

## API Reference

### `compute_run_id(case_id, variant, seed)`

Generate a deterministic run ID string.

```python
from backend.app.services.experiment_runner import compute_run_id

run_id = compute_run_id("example_case", "baseline", 1)
# => "example_case__baseline__s1"
```

### `validate_config(config)`

Validate a config dictionary against the schema. Raises `ValueError` on invalid input.

```python
from backend.app.services.experiment_runner import validate_config

validate_config({
    "case_id": "test",
    "variant": "baseline",
    "memory_mode": "baseline",
    "seeds": [1, 2],
})
```

### `ExperimentRunner`

Main experiment runner class.

```python
from backend.app.services.experiment_runner import ExperimentRunner

runner = ExperimentRunner(
    case_id="example_case",
    variant="baseline",
    seed=1,
    memory_mode="baseline",
    project_root="/path/to/MiroFish",
)

# Create output directories
runner.create_output_directory()

# Save config snapshot (redacts API keys)
runner.save_config_snapshot(config_dict)

# Compute hashes
seed_hashes = runner.hash_seed_documents()
prompt_hashes = runner.hash_prompts()

# Dry run (creates all artifacts, no simulation)
result = runner.run_dry_run()

# Full run (requires backend services)
result = runner.run()
```

#### `ExperimentRunner.from_yaml(path, **overrides)`

Load runner from a YAML config file with optional overrides.

```python
runner = ExperimentRunner.from_yaml(
    "configs/memory_baseline.yaml",
    seed=2,           # Override seed
    memory_mode="experimental",  # Override memory mode
)
```

### `compare_results(case_id, runs_root)`

Compare baseline vs experimental results for a case.

```python
from backend.app.services.experiment_runner import compare_results

comparison = compare_results("example_case", runs_root="runs")
# Returns dict with per-seed comparison of metrics
```

## Security

- **API key redaction**: Config snapshots replace `llm_api_key_env` values with `null`
- **SHA-256 hashing**: All seed documents and prompts are hashed for integrity verification
- **No secrets in output**: Run manifests and results files contain no API keys

## Testing

34 tests covering:

- Deterministic run ID generation and validation
- Config validation (required fields, valid memory modes, unknown keys)
- SHA-256 hashing (text, bytes, file, missing files)
- ExperimentRunner initialization and YAML loading
- Output directory creation
- Config snapshot creation and API key redaction
- Seed document and prompt hashing
- Results JSON and run manifest creation
- Environment variable overrides (baseline/experimental/model)
- Baseline vs experimental comparison

```bash
cd /home/lucas76hz/Desktop/MiroFish
python -m pytest backend/tests/test_experiment_runner.py -v
```