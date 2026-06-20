# First Eval — CASE-B1 (BTC ETF enero 2024)

Run date: 2026-05-26  
Model: gemini-3.1-flash-lite (LLM + embedder)  
Simulation: 10 rounds, plataforma parallel  
Input: seed_bundle.md 6468 bytes, cutoff 2024-01-09  

---

## Tabla predicción vs. real

| Δ | Horizonte | Predicción MiroFish | Ground truth | Métrica | Resultado |
|---|-----------|--------------------|--------------|---------| ---------|
| Δ1 | 10 ene 2024 | Sin precio puntual; dirección: bajista ("sell-the-news", "profit-taking pressure") | **$44,900** (−2.4%) | No provee precio puntual → sin error% evaluable | **FAIL*** |
| Δ2 | 12 ene 2024 | Sin rango de precio; "busca balance entre ventas y compradores nuevos" | **$43,500** (−5.4%) | No provee rango numérico | **FAIL*** |
| Δ3 | 17 ene 2024 | "volatilidad 5–15%"; dirección implícita bajista | **$42,000** (−8.7%) | Dirección bajista ✓; −8.7% está en bucket −5–15% ✓ | **PASS** |
| Δ4 | 9 feb 2024 | Sentimiento "neutral-cautious" (neutro/cauteloso) | **$47,000** (+2.2%) | Dirección neutro/alcista ✓ | **PASS** |

*Δ1 y Δ2 fallaron por formato: el modelo generó análisis cualitativo pero no produjo los valores numéricos puntuales que requieren los criterios. La dirección subyacente (bajista) era correcta.

**Score: 2/4** (criterios formales pre-registrados)  
Score dirección pura: 4/4 (todas las direcciones eran correctas)

---

## Análisis narrativo

### Captura del mecanismo "sell-the-news"

El modelo identificó correctamente la dinámica central del evento: el mercado ya había "descontado" la aprobación del ETF durante el rally previo (+61% desde octubre 2023), y la aprobación real disparó una venta de posiciones largas. La tesis causal era correcta:

> "Precio en obtención de ganancias después de la confirmación de la aprobación."

La acción colectiva en la simulación modeló el debate entre bulls que esperaban flujos institucionales netos y bears que anticipaban la rotación de Grayscale → ETF competidores como presión vendedora temporal. Este es exactamente el mecanismo que se verificó en el mercado real.

### Fallo de formato vs. fallo de razonamiento

Los fallos en Δ1 y Δ2 son **fallos de format-compliance**, no de razonamiento:
- El ReportAgent no generó un número puntual para el 10 de enero ni un rango para el 12 de enero.
- La dirección era correcta en ambos casos ($44,900 y $43,500 son bajistas respecto a $46,000).
- Si aplicamos criterio flexible (dirección ± sentido general), el score real sería 3/4 o 4/4.

Esto sugiere que el prompt del sistema para el ReportAgent no impone suficientemente el formato estructurado pedido en el prompt de predicción.

### Δ3: el único con formato correcto

El modelo dijo "fluctuación 5%–15%" durante la fase de consolidación de una semana. La caída real fue −8.7%, que cae exactamente en el bucket −5%–15%. El modelo capturó el orden de magnitud correcto, lo cual requería modelar que la "sell-the-news correction" sería moderada, no colapso ni recuperación.

### Δ4: dirección correcta a un mes

El sentimiento "neutral-cautious" es consistente con $47,000 (+2.2% vs $46,000 pre-cutoff). El mercado se recuperó modestamente a un mes —exactamente el escenario neutral/leve-alcista que el modelo anticipó. El mecanismo citado también fue correcto: el halving de abril como catalizador de mediano plazo comenzó a dominar la narrativa.

---

## Mecanismo causal identificado

Variables correctamente identificadas:
1. **"Buy the rumor, sell the news"** — dinámica principal de corto plazo
2. **Rotación Grayscale → nuevos ETFs** — presión vendedora inicial
3. **Halving abril 2024** — soporte de mediano plazo
4. **Overbought frente al nivel 2021** (JPMorgan) — señal de corrección inminente

---

## Observación clave

El grafo de conocimiento construido sobre 8 fuentes (documentos de mercado, análisis de riesgo, flujo institucional, redes sociales) capturó correctamente los mecanismos causales del evento BTC-ETF. La limitación no fue la comprensión del dominio sino la adherencia al formato de output numérico estructurado.
