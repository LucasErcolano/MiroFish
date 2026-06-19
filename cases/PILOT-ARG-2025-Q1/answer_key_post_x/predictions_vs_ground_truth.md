# Predictions vs Ground Truth — PILOT-ARG-2025-Q1

Date: 2026-05-26
Run evaluado: `model_output_raw/mirofish_report_raw.md` Run 1
Modelo: gemini-2.5-flash-lite (reemplazo de gemini-2.0-flash-lite, no disponible)
Runner: adapted current-repo runner, sin OASIS/Zep/Graphiti completo.

---

## 1. Electoral

| | Modelo (Run 1) | Ground truth |
|---|---|---|
| Rango voto LLA | 38–45% | ~40.7% (DINE oficial) / 40.84% (media) |
| Escenario A: LLA <35% | 15% prob | No ocurrió |
| Escenario B: LLA 35–42% | 50% prob | **Resultado real cae aquí** |
| Escenario C: LLA >42% | 35% prob | No ocurrió |
| Impacto legislativo | Sin mayoría propia, necesita acuerdos, oposición fragmentada | Correcto — LLA ganó bancas acercándose al tercio para sostener vetos; no obtuvo mayoría propia |

**Veredicto: Acierto.** El ~40.7% real cae dentro del rango 38–45% de Run 1 y dentro del Escenario B (escenario modal del modelo con 50%). El fortalecimiento legislativo fue correctamente anticipado sin sobrestimar mayoría propia.

---

## 2. Macroeconómica (inflación)

| | Modelo (Run 1) | Ground truth |
|---|---|---|
| Rango inflación acumulada | 30–40% | **31.5%** (INDEC, acumulada 2025; IPC dic 2025: 2.8%) |
| Escenario A: <30% | 20% prob | No ocurrió |
| Escenario B: 30–40% | 60% prob | **Resultado real cae aquí** (extremo bajo) |
| Escenario C: >40% | 20% prob | No ocurrió |

**Veredicto: Acierto.** 31.5% está dentro del rango predicho, en el extremo bajo del Escenario B. El escenario modal del modelo (60%) fue correcto. El 20% asignado a Escenario A fue el error de dirección más cercano — el resultado quedó justo por encima del umbral de 30%.

---

## 3. Dimensiones cualitativas (rúbrica 1-5, per first_eval.md)

| Dimensión | Score | Hallazgo clave |
|---|---:|---|
| Especificidad | 4/5 | Run 1 dio rangos y probabilidades explícitos; Runs 2–3 más vagos en voto |
| Plausibilidad | 4/5 | Rango 38–45% incluye resultado real; 30–40% alinea con 31.5%; -1 por variación entre runs |
| Cobertura | 5/5 | Integró inflación, salarios, empleo, reservas, crawling peg, FMI, oposición, gobernabilidad |
| Consistencia causal | 4/5 | Cadena plausible (desinflación → salarios reales → percepción → voto); -1 por probabilidades inferidas |
| Ausencia de post-corte | 5/5 | No se detectaron datos específicos post-corte; elecciones formuladas como predicción |
| Utilidad | 5/5 | Produjo escenarios, riesgos y señales tempranas monitoreables |

**Total: 27/30**

---

## Conclusión

El modelo acertó ambas predicciones clave:

- **Electoral:** LLA ~40–41%, dentro de 38–45%, Escenario B.
- **Macro:** Inflación 31.5%, dentro de 30–40%, Escenario B.

La limitación principal es que Runs 2 y 3 evitaron comprometerse con un rango numérico de voto explícito — solo Run 1 fue suficientemente específico para registrar el acierto directo. La evaluación otorga crédito por corrección basada en rango, no en precisión decimal, y no encontró evidencia de fuga temporal.

Esta corrida corresponde al runner adaptado (sin agentes sociales OASIS completos); los resultados del backtesting real con OASIS están en `real_mirofish_round_1/`.
