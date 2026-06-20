# Accessible electoral sources replacing/triangulating Reuters

Status: PASS for accessible alternatives. Reuters remains blocked, but the electoral ground truth can be supported without Reuters using the sources below.

## Best replacement source
- GT4_BATIMES_20251026 — Buenos Aires Times, 2025-10-26.
  - Accessible by automated fetch.
  - Reports LLA at 40.84% of votes cast for Chamber of Deputies and Senate with 90% counted.
  - Reports Fuerza Patria around 31.64%.
  - States the result strengthened Milei in Congress and moved LLA close to the one-third needed to shield vetoes.

## Official cross-check
- GT7_DINE_API_2025 — Dirección Nacional Electoral / Ministerio del Interior, Sistema de Publicación de Resultados Electorales.
  - Accessible via official API.
  - Local reproducible computation saved under `answer_key_post_x/sources/DINE_resultados_2025/`.
  - For 2025 Generales, Provisorio, Diputado Nacional, summing party names containing `LIBERTAD AVANZA` across 24 districts gives 9,341,798 votes over 22,977,871 positive votes = 40.6556%.
  - Use this as official-source cross-check, not as a replacement for all seat/gobernability claims.

## Corroborating sources
- GT3_AP_20251027 — AP News, accessible. Reports LLA scored over 40% vs 31% Peronism, and picked up 14 Senate seats and 64 lower-house seats, enough to uphold vetoes/block impeachment efforts.
- GT6_NPR_20251027 — NPR, accessible. Carries the same AP account: over 40% vs 31%, 14 Senate seats and 64 lower-house seats.
- GT5_ELPAIS_20251027 — El País English, accessible. Reports Milei won midterms with more than 40% and discusses deputies/senators and congressional balance.

Recommendation: use GT4 as the precise media numerical citation, GT7 as official reproducible cross-check, and AP/NPR/El País as triangulation for direction, >40% and legislative strengthening. Reuters can remain documented as blocked, not required for the answer key.
