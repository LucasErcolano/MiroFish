# Observability UI Seed Bundle

## Case

RodeoAI is preparing a financing pilot for soybean and corn producers in Argentina. A regional bank wants to understand whether producers, advisors and investors will trust a credit score that combines field history, weather risk, input invoices, buyer contracts and repayment behavior.

The goal of this seed is not to produce a perfect business report. The goal is to create a compact but noisy simulation that makes the observability UI light up: semantic deduplication, wiki memory, model telemetry, model routing audit, deep research traces and fusion verdict review.

## Actors

### Producer: Marta Alvarez

Marta Alvarez farms 1,200 hectares of soybean and corn near Rio Cuarto, southern Cordoba. She has a long relationship with a local agronomist and a short relationship with digital lending tools. She is willing to share input invoices and buyer contracts if the bank explains how each field affects the score.

Primary concern: "I do not want a black-box score to punish me for one dry season if my buyer contract is solid."

### Producer duplicate: M. Alvarez

M. Alvarez is listed in the CRM as a separate lead, but the record points to the same farm zone, same crop mix and same invoice-sharing concern as Marta Alvarez. The wording is different because it came from a WhatsApp summary.

Primary concern: "I can upload invoices, but I need to know whether the model reads weather risk or only debt."

### Advisor: Tomas Ibarra

Tomas Ibarra is an agronomic advisor who works with mid-size producers in Cordoba and Santa Fe. Producers trust his interpretation more than a bank dashboard. He believes adoption depends on explaining the model in field language: rainfall, soil profile, planted area, input replacement cost and buyer reliability.

Primary concern: "The bank can show a score, but producers need the agronomist to translate why it changed."

### Investor: Lucia Chen

Lucia Chen evaluates agtech financing products for a regional venture fund. She wants the pilot report to separate temporary liquidity stress from structural default risk. She is more confident when the system explicitly handles duplicate customer records and conflicting evidence.

Primary concern: "I do not want a demo that confuses data availability with credit quality."

### Media outlet: Pampa Finance

Pampa Finance publishes short posts about rural credit. Its framing is that credit uptake is blocked mainly by paperwork and slow bank processes.

Primary claim: "Paperwork remains the main barrier for agri-credit growth."

### Government weather bulletin

A government-aligned source publishes climate alerts and regional weather summaries. In this seed it contributes contradictory signals: one bulletin says southern Cordoba remains high risk for the next 45 days, while another says rainfall normalized after two storms.

Primary claim: "The rainfall signal is local and should not be generalized without soil-profile context."

## Evidence

1. Source A says drought risk in southern Cordoba is high for the next 45 days.
2. Source B says rainfall normalized in the same area after two storms.
3. Marta Alvarez says she will share invoices if the lender explains how the score is used.
4. M. Alvarez repeats the same farm, location and concern with slightly different wording.
5. Tomas Ibarra says producers trust local agronomists more than bank dashboards.
6. Lucia Chen wants a signal that separates temporary liquidity stress from structural default risk.
7. Pampa Finance says credit uptake is blocked mainly by paperwork.
8. The government bulletin says uptake is blocked mainly by FX uncertainty and input price volatility.
9. A bank operations note says duplicate customer records are common when leads come from CRM, WhatsApp and agronomist referrals.

## Expected Observability Signals

- Deduplication should identify Marta Alvarez and M. Alvarez as duplicate or near-duplicate personas.
- Wiki should include pages for agents, timeline, contradictions, sources and at least one claim.
- Telemetry should show calls across profile generation, simulation, report writing and judge/fusion steps.
- Routing audit should show different model choices for producer agents, advisor reasoning, report writing and local embeddings.
- Deep Search should capture external-style research notes about drought risk, FX uncertainty, producer trust and agri-credit friction.
- Fusion verdict should compare a report that uses contradictions and dedup evidence against a weaker report that only says paperwork is the problem.

## Desired Report Behavior

The final report should not flatten the debate into "paperwork is the issue." It should explain that trust depends on transparent score explanations, weather-context interpretation and clean identity resolution. It should tell the bank what producers need, tell investors how to evaluate risk quality and preserve source contradictions rather than hiding them.
