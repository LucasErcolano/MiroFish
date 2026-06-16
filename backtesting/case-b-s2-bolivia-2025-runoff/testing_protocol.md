# Testing Protocol - Temporal Packages

Este archivo documenta que representa cada paquete temporal del caso y como debe usarse en MiroFish.

## Regla general

La corrida recomendada es **acumulativa**: cada `T` representa todo lo que estaria disponible hasta esa fecha, no solo los documentos nuevos de ese tramo.

No subir como input:

- `ground_truth_private.md`
- `rubric.md`
- `internal_notes.md`
- `manifest.csv`
- `case_card.md`
- este `testing_protocol.md`

Subir siempre:

- documentos del paquete temporal correspondiente;
- `question.md`.

Los paquetes acumulativos versionados estan disponibles con dos nombres:

- `seed_T0.md` a `seed_T3.md`: artefactos con el nombre pedido por la issue.
- `assembled_T0.md` a `assembled_T3.md`: alias equivalentes con el mismo contenido.

## T0 - Antes de la primera vuelta

Fecha maxima: `2025-08-16`

Idea: MiroFish solo ve el contexto previo. Todavia no sabe quien entro al balotaje.

Incluye:

- crisis economica;
- desgaste y fragmentacion del MAS;
- encuestas pre-primera vuelta;
- candidatos visibles antes de votar.

Fuentes:

- `input/source-01-pre-first-round-context.md`
- `input/source-02-first-round-poll-context.md`

Sirve para ver que predice con informacion inicial e incompleta.

## T1 - Despues de la primera vuelta

Fecha maxima: `2025-08-18`

Idea: MiroFish ya sabe que hubo sorpresa: Rodrigo Paz gano la primera vuelta y entra al balotaje contra Jorge "Tuto" Quiroga.

Incluye T0 mas:

- resultado de primera vuelta;
- Paz primero;
- Quiroga segundo;
- MAS afuera del balotaje;
- reordenamiento de votantes.

Fuentes acumuladas:

- `input/source-01-pre-first-round-context.md`
- `input/source-02-first-round-poll-context.md`
- `input/source-03-first-round-surprise.md`
- `input/source-04-mas-collapse-runoff.md`

Sirve para ver si MiroFish actualiza fuerte respecto de T0.

## T2 - Campania de balotaje

Fecha maxima: `2025-10-10`

Idea: MiroFish ve informacion sobre las plataformas y perfiles de los dos candidatos.

Incluye T1 mas:

- Paz como perfil mas moderado;
- Quiroga como perfil mas pro-mercado/austeridad;
- diferencias sobre FMI, subsidios, empresas estatales, politica social;
- rol de los vicepresidentes.

Fuentes acumuladas:

- `input/source-01-pre-first-round-context.md`
- `input/source-02-first-round-poll-context.md`
- `input/source-03-first-round-surprise.md`
- `input/source-04-mas-collapse-runoff.md`
- `input/source-05-runoff-policy-contrast.md`

Sirve para ver si MiroFish razona sobre transferencias de votos y preferencias sociales, no solo encuestas.

## T3 - Tramo final antes del balotaje

Fecha maxima: `2025-10-17`

Idea: MiroFish ve evidencia cercana a la eleccion, incluida una encuesta tardia que favorece a Quiroga.

Incluye T2 mas:

- encuesta del 13 de octubre: Quiroga 44.9%, Paz 36.5%;
- senal de relaciones con Estados Unidos;
- documento deportivo como ruido temporalmente valido.

Fuentes acumuladas:

- `input/source-01-pre-first-round-context.md`
- `input/source-02-first-round-poll-context.md`
- `input/source-03-first-round-surprise.md`
- `input/source-04-mas-collapse-runoff.md`
- `input/source-05-runoff-policy-contrast.md`
- `input/source-06-late-poll-quiroga-lead.md`
- `input/source-07-us-relations-signal.md`
- `input/source-08-football-noise.md`

Sirve para ver si MiroFish se deja llevar por la ultima encuesta o si balancea todo el contexto.

## Resultado esperado del protocolo

Comparar los reportes `T0`, `T1`, `T2` y `T3` para observar:

- si cambia el ganador predicho;
- si cambian los porcentajes estimados;
- si cambia el margen;
- si aparecen o desaparecen mecanismos causales;
- si el documento de ruido afecta indebidamente el reporte;
- si hay leakage de informacion posterior al paquete.
