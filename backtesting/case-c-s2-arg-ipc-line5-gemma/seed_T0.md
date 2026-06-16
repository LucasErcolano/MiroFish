# Seed T0 - Argentina IPC 2025

Case ID: `case-c-s2-arg-ipc-line5-gemma`

Temporal package: `T0`

Max document date: `2024-12-31`

Rule: use only the evidence below. Do not use January 2025 releases, post-cutoff data, real IPC outcomes for 2025, or later market reports.

## Included source_ids

- `INST_01`: official Diputados note on pension-law veto, 2024-09-11.
- `INST_02`: Chequeado supporting note on veto count and two-thirds rule, 2024-09-11.
- `SOCIAL_01`: UCA/ODSA subsistence and poverty report, 2024-12-05.
- `POLL_01`: CB Consultora national survey, 2024-12-06.
- `MACRO_01`: BBVA Argentina Economic Outlook, December 2024 / 4Q24.

## Social and institutional baseline

Argentina enters 2025 with severe social stress. The UCA/ODSA report records poverty of 49.9% in 3Q2024 and broader subsistence/privation pressures. For simulation, this should initialize household stress, sensitivity to wages and employment, potential protest pressure, and political limits to continued adjustment [SOCIAL_01].

Opinion evidence from December 2024 separates material hardship from political support. CB Consultora provides pre-cutoff measures of public approval and household economic perception. The key hypothesis is whether resilient approval and rejection of previous alternatives can coexist with deteriorated household conditions [POLL_01].

The institutional constraint is Congress. Diputados reported on 2024-09-11 that the attempt to insist against the pension-law veto received 153 positive votes, 87 negative votes, and 8 abstentions, below the two-thirds threshold. Chequeado corroborates the count and rule. This initializes a veto shield: the Executive can sustain vetoes if it preserves at least one-third blocking power, but that depends on allies and negotiation [INST_01; INST_02].

## Macro baseline before January releases

BBVA's December 2024 outlook frames Argentina in a recovery/desinflation scenario, conditional on the continuity of fiscal adjustment, exchange-rate management, reserves, and political sustainability. It supplies expectations on growth, inflation, fiscal position, exchange-rate risks, and the limits of adjustment [MACRO_01].

At T0, the model should know that disinflation is underway but fragile. It should not yet use the official December 2024 IPC release, the December 2024 REM, the IMF January 2025 evaluation, the BCRA crawling-peg decision, or the January fiscal close announcement.

## Risks to simulate

- Social stress can weaken tolerance to adjustment [SOCIAL_01; POLL_01].
- Congressional fragility can limit fiscal consolidation or force negotiations [INST_01; INST_02].
- The macro scenario depends on fiscal continuity, reserves, exchange-rate policy, and political credibility [MACRO_01].
- Inflation can continue falling, but a correction in FX, tariffs, or confidence could interrupt the trend [MACRO_01].
