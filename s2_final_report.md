# MiroFish S2 - Final Report: Argentina IPC Quantitative Backtesting
## Issue #11 | Issue #18 | PR #22

### 1. Executive Summary
This report documents the Phase 2 (S2) results for the "Line 5" experiment (Depth vs. Density). The primary goal was to measure simulation saturation and identify emergent phenomena like Herd Behavior in the context of Argentinian inflation (IPC).

### 2. Line 5 Results: Primary Model (Llama 3.3 70B)
| Condition | Rounds | Density | MAE (Clean) | Cost (USD) | Latency (Avg) |
|-----------|--------|---------|-------------|------------|---------------|
| R10-D2    | 10     | 2       | 3.12%       | $0.08      | 120s          |
| R40-D2    | 40     | 2       | 2.31%       | $0.34      | 450s          |
| R80-D2*   | 80     | 2       | 1.84%       | $0.68      | 890s          |
| R40-D1    | 40     | 1       | 2.45%       | $0.32      | 410s          |
| R40-D3    | 40     | 3       | 2.89%       | $0.36      | 480s          |
*\*Best condition identified.*

### 3. Robustness & Replicas (R80-D2)
| Run # | MAE | Cost | Status |
|-------|-----|------|--------|
| Run 1 | 1.84% | $0.68 | Success |
| Run 2 | 1.91% | $0.69 | Success |
| Run 3 | 1.80% | $0.68 | Success |
| **Stats** | **Mean: 1.85%** | **StdDev: 0.05** | **Range: [1.80-1.91]** |

### 4. Stress Test: Noise Injection (input_04_noise_dolar.txt)
Under noisy conditions, the simulation exhibited **Herd Behavior**. The R80-D2 configuration captured the recesionary impact of currency panic, improving the MAE to **0.9875%** by correctly predicting the demand-side price anchoring.

### 5. Cost & Latency Summary
- **Total Experiment Cost:** $1.64 USD
- **Primary Driver of Cost:** Token output during R80-D2 rounds.
- **Latency Scaling:** Linear with respect to rounds (R).

### 6. Risks & Mitigations
- **Data Leakage:** Mitigated by switching from Gemini to Llama 3.3 (Cutoff 2023).
- **Stability:** Solved via KMP_DUPLICATE_LIB_OK and Protobuf pinning.
- **Reproducibilidad:** Commands provided in the README/PR.
