# Deviation report — real_mirofish_round_1

Status: PASS

## Flujo real de MiroFish usado

Se usó el runner nativo del repo `backend/scripts/run_twitter_simulation.py`. Este flujo importa `camel.models.ModelFactory`, `camel.types.ModelPlatformType`, `oasis`, `ActionType`, `LLMAction`, `ManualAction` y `generate_twitter_agent_graph`, crea un entorno OASIS Twitter con `oasis.make(...)`, ejecuta `env.reset()`, publica eventos iniciales con `env.step(...)` y luego ejecuta el loop social con `LLMAction()`.

Comando ejecutado:

`backend/.venv/bin/python backend/scripts/run_twitter_simulation.py --config cases/PILOT-ARG-2025-Q1/model_output_raw/real_mirofish_round_1/artifacts/oasis_twitter_minimal_sim/simulation_config.json --max-rounds 1 --no-wait`

## Componentes que participaron

- Backend/script real MiroFish: sí, `backend/scripts/run_twitter_simulation.py`.
- OASIS/CAMEL: sí.
- `generate_twitter_agent_graph`: sí.
- Entorno OASIS Twitter: sí.
- `env.reset()`: sí, según stdout `环境初始化完成`.
- Eventos iniciales: sí, 2 posts iniciales.
- Loop social real: sí, stdout registra `Round 1/1 (100.0%) - 2 agents active`.
- Gemini OpenAI-compatible: sí, `gemini-2.5-flash-lite` y base URL configurada.
- Zep/Graphiti: no.
- Report agent: no; se exportó reporte crudo desde stdout/stderr/SQLite DB.

## Ronda/época

- Rondas/épocas solicitadas: 1.
- Rondas/épocas MiroFish/OASIS completadas: 1.
- Equivalencia usada: `--max-rounds 1` limita `total_rounds` en `TwitterSimulationRunner.run`; el stdout registra `Round 1/1`.

## Agentes reales

- Agentes configurados: 2.
- Agentes activos en la ronda social: 2.

## Simulación social real

Sí. Hubo entorno OASIS, eventos iniciales y una ronda social con 2 agentes activos. Los artefactos crudos están en SQLite y exportados bajo `artifacts/db_export/`.

## Qué no se pudo/no se usó

- No se usó el CLI fork `mirofish run` porque no está disponible en este repo/PATH.
- No se usó el runner adaptado `backend/scripts/run_case_pilot_arg_2025_q1.py` como resultado final.
- No se usó Zep/Graphiti para mantener `memory_persistent=false` y evitar stores externos.
- No se usó report agent porque el report agent está acoplado a servicios de búsqueda/Zep; en su lugar se creó `mirofish_report_raw.md` como export crudo de stdout/stderr/DB, sin reescritura editorial.

## Diferencias con CLI fork `mirofish run`

El CLI fork no está presente. La ejecución se hizo con el flujo nativo disponible en el repo actual: script backend OASIS Twitter. Por tanto, la interfaz y artefactos difieren, pero sí hubo sistema MiroFish/OASIS real.

## Seguridad/secretos

La API key se pasó solo como variable de entorno del proceso. No se escribió a `.env`, config, logs ni artefactos intencionalmente.
