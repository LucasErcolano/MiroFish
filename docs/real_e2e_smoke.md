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

For DeepInfra, set `DEEPINFRA_API_KEY` and use the equivalent overlay:

```bash
npm run docker-up:deepinfra-smoke
npm run smoke-test:real
npm run docker-down:deepinfra-smoke
```

The command fails unless the graph is non-empty, at least one round and action
are observed, memory evidence exists, ReportAgent produces non-empty Markdown,
the environment closes successfully, and the API key is absent from artifacts.

## Verified Result

The CPU-only Compose image was rebuilt and verified from an empty Neo4j volume
on 2026-07-10 with Qwen3-8B and Qwen3 Embedding through OpenRouter:

| Gate | Result |
| --- | --- |
| Graphiti | 1 chunk, 4 nodes, 3 edges |
| OASIS | 3 agents, 9 rounds, 6 actions |
| Reddit database | 3 posts, 8 traces |
| Experimental memory | evidence and `core_memory.json` captured |
| ReportAgent | 4,921-byte Spanish report |
| Cleanup | OASIS closed through `close-env` |
| Secret scan | no provider key in generated artifacts |

The same flow was then verified through DeepInfra with Gemma 3 27B and
BGE-M3 embeddings:

| Gate | Result |
| --- | --- |
| Graphiti | 1 chunk, 7 nodes, 6 edges |
| OASIS | 3 agents, 9 rounds, 6 actions |
| Experimental memory | evidence and `core_memory.json` captured |
| ReportAgent | 6,051-byte Spanish report |
| Cleanup | OASIS closed through `close-env` |
| Secret scan | neither provider key appeared in generated artifacts |

The OpenRouter and DeepInfra E2Es took 647 and 562 seconds respectively. The
backend lock selects the official CPU-only PyTorch wheels because the supported
Docker path uses hosted providers and exposes no GPU. The resulting image was
4.19 GB instead of the previous 14.3 GB CUDA build. Peak host RAM remained near
52% on a 64 GB machine and returned to baseline after Docker stopped. Raw runs,
databases, logs, and reports remain under git-ignored runtime directories and
are not committed.

## Why Spanish

The fork currently ships complete native ReportAgent prompt sets for Spanish
and Chinese. English falls back to the original Chinese prompts and can fail the
strict language-consistency gate, so the reproducible smoke explicitly requests
Spanish output instead of weakening that gate.
