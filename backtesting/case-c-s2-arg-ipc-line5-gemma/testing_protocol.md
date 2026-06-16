# Testing Protocol - Gemma Line 5

Este archivo documenta como correr el caso IPC en MiroFish para probar profundidad de simulacion / cantidad de rondas.

## Regla general

Mantener fijo:

- evidencia: `input/seed_bundle.md`
- pregunta: `question.md`
- restricciones: `system_constraints.md`
- modelo evaluado: `google/gemma-3-27b-it`
- cutoff de informacion: `2025-01-31`

Cambiar solo:

- cantidad de rondas
- densidad/interacciones si el flujo de simulacion lo permite
- metadatos de variante

## Inputs a subir

Subir:

- `input/seed_bundle.md`
- `question.md`
- `system_constraints.md`

No subir:

- `ground_truth_private.md`
- `rubric.md`
- `manifest.csv`
- `config_matrix_source.yaml`
- cualquier archivo dentro de `output/`

## Variantes propuestas

| Variant | Rounds | Density | Objetivo |
| --- | ---: | ---: | --- |
| `gemma_R10_D2` | 10 | 2 | baja profundidad |
| `gemma_R40_D2` | 40 | 2 | baseline comparable |
| `gemma_R80_D2` | 80 | 2 | profundidad alta |
| `gemma_R40_D1` | 40 | 1 | menor densidad de interaccion |
| `gemma_R40_D3` | 40 | 3 | mayor densidad de interaccion |

Si MiroFish todavia no expone `density`, registrar la variante igual y marcar `density_applied=false` en las notas de corrida.

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
  --report backtesting/case-c-s2-arg-ipc-line5-gemma/output/gemma_R40_D2/report.md \
  --variant gemma_R40_D2 \
  --model-policy gemma_line5 \
  > backtesting/case-c-s2-arg-ipc-line5-gemma/output/gemma_R40_D2/eval_result.json
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
