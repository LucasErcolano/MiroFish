# Rubric

## Score objetivo

Maximo: 5 puntos.

- 1 punto: el ganador predicho es Argentina.
- 1 punto: incluye `confidence` parseable entre 0 y 1.
- 1 punto: incluye rangos de probabilidad parseables para Argentina y Colombia.
- 1 punto: la justificacion y la incertidumbre citan `source_id`.
- 1 punto: no hay filtracion post-cutoff ni uso del resultado real.

## Interpretacion secundaria

- T0 deberia ser mas incierto porque solo contiene contexto base.
- T1 agrega forma reciente y deberia mejorar la calidad causal.
- T2 agrega mercado/modelos y deberia subir confianza por Argentina.
- T3 agrega contrapeso Colombia y deberia mantener Argentina como favorita, pero con incertidumbre mas explicita.

## No medir

- No se mide marcador exacto.
- No se mide si acierta que hubo tiempo extra.
- No se debe premiar informacion posterior al 13 de julio de 2024.
