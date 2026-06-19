# First Eval — CASE-B2 (Argentina IPC 2025)

Run date: 2026-05-27  
Model: gemini-3.1-flash-lite (LLM) + paraphrase-multilingual-MiniLM-L12-v2 (embedder, local fallback)  
Simulation: 10 rounds, 27 actions (13 Twitter + 14 Reddit), plataforma parallel  
Input: seed_bundle.md 6430 bytes, cutoff 2025-01-31  

---

## Tabla predicción vs. real

| Δ | Horizonte | Predicción MiroFish | Ground truth (INDEC) | Métrica | Resultado |
|---|-----------|--------------------|-----------------------|---------|-----------|
| Δ1 | Feb 2025 | 2.5% (rango 2.2%–2.8%) | **2.4%** | Error abs = 0.1pp (umbral ≤1.5pp); real en rango | **PASS** |
| Δ2 | Abr 2025 | 1.8%–2.3%, "estable desacelerando" | **3.7%** | 3.7% fuera del rango 1.8%–2.3% | **FAIL** |
| Δ3 | Jul 2025 | bucket "moderada 2%–4%" | **~3.0%** | Bucket correcto (2%–4%) | **PASS** |
| Δ4 | Dic 2025 | "significativamente reducida", sentimiento "consolidado" — sin rango acumulado explícito | Acumulada: **31.5%**, mensual Dic: **2.8%** | No provee rango → no evaluable formalmente | **FAIL*** |

*Δ4 parcialmente correcto: el sentimiento "inicial consolidado" es consistente con el programa que sobrevivió el año. El fallo es de formato: el modelo no generó un rango de acumulada 2025 como pedía el prompt.

**Score: 2/4** (criterios formales pre-registrados)

---

## Análisis narrativo

### Δ1 — Excelente precisión de corto plazo

El modelo capturó con exactitud el nivel de febrero: 2.5% predicho vs 2.4% real (error 0.1pp). El mecanismo causal que citó —la reducción del crawling peg al 1% mensual anunciada por el BCRA el 16/01/2025— es factualmente correcto y fue la variable dominante del ancla nominal en ese período. Esto sugiere que el grafo de conocimiento extrajo correctamente la señal de política monetaria del seed bundle.

### Δ2 — Miss significativo en Q2

El modelo predijo una continuidad de la desinflación (1.8%–2.3%) para abril, pero el dato real fue 3.7% —una aceleración, no una desaceleración. El error es grande (~1.4–1.9pp respecto al centro del rango).

**¿Por qué falló?** El seed bundle (con cutoff 31/01/2025) no contenía señales de los shocks que explicaron el repunte de abril. El modelo asumió trayectoria lineal de desinflación. Las causas probables del repunte en Q2 2025 son ajustes de tarifas de servicios públicos, efectos estacionales o shocks de oferta, ninguno de los cuales era predecible desde los documentos disponibles antes del corte.

Este es un fallo informativo: el modelo confundió "tendencia dominante" con "trayectoria determinística". La desinflación real fue no lineal, con saltos hacia arriba en Q2.

### Δ3 — Recuperación a 6 meses

A pesar del miss en Δ2, el modelo acertó el bucket de julio (3.0% cae en el rango 2%–4% = moderada). Esto es notable: el modelo pasó por alto el repunte de Q2 pero tenía razón sobre el nivel a mitad de año. Sugiere que la tesis de desinflación de mediano plazo era correcta aunque la trayectoria intermedia no lo era.

### Δ4 — Correcto en dirección, incompleto en formato

El modelo dijo "estabilidad inicial consolidada" y "acumulada significativamente más baja", lo cual es consistente con 31.5% (frente al 117.8% de 2024). Sin embargo no generó el rango numérico pedido (p.ej. "25%–40%"). El fallo es de **adherencia al formato del prompt**, no de razonamiento causal. El sistema de ReportAgent no forzó la estructura de la respuesta correctamente.

---

## Mecanismo causal identificado

El modelo identificó tres variables correctas:
1. **Crawling peg al 1%** — ancla nominal principal (citado con source_id correcto)
2. **Superávit fiscal cero** — sostenibilidad del programa
3. **IMF como validador político** — condicionalidad que refuerza la credibilidad

El riesgo principal identificado (apreciación real del tipo de cambio que perjudica exportadores) también es correcto y fue la tensión central de la política económica en 2025.

---

## Observaciones sobre el run

- **Embedder local**: se usó `paraphrase-multilingual-MiniLM-L12-v2` (384 dims, zero-padded a 3072) como fallback porque la cuota diaria de `gemini-embedding-001` estaba agotada (B1 la consumió entera). La calidad semántica del grafo es inferior a B1 —el multilingüe captura bien el español pero con menor resolución conceptual que el embedder de Gemini.
- **Grafo pequeño**: 25 nodos, 16 edges. Para comparar: B1 tuvo un grafo similar. Ambos son pequeños para el tamaño del seed bundle (6-7KB). Graphiti con `GRAPHITI_MAX_COROUTINES=5` construye el grafo secuencialmente y puede no saturar todos los chunks.
- **Report en chino**: el ReportAgent generó el informe en chino (idioma de la interfaz). Las predicciones son correctas pero la presentación requiere traducción para evaluación.
