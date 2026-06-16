# Case Card - Argentina IPC 2025 Gemma Line 5

## Identificacion

- Case id local: `case-c-s2-arg-ipc-line5-gemma`
- Caso fuente: `CASE-B2-ARG-IPC-2025`
- Issue fuente: `#11`
- Linea experimental: inclusion temporal de informacion, con Gemma como probe
- Dominio: macroeconomia cuantitativa, inflacion mensual Argentina
- Fecha de corte: `2025-01-31`

## Horizontes de prediccion

- `Delta 1`: febrero 2025
- `Delta 2`: abril 2025
- `Delta 3`: julio 2025
- `Delta 4`: diciembre 2025 y acumulada 2025

## Pregunta central

Usando exclusivamente documentos fechados hasta el `2025-01-31`, predecir la variacion mensual del IPC argentino para cada horizonte y explicar la trayectoria de desinflacion con evidencia por `source_id`.

## Paquetes temporales

- `T0`: evidencia social, institucional y macro disponible hasta fines de 2024.
- `T1`: agrega expectativas REM diciembre 2024 e IMF constraints publicados hasta `2025-01-10`.
- `T2`: agrega IPC oficial diciembre 2024 y framing politico publicados hasta `2025-01-14`.
- `T3`: agrega crawling peg, cierre fiscal, monetary report y World Bank hasta `2025-01-31`.

La corrida recomendada es acumulativa para observar si MiroFish corrige o estabiliza sus predicciones a medida que entra informacion nueva.

## Complexity Gate

- Documentos utilizables: 13
- Fechas documentales distintas: mas de 3, entre finales de 2024 y enero de 2025
- Fuentes: BCRA, INDEC, FMI, BBVA, World Bank, MECON, medios/consultoras y fuentes sociales
- Hipotesis causales competidoras:
  - desinflacion por ancla cambiaria, disciplina fiscal y expectativas
  - repunte por inercia, precios regulados, atraso cambiario o tension social/politica
- Entidades extraibles: mas de 20
- Ground truth: aislado en `ground_truth_private.md`
- Metrica: errores/rangos por horizonte, definida en `rubric.md`

## Politica de modelos

El PR fuente usaba otro modelo primario. En esta rama, el objetivo es una prueba temporal con Gemma:

```text
google/gemma-3-27b-it
```

Las corridas Gemma no deben mezclarse con la politica primaria del PR fuente. Deben etiquetarse como `gemma_temporal_probe`.

## Leakage

El modelo no debe recibir informacion posterior al `2025-01-31`.

Archivos privados:

- `ground_truth_private.md`
- `rubric.md`
- `output/`
- outputs/evaluaciones previas del caso fuente

## Nota de nomenclatura

El paquete fuente tiene nombres heredados como `CASE-B2` y `PILOT-ARG-2025-Q1`. Para esta rama se usa el nombre operacional `case-c-s2-arg-ipc-line5-gemma`, porque el objetivo local es correr IPC como caso de backtesting para Linea 5.
