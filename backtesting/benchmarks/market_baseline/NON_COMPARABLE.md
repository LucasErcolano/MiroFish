# Non Comparable Rows

Rows are marked non-comparable when the temporal package does not contain a defensible numeric market/proxy for the target.

Expected non-comparable cases in the one-shot benchmark:

- Bolivia T0: no direct Paz-vs-Quiroga runoff proxy exists in the pre-first-round package.
- Copa T0/T1: no market/model probability is included before the T2 market evidence package.
- IPC monthly horizons: the available market proxy is annual REM inflation, not monthly forecasts for February, April, July or December.

These rows remain in `mirofish_predictions.csv` and `metrics_per_question.csv`, but they are excluded from market-adjusted aggregate metrics.

