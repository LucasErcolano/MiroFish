# Market Baseline Temporal Benchmark

This report compares existing MiroFish T0-T3 predictions against market/proxy signals available at the same temporal package.

No new MiroFish simulations were run for this benchmark.

## Executive Summary

- Total rows: 28
- Comparable rows with market/proxy: 27
- Unavailable market/proxy rows: 0
- Rows where MiroFish beats market/proxy by delta Brier: 9
- Average delta Brier over comparable rows: 0.014

Negative delta means MiroFish has lower error than the market/proxy. Positive delta means the market/proxy is better.

For IPC numeric targets, Brier is a scaled squared error over percentage values; absolute error is also reported.

## Bolivia 2025 Runoff

| T | Target | Cutoff | p(MiroFish) | p(market/proxy) | Quality | Brier MF | Brier market | Delta Brier | Comparable |
|---|---|---|---:|---:|---|---:|---:|---:|---|
| T0 | paz_wins | 2025-08-16 | n/a | 0.271 | LOW | n/a | n/a | n/a | false |
| T1 | paz_wins | 2025-08-18 | 0.536 | 0.544 | MEDIUM | 0.215 | 0.208 | 0.008 | true |
| T2 | paz_wins | 2025-10-08 | 0.454 | 0.455 | HIGH | 0.299 | 0.297 | 0.002 | true |
| T3 | paz_wins | 2025-10-17 | 0.453 | 0.448 | HIGH | 0.300 | 0.304 | -0.005 | true |

## Argentina IPC 2025

| T | Target | Cutoff | MiroFish | Market/proxy | Quality | Abs err MF | Abs err market | Delta abs | Comparable |
|---|---|---|---:|---:|---|---:|---:|---:|---|
| T0 | delta_1_feb | 2024-12-31 | 1.800 | 2.400 | HIGH | 0.600 | 0.000 | 0.600 | true |
| T0 | delta_2_apr | 2024-12-31 | 1.600 | 2.300 | HIGH | 2.100 | 1.400 | 0.700 | true |
| T0 | delta_3_jul | 2024-12-31 | 1.150 | 1.500 | MEDIUM | 1.850 | 1.500 | 0.350 | true |
| T0 | delta_4_dec | 2024-12-31 | 1.200 | 1.400 | MEDIUM | 1.600 | 1.400 | 0.200 | true |
| T0 | accumulated_2025 | 2024-12-31 | 17.500 | 28.100 | HIGH | 14.000 | 3.400 | 10.600 | true |
| T1 | delta_1_feb | 2025-01-10 | 1.800 | 2.300 | HIGH | 0.600 | 0.100 | 0.500 | true |
| T1 | delta_2_apr | 2025-01-10 | 2.000 | 2.000 | HIGH | 1.700 | 1.700 | 0.000 | true |
| T1 | delta_3_jul | 2025-01-10 | 1.600 | 1.500 | MEDIUM | 1.400 | 1.500 | -0.100 | true |
| T1 | delta_4_dec | 2025-01-10 | 1.500 | 1.400 | MEDIUM | 1.300 | 1.400 | -0.100 | true |
| T1 | accumulated_2025 | 2025-01-10 | 25.000 | 25.900 | HIGH | 6.500 | 5.600 | 0.900 | true |
| T2 | delta_1_feb | 2025-01-14 | 2.500 | 2.300 | HIGH | 0.100 | 0.100 | 0.000 | true |
| T2 | delta_2_apr | 2025-01-14 | 2.000 | 2.000 | HIGH | 1.700 | 1.700 | 0.000 | true |
| T2 | delta_3_jul | 2025-01-14 | 1.600 | 1.500 | MEDIUM | 1.400 | 1.500 | -0.100 | true |
| T2 | delta_4_dec | 2025-01-14 | 1.200 | 1.400 | MEDIUM | 1.600 | 1.400 | 0.200 | true |
| T2 | accumulated_2025 | 2025-01-14 | 25.000 | 25.900 | HIGH | 6.500 | 5.600 | 0.900 | true |
| T3 | delta_1_feb | 2025-01-31 | 2.500 | 2.300 | HIGH | 0.100 | 0.100 | 0.000 | true |
| T3 | delta_2_apr | 2025-01-31 | 2.150 | 2.000 | HIGH | 1.550 | 1.700 | -0.150 | true |
| T3 | delta_3_jul | 2025-01-31 | 1.850 | 1.500 | MEDIUM | 1.150 | 1.500 | -0.350 | true |
| T3 | delta_4_dec | 2025-01-31 | 2.000 | 1.400 | MEDIUM | 0.800 | 1.400 | -0.600 | true |
| T3 | accumulated_2025 | 2025-01-31 | 27.500 | 25.900 | HIGH | 4.000 | 5.600 | -1.600 | true |

## Copa America 2024 Final

| T | Target | Cutoff | p(MiroFish) | p(market/proxy) | Quality | Brier MF | Brier market | Delta Brier | Comparable |
|---|---|---|---:|---:|---|---:|---:|---:|---|
| T0 | argentina_wins | 2024-07-13 | 0.625 | 0.837 | LOW | 0.141 | 0.027 | 0.114 | true |
| T1 | argentina_wins | 2024-07-13 | 0.650 | 0.627 | HIGH | 0.122 | 0.139 | -0.016 | true |
| T2 | argentina_wins | 2024-07-13 | 0.490 | 0.627 | HIGH | 0.260 | 0.139 | 0.121 | true |
| T3 | argentina_wins | 2024-07-13 | 0.490 | 0.627 | HIGH | 0.260 | 0.139 | 0.121 | true |

## Interpretation

- Bolivia now has market/proxy signals across all T, but T0 remains non-comparable in the metric table because the saved MiroFish artifact does not expose a parseable `paz_wins` probability. From T1 onward, the comparison is clear: T1 first-round results favor Paz, while T2/T3 direct runoff polls favor Quiroga. The final ground truth favored Paz, so the late direct polls acted as strong but misleading market/proxy signals.
- IPC now has comparisons for every monthly and accumulated target. February, April and accumulated 2025 use REM values; July and December use Bloomberg/Invecq market-implied bucket averages, marked `MEDIUM` because they are period-average proxies rather than exact month-specific forecasts.
- Copa is comparable across all T, but proxy quality changes over time: T0 uses a rough pre-tournament outright model normalized over the eventual finalists, while T1-T3 use a cleaner two-way lift-trophy bookmaker proxy. The later DraftKings 2024-07-14 price is excluded because the canonical cutoff is 2024-07-13.

## Caveats

- Market/proxy rows use external deep-research signals only when publication dates satisfy the temporal cutoff.
- Non-comparable rows are intentionally left out of market-adjusted aggregates.
- Bolivia T0/T1 proxies are not direct runoff odds; they use first-round relative Paz/Quiroga information and are marked lower quality than direct runoff polls.
- Copa T0 is not a direct final matchup price; it is a normalized pre-tournament title-probability proxy.
- IPC July and December comparisons should be read as bucket-proxy comparisons, not as exact REM month-point comparisons.
