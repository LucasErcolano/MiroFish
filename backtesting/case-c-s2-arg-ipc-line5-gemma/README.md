# Backtesting Case C S2 - Argentina IPC 2025 Gemma Line 5

Issue fuente: #11 - S2 Investigador 2: caso cuantitativo.

Linea relacionada: Linea 5 - profundidad de simulacion / cantidad de rondas.

## Objetivo

Armar el caso IPC en formato `backtesting/`, como el caso Bolivia, para correr pruebas Gemma con paquetes temporales acumulativos.

La pregunta no es quien gana una eleccion, sino si MiroFish puede predecir la trayectoria del IPC argentino 2025 y como cambia esa prediccion cuando entra nueva informacion entre `T0` y `T3`.

## Pregunta

Con documentos fechados hasta el `2025-01-31`, predecir:

- `Delta 1`: IPC mensual febrero 2025, valor puntual y rango.
- `Delta 2`: IPC mensual abril 2025, rango y tendencia.
- `Delta 3`: IPC mensual julio 2025, bucket de inflacion.
- `Delta 4`: IPC mensual diciembre 2025 y rango de inflacion acumulada 2025.
- mecanismo causal, variable dominante y riesgo principal.

La pregunta completa esta en `question.md`.

## Que documentos tenemos

El paquete trae 13 documentos utilizables antes del cutoff, condensados en `input/seed_bundle.md`.

Tipos de documentos:

- macro/inflacion: BBVA outlook, INDEC IPC diciembre 2024, BCRA REM diciembre 2024, World Bank GEP enero 2025.
- monetarios/BCRA: crawling peg 1% mensual y reporte monetario diciembre 2024.
- fiscales: comunicado MECON sobre superavit fiscal 2024.
- institucionales/politicos: FMI ex-post evaluation, Americas Quarterly, veto jubilatorio en Diputados, Chequeado.
- sociales/opinion publica: encuesta CB Consultora y reporte UCA/ODSA sobre pobreza/subsistencia.

Tambien hay documentos excluidos en `manifest.csv`; no se usan porque son post-cutoff, fallback o no pertenecen al input principal.

## Paquetes temporales

- `T0`: base social, institucional y macro 2024. Max document date: `2024-12-31`.
- `T1`: agrega REM diciembre 2024 e IMF Ex-post Evaluation. Max document date: `2025-01-10`.
- `T2`: agrega IPC oficial diciembre 2024 y framing politico 2025. Max document date: `2025-01-14`.
- `T3`: agrega crawling peg 1%, cierre fiscal 2024, monetary report y World Bank. Max document date: `2025-01-31`.

El paquete es acumulativo: `T1` incluye `T0`, `T2` incluye `T1`, y `T3` incluye todo el input valido pre-cutoff.

## Estructura

- `input/seed_bundle.md`: evidencia sintetizada que se puede subir a MiroFish.
- `seed_T0.md` a `seed_T3.md`: inputs acumulativos principales.
- `assembled_T0.md` a `assembled_T3.md`: alias equivalentes para mantener la convencion de Bolivia.
- `question.md`: pregunta congelada.
- `system_constraints.md`: restricciones del prompt original.
- `manifest.csv`: auditoria de fuentes, roles y exclusiones.
- `config_matrix.yaml`: matriz operacional temporal `T0-T3`.
- `config_matrix_source.yaml`: matriz original importada del issue fuente, preservada como referencia.
- `input/hashes.json`: hashes del paquete fuente.
- `ground_truth_private.md`: respuesta posterior al cutoff; no subir como input.
- `rubric.md`: metrica de evaluacion.
- `testing_protocol.md`: como correr las variantes Gemma.
- `eval_objective.py`: evaluador JSON basico para reportes generados.
- `output/`: destino para reportes y evaluaciones de cada corrida.

## Regla de inputs

Subir a MiroFish:

- uno de `seed_T0.md`, `seed_T1.md`, `seed_T2.md`, `seed_T3.md`
- `question.md`
- `system_constraints.md` si el flujo permite agregar restricciones de sistema

No subir:

- `ground_truth_private.md`
- `rubric.md`
- `manifest.csv`
- `config_matrix.yaml`
- `config_matrix_source.yaml`
- `testing_protocol.md`
- outputs previos

## Estado

Este directorio todavia no contiene corridas nuevas. El siguiente paso es ejecutar Gemma para `T0`, `T1`, `T2` y `T3`, y guardar cada resultado en `output/<variant>/`.
