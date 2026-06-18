# Prompt

Con la informacion disponible hasta el 13 de julio de 2024, predecir quien ganara la final de la Copa America 2024 entre Argentina y Colombia.

Responder exclusivamente en espanol.

La respuesta debe:

- elegir un unico ganador esperado;
- justificar la prediccion usando solo evidencia del contexto entregado;
- mencionar los principales factores de incertidumbre;
- no usar informacion posterior al 13 de julio de 2024.

Formato esperado:

Ganador predicho: Argentina o Colombia

Justificacion:
- evidencia 1
- evidencia 2
- evidencia 3

Incertidumbre:
- factor 1
- factor 2

Tambien devolver una salida estructurada JSON con:

- `predicted_winner`: Argentina o Colombia.
- `confidence`: numero entre 0 y 1.
- `winner_probability_point`: probabilidad puntual del ganador elegido.
- `winner_probability_range`: rango estrecho para el ganador elegido, con `winner_min` y `winner_max`.
- `predicted_goal_margin`: diferencia esperada de goles para el ganador, con valor puntual y rango.
- `probability_calibration`: explicacion breve de como se eligieron la confianza y los rangos.
- `probability_drivers`: factores que suben o bajan la probabilidad de cada equipo, con `source_id`.
- `justification`: claims con `source_id`.
- `uncertainty`: factores con `source_id`.
- `evidence`: claims principales con `source_id`.

Reglas de calibracion:

- No usar un rango generico fijo para todas las corridas.
- El rango de probabilidad del ganador debe ser estrecho: `winner_max - winner_min <= 0.05`.
- `winner_probability_point` debe caer dentro de ese rango.
- Si no hay odds/modelos probabilisticos directos, expresar la incertidumbre bajando la confianza y explicandola, no usando un rango enorme.
- Si aparecen odds, modelos o mercados, anclar el punto medio a esa evidencia.
- La confianza debe cambiar cuando cambia la evidencia temporal.
- Evitar valores redondos repetidos salvo que esten justificados por las fuentes.
- La diferencia de goles debe ser una prediccion pre-partido, no el resultado real.
