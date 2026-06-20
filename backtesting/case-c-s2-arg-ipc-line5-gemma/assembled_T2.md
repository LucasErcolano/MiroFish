# Seed T2 - Argentina IPC 2025

Case ID: `case-c-s2-arg-ipc-line5-gemma`

Temporal package: `T2`

Max document date: `2025-01-14`

Rule: this package is cumulative. It includes the full T1 evidence plus the official December 2024 IPC release and January political framing. Do not use documents published after `2025-01-14`.

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

## Social and institutional baseline carried from T0

Argentina enters 2025 with severe social stress. The UCA/ODSA report records poverty of 49.9% in 3Q2024 and broader subsistence/privation pressures. For simulation, this should initialize household stress, sensitivity to wages and employment, potential protest pressure, and political limits to continued adjustment [SOCIAL_01].

Opinion evidence from December 2024 separates material hardship from political support. CB Consultora provides pre-cutoff measures of public approval and household economic perception. The key hypothesis is whether resilient approval and rejection of previous alternatives can coexist with deteriorated household conditions [POLL_01].

The institutional constraint is Congress. Diputados reported on 2024-09-11 that the attempt to insist against the pension-law veto received 153 positive votes, 87 negative votes, and 8 abstentions, below the two-thirds threshold. Chequeado corroborates the count and rule. This initializes a veto shield: the Executive can sustain vetoes if it preserves at least one-third blocking power, but that depends on allies and negotiation [INST_01; INST_02].

## Macro and external baseline carried from T1

BBVA's December 2024 outlook frames Argentina in a recovery/desinflation scenario, conditional on the continuity of fiscal adjustment, exchange-rate management, reserves, and political sustainability. It supplies expectations on growth, inflation, fiscal position, exchange-rate risks, and the limits of adjustment [MACRO_01].

The BCRA REM for December 2024, published on `2025-01-07`, gives a market-expectations anchor before the final cutoff. It points to expected 2025 growth around 4.5% and expected 2025 inflation around 25.9%, plus exchange-rate, fiscal, and monetary expectations [MACRO_03].

The IMF Ex-post Evaluation, published on `2025-01-10`, adds external constraints: reserves, exchange-rate normalization, dismantling controls, real interest rates, fiscal consistency, and the social cost of adjustment. The IMF should be modeled as a constraint/agent: support can improve confidence and reserves, but conditionality pushes toward policy consistency and eventual FX normalization [GEO_01].

## New evidence added at T2

INDEC's December 2024 IPC report, published on `2025-01-14`, gives the last official monthly inflation datapoint available in this package: 2.7% monthly in December 2024 and 117.8% accumulated inflation for 2024. This is now the concrete starting point for the 2025 IPC trajectory [MACRO_02].

Americas Quarterly's January 2025 snapshot frames the 2025 legislative election as a political validation test for Milei's economic program, with implications for FMI, geopolitics, and legislative capacity. This does not replace macro evidence, but it should affect agents' expectations about governability and policy continuity [POL_01].

## Updated causal picture at T2

At T2, MiroFish should now combine the full social/institutional baseline, the REM and IMF constraints, and an observed inflation starting point:

- monthly inflation has already fallen to 2.7% by December 2024 [MACRO_02];
- market expectations point to lower 2025 inflation, but the path can still be non-linear [MACRO_03];
- IMF scrutiny keeps reserves, FX normalization, and policy consistency central [GEO_01];
- political validation and congressional capacity matter for program credibility during 2025 [POL_01; INST_01; INST_02];
- social stress remains the counterweight to optimistic macro projections [SOCIAL_01; POLL_01].

## Risks to simulate

- Social stress can weaken tolerance to adjustment [SOCIAL_01; POLL_01].
- Congressional fragility can limit fiscal consolidation or force negotiations [INST_01; INST_02].
- The macro scenario still depends on fiscal continuity, reserves, exchange-rate policy, and political credibility [MACRO_01].
- Over-extrapolating from December 2024 IPC into a smooth 2025 path [MACRO_02].
- Ignoring IMF and FX constraints after adding the official IPC datapoint [GEO_01].
- Treating the election and governability context as noise when it can affect expectations and policy continuity [POL_01].
