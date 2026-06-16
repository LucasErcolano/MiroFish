# Case Card - Bolivia 2025 Presidential Runoff

## Caso

- Dominio: politico-social.
- Evento: balotaje presidencial de Bolivia.
- Fecha de balotaje: 2025-10-19.
- Pregunta principal: ganador del balotaje y porcentaje aproximado de votos.
- Modelo primario: `qwen/qwen3-8b` via OpenRouter.
- Cutoff del modelo primario: 2025-03-31.
- Resultado real: separado en `ground_truth_private.md`.

## Estado de ejecucion

Las corridas guardadas en este PR son `*_gemma_probe`. Sirven como evidencia del protocolo temporal end-to-end, pero no deben contarse como la pasada primaria fija `qwen/qwen3-8b`.

Para cierre estricto de S2 falta una pasada limpia con el modelo primario fijo y, si se aplica la regla de robustez S2, las replicas requeridas de la mejor condicion.

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
- Minimo 20 entidades relevantes extraibles: si. Entidades esperadas en las fuentes incluyen Rodrigo Paz, Jorge "Tuto" Quiroga, Edman Lara, Juan Pablo Velasco, Samuel Doria Medina, Manfred Reyes Villa, Eduardo del Castillo, Andronico Rodriguez, Luis Arce, Evo Morales, Jaime Paz Zamora, Movimiento al Socialismo, AS/COA, AtlasIntel, La Razon, Captura Consulting, Red Uno, AP, Reuters, Bolivia.com, Departamento de Estado de EE.UU., Marco Rubio, Christopher Landau, FMI, empresas estatales, gobiernos regionales, Tarija, Cochabamba, El Alto, Bolivia, Estados Unidos y la seleccion boliviana de futbol.
- Ground truth fuera del input: si.
- Evento posterior al cutoff del modelo: si.
- Metrica definida antes de ejecutar: si.

## Regla temporal

Ningun archivo de `input/` debe incluir resultados publicados el 19 de octubre de 2025 despues del cierre electoral ni analisis posteriores al resultado. El resultado real queda solo en `ground_truth_private.md`.
