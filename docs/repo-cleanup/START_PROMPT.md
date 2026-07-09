# Start Prompt

Use this when starting the actual cleanup in a fresh thread or goal.

```text
Work in C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish-stable-cleanup on branch codex/stable-fork-cleanup. First read AGENTS.md and docs/repo-cleanup/{AGENT_STATE.md,PLAN.md,MERGE_LEDGER.md,ARTIFACT_POLICY.md,VALIDATION_RUNBOOK.md,FEATURE_PR_CANDIDATES_DRAFT.md}. Continue from those docs; do not rediscover from scratch.

Goal: turn this into a stable, presentable MiroFish fork. Base is origin/feat/ui-observability-dock. Selectively import from origin/backtesting-feature-augmented and origin/feat/issue-28-linea6-entropia; treat origin/backtesting-baseline as reference because it is already included in augmented unless re-verification says otherwise. Do not directly merge entropy. Do not commit raw runs, DBs, traces, caches, or huge generated outputs.

Required final state: README/.env.example/Docker or Compose/smoke/run-example/test commands documented and verified as far as possible; features documented as upstream PR candidates; artifacts cleaned; validations run; local commits made. Do not push unless explicitly asked. Update AGENT_STATE.md before and after each major phase, MERGE_LEDGER.md after each import/conflict decision, and VALIDATION_RUNBOOK.md if actual commands differ.
```
