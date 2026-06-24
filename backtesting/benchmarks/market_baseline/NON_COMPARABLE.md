# Non Comparable Rows

Rows are marked non-comparable when the temporal package does not have a defensible numeric market/proxy for the target under the same cutoff rule.

Expected non-comparable cases in the one-shot benchmark:

- Bolivia T0: now has a low-quality market proxy, but the saved MiroFish artifact does not expose a parseable `paz_wins` probability for the binary metric.
- IPC July 2025 monthly inflation: no directly comparable pre-cutoff monthly REM/proxy was found in the gathered public sources.
- IPC December 2025 monthly inflation: no directly comparable pre-cutoff monthly REM/proxy was found in the gathered public sources.

These rows remain in `mirofish_predictions.csv` and `metrics_per_question.csv`, but they are excluded from market-adjusted aggregate metrics.

Notes:

- Bolivia T0/T1 market signals are first-round proxies, not direct runoff markets.
- Copa T0 is a low-quality pre-tournament outright proxy; T1-T3 use a cleaner lift-trophy bookmaker proxy available before the canonical cutoff.
- The Copa DraftKings source published on 2024-07-14 is not used in the canonical benchmark because the case cutoff is 2024-07-13.
