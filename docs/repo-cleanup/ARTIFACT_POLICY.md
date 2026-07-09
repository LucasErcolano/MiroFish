# Artifact Policy

The stable fork should be reproducible and presentable, not a dump of local
experiments.

## Commit These

- Source code needed to run features.
- Small configs and examples.
- README and docs.
- Test files.
- Compact result summaries:
  - `.md`
  - `.csv`
  - small `.json` summaries
- Evaluation manifests when they are compact and human-readable.
- Representative tiny fixtures for smoke/regression tests.

## Do Not Commit These

- `runs/` raw run directories.
- SQLite databases (`*.db`, `*.sqlite`, `*.sqlite3`).
- Backend uploads/logs/caches.
- Virtual environments.
- `node_modules/`.
- Raw request traces unless explicitly small and required.
- Raw worldbuilding traces unless explicitly small and required.
- Large generated output directories.
- API keys, `.env`, secrets, or copied terminal output containing secrets.

## Gray Area

For research evidence, prefer compact derived files over raw evidence:

- Good: `metrics.csv`, `summary.json`, `final_report.md`.
- Avoid: full `request_trace.json`, DB exports, complete generated reports for
  every condition, duplicate output bundles.

If a raw artifact is necessary for auditability, move it into a clearly named
compact sample folder and document why in `MERGE_LEDGER.md`.

## Checks Before Commit

Use these before staging:

```powershell
git status --short --untracked-files=all
git diff --stat
git diff --check
```

Suggested searches:

```powershell
rg -n "API_KEY|SECRET|TOKEN|Bearer " .env* backend docs scripts tests
rg --files | rg "(^runs/|node_modules|\\.venv|\\.db$|\\.sqlite|request_trace\\.json|worldbuilding_trace\\.json)"
npm run hygiene
```
