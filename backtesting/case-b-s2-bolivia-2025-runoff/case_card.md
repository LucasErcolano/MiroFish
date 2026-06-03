# Case Card - Bolivia 2025 Presidential Runoff

## Caso

- Dominio: politico-social.
- Evento: balotaje presidencial de Bolivia.
- Fecha de balotaje: 2025-10-19.
- Pregunta principal: ganador del balotaje y porcentaje aproximado de votos.
- Modelo primario: `qwen/qwen3-8b` via OpenRouter.
- Cutoff del modelo primario: 2025-03-31.
- Resultado real: separado en `ground_truth_private.md`.

## Hipotesis competidoras

1. **Paz gana por moderacion:** Rodrigo Paz capta voto anti-MAS sin activar tanto miedo al ajuste como Quiroga.
2. **Quiroga gana por experiencia/oposicion dura:** Jorge "Tuto" Quiroga consolida el voto de derecha y capitaliza el rechazo al MAS.
3. **Encuestas subestiman voto territorial:** las encuestas cercanas pueden no capturar organizacion territorial, voto rural o transferencia de apoyos.

## Complexity gate S2

- Minimo 6 documentos seed: si.
- Minimo 3 fechas documentales distintas: si.
- Minimo 3 fuentes o tipos de fuente: si.
- Minimo 2 hipotesis causales competidoras: si.
- Minimo 1 documento distractor/noise temporalmente valido: si.
- Minimo 20 entidades relevantes extraibles: probable; validar tras construir grafo.
- Ground truth fuera del input: si.
- Evento posterior al cutoff del modelo: si.
- Metrica definida antes de ejecutar: si.

## Regla temporal

Ningun archivo de `input/` debe incluir resultados publicados el 19 de octubre de 2025 despues del cierre electoral ni analisis posteriores al resultado. El resultado real queda solo en `ground_truth_private.md`.
