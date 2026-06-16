# Rubric - Argentina IPC 2025

La evaluacion se hace despues de generar el reporte, usando `ground_truth_private.md`.

## Metrica primaria

| Delta | Objetivo | PASS |
| --- | --- | --- |
| Delta 1 | Febrero 2025, valor puntual IPC mensual | Error absoluto <= 1.5pp |
| Delta 2 | Abril 2025, rango IPC mensual | Valor real cae dentro del rango y el rango mide <= 4pp |
| Delta 3 | Julio 2025, bucket | Bucket correcto: moderada, 2-4% |
| Delta 4 | Acumulada 2025 | Rango correcto: 30-40% |

## Ground truth resumido

- Febrero 2025: 2.4%
- Abril 2025: 3.7%
- Julio 2025: alrededor de 3.0%, bucket moderada
- Diciembre 2025: 2.8%
- Acumulada 2025: 31.5%

## Metrica secundaria

- Consistencia causal: identifica si la variable dominante fue macro/monetaria/fiscal/social.
- Uso de evidencia: cita `source_id` para claims importantes.
- No leakage: no menciona datos posteriores al `2025-01-31` como si fueran input.
- Estabilidad narrativa: el mecanismo causal no contradice los numeros predichos.

## Resultado esperado de cada evaluacion

Cada variante Gemma debe producir un archivo:

```text
output/<variant>/eval_result.json
```

Campos minimos recomendados:

```json
{
  "case_id": "case-c-s2-arg-ipc-line5-gemma",
  "variant": "gemma_R40_D2",
  "model_policy": "gemma_line5",
  "delta_1": {"prediction": null, "pass": null},
  "delta_2": {"range": null, "pass": null},
  "delta_3": {"bucket": null, "pass": null},
  "delta_4": {"accumulated_range": null, "pass": null},
  "leakage_detected": null,
  "notes": ""
}
```
