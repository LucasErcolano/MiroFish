# Market Baseline Temporal Benchmark

Issue #33 benchmark for comparing existing MiroFish temporal predictions against market/proxy signals available at the same evidence package.

Included cases:

- Bolivia 2025 runoff, T0-T3.
- Argentina IPC 2025, T0-T3.
- Copa America 2024 final, T0-T3.

Run the full pipeline:

```bash
python3 backtesting/benchmarks/market_baseline/scripts/run_all.py
```

Generated artifacts:

- `temporal_cutoffs.csv`
- `mirofish_predictions.csv`
- `market_odds.csv`
- `metrics_per_question.csv`
- `MARKET_BASELINE_REPORT.md`

No MiroFish simulations are run by this benchmark. It only reads existing outputs.

