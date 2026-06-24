# Market Baseline Temporal Benchmark

This report compares existing MiroFish T0-T3 predictions against market/proxy signals available at the same temporal package.

No new MiroFish simulations were run for this benchmark.

## Executive Summary

- Total rows: 28
- Comparable rows with market/proxy: 8
- Unavailable market/proxy rows: 20
- Rows where MiroFish beats market/proxy by delta Brier: 4
- Average delta Brier over comparable rows: 0.010

Negative delta means MiroFish has lower error than the market/proxy. Positive delta means the market/proxy is better.

For IPC numeric targets, Brier is a scaled squared error over percentage values; absolute error is also reported.

## Bolivia 2025 Runoff

| T | Target | Cutoff | p(MiroFish) | p(market/proxy) | Quality | Brier MF | Brier market | Delta Brier | Comparable |
|---|---|---|---:|---:|---|---:|---:|---:|---|
| T0 | paz_wins | 2025-08-16 | n/a | n/a | UNAVAILABLE | n/a | n/a | n/a | false |
| T1 | paz_wins | 2025-08-18 | 0.536 | 0.552 | LOW | 0.215 | 0.201 | 0.014 | true |
| T2 | paz_wins | 2025-10-08 | 0.454 | 0.552 | LOW | 0.299 | 0.201 | 0.098 | true |
| T3 | paz_wins | 2025-10-17 | 0.453 | 0.448 | MEDIUM | 0.300 | 0.304 | -0.005 | true |

## Argentina IPC 2025

| T | Target | Cutoff | MiroFish | Market/proxy | Quality | Abs err MF | Abs err market | Delta abs | Comparable |
|---|---|---|---:|---:|---|---:|---:|---:|---|
| T0 | delta_1_feb | 2024-12-31 | 1.800 | n/a | UNAVAILABLE | 0.600 | n/a | n/a | false |
| T0 | delta_2_apr | 2024-12-31 | 1.600 | n/a | UNAVAILABLE | 2.100 | n/a | n/a | false |
| T0 | delta_3_jul | 2024-12-31 | 1.150 | n/a | UNAVAILABLE | 1.850 | n/a | n/a | false |
| T0 | delta_4_dec | 2024-12-31 | 1.200 | n/a | UNAVAILABLE | 1.600 | n/a | n/a | false |
| T0 | accumulated_2025 | 2024-12-31 | 17.500 | n/a | UNAVAILABLE | 14.000 | n/a | n/a | false |
| T1 | delta_1_feb | 2025-01-10 | 1.800 | n/a | UNAVAILABLE | 0.600 | n/a | n/a | false |
| T1 | delta_2_apr | 2025-01-10 | 2.000 | n/a | UNAVAILABLE | 1.700 | n/a | n/a | false |
| T1 | delta_3_jul | 2025-01-10 | 1.600 | n/a | UNAVAILABLE | 1.400 | n/a | n/a | false |
| T1 | delta_4_dec | 2025-01-10 | 1.500 | n/a | UNAVAILABLE | 1.300 | n/a | n/a | false |
| T1 | accumulated_2025 | 2025-01-10 | 25.000 | 25.900 | MEDIUM | 6.500 | 5.600 | 0.900 | true |
| T2 | delta_1_feb | 2025-01-14 | 2.500 | n/a | UNAVAILABLE | 0.100 | n/a | n/a | false |
| T2 | delta_2_apr | 2025-01-14 | 2.000 | n/a | UNAVAILABLE | 1.700 | n/a | n/a | false |
| T2 | delta_3_jul | 2025-01-14 | 1.600 | n/a | UNAVAILABLE | 1.400 | n/a | n/a | false |
| T2 | delta_4_dec | 2025-01-14 | 1.200 | n/a | UNAVAILABLE | 1.600 | n/a | n/a | false |
| T2 | accumulated_2025 | 2025-01-14 | 25.000 | 25.900 | MEDIUM | 6.500 | 5.600 | 0.900 | true |
| T3 | delta_1_feb | 2025-01-31 | 2.500 | n/a | UNAVAILABLE | 0.100 | n/a | n/a | false |
| T3 | delta_2_apr | 2025-01-31 | 2.150 | n/a | UNAVAILABLE | 1.550 | n/a | n/a | false |
| T3 | delta_3_jul | 2025-01-31 | 1.850 | n/a | UNAVAILABLE | 1.150 | n/a | n/a | false |
| T3 | delta_4_dec | 2025-01-31 | 2.000 | n/a | UNAVAILABLE | 0.800 | n/a | n/a | false |
| T3 | accumulated_2025 | 2025-01-31 | 27.500 | 25.900 | MEDIUM | 4.000 | 5.600 | -1.600 | true |

## Copa America 2024 Final

| T | Target | Cutoff | p(MiroFish) | p(market/proxy) | Quality | Brier MF | Brier market | Delta Brier | Comparable |
|---|---|---|---:|---:|---|---:|---:|---:|---|
| T0 | argentina_wins | 2024-07-13 | 0.625 | n/a | UNAVAILABLE | 0.141 | n/a | n/a | false |
| T1 | argentina_wins | 2024-07-13 | 0.650 | n/a | UNAVAILABLE | 0.122 | n/a | n/a | false |
| T2 | argentina_wins | 2024-07-13 | 0.490 | 0.476 | HIGH | 0.260 | 0.275 | -0.014 | true |
| T3 | argentina_wins | 2024-07-13 | 0.490 | 0.476 | HIGH | 0.260 | 0.275 | -0.014 | true |

## Interpretation

- Bolivia shows the intended temporal behavior clearly: after T1, both MiroFish and the first-round proxy favor Paz, but the late T3 poll moves the market/proxy toward Quiroga and MiroFish also shifts toward Quiroga. The final ground truth favored Paz, so the late poll acted as a strong but misleading signal.
- Copa has no explicit market proxy in T0/T1, then T2/T3 add market/model probabilities around Argentina. MiroFish remains close to that market anchor and predicts Argentina correctly.
- IPC is only partly market-comparable in this one-shot because the available proxy is annual REM inflation, not monthly paths. The benchmark therefore treats monthly rows as MiroFish-only and compares accumulated 2025 where the REM anchor is available.

## Caveats

- Market/proxy rows use only signals already present in the temporal evidence packages; this is not an external odds-history research pass.
- `UNAVAILABLE` rows are intentionally left out of market-adjusted aggregates.
- Bolivia T1/T2 proxies are not direct runoff odds; they use first-round relative Paz/Quiroga information and are marked `LOW` quality.
- IPC annual REM is a market-expectations proxy for accumulated inflation, not a direct monthly forecast.
