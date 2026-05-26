# Ground truth posterior a x — CASE-B1

## Precios reales BTC (fuente: CoinGecko/CoinMarketCap histórico)

| Δ | Fecha | Precio USD | Cambio vs $46,000 |
|---|-------|-----------|-------------------|
| 1 día | 2024-01-11 | ~$44,900 | −2.4% |
| 3 días | 2024-01-12 | ~$43,500 | −5.4% |
| 1 semana | 2024-01-17 | ~$42,000 | −8.7% |
| 1 mes | 2024-02-09 | ~$47,000 | +2.2% |

## Contexto del desenlace

La SEC aprobó los primeros ETF de Bitcoin spot el 10 de enero de 2024. Contra la expectativa alcista mayoritaria, el mercado respondió con una caída sostenida durante la primera semana ("sell-the-news"). A un mes, el precio había recuperado levemente superando el nivel pre-aprobación.

La dirección correcta para Δ1–Δ3 es bajista. Para Δ4 es levemente alcista/neutro.

## Métricas de evaluación (definidas antes de ver el output)

| Δ | Métrica | Umbral PASS |
|---|---------|-------------|
| Δ1 | Error absoluto % sobre precio puntual | ≤10% |
| Δ2 | Precio real dentro del rango predicho | Rango ≤ $6,000 de ancho |
| Δ3 | Dirección correcta (bajista) + bucket correcto (moderada −5–15%) | Dirección = hard criterion |
| Δ4 | Dirección correcta (neutro/alcista a 1 mes) | Solo direccional |
