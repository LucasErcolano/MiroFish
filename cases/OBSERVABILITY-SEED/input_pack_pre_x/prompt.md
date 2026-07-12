# Simulation Prompt

Run a compact but high-signal simulation for the RodeoAI agri-credit pilot using the attached seed bundle.

I want the run to deliberately exercise the observability features:

- Use semantic deduplication and call out that "Marta Alvarez" and "M. Alvarez" are likely the same producer.
- Preserve contradictions between drought-risk evidence and rainfall-normalization evidence.
- Generate wiki/audit pages for agents, sources, contradictions, timeline and at least one claim.
- Use Deep Search to enrich the context around Argentine agri-credit, weather risk, FX uncertainty, paperwork friction and producer trust.
- Route different roles through different model classes where available: cheap/small model for simple social posts, stronger reasoning model for advisor/report synthesis, local embeddings for dedup/search, fusion/judge model for final comparison.
- Make telemetry useful by keeping enough model calls to show multiple models, latencies, token counts, one parse-warning style event and one recovered error.
- Produce a final investor-facing synthesis that separates temporary liquidity stress from structural default risk.

Simulation requirement:

Simulate a discussion among Argentine soybean/corn producers, an agronomic advisor, a rural-credit media source, a government weather source and an agtech investor about whether producers would trust a RodeoAI-backed financing score. The score uses invoices, buyer contracts, weather risk and repayment history. The simulation should expose trust barriers, contradictory evidence, duplicate customer records and what a bank or investor should change before a pilot.

Report focus:

1. What producers need to trust the score.
2. How advisor interpretation changes adoption.
3. Which source contradictions matter for the credit decision.
4. What duplicate CRM records do to simulation quality.
5. What an investor should believe or doubt after the run.
