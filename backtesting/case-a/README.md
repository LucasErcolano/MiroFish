# Backtesting Case A - Copa America 2024 Final

Issue: #10 - S1 Backtesting case A: simple self-verifiable event

## Objetivo

Evaluar si MiroFish puede predecir un evento deportivo con resultado objetivo usando solo informacion disponible antes del evento.

## Caso

- Dominio: futbol / torneo internacional.
- Evento: final de la Copa America 2024 entre Argentina y Colombia.
- Pregunta: predecir quien ganara la final.
- Fecha de corte documental `x`: 2024-07-13 23:59 UTC.
- Fecha del evento: 2024-07-14 en Miami Gardens, Florida.
- Delta temporal: aproximadamente 1 dia.
- Resultado real: guardado fuera del input en `ground-truth.md`.

## Regla temporal

Los archivos dentro de `input/` solo pueden contener informacion publicada antes o durante la fecha de corte. No deben incluir el resultado final ni informacion publicada despues del partido.

## Fuentes permitidas como input

1. `input/source-01-opta-preview.txt`
   - Fuente: Opta Analyst.
   - Publicacion: 2024-07-13.
   - Uso: probabilidades, forma de equipos, jugadores clave, historial.

2. `input/source-02-conmebol-preview.txt`
   - Fuente: CONMEBOL Copa America.
   - Publicacion: antes de la final.
   - Uso: datos de sede, contexto oficial, rachas y detalles previos.

## Prompt para MiroFish

Usar el texto de `prompt.md` como requerimiento de simulacion/prediccion.

## Configuracion recomendada

- Usar un proyecto nuevo de MiroFish.
- Usar baseline: `USE_EXPERIMENTAL_MEMORY=false` o variable no definida.
- No mezclar con la PR #13 de memoria experimental.
- Registrar modelo, fecha de corrida y output en `run-notes.md`.

## Criterio de evaluacion

La metrica primaria es objetiva:

- `correcto`: MiroFish predice como ganador a Argentina.
- `incorrecto`: MiroFish predice como ganador a Colombia, empate sin ganador, o no responde de forma evaluable.

La justificacion cualitativa se guarda aparte en `evaluation.md`.
