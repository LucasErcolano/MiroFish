# Read-Only Reviewer Prompts

Use subagents for read-only review and synthesis. The main thread should be the
only writer.

## Branch Audit Reviewer

```text
Read AGENTS.md and docs/repo-cleanup/*.md. Do not edit files. Compare these branches against codex/stable-fork-cleanup: origin/backtesting-feature-augmented, origin/backtesting-baseline, origin/feat/issue-28-linea6-entropia. Report which files/features should be imported, which should be ignored as raw artifacts, and any direct-merge risks. Write concise findings to docs/repo-cleanup/reviewer-findings/branch-audit.md.
```

## Docker / Runtime Reviewer

```text
Read AGENTS.md and docs/repo-cleanup/*.md. Do not edit files. Inspect README.md, .env.example, Dockerfile, docker-compose.yml, package.json, backend dependency files, and existing smoke/test scripts. Report what must change so clone -> env -> docker compose up --build and smoke-test are credible. Write findings to docs/repo-cleanup/reviewer-findings/runtime.md.
```

## Artifact Hygiene Reviewer

```text
Read AGENTS.md and docs/repo-cleanup/*.md. Do not edit files. Inspect the current diff and likely imported paths for raw runs, DBs, traces, caches, secrets, and oversized generated outputs. Report exact patterns and paths to exclude or remove. Write findings to docs/repo-cleanup/reviewer-findings/artifact-hygiene.md.
```

## Final Review

```text
Read AGENTS.md and docs/repo-cleanup/*.md. Do not edit files. Review the final diff for merge mistakes, missing validation, stale docs, accidental raw artifacts, and commands that do not match the repo. Prioritize findings by severity and give file/path references. Write findings to docs/repo-cleanup/reviewer-findings/final-review.md.
```
