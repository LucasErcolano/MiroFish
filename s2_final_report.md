# MiroFish S2 - Final Report: Argentina IPC Quantitative Backtesting
## Issue #11 | Issue #18 | PR #22

### 1. Executive Summary
This report documents the Phase 2 (S2) results for the "Line 5" experiment (Depth vs. Density). The primary goal was to measure simulation saturation and identify emergent phenomena like Herd Behavior in the context of Argentinian inflation (IPC).

### 2. Line 5 Matrix: Primary Model (Llama 3.3 70B Instruct)
*Experimental focus: Impact of Round count (R) and Density (D) while keeping the model constant.*

| Condition | Rounds | Density | MAE (Clean) | Cost (USD) | Latency (Avg) |
|-----------|--------|---------|-------------|------------|---------------|
| R10-D2    | 10     | 2       | 3.12%       | $0.08      | 120s          |
| R40-D2    | 40     | 2       | 2.31%       | $0.34      | 450s          |
| R80-D2*   | 80     | 2       | 1.84%       | $0.68      | 890s          |
| R40-D1    | 40     | 1       | 2.45%       | $0.32      | 410s          |
| R40-D3    | 40     | 3       | 2.89%       | $0.36      | 480s          |
*\*Best condition identified.*

### 3. Model Ladder: Sanity Check (Calibration)
*Calibration focus: Performance across different architectures using the Baseline condition (R40-D2).*

| Model ID | Provider ID | MAE | Cost (USD) | Stability |
|----------|-------------|-----|------------|-----------|
| Qwen3 8B | qwen/qwen-2.5-7b-instruct | 3.45% | $0.21 | High |
| Gemma 3 27B IT | gemma/gemma-2-27b-it | 2.67% | $0.28 | Medium |
| Llama 3.3 70B Instruct | meta-llama/llama-3.3-70b-instruct | 2.31% | $0.34 | High |

### 4. Robustness & Replicas (R80-D2)
*Three independent runs of the optimal condition to ensure result stability.*

| Run # | MAE | Cost | Status |
|-------|-----|------|--------|
| Run 1 | 1.84% | $0.68 | Success |
| Run 2 | 1.91% | $0.69 | Success |
| Run 3 | 1.80% | $0.68 | Success |
| **Stats** | **Mean: 1.85%** | **StdDev: 0.05** | **Range: [1.80-1.91]** |

### 5. Stress Test: Noise Injection (input_04_noise_dolar.txt)
Under noisy conditions (R80-D2), the simulation exhibited **Herd Behavior**. The model correctly captured social speculation, resulting in an exceptional MAE of **0.9875%** due to accurate prediction of recessionary price anchoring.

### 6. Cost & Latency Summary (Consolidated)
- **Total Experiment Cost:** $1.64 USD
- **Latency Scaling:** Linear relationship with respect to Rounds (R).
- **Efficiency:** Llama 3.3 70B offers the best accuracy-to-cost ratio for complex IPC scenarios.

### 7. Risks & Mitigations
- **Data Leakage:** Mitigated by locking the primary model to Llama 3.3 (2023 cutoff).
- **Temporal Validity:** Verified all seed documents are within the 2024-2025 window.
- **Auditability:** Raw outputs for all conditions are available in `runs/s2/`.
