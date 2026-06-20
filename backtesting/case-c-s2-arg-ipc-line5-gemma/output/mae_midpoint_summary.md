# Midpoint MAE Summary

Method:
- For each predicted range, use midpoint = `(min + max) / 2`.
- Compute absolute error against ground truth.
- `MAE without accumulated` uses `feb`, `apr`, `jul`, `dec`.
- `MAE with accumulated` adds `accumulated_2025` as a fifth target.

Ground truth:
- `delta_1_feb = 2.4`
- `delta_2_apr = 3.7`
- `delta_3_jul = 3.0`
- `delta_4_dec = 2.8`
- `accumulated_2025 = 31.5`

## Results

| Variant | Feb err | Apr err | Jul err | Dec err | Acc err | MAE (4 deltas) | MAE (4 deltas + accumulated) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gemma_T0_R40_D2` | 0.55 | 2.10 | 1.85 | 1.50 | 14.00 | 1.50 | 4.00 |
| `gemma_T1_R40_D2` | 0.55 | 1.70 | 1.40 | 1.30 | 6.50 | 1.2375 | 2.29 |
| `gemma_T2_R40_D2` | 0.20 | 1.70 | 1.40 | 1.40 | 6.50 | 1.175 | 2.24 |
| `gemma_T3_R40_D2` | 0.10 | 1.55 | 1.15 | 0.55 | 4.00 | 0.8375 | 1.47 |

## Midpoints

| Variant | Feb mid | Apr mid | Jul mid | Dec mid | Acc mid |
| --- | ---: | ---: | ---: | ---: | ---: |
| `gemma_T0_R40_D2` | 1.85 | 1.60 | 1.15 | 1.30 | 17.50 |
| `gemma_T1_R40_D2` | 1.85 | 2.00 | 1.60 | 1.50 | 25.00 |
| `gemma_T2_R40_D2` | 2.60 | 2.00 | 1.60 | 1.40 | 25.00 |
| `gemma_T3_R40_D2` | 2.50 | 2.15 | 1.85 | 2.25 | 27.50 |
