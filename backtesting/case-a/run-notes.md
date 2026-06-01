# Run Notes

Status: second run completed and report output is evaluable for the objective winner metric.

## Environment

- Date run: 2026-05-23
- Branch: `feat/issue-10-backtesting-case-a`
- MiroFish commit:
- Model: `qwen2.5:0.5b`
- LLM base URL: `http://127.0.0.1:11434/v1`
- Embedding model: `nomic-embed-text`
- Graph backend: Graphiti + Neo4j local
- `USE_EXPERIMENTAL_MEMORY`: not enabled

## MiroFish project

- Project ID: `proj_53e06b67fcf5`
- Graph ID: `mirofish_1403b64cd2074a35`
- Simulation ID: `sim_f9d8b7ec5d68`
- Report ID: `report_2d2de41798cf`

## Uploaded input files

- `input/source-01-opta-preview.txt`
- `input/source-02-conmebol-preview.txt`

## Output files

- Report markdown: `output/report_2d2de41798cf.md`
- Screenshots or exported artifacts:

## Timing

- Start: 23:41:03
- End: 23:42:21
- Total runtime: 77.23 seconds

## Outcome

The report completed according to MiroFish, but the generated content did not produce a winner prediction. It should be treated as a non-evaluable run caused by the small local model failing the report-agent instruction format.

## Second run

- Date run: 2026-05-24
- Model: `openai/gpt-4o-mini` through OpenRouter for LLM/Graphiti calls
- Embedding model: `nomic-embed-text` through local Ollama-compatible endpoint
- Graph ID: `mirofish_462b790e44f1419c`
- Simulation ID: `sim_4ff02f36483f`
- Report ID: `report_3736fb6ac644`
- Output file: `output/report_3736fb6ac644.md`

Outcome: the report predicts Argentina, which matches the ground truth winner. The run is usable for the binary backtesting score, but the report body is mostly Chinese despite the Spanish-only prompt, so language compliance and report quality should be marked as failed/partial.
