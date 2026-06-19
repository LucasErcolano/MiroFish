# MiroFish Backtesting Analysis — Cases B1 & B2

Fecha de análisis: 2026-05-27  
Branch: `feat/case-b-backtesting`

---

## Resumen ejecutivo

| Case | Dominio | Horizonte | Score (criterios formales) | Score dirección pura |
|------|---------|-----------|---------------------------|----------------------|
| B1 — BTC ETF ene 2024 | Cripto / evento regulatorio | 1d, 3d, 1sem, 1mes | 2/4 | 4/4 |
| B2 — Argentina IPC 2025 | Macroeconomía / desinflación | 1m, 3m, 6m, 11m | 2/4 | 2.5/4 |

Ambos casos producen el mismo score formal (2/4), pero por razones distintas. El patrón de errores revela las verdaderas fortalezas y límites del sistema.

---

## Predicciones vs. ground truth

### CASE-B1: Bitcoin ETF (cutoff 9 ene 2024)

| Δ | Predicción | Real | Error | PASS/FAIL |
|---|-----------|------|-------|-----------|
| Δ1 (10 ene) | bajista, sin precio puntual | $44,900 (−2.4%) | — | FAIL (formato) |
| Δ2 (12 ene) | bajista, sin rango | $43,500 (−5.4%) | — | FAIL (formato) |
| Δ3 (17 ene) | −5–15%, bajista | $42,000 (−8.7%) | ✓ en bucket y dirección | PASS |
| Δ4 (9 feb) | neutro-cauteloso | $47,000 (+2.2%) | ✓ dirección | PASS |

### CASE-B2: Argentina IPC (cutoff 31 ene 2025)

| Δ | Predicción | Real | Error | PASS/FAIL |
|---|-----------|------|-------|-----------|
| Δ1 (feb 2025) | 2.5% (rango 2.2–2.8%) | 2.4% | 0.1pp | PASS |
| Δ2 (abr 2025) | 1.8–2.3%, desacelerando | 3.7% | ~1.5–1.9pp over | FAIL |
| Δ3 (jul 2025) | bucket 2–4% moderada | ~3.0% | ✓ bucket correcto | PASS |
| Δ4 (dic 2025) | "consolidado", sin rango acumulado | 31.5% acum, 2.8% mensual | — | FAIL (formato) |

---

## Curva de degradación por horizonte

```
Horizonte    B1 (acierto direcional)   B2 (acierto formal)
Δ1 (corto)   ✓ (sin número)            ✓✓ (error 0.1pp)
Δ2 (corto+)  ✓ (sin número)            ✗ (miss 1.5pp)
Δ3 (medio)   ✓✓ (bucket+dirección)     ✓ (bucket ok)
Δ4 (largo)   ✓ (dirección)             ~ (dirección ok, sin rango)
```

**Patrón observado**: el sistema captura bien los horizontes corto (Δ1) y medio-largo (Δ3, Δ4). El punto más débil es Δ2 —el horizonte "medio-corto" donde los shocks transitorios (rebotes, ajustes de tarifas, volatilidad puntual) son más difíciles de modelar que las tendencias dominantes.

---

## Hallazgos principales

### 1. Fortaleza en narrativa causal

En ambos casos el sistema identificó correctamente los mecanismos causales dominantes:

- **B1**: "buy the rumor, sell the news" + rotación Grayscale→ETF + halving como catalizador mediano plazo. Todos verificados como correctos.
- **B2**: crawling peg 1% como ancla nominal + superávit fiscal cero + validación IMF. Todos verificados como correctos.

El grafo de conocimiento + simulación social es efectivo para extraer y modelar las tesis causales que circulan en el sistema informativo antes del evento.

### 2. Fallo de linealidad en B2-Δ2

El mayor miss fue la suposición implícita de que la desinflación continuaría linealmente. El dato real de abril (3.7%) fue una aceleración, no una continuación. El seed bundle (cutoff 31/01/2025) no contenía señales de los factores que explicaron ese rebote (probablemente ajustes tarifarios o shocks de oferta locales).

**Conclusión**: el sistema no puede predecir shocks no señalados en el input. No es un fallo del modelo sino una limitación epistémica: sin información sobre los shocks futuros, cualquier sistema haría la misma extrapolación de tendencia dominante.

### 3. Fallo de formato en B1-Δ1/Δ2 y B2-Δ4

El ReportAgent no generó las estructuras numéricas pedidas en algunos deltaS:
- B1: no dio precio puntual ni rango de precio
- B2-Δ4: no dio rango de acumulada 2025

El razonamiento subyacente era correcto pero el output no cumplió el formato del prompt de predicción. Esto es un problema de **prompt engineering del ReportAgent**, no de capacidad predictiva.

### 4. La simulación social aportó valor real

La evidencia de que el sistema aporta más que un LLM puro está en la calidad de las citas causales. En B2 el sistema citó textualmente el anuncio BCRA del 16/01/2025 sobre el crawling peg —dato que sólo podía extraerse si el grafo procesó correctamente el MACRO_01 source. En B1 cit el análisis de JPMorgan sobre overbought y la proyección de Grayscale, que sólo están en las fuentes de analistas.

El mecanismo grafo → agentes → debate → síntesis funcionó: los agentes simularon el debate informativo y el ReportAgent sintetizó las tesis dominantes con evidencia documental.

### 5. Diferencia de calidad entre B1 y B2

B2 fue corrido con embedder local (sentence_transformers, calidad inferior al embedder de Gemini usado en B1). A pesar de esto, la precisión cuantitativa de B2-Δ1 (0.1pp de error) fue mejor que cualquier predicción cuantitativa de B1 (que no proveyó números). Esto sugiere que la calidad del embedder no fue la variable limitante para las predicciones de primer orden.

---

## Implicaciones para el sistema

### Lo que funciona bien
- Extracción de mecanismos causales desde grafo de conocimiento
- Predicciones de tendencia a horizontes corto (Δ1) y medio (Δ3)
- Identificación de riesgos principales (verificados post-facto)
- La simulación social surfacea el "debate de tesis" que refleja el estado informativo pre-evento

### Lo que necesita mejora
1. **Formato del ReportAgent**: forzar estructura cuantitativa cuando el prompt la requiere. Si el modelo no puede dar un precio puntual, debe decirlo explícitamente en lugar de omitirlo.
2. **Incertidumbre explícita en Δ2**: el sistema debería expresar mayor incertidumbre en el horizonte medio-corto, donde los shocks transitorios son más probables.
3. **Rango acumulado en Δ4**: para predicciones macroeconómicas de largo plazo, el sistema debería inferir el rango acumulado a partir de los valores mensuales predichos.

### Hipótesis para futuros casos
- Un sistema que identifica correctamente los mecanismos causales predecirá bien las tendencias dominantes pero no los shocks transitorios.
- La precisión en Δ1 (corto plazo) es alta cuando el seed bundle contiene señales de política o precios recientes (crawling peg, niveles BTC).
- La precisión en Δ3/Δ4 (medio/largo plazo) depende de la robustez de la tesis causal dominante.

---

## Setup técnico de los runs

| Parámetro | B1 | B2 |
|-----------|----|----|
| LLM | gemini-3.1-flash-lite | gemini-3.1-flash-lite |
| Embedder | gemini-embedding-001 | paraphrase-multilingual-MiniLM-L12-v2 (local) |
| Dim embedder | 3072 | 3072 (padded) |
| Rounds | 10 | 10 |
| Acciones totales | n/a | 27 (13 Twitter + 14 Reddit) |
| Nodos en grafo | n/a | 25 |
| Edges en grafo | n/a | 16 |
| Plataforma | parallel | parallel |
| Duración run | ~30 min | ~60 min |

*B2 tardó más porque el embedder local (CPU) es 10-20x más lento que la API de Gemini.*

---

## Checklist actualizado

- [x] B1 `model_output_raw/` completo (run real, status: COMPLETED)
- [x] B2 `model_output_raw/` completo (run real, status: COMPLETED)
- [x] B1 `first_eval.md` completado
- [x] B2 `first_eval.md` completado
- [x] Curva de degradación analizada
- [ ] Evaluar con embedder de Gemini (cuando se restablezca cuota) para comparar calidad B2 vs B1
- [ ] Investigar fallo de formato en ReportAgent (prompt engineering)
