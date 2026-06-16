# Seed T2 - Argentina IPC 2025

Case ID: `case-c-s2-arg-ipc-line5-gemma`

Temporal package: `T2`

Max document date: `2025-01-14`

Rule: this package is cumulative. It includes all T1 evidence plus the official December 2024 IPC release and January political framing. Do not use documents published after `2025-01-14`.

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

## T1 carryover

Before the new evidence, the system has a fragile disinflation scenario, market expectations for materially lower 2025 inflation, IMF constraints on reserves and exchange-rate normalization, high poverty/social stress, and a Congress where the Executive needs a veto shield [MACRO_01; MACRO_03; GEO_01; SOCIAL_01; INST_01].

## New evidence at T2

INDEC's December 2024 IPC report, published on `2025-01-14`, gives the last official monthly inflation datapoint available in this package: 2.7% monthly in December 2024 and 117.8% accumulated inflation for 2024. This is the concrete starting point for the 2025 IPC trajectory [MACRO_02].

Americas Quarterly's January 2025 snapshot frames the 2025 legislative election as a political validation test for Milei's economic program, with implications for FMI, geopolitics, and legislative capacity. This does not replace macro evidence, but it should affect agents' expectations about governability and policy continuity [POL_01].

## Updated causal picture

At T2, MiroFish should update using a real observed inflation baseline:

- monthly inflation has already fallen to 2.7% by December 2024 [MACRO_02];
- market expectations point to lower 2025 inflation, but the path can be non-linear [MACRO_03];
- political validation and congressional capacity matter for program credibility during 2025 [POL_01; INST_01];
- social stress remains the counterweight to optimistic macro projections [SOCIAL_01].

## Risks to simulate

- Over-extrapolating from December 2024 IPC into a smooth 2025 path [MACRO_02].
- Treating the election/political context as noise when it can affect expectations and policy continuity [POL_01].
- Ignoring IMF/FX constraints after adding the official IPC datapoint [GEO_01].
