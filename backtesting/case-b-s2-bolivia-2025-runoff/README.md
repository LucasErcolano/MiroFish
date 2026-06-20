# Backtesting Case B S2 - Bolivia 2025 Presidential Runoff

Issue: #17 - S2 Investigador 1: actualizacion temporal con evidencia post-cutoff

## Objetivo

Evaluar si MiroFish actualiza una prediccion politico-social cuando recibe evidencia nueva que cambia fuertemente la expectativa inicial.

## Pregunta

Con la evidencia disponible hasta cada paquete temporal, identificar los candidatos competitivos del balotaje presidencial de Bolivia del 19 de octubre de 2025, predecir quien ganara y estimar porcentajes de voto.

## Por que este caso

Este caso reemplaza a las legislativas argentinas 2025 porque tiene un giro mas claro:

- antes de la primera vuelta, Rodrigo Paz no era el favorito fuerte;
- en la primera vuelta, Paz sorprende y queda competitivo;
- cerca del balotaje, algunas encuestas muestran ventaja de Quiroga;
- el resultado final contradice esa expectativa: Paz gana con alrededor de 54%;
- el caso ocurre meses despues del cutoff de Qwen3 8B.

## Modelo primario

Modelo primario fijo para S2:

```bash
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL_NAME=qwen/qwen3-8b
GRAPHITI_LLM_CLIENT_MODE=generic
GRAPHITI_LLM_BASE_URL=https://openrouter.ai/api/v1
GRAPHITI_LLM_MODEL=openai/gpt-4o-mini
GRAPHITI_LLM_SMALL_MODEL=openai/gpt-4o-mini
GRAPHITI_MAX_COROUTINES=1
LLM_REQUEST_MIN_INTERVAL_SECONDS=7
LLM_REQUEST_MAX_RETRIES=3
LLM_REQUEST_RETRY_BACKOFF_SECONDS=12
```

Qwen3 8B tiene cutoff reportado el 31 de marzo de 2025. La eleccion y todos los documentos del caso son posteriores a esa fecha y anteriores al resultado del balotaje, salvo el ground truth privado.

Nota operativa: Graphiti usa `openai/gpt-4o-mini` para extraccion estructurada del grafo porque Qwen3 8B no siempre devuelve JSON valido para Graphiti. El modelo evaluado para la prediccion sigue siendo `qwen/qwen3-8b`.

Estado actual de este PR: los outputs versionados son `*_gemma_probe`. No deben mezclarse con la politica primaria `qwen/qwen3-8b`; quedan como prueba de protocolo temporal y corrida end-to-end. Para cierre estricto de la issue falta ejecutar y guardar la pasada primaria Qwen, y replicas si se exige la regla S2 de robustez.

## Paquetes temporales

- `T0`: contexto de crisis economica, desgaste del MAS y favoritos previos a la primera vuelta.
- `T1`: sorpresa de primera vuelta; Paz entra al balotaje.
- `T2`: campania de balotaje, clivaje moderacion vs ajuste, voto anti-MAS.
- `T3`: encuesta cercana que da ventaja a Quiroga mas senales finales contradictorias.

Artefactos de input:

- `seed_T0.md`, `seed_T1.md`, `seed_T2.md`, `seed_T3.md`: nombres estrictos pedidos por la issue.
- `assembled_T0.md`, `assembled_T1.md`, `assembled_T2.md`, `assembled_T3.md`: alias equivalentes generados con el mismo contenido.

## Armar inputs

```bash
python backtesting/scripts/assemble_temporal_package.py \
  --manifest backtesting/case-b-s2-bolivia-2025-runoff/manifest.csv \
  --package T0 \
  --out backtesting/case-b-s2-bolivia-2025-runoff/seed_T0.md \
  --cutoff 2025-08-16
```

Para T1/T2/T3 cambiar `--package` y `--cutoff` segun la fecha maxima del paquete.

El significado de cada paquete temporal y la recomendacion de correrlos de forma acumulativa esta documentado en `testing_protocol.md`.

## Regla de inputs

Los archivos de `input/` no deben ser solo un link suelto, pero tampoco conviene pegar articulos completos con copyright. Cada input debe ser una nota de fuente autocontenida:

- URL, fuente, fecha y tipo de fuente;
- cuerpo factual neutral, parecido a una nota o dossier de fuente;
- numeros, encuestas o citas breves cuando sean necesarias;
- ninguna informacion posterior al cutoff del paquete;
- ninguna etiqueta experimental como `T0`, `T1`, `signal` o `noise`;
- ninguna seccion de `hechos extraidos` o recomendacion interpretativa.

Si una fuente es oficial, publica o propia, se puede incluir mas texto. Para notas periodisticas comerciales, usar resumen factual y extractos cortos.

La asignacion a `T0/T1/T2/T3`, el rol `signal/noise` y el control de fechas viven solo en `manifest.csv`.

Las hipotesis de lectura y expectativas del experimento van en `internal_notes.md`, que no debe subirse como input a MiroFish.

## Evaluacion

Metrica primaria:

- `correcto`: predice a Rodrigo Paz como ganador del balotaje.
- `incorrecto`: predice a Jorge "Tuto" Quiroga, empate/no evaluable u otro ganador.

Metricas secundarias:

- error absoluto medio de porcentajes para Paz, Quiroga y otros/blanco/nulo;
- error absoluto del margen Paz - Quiroga;
- rubrica cualitativa de causalidad, uso de evidencia, actualizacion temporal y ausencia de leakage.
