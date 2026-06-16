# Gemma Line 5 Test Plan

Objetivo: usar el caso cuantitativo de Issue #11 / Linea 5 como segundo caso de pruebas Gemma en esta rama, separado del caso Bolivia.

## Origen del paquete

- Issue: `#11`
- PR fuente: `#22`
- Rama fuente: `feat/case-b-backtesting`
- Caso importado: `cases/CASE-B2-ARG-IPC-2025`

## Pregunta

La pregunta congelada esta en:

```text
cases/CASE-B2-ARG-IPC-2025/prompt_frozen/prompt.md
```

Resumen: con documentos fechados hasta el `2025-01-31`, predecir la variacion mensual del IPC argentino para febrero, abril, julio y diciembre de 2025, explicar mecanismo causal, riesgos y evidencia por `source_id`.

## Evidencia importada

Input permitido para MiroFish:

```text
cases/CASE-B2-ARG-IPC-2025/input_pack_pre_x/seed_bundle.md
cases/CASE-B2-ARG-IPC-2025/prompt_frozen/prompt.md
cases/CASE-B2-ARG-IPC-2025/prompt_frozen/system_constraints.md
```

Archivos de auditoria:

```text
cases/CASE-B2-ARG-IPC-2025/case_card.md
cases/CASE-B2-ARG-IPC-2025/input_pack_pre_x/manifest.csv
cases/CASE-B2-ARG-IPC-2025/input_pack_pre_x/hashes.json
cases/CASE-B2-ARG-IPC-2025/input_pack_pre_x/README.md
```

Ground truth separado, no subir como input:

```text
cases/CASE-B2-ARG-IPC-2025/answer_key_post_x/ground_truth.md
cases/CASE-B2-ARG-IPC-2025/answer_key_post_x/first_eval.md
```

## Condiciones Gemma propuestas

Usar Gemma como modelo fijo para comparar profundidad/densidad sin mezclar con el modelo primario Llama del PR #22:

| Variant | Rounds | Density | Objetivo |
| --- | ---: | ---: | --- |
| `gemma_R10_D2` | 10 | 2 | baja profundidad |
| `gemma_R40_D2` | 40 | 2 | baseline comparable |
| `gemma_R80_D2` | 80 | 2 | saturacion/profundidad alta |
| `gemma_R40_D1` | 40 | 1 | menor densidad de interaccion |
| `gemma_R40_D3` | 40 | 3 | mayor densidad de interaccion |

Modelo recomendado para esta expansion:

```text
google/gemma-3-27b-it
```

## Reglas

- Mantener `seed_bundle.md` y prompt constantes entre condiciones.
- Cambiar solo rounds/density y metadatos de run.
- Guardar `worldbuilding_trace.json` por simulacion.
- Guardar output crudo, config, costo/latencia si existe, y evaluacion objetiva.
- No incluir `answer_key_post_x` ni outputs previos como input.

## Resultado esperado

Crear una tabla final Gemma con:

- predicciones por horizonte;
- MAE o hit por metrica del `ground_truth.md`;
- parse errors;
- costo/latencia;
- ruta al `worldbuilding_trace.json`;
- notas de estabilidad narrativa.
