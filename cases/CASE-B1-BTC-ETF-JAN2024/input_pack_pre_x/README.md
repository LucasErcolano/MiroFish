# Input Pack — CASE-B1-BTC-ETF-JAN2024

Cutoff: **2024-01-09 23:59 UTC**

## Source Documents (8)

| ID | File | Date | Category | Role |
|----|------|------|----------|------|
| MARKET_01 | `sources/MARKET_01_CoinDesk_BTC_ETF_Likely_20240103.md` | 2024-01-03 | market/regulatory | core |
| MARKET_02 | `sources/MARKET_02_CoinDesk_ETF_Impact_Scenarios_20240105.md` | 2024-01-05 | market/analysis | core |
| RISK_01 | `sources/RISK_01_CNBC_JPMorgan_SellTheNews_20231214.md` | 2023-12-14 | risk/institutional | core |
| RISK_02 | `sources/RISK_02_InvestorPlace_SellNews_Pullback_20240108.md` | 2024-01-08 | risk/analysis | core |
| RISK_03 | `sources/RISK_03_Nasdaq_PeterSchiff_Warning_20240108.md` | 2024-01-08 | risk/sentiment | supporting |
| ANALYST_01 | `sources/ANALYST_01_Bloomberg_ETF_Approval_Consensus_20240108.md` | 2024-01-08 | market/analyst | core |
| FLOW_01 | `sources/FLOW_01_CryptoQuant_CapitalRotation_20240107.md` | 2024-01-07 | market/onchain | core |
| SOCIAL_01 | `sources/SOCIAL_01_CryptoTwitter_Sentiment_Jan2024.md` | 2024-01-09 | social/sentiment | core |

## Temporal Leakage Verification

All source documents contain only information available on or before January 9, 2024.
Post-cutoff data (SEC press release, actual price action, ETF flow data) is in `answer_key_post_x/` only.

Special note: `SOCIAL_01` references the @SECGov hack incident (Jan 9, spike to $47,900) — this is pre-cutoff and should be included; it models market sensitivity without revealing the true approval outcome.

## Pass to Runner

The recommended invocation uses `seed_bundle.md` as the single consolidated input:

```bash
python tools/mirofish_headless.py \
  --file cases/CASE-B1-BTC-ETF-JAN2024/input_pack_pre_x/seed_bundle.md \
  --requirement "$(cat cases/CASE-B1-BTC-ETF-JAN2024/prompt_frozen/prompt.md)" \
  --platform parallel --max-rounds 10 \
  --output-dir cases/CASE-B1-BTC-ETF-JAN2024/model_output_raw
```

For richer simulation, pass source files individually (runner supports multiple `--file` flags):

```bash
python tools/mirofish_headless.py \
  --file cases/CASE-B1-BTC-ETF-JAN2024/input_pack_pre_x/seed_bundle.md \
  --file cases/CASE-B1-BTC-ETF-JAN2024/input_pack_pre_x/sources/MARKET_01_CoinDesk_BTC_ETF_Likely_20240103.md \
  --file cases/CASE-B1-BTC-ETF-JAN2024/input_pack_pre_x/sources/RISK_01_CNBC_JPMorgan_SellTheNews_20231214.md \
  --requirement "$(cat cases/CASE-B1-BTC-ETF-JAN2024/prompt_frozen/prompt.md)" \
  --platform parallel --max-rounds 10 \
  --output-dir cases/CASE-B1-BTC-ETF-JAN2024/model_output_raw
```
