# Ground truth posterior a x — CASE-B2

## IPC mensual real (fuente: INDEC oficial)

| Δ | Mes | IPC mensual % |
|---|-----|--------------|
| Δ1 | Feb 2025 | 2.4% |
| Δ2 | Abr 2025 | 3.7% |
| Δ3 | Jul 2025 | ~3.0% (confirmar con INDEC al ejecutar) |
| Δ4 | Dic 2025 | 2.8% |

Inflación acumulada 2025: 31.5% (INDEC, publicado enero 2026).

## Contexto

La desinflación fue real pero no lineal. Febrero fue baja (2.4%), hubo repuntes en Q2 (3.7% en abril), y cerró el año en 2.8% mensual. La acumulada quedó en el rango medio-bajo del escenario B (30–40%) del piloto Case C.

## Métricas de evaluación (definidas antes de ver el output)

| Δ | Métrica | Umbral PASS |
|---|---------|-------------|
| Δ1 | Error absoluto sobre valor puntual | ≤1.5pp (ej: predice 2.4±1.5) |
| Δ2 | ¿Real cae en rango predicho? | Rango ≤ 4pp de ancho |
| Δ3 | Bucket correcto (2–4% = moderada) | Correcto/incorrecto |
| Δ4 | Acumulada 2025 en rango correcto (30–40%) | Rango hit |
