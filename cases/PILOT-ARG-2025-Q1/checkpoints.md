# Checkpoints — PILOT-ARG-2025-Q1

## CP-01 — Carpeta creada
1. Archivos creados/modificados: `README.md`, estructura completa bajo `cases/PILOT-ARG-2025-Q1/`.
2. Comando ejecutado: `python create_pilot_case.py`.
3. Hash/evidencia: README sha256 `85df0613dbebdc45584b536e933887530736c92064679bc82990cc77ee4766ed`.
4. Riesgos detectados: ejecución MiroFish aún dependía de CLI no verificado.
5. Estado: PASS.

## CP-02 — Ficha del caso
1. Archivos creados/modificados: `case_card.md`.
2. Comando ejecutado: `python create_pilot_case.py`.
3. Hash/evidencia: case_card sha256 `afcc21ae06e5d51a4fdb74b1f701d690f5c39cc6fe15cb5a811e8e6d523aea80`.
4. Riesgos detectados: ninguno; desenlace real solo se referencia como separado en `answer_key_post_x`.
5. Estado: PASS.

## CP-03 — Configuración MiroFish previa
1. Archivos creados/modificados: `model_output_raw/run_config.json`, `run_manifest.json`.
2. Comando ejecutado: `mirofish --help && mirofish run --help`.
3. Hash/evidencia: run_config sha256 `d66b501908cd91780fac751a859b734cc1291bf288cbccf412f0149730b0e4f9`; evidencia CLI: `mirofish: command not found`.
4. Riesgos detectados: todos los parámetros runtime quedan marcados como `unsupported_parameter=true` porque el CLI no existe en PATH.
5. Estado: BLOCKED.

## CP-04 — Fuentes pre-corte guardadas y hasheadas
1. Archivos creados/modificados: `input_pack_pre_x/manifest.csv`, `input_pack_pre_x/sources/*`, `input_pack_pre_x/excerpts/*`, `input_pack_pre_x/hashes.json`.
2. Comando ejecutado: `python create_pilot_case.py`.
3. Hash/evidencia: manifest sha256 `507a8ff2ea9d4e0a7c0387aa4aeadaa3067a56224b044a9d2b309cda17b84e25`; `input_pack_pre_x/hashes.json` contiene hashes por archivo.
4. Riesgos detectados: algunas fuentes HTML pueden contener boilerplate dinámico del sitio; se preservaron extractos separados para auditoría.
5. Estado: PASS.

## CP-05 — Seed bundle y escaneo temporal
1. Archivos creados/modificados: `input_pack_pre_x/seed_bundle.md`, `model_output_raw/artifacts/pre_cutoff_scan.py`, `model_output_raw/artifacts/pre_cutoff_scan.log`.
2. Comando ejecutado: `python model_output_raw/artifacts/pre_cutoff_scan.py`.
3. Hash/evidencia: seed_bundle sha256 `f21cc14552fde8c1b0cab41d76ba2878aafd96e1a205c4dcad88c3a6f55a850d`; log: `{'forbidden_matches': [], 'bad_dates': [], 'status': 'PASS'}`.
4. Riesgos detectados: el escaneo es heurístico; no reemplaza revisión humana de fuentes.
5. Estado: PASS.

## CP-06 — Prompt congelado
1. Archivos creados/modificados: `prompt_frozen/prompt.md`, `prompt_frozen/system_constraints.md`, `prompt_frozen/output_schema.json`, `prompt_frozen/prompt_hash.txt`.
2. Comando ejecutado: `python create_pilot_case.py`.
3. Hash/evidencia: prompt sha256 `25f80a94cb31a1aacae284c2840991957d937bf4c4d11683efd5ab4285ad7058`.
4. Riesgos detectados: ninguno; prompt generado antes del intento de corrida.
5. Estado: PASS.

## CP-07 — Ejecución de MiroFish
1. Archivos creados/modificados: `model_output_raw/stdout.log`, `model_output_raw/stderr.log`, `model_output_raw/exit_code.txt`, `model_output_raw/mirofish_report_raw.md`, `model_output_raw/verdict_raw.json`.
2. Comando ejecutado: `mirofish run --files input_pack_pre_x/sources/* input_pack_pre_x/seed_bundle.md --requirement "$(cat prompt_frozen/prompt.md)" --json > model_output_raw/stdout.log 2> model_output_raw/stderr.log`.
3. Hash/evidencia: exit code `127`; stderr `/usr/bin/bash: line 3: mirofish: command not found`.
4. Riesgos detectados: no hay output crudo real. El archivo `mirofish_report_raw.md` es registro de bloqueo, no predicción.
5. Estado: BLOCKED.

## CP-08 — Answer key separado
1. Archivos creados/modificados: `answer_key_post_x/ground_truth.md`, `answer_key_post_x/source_manifest.csv`, `answer_key_post_x/sources/*`.
2. Comando ejecutado: `python create_pilot_case.py`.
3. Hash/evidencia: ground_truth sha256 `b23cc3a111f6cd357d804a1a15f17fe90fa0657737eb1538095eb426ddb74629`.
4. Riesgos detectados: Reuters bloqueó fetch automatizado con 401; se guardó la página de bloqueo y se documentó que la cifra electoral proviene del dato provisto en el encargo, pendiente de copia licenciada/verificable si se requiere auditoría externa.
5. Estado: NEEDS_REVIEW.

## CP-09 — Rúbrica 1-5
1. Archivos creados/modificados: `answer_key_post_x/rubric_1_5.md`.
2. Comando ejecutado: `python create_pilot_case.py`.
3. Hash/evidencia: rubric sha256 `6dd7d65898d1659b00eeffc5c10540829c249da37a9c0cfb2b555380600c5f93`.
4. Riesgos detectados: ninguno.
5. Estado: PASS.

## CP-10 — Primera evaluación
1. Archivos creados/modificados: `answer_key_post_x/first_eval.md`.
2. Comando ejecutado: `python create_pilot_case.py`.
3. Hash/evidencia: first_eval sha256 `97d12ba29e599d464c95bf165e9251d09b1922cb3735e5162c2b5fa3243cf725`.
4. Riesgos detectados: evaluación no puntuada porque no existe output crudo real.
5. Estado: BLOCKED.

## CP-11 — Paquete S2
1. Archivos creados/modificados: `answer_key_post_x/evaluator_packet.md`, `answer_key_post_x/s2_plan.md`.
2. Comando ejecutado: `python create_pilot_case.py`.
3. Hash/evidencia: evaluator_packet sha256 `60c356c21500dc81188704e036afa358e67bb071831f7c2c6d7063ebfdce4be5`; s2_plan sha256 `69451e5a1ad0da0c25725a845f9285260e41aea8c114b7bd4642717975f7fd5e`.
4. Riesgos detectados: evaluadores no pueden puntuar hasta que exista output crudo real.
5. Estado: NEEDS_REVIEW.

## Checklist final de aceptación
- [x] Existe ficha del caso con dominio, pregunta, x, delta y desenlace real.
- [x] Los documentos input están listados, fechados, guardados y hasheados.
- [x] Existe prompt congelado con hash.
- [x] MiroFish fue ejecutado o el bloqueo quedó documentado.
- [x] La salida cruda quedó guardada como bloqueo, no como predicción.
- [x] Existe rúbrica 1-5.
- [x] Existe primera evaluación o plan S2.
- [x] Ground truth está separado de inputs y output.
- [x] No hay datos post-corte detectados por escaneo heurístico en input_pack_pre_x.
- [x] run_manifest.json permite reproducir la corrida o reproducir el bloqueo.


## CP-08 addendum — Reuters vía Scrapling
1. Archivos creados/modificados: `answer_key_post_x/reuters_scrapling_attempt.md`, `model_output_raw/artifacts/scrapling_reuters_fetch.py`, `model_output_raw/artifacts/scrapling_reuters_browser_fetch.py`, logs correspondientes y fuentes vacías de intento Scrapling.
2. Comando ejecutado: `Scrapling Fetcher.get`, `StealthyFetcher.fetch` y `DynamicFetcher.fetch` contra la URL de Reuters.
3. Hash/evidencia: reuters_scrapling_attempt sha256 `c1125ad408e623d9eb52a383d440b00fb67d59f60931c3cb9d5736d63606dfab`; logs indican HTTP 401 con cuerpo vacío.
4. Riesgos detectados: Scrapling no salteó el bloqueo Reuters en este entorno; fuente electoral post-corte aún requiere copia verificable alternativa/licenciada.
5. Estado: BLOCKED / NEEDS_REVIEW.


## CP-08 addendum 2 — Fuentes accesibles equivalentes
1. Archivos creados/modificados: `answer_key_post_x/accessible_electoral_sources.md`, `answer_key_post_x/ground_truth.md`, `answer_key_post_x/source_manifest.csv`, copias HTML/TXT/extractos de AP, Buenos Aires Times, El País English y NPR en `answer_key_post_x/sources/`.
2. Comando ejecutado: búsqueda DuckDuckGo Lite + `requests.get()` para fuentes candidatas; extracción local de snippets.
3. Hash/evidencia: accessible_electoral_sources sha256 `5e70551c919a247f9550179c8625b3693362890c91d6be031ce7081da9b1eab6`; ground_truth sha256 `4a9483677c45d7b5abc382b6c91c7f5ae9717a34623f6a547e9a79371d6fbf81`.
4. Riesgos detectados: Buenos Aires Times reporta cifra con 90% contado; AP/NPR/El País corroboran “más de 40%” y fortalecimiento legislativo. Para cifra oficial final exacta, agregar fuente electoral oficial si se requiere máxima precisión.
5. Estado: PASS.


## Option 3 addendum — Auditoría de paquete y fortalecimiento de answer key
1. Archivos creados/modificados: `answer_key_post_x/quality_audit_pre_run.md`, `answer_key_post_x/rubric_1_5.md`, `answer_key_post_x/ground_truth.md`, `answer_key_post_x/accessible_electoral_sources.md`, `answer_key_post_x/source_manifest.csv`, `answer_key_post_x/sources/DINE_resultados_2025/*`, `model_output_raw/artifacts/official_election_source_fetch.py`.
2. Comando ejecutado: `python model_output_raw/artifacts/pre_cutoff_scan.py`; `python model_output_raw/artifacts/official_election_source_fetch.py`.
3. Hash/evidencia: quality_audit sha256 `63771cb0645bdee8cb9c1e3fd97243c4cf16a4ffe7b5055c5ac118ad52f22722`; official_api_summary sha256 `feab502b4ac2b95992fc660fc6fa537e111cae433f1d5b53c53f0107be392019`; ground_truth sha256 `fbc79175aaedc953225fa6196fa6a21a602c2d2493c6fc2b903c542c0b3cf160`; rubric sha256 `54f2db2860908885832ce555de9149d328831f6c8c25783b8cf2321818d1508f`.
4. Riesgos detectados: API oficial computada para Diputados arroja 40.6556% para nombres que contienen Libertad Avanza; Buenos Aires Times reporta 40.84% con 90% contado y alcance combinado. Se documentó rango recomendado 40–41% para no sobreajustar decimales.
5. Estado: PASS.


## Option 2 — Adapted current-repo runner
1. Archivos creados/modificados: `backend/scripts/run_case_pilot_arg_2025_q1.py`, `package.json`, `backend/requirements-oasis.txt`, `model_output_raw/adapted_run_config.json`, `model_output_raw/artifacts/adapted_repo_runner.md`, `model_output_raw/artifacts/adapted_input_packet.md`, `model_output_raw/stdout.log`, `model_output_raw/stderr.log`, `model_output_raw/exit_code.txt`, `model_output_raw/mirofish_report_raw.md`, `model_output_raw/verdict_raw.json`.
2. Comando ejecutado: `python backend/scripts/run_case_pilot_arg_2025_q1.py --case-dir cases/PILOT-ARG-2025-Q1 > cases/PILOT-ARG-2025-Q1/model_output_raw/stdout.log 2> cases/PILOT-ARG-2025-Q1/model_output_raw/stderr.log`; verificación: `python -m py_compile backend/scripts/run_case_pilot_arg_2025_q1.py`.
3. Hash/evidencia: adapted runner sha256 `06e37784444f2850d9ae2ca608c37782bd4c925cb1f16104ba1f7545faefa587`; adapted_run_config sha256 `bb22451ad6ef46ff0f4a4a3443c2246458bcd8162822aa9d68d00400b170e225`; adapted_input_packet sha256 `5bb3455b683faa5d762c660f6928642bc384974b88d019b864346c0b18560b48`; stdout sha256 `654205b47a7187acae74c60ccd801960804f41098970f723e5dd1e75953bc78f`; verdict sha256 `ae2ba0703cf6aa6b57f0db8928ce321597a1ad29c5c10db5e6be6efcec5e3cfe`.
4. Riesgos detectados: el repo actual no expone CLI `mirofish`; la corrida adaptada no ejecuta OASIS/Zep/Graphiti, sino un fallback LLM directo con input local. Además falta `LLM_API_KEY`, por lo que no hay output crudo real todavía. Se detectó y mitigó parcialmente un conflicto de dependencias: `graphiti-core==0.28.2` requiere `neo4j>=5.26.0`, mientras `camel-oasis==0.2.5` fija `neo4j==5.23.0`; OASIS queda documentado como entorno separado en `backend/requirements-oasis.txt`.
5. Estado: BLOCKED por falta de `LLM_API_KEY`; runner adaptado listo para reintento reproducible.


## CP-07/CP-10 — Adapted Gemini run completed
1. Archivos creados/modificados: `model_output_raw/mirofish_report_raw.md`, `model_output_raw/verdict_raw.json`, `model_output_raw/stdout.log`, `model_output_raw/stderr.log`, `model_output_raw/exit_code.txt`, `model_output_raw/adapted_run_config.json`, `model_output_raw/artifacts/adapted_run_1_raw.md`, `model_output_raw/artifacts/adapted_run_2_raw.md`, `model_output_raw/artifacts/adapted_run_3_raw.md`, `answer_key_post_x/first_eval.md`, `run_manifest.json`, `model_output_raw/artifacts/adapted_repo_runner.md`.
2. Comando ejecutado: adapted runner via Gemini OpenAI-compatible endpoint. The API key was passed only as an environment variable and is not recorded in repo files. Requested model `gemini-2.0-flash-lite` returned HTTP 404; fallback `gemini-2.5-flash-lite` completed.
3. Hash/evidencia: raw report sha256 `117279591956754bdf3f178e60c1847bd5c9d77a6cb777a39053c027e2250635`; verdict sha256 `dc33db72537acd16f8f7151bd9e81a992aee81e46b31546bc1ab93ac39567925`; run1 sha256 `5bd828723eb5c6ccf9d2c2c1631a6cc36bc2ca06814299dda6e014fb6bca6ee4`; run2 sha256 `2196d2f25d3d22b2e21446a609e6d7f1e7d5c37e30d1c9276dbc616d5a232bf5`; run3 sha256 `77aeb3ca561bd231de23ff778d0eae43c6ef7dfcec95816678bf9f04ee313f5c`; first_eval sha256 `5a592ad80bca5b7e0aa56ab6b21313d7f5806dda2f426b1a38d5ad36097cbc20`.
4. Riesgos detectados: esta es corrida adaptada, no CLI `mirofish` ni OASIS/Zep/Graphiti. Gemini no acepta el parámetro HTTP `seed`, por lo que se registra el seed como intención de auditoría pero no como garantía de determinismo del proveedor. `gemini-2.0-flash-lite` no estuvo disponible para esta cuenta; se usó `gemini-2.5-flash-lite`.
5. Estado: PASS para corrida adaptada; NEEDS_REVIEW si se exige equivalencia estricta con MiroFish CLI/OASIS.

## CP-12 — Real MiroFish/OASIS round-1 attempt
1. Archivos creados/modificados: `model_output_raw/real_mirofish_round_1/run_config.json`, `stdout.log`, `stderr.log`, `mirofish_report_raw.md`, `verdict_raw.json`, `deviation_report.md`, `run_hashes.json`, `artifacts/oasis_twitter_minimal_sim/*`, `artifacts/db_export/*`, `run_manifest.json`, `model_output_raw/run_hashes.json`.
2. Comando ejecutado: `backend/.venv/bin/python backend/scripts/run_twitter_simulation.py --config cases/PILOT-ARG-2025-Q1/model_output_raw/real_mirofish_round_1/artifacts/oasis_twitter_minimal_sim/simulation_config.json --max-rounds 1 --no-wait`. La API key se pasó solo por variable de entorno del proceso y no se escribió a archivos.
3. Hash/evidencia: real run_config sha256 `fc7087d6912cb04f059f1d203585d5b04432785f217bd5d45a6874c6292a8efa`; verdict sha256 `8804f9e5e82410368ba34d07a94b2194799e209bff3f017296f4a88758e28011`; raw report sha256 `61a1db4a80142d0940dd0c8172f3b44db5c60056435b9fecfa4e204b90741c2f`; stdout sha256 `51a71f2fc6e8abb2109fedc2c5904871423d240a29a3e2f67d1cc0a386ef36fc`; SQLite db sha256 `8cd8052be0fc9149964e814e05f8e196af3ec0190434b6931b94a3ce3b9d5e33`.
4. Riesgos detectados: no se usó CLI `mirofish run` porque no existe en PATH; se usó el script OASIS nativo del backend. No se usó Zep/Graphiti ni report agent para mantener memoria persistente/RAG externos apagados. Gemini no recibe `seed` HTTP.
5. Estado: PASS. Rondas/épocas MiroFish completadas: 1. Agentes reales activos: 2. Escaneo temporal: PASS. Escaneo secretos en artefactos: PASS.
