# Seed T3 - Argentina IPC 2025

Case ID: `case-c-s2-arg-ipc-line5-gemma`

Temporal package: `T3`

Max document date: `2025-01-31`

Rule: this package is cumulative and represents the full valid pre-cutoff input. Do not use IPC January 2025, REM January 2025, reports after `2025-01-31`, real 2025 IPC outcomes, or election results.

## Included source_ids

- `INST_01`
- `INST_02`
- `SOCIAL_01`
- `POLL_01`
- `MACRO_01`
- `MACRO_03`
- `GEO_01`
- `MACRO_02`
- `POL_01`
- `MONETARY_01`
- `FISCAL_01`
- `MONETARY_02`
- `MACRO_04`

## T2 carryover

The system has a December 2024 official IPC baseline of 2.7% monthly and 117.8% accumulated 2024 inflation, market expectations for lower 2025 inflation, IMF constraints on FX/reserves, political validation risk around the 2025 legislative election, high poverty/social stress, and a congressional veto shield that depends on coalition discipline [MACRO_02; MACRO_03; GEO_01; POL_01; SOCIAL_01; INST_01].

## New evidence at T3

The BCRA announced on `2025-01-16` that the official crawling peg would move to 1% monthly from `2025-02-01`. This reinforces the exchange rate as nominal anchor and can lower tradables inflation, but it also raises risks of real appreciation, pressure on exporters/reserves, and future correction [MONETARY_01].

MECON reported on `2025-01-17` that the national public sector registered an annual financial surplus for the first time since 2010. This strengthens the fiscal anchor and credibility of deficit zero, but also tightens the political constraint: the Executive has less room to respond to poverty, provinces, or congressional pressure with spending [FISCAL_01; SOCIAL_01; INST_01].

The BCRA December 2024 monetary report adds liquidity, monetary base, remunerated liabilities/LEFI, private credit, banking conditions, and monetary transmission context at the end of 2024 [MONETARY_02].

The World Bank January 2025 regional outlook projects a rebound for Argentina around 5% in 2025 and 4.7% in 2026, giving external support to the recovery scenario [MACRO_04].

## Full pre-cutoff causal picture

At T3, MiroFish should balance three forces:

- disinflation anchors: December IPC 2.7%, lower crawling peg, fiscal surplus, REM expectations, and recovery projections [MACRO_02; MONETARY_01; FISCAL_01; MACRO_03; MACRO_04];
- fragility channels: FX controls/reserves, possible real appreciation, tariff/relative-price corrections, and IMF constraints [GEO_01; MONETARY_01; MACRO_01];
- political/social constraints: poverty, household stress, congressional veto shield, midterm validation, and tolerance to adjustment [SOCIAL_01; POLL_01; INST_01; POL_01].

## Risks to simulate

- A low crawling peg can support disinflation but accumulate FX misalignment [MONETARY_01].
- Fiscal credibility supports expectations but can increase social and provincial stress [FISCAL_01; SOCIAL_01].
- IMF support/constraints can improve confidence while forcing difficult normalization steps [GEO_01].
- The 2025 inflation path can be lower than 2024 but still non-linear, especially if Q2 relative-price or FX pressures appear [MACRO_01; MACRO_02; MACRO_03].
