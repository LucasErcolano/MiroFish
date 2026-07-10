# Real End-to-End Smoke

This fork includes an opt-in paid smoke that exercises the same backend API
sequence as the UI:

1. Generate an ontology from a 1.2 KB seed.
2. Build a Graphiti graph in Neo4j.
3. Generate OASIS profiles and simulation configuration.
4. Run both Twitter and Reddit for nine bounded rounds.
5. Update experimental memory.
6. Generate a ReportAgent report while OASIS remains available.
7. Capture sanitized artifacts and close OASIS gracefully.

## Run

Set `OPENROUTER_API_KEY` in `.env` or the shell, then run:

```bash
npm run docker-up:openrouter-smoke
npm run smoke-test:real
npm run docker-down:openrouter-smoke
```

The command fails unless the graph is non-empty, at least one round and action
are observed, memory evidence exists, ReportAgent produces non-empty Markdown,
the environment closes successfully, and the API key is absent from artifacts.

## Verified Result

The Compose path was rebuilt from an empty Neo4j volume and verified on
2026-07-10 with Qwen3-8B and Qwen3 Embedding through OpenRouter:

| Gate | Result |
| --- | --- |
| Graphiti | 1 chunk, 3 nodes, 1 edge |
| OASIS | 2 agents, 9 rounds, 13 actions |
| Reddit database | 3 posts, 1 comment |
| Experimental memory | evidence and `core_memory.json` captured |
| ReportAgent | 3,386-byte Spanish report |
| Cleanup | OASIS closed through `close-env` |
| Secret scan | no provider key in generated artifacts |

The final cached-image E2E took about ten minutes. The first Docker build is
substantially slower because the OASIS dependency graph includes large
PyTorch/CUDA wheels. Raw runs, databases, logs, and reports remain under
git-ignored runtime directories and are not committed.

## Why Spanish

The fork currently ships complete native ReportAgent prompt sets for Spanish
and Chinese. English falls back to the original Chinese prompts and can fail the
strict language-consistency gate, so the reproducible smoke explicitly requests
Spanish output instead of weakening that gate.
