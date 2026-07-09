# Merge Ledger

This file records every source import, merge, cherry-pick, conflict, and
validation decision. Update it during the cleanup work.

## Initial Preparation

- Date: 2026-07-09
- Worktree: `C:\Users\joaco\Documents\IA\Year-4\Semestre-1\NLP\MiroFish-stable-cleanup`
- Branch: `codex/stable-fork-cleanup`
- Base: `origin/feat/ui-observability-dock`
- Status: preparation only; no branch imports started.

## Source Branch Summary

| Branch | Intended Use | Direct Merge? | Notes |
| --- | --- | --- | --- |
| `origin/feat/ui-observability-dock` | Base branch | Already base | Closest to current functional UI. |
| `origin/backtesting-feature-augmented` | Backtesting/multimodel/wiki/IPCs | No, import selectively | Contains baseline; also contains many raw artifacts. |
| `origin/backtesting-baseline` | Reference for baseline docs/results | Usually no | Ancestor of augmented at prep time. |
| `origin/feat/issue-28-linea6-entropia` | Entropy/linea6 feature | No | Older base; direct merge would delete modern files. |

## Import Entries

Add entries below as work starts.

### Template

```text
Date:
Source branch/commit:
Import method:
Files/areas touched:
Conflicts:
Decision:
Validation:
Notes:
```
