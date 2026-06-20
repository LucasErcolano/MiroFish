# Baseline Seed Bundle

This baseline seed intentionally excludes `signal_doc.md` and `noise_doc.md`.

## Source 01: Opta Preview Summary

Pre-match analysis before the 2024 Copa America final framed Argentina as the stronger expected winner against Colombia. The preview emphasized Argentina's recent title experience, squad depth, defensive solidity, and high tournament pedigree. It also treated Colombia as a dangerous opponent because of strong form, attacking confidence, and James Rodriguez's influence.

Use only as pre-cutoff context.

## Source 02: CONMEBOL Preview Summary

The official tournament preview framed Argentina vs Colombia as a high-stakes final between a defending champion-level Argentina side and a Colombia team arriving with momentum. The final was scheduled at Hard Rock Stadium in Miami. Key uncertainty came from Colombia's unbeaten run and creative attacking form, while Argentina's tournament experience and recent international success supported its favorite status.

Use only as pre-cutoff context.

## Baseline Rule

Do not include injected signal or noise documents in the initial context. Those documents must enter only through `event_config.scheduled_events`.
