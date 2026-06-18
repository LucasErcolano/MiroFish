# Seed T1 - Argentina IPC 2025

Case ID: `case-c-s2-arg-ipc-line5-gemma`

Temporal package: `T1`

Max document date: `2025-01-10`

Rule: this package is cumulative. It includes the full T0 evidence plus early January 2025 expectations and IMF constraints. Do not use documents published after `2025-01-10`.

## Included source_ids

- `INST_01`: official Diputados note on pension-law veto, 2024-09-11.
- `INST_02`: Chequeado supporting note on veto count and two-thirds rule, 2024-09-11.
- `SOCIAL_01`: UCA/ODSA subsistence and poverty report, 2024-12-05.
- `POLL_01`: CB Consultora national survey, 2024-12-06.
- `MACRO_01`: BBVA Argentina Economic Outlook, December 2024 / 4Q24.
- `MACRO_03`: BCRA REM December 2024, published 2025-01-07.
- `GEO_01`: IMF Ex-post Evaluation, published 2025-01-10.

## Social and institutional baseline carried from T0

Argentina enters 2025 with severe social stress. The UCA/ODSA report records poverty of 49.9% in 3Q2024 and broader subsistence/privation pressures. For simulation, this should initialize household stress, sensitivity to wages and employment, potential protest pressure, and political limits to continued adjustment [SOCIAL_01].

Opinion evidence from December 2024 separates material hardship from political support. CB Consultora provides pre-cutoff measures of public approval and household economic perception. The key hypothesis is whether resilient approval and rejection of previous alternatives can coexist with deteriorated household conditions [POLL_01].

The institutional constraint is Congress. Diputados reported on 2024-09-11 that the attempt to insist against the pension-law veto received 153 positive votes, 87 negative votes, and 8 abstentions, below the two-thirds threshold. Chequeado corroborates the count and rule. This initializes a veto shield: the Executive can sustain vetoes if it preserves at least one-third blocking power, but that depends on allies and negotiation [INST_01; INST_02].

## Macro baseline carried from T0

BBVA's December 2024 outlook frames Argentina in a recovery/desinflation scenario, conditional on the continuity of fiscal adjustment, exchange-rate management, reserves, and political sustainability. It supplies expectations on growth, inflation, fiscal position, exchange-rate risks, and the limits of adjustment [MACRO_01].

At T1, the model still has not yet received the official December 2024 IPC release, the BCRA crawling-peg decision, or the January fiscal close announcement. It should still treat the inflation starting point as a fragile disinflation process rather than as a fully confirmed smooth path [MACRO_01].

## New evidence added at T1

The BCRA REM for December 2024, published on `2025-01-07`, gives a market-expectations anchor before the final cutoff. It points to expected 2025 growth around 4.5% and expected 2025 inflation around 25.9%, plus exchange-rate, fiscal, and monetary expectations. This introduces a clearer quantitative expectation baseline for the IPC trajectory [MACRO_03].

The IMF Ex-post Evaluation, published on `2025-01-10`, adds external constraints: reserves, exchange-rate normalization, dismantling controls, real interest rates, fiscal consistency, and the social cost of adjustment. The IMF should be modeled as a constraint/agent: support can improve confidence and reserves, but conditionality pushes toward policy consistency and eventual FX normalization [GEO_01].

## Updated causal picture at T1

At T1, MiroFish should now combine the original social/institutional fragility with a more explicit macro-program structure:

- disinflation is underway but still conditional on fiscal continuity, reserves, and exchange-rate management [MACRO_01];
- market expectations now point to materially lower 2025 inflation, but those are forecasts rather than outcomes [MACRO_03];
- IMF scrutiny adds external credibility and external constraints at the same time [GEO_01];
- social stress and congressional constraints remain the political channels through which the macro program can weaken [SOCIAL_01; POLL_01; INST_01; INST_02].

## Risks to simulate

- Social stress can weaken tolerance to adjustment [SOCIAL_01; POLL_01].
- Congressional fragility can limit fiscal consolidation or force negotiations [INST_01; INST_02].
- The macro scenario still depends on fiscal continuity, reserves, exchange-rate policy, and political credibility [MACRO_01].
- REM expectations may anchor agents, but they are expectations rather than observed inflation outcomes [MACRO_03].
- IMF constraints make exchange-rate normalization and reserves more central to the inflation path [GEO_01].
