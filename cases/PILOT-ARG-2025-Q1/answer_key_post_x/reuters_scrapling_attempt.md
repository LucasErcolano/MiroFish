# Reuters Scrapling attempt

Objetivo: usar Scrapling para obtener una copia auditable de la nota de Reuters usada en el ground truth electoral.

URL objetivo:
https://www.reuters.com/world/americas/argentines-vote-high-stakes-test-mileis-libertarian-vision-2025-10-26/

Comandos/acciones ejecutadas:
- `python -m venv .hermes-scrapling-venv`
- `.hermes-scrapling-venv/bin/pip install scrapling==0.4.8 curl_cffi playwright browserforge camoufox patchright msgspec`
- `.hermes-scrapling-venv/bin/python -m patchright install chromium`
- `python model_output_raw/artifacts/scrapling_reuters_fetch.py`
- `python model_output_raw/artifacts/scrapling_reuters_browser_fetch.py`

Resultados:
- `scrapling.Fetcher.get`: HTTP 401, cuerpo vacío.
- `scrapling.StealthyFetcher.fetch`: HTTP 401, cuerpo vacío.
- `scrapling.DynamicFetcher.fetch`: HTTP 401, cuerpo vacío.

Evidencia:
- Log estático: `model_output_raw/artifacts/scrapling_reuters_fetch.log`
- Log browser/stealth: `model_output_raw/artifacts/scrapling_reuters_browser_fetch.log`
- HTML/TXT resultantes en `answer_key_post_x/sources/` quedaron vacíos para los fetches Scrapling porque Reuters respondió 401.

Conclusión: Scrapling fue probado pero no salteó el bloqueo de Reuters en este entorno. El item Reuters sigue en NEEDS_REVIEW y requiere copia licenciada/manual o fuente alternativa accesible para auditoría externa.
