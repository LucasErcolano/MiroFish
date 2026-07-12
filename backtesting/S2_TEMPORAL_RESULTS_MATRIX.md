# S2 Temporal Results Matrix

Resumen comparativo de corridas temporales T0-T3 para Bolivia, IPC Argentina y Copa America. Los resultados salen de los `eval_result.json` guardados localmente.

## Bolivia 2025 Runoff

| T | Prediccion | Correcto | Votos predichos | MAE voto | Margen predicho | Error margen | Parse errors |
|---|---|---:|---|---:|---:|---:|---:|
| T0 | null | no | otros=20% | null | 4.0 | 5.06 | 2 |
| T1 | paz_gana | si | paz=52%, quiroga=45%, otros=3% | 2.0 | 9.0 | 0.06 | 0 |
| T2 | quiroga_gana | no | paz=44%, quiroga=53%, otros=3% | 7.02 | -9.0 | 18.06 | 0 |
| T3 | quiroga_gana | no | paz=43%, quiroga=52%, otros=5% | 7.687 | -9.0 | 18.06 | 0 |

## IPC Argentina 2025

| T | Score | Feb pred/err | Abr rango | Jul rango | Dic pred/err | Acum. rango | MAE mensual | MAE mensual + acum | Parse errors |
|---|---:|---|---|---|---|---|---:|---:|---:|
| T0 | 1/5 | 1.8 / 0.6 | [1.0, 2.2] | [0.8, 1.5] | 1.2 / 1.6 | [10.0, 25.0] | 1.538 | 4.03 | 0 |
| T1 | 1/5 | 1.8 / 0.6 | [1.5, 2.5] | [1.2, 2.0] | 1.5 / 1.3 | [20.0, 30.0] | 1.25 | 2.3 | 0 |
| T2 | 1/5 | 2.5 / 0.1 | [1.5, 2.5] | [1.0, 2.2] | 1.2 / 1.6 | [20.0, 30.0] | 1.2 | 2.26 | 0 |
| T3 | 3/5 | 2.5 / 0.1 | [1.5, 2.8] | [1.2, 2.5] | 2.0 / 0.8 | [20.0, 35.0] | 0.9 | 1.52 | 0 |

## Copa America 2024 Final

| T | Prediccion | Correcto | Confianza | Prob. punto | Rango ganador | Ancho valido | Margen goles | Score | Parse errors |
|---|---|---:|---:|---:|---|---:|---|---:|---:|
| T0 | Argentina | si | 0.75 | 0.625 | 0.575-0.675 (w=0.1) | no | 1.0 [0.5, 1.5] | 4/5 | 0 |
| T1 | Argentina | si | 0.75 | 0.65 | 0.6-0.7 (w=0.1) | no | 1.0 [0.5, 1.5] | 5/5 | 0 |
| T2 | Argentina | si | 0.78 | 0.49 | 0.46-0.51 (w=0.05) | si | 1.0 [0.0, 2.0] | 5/5 | 0 |
| T3 | Argentina | si | 0.72 | 0.49 | 0.46-0.51 (w=0.05) | si | 1.0 [1.0, 2.0] | 5/5 | 0 |

## Notas

- Bolivia usa la salida objetiva del evaluador electoral (`winner_score`, MAE de voto y error de margen).
- IPC usa el punto mensual cuando existe y el punto medio del rango cuando la salida es rango; la columna `MAE mensual + acum` agrega el error del punto medio de inflacion acumulada 2025.
- Copa America usa ganador, probabilidad puntual del ganador, rango estrecho del ganador y margen de goles esperado. En T0/T1 el rango sigue excediendo el maximo de 5 puntos; T2/T3 cumplen.
- Todos los casos reportan `parse_errors` para separar calidad de parsing de calidad predictiva.
