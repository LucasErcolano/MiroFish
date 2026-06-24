# Market Baseline Schema

## `temporal_cutoffs.csv`

- `case_id`: stable case identifier.
- `temporal_package`: `T0`, `T1`, `T2`, `T3`.
- `cutoff_date`: maximum effective document date for that package.
- `source_ids`: semicolon-separated cumulative sources.
- `evidence_added`: semicolon-separated sources added in that T.

## `mirofish_predictions.csv`

- `case_id`, `temporal_package`, `target`: join keys.
- `metric_family`: `binary` or `numeric_percent`.
- `p_mirofish`: probability for binary targets.
- `point_estimate`, `range_min`, `range_max`: numeric prediction fields.
- `ground_truth_value`: `1/0` for binary targets, percentage value for numeric targets.
- `artifact_path`: source artifact used for extraction.

## `market_odds.csv`

- `market_source_type`: `PROXY_ODDS`, `PROXY_SURVEY`, `PROXY_EXPECTATIONS`, `PROXY_CARRY_FORWARD`, or `UNAVAILABLE`.
- `p_market`: probability for binary targets.
- `market_value`: percentage value for numeric targets.
- `quality_flag`: `HIGH`, `MEDIUM`, `LOW`, `UNAVAILABLE`.

## `metrics_per_question.csv`

- `brier_mirofish`, `brier_market`, `delta_brier`: core market-adjusted comparison.
- `log_loss_*`: only for binary probability rows.
- `abs_error_*`: numeric percent rows.
- `comparable`: `true` only when a market/proxy value exists.

