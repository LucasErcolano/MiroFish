# Seed T3 - Argentina IPC 2025

Case ID: `case-c-s2-arg-ipc-line5-gemma`

Temporal package: `T3`

Max document date: `2025-01-31`

Rule: this package is cumulative and represents the full valid pre-cutoff input. Do not use IPC January 2025, REM January 2025, reports after `2025-01-31`, real 2025 IPC outcomes, or election results.

## Included source_ids

- `INST_01`: official Diputados note on pension-law veto, 2024-09-11.
- `INST_02`: Chequeado supporting note on veto count and two-thirds rule, 2024-09-11.
- `SOCIAL_01`: UCA/ODSA subsistence and poverty report, 2024-12-05.
- `POLL_01`: CB Consultora national survey, 2024-12-06.
- `MACRO_01`: BBVA Argentina Economic Outlook, December 2024 / 4Q24.
- `MACRO_03`: BCRA REM December 2024, published 2025-01-07.
- `GEO_01`: IMF Ex-post Evaluation, published 2025-01-10.
- `MACRO_02`: INDEC IPC December 2024, published 2025-01-14.
- `POL_01`: Americas Quarterly January 2025 political snapshot.
- `MONETARY_01`: BCRA crawling peg 1% announcement, published 2025-01-16.
- `FISCAL_01`: MECON fiscal surplus announcement, published 2025-01-17.
- `MONETARY_02`: BCRA December 2024 monetary report.
- `MACRO_04`: World Bank January 2025 regional outlook.

## Social and institutional baseline carried from T0

Argentina enters 2025 with severe social stress. The UCA/ODSA report records poverty of 49.9% in 3Q2024 and broader subsistence/privation pressures. For simulation, this should initialize household stress, sensitivity to wages and employment, potential protest pressure, and political limits to continued adjustment [SOCIAL_01].

Opinion evidence from December 2024 separates material hardship from political support. CB Consultora provides pre-cutoff measures of public approval and household economic perception. The key hypothesis is whether resilient approval and rejection of previous alternatives can coexist with deteriorated household conditions [POLL_01].

The institutional constraint is Congress. Diputados reported on 2024-09-11 that the attempt to insist against the pension-law veto received 153 positive votes, 87 negative votes, and 8 abstentions, below the two-thirds threshold. Chequeado corroborates the count and rule. This initializes a veto shield: the Executive can sustain vetoes if it preserves at least one-third blocking power, but that depends on allies and negotiation [INST_01; INST_02].

## Macro, market, and external baseline carried from T2

BBVA's December 2024 outlook frames Argentina in a recovery/desinflation scenario, conditional on the continuity of fiscal adjustment, exchange-rate management, reserves, and political sustainability. It supplies expectations on growth, inflation, fiscal position, exchange-rate risks, and the limits of adjustment [MACRO_01].

The BCRA REM for December 2024, published on `2025-01-07`, gives a market-expectations anchor before the final cutoff. It points to expected 2025 growth around 4.5% and expected 2025 inflation around 25.9%, plus exchange-rate, fiscal, and monetary expectations [MACRO_03].

The IMF Ex-post Evaluation, published on `2025-01-10`, adds external constraints: reserves, exchange-rate normalization, dismantling controls, real interest rates, fiscal consistency, and the social cost of adjustment. The IMF should be modeled as a constraint/agent: support can improve confidence and reserves, but conditionality pushes toward policy consistency and eventual FX normalization [GEO_01].

INDEC's December 2024 IPC report, published on `2025-01-14`, gives the last official monthly inflation datapoint available before the full cutoff: 2.7% monthly in December 2024 and 117.8% accumulated inflation for 2024. This is the concrete starting point for the 2025 IPC trajectory [MACRO_02].

Americas Quarterly's January 2025 snapshot frames the 2025 legislative election as a political validation test for Milei's economic program, with implications for FMI, geopolitics, and legislative capacity [POL_01].

## New evidence added at T3

The BCRA announced on `2025-01-16` that the official crawling peg would move to 1% monthly from `2025-02-01`. This reinforces the exchange rate as nominal anchor and can lower tradables inflation, but it also raises risks of real appreciation, pressure on exporters/reserves, and future correction [MONETARY_01].

MECON reported on `2025-01-17` that the national public sector registered an annual financial surplus for the first time since 2010. This strengthens the fiscal anchor and credibility of deficit zero, but also tightens the political constraint: the Executive has less room to respond to poverty, provinces, or congressional pressure with spending [FISCAL_01; SOCIAL_01; INST_01].

The BCRA December 2024 monetary report adds liquidity, monetary base, remunerated liabilities/LEFI, private credit, banking conditions, and monetary transmission context at the end of 2024 [MONETARY_02].

The World Bank January 2025 regional outlook projects a rebound for Argentina around 5% in 2025 and 4.7% in 2026, giving external support to the recovery scenario [MACRO_04].

## Full pre-cutoff causal picture at T3

At T3, MiroFish should balance three forces:

- disinflation anchors: December IPC 2.7%, lower crawling peg, fiscal surplus, REM expectations, and recovery projections [MACRO_02; MONETARY_01; FISCAL_01; MACRO_03; MACRO_04];
- fragility channels: FX controls, reserves, possible real appreciation, tariff or relative-price corrections, and IMF constraints [GEO_01; MONETARY_01; MACRO_01];
- political and social constraints: poverty, household stress, congressional veto shield, midterm validation, and tolerance to adjustment [SOCIAL_01; POLL_01; INST_01; INST_02; POL_01].

## Risks to simulate

- Social stress can weaken tolerance to adjustment [SOCIAL_01; POLL_01].
- Congressional fragility can limit fiscal consolidation or force negotiations [INST_01; INST_02].
- A low crawling peg can support disinflation but accumulate FX misalignment [MONETARY_01].
- Fiscal credibility supports expectations but can increase social and provincial stress [FISCAL_01; SOCIAL_01].
- IMF support and IMF constraints can improve confidence while forcing difficult normalization steps [GEO_01].
- The 2025 inflation path can be lower than 2024 but still non-linear, especially if Q2 relative-price or FX pressures appear [MACRO_01; MACRO_02; MACRO_03].
