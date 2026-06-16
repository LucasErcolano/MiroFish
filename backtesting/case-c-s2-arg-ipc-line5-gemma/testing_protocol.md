# Testing Protocol - IPC Temporal Packages

Este archivo documenta como correr el caso IPC en MiroFish para probar como cambia la prediccion cuando se agrega informacion nueva.

## Regla general

Mantener fijo:

- pregunta: `question.md`
- restricciones: `system_constraints.md`
- modelo evaluado: `google/gemma-3-27b-it`
- rondas: `40`
- density: `2`, si el flujo lo permite

Cambiar solo:

- paquete temporal: `seed_T0.md`, `seed_T1.md`, `seed_T2.md`, `seed_T3.md`
- metadatos de run

## Inputs a subir

Subir:

- uno de los paquetes `seed_T0.md` a `seed_T3.md`
- `question.md`
- `system_constraints.md`

No subir:

- `ground_truth_private.md`
- `rubric.md`
- `manifest.csv`
- `config_matrix.yaml`
- `config_matrix_source.yaml`
- cualquier archivo dentro de `output/`

## Paquetes temporales

| Variant | Input | Max date | Objetivo |
| --- | --- | --- | --- |
| `gemma_T0_R40_D2` | `seed_T0.md` | `2024-12-31` | prediccion con contexto social/macro inicial |
| `gemma_T1_R40_D2` | `seed_T1.md` | `2025-01-10` | agrega expectativas REM e IMF constraints |
| `gemma_T2_R40_D2` | `seed_T2.md` | `2025-01-14` | agrega IPC oficial diciembre y framing politico |
| `gemma_T3_R40_D2` | `seed_T3.md` | `2025-01-31` | paquete completo pre-cutoff |

Los `assembled_T0.md` a `assembled_T3.md` son copias equivalentes para mantener el mismo naming que Bolivia.

## Artefactos por corrida

Guardar cada corrida en:

```text
output/<variant>/
```

Archivos recomendados:

- `run_notes.md`: fecha, modelo, config, si density fue aplicada, costo/latencia si existe.
- `report.md`: reporte final de MiroFish.
- `worldbuilding_trace.json`: snapshot de planificacion/perfiles/config.
- `eval_result.json`: evaluacion con la rubrica.

Comando de evaluacion:

```bash
python3 backtesting/case-c-s2-arg-ipc-line5-gemma/eval_objective.py \
  --report backtesting/case-c-s2-arg-ipc-line5-gemma/output/gemma_T3_R40_D2/report.md \
  --variant gemma_T3_R40_D2 \
  --model-policy gemma_temporal_probe \
  > backtesting/case-c-s2-arg-ipc-line5-gemma/output/gemma_T3_R40_D2/eval_result.json
```

## Comparacion final

La tabla final debe comparar:

- predicciones por horizonte;
- PASS/FAIL por delta;
- error de Delta 1;
- si Delta 2 cae en rango;
- bucket Delta 3;
- rango acumulado Delta 4;
- leakage;
- parse errors o fallas operativas;
- costo/latencia;
- ruta al `worldbuilding_trace.json`.

## Sweep de profundidad opcional

Despues de completar `T0-T3`, se puede volver sobre `T3` y correr variantes de rondas/density:

- `gemma_T3_R10_D2`
- `gemma_T3_R80_D2`
- `gemma_T3_R40_D1`
- `gemma_T3_R40_D3`

Ese sweep es secundario. La primera comparacion de esta issue es temporal.
