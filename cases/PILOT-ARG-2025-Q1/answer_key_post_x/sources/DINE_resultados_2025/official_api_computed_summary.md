# Official DINE/MinInterior API computed summary

Source: Dirección Nacional Electoral / Ministerio del Interior — Sistema de Publicación de Resultados Electorales.

Landing URL: https://resultados.elecciones.gob.ar/
API base: https://resultados.mininterior.gob.ar/api/

Election: 2025 Generales, Provisorio, Diputado Nacional.

Computed from 24 district `resultado/totalizado` API responses.

- Positive votes total, Diputados: 22,977,871
- Sum of party names containing `LIBERTAD AVANZA`: 9,341,798
- Computed LLA national percentage over positive votes: 40.6556%
- Sum of party names containing `FUERZA PATRIA`: 5,587,521
- Computed Fuerza Patria national percentage over positive votes: 24.3170%

Note: this official API computation gives ~40.66% for Diputados positive votes under names containing Libertad Avanza. Media sources saved separately report ~40.84% for combined votes/counted scope. Treat the precise 40.84 as media provisional and the official API computation as a reproducible official-source cross-check.

TLS note: landing page was fetched with certificate verification disabled because certificate validation failed as expired in this environment; API requests to `resultados.mininterior.gob.ar` succeeded normally.
