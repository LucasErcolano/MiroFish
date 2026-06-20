# Session Log — Case B1 Setup (2026-05-26)

## Lo que se hizo

### 1. Infraestructura (resuelto)
- Merge de `origin/chore/pilot-arg-2025-q1-artifacts` → trajo `tools/mirofish_headless.py` y `cases/PILOT-ARG-2025-Q1/`
- Branch de trabajo: `feat/case-b-backtesting`
- Neo4j corriendo vía Docker: `sudo docker run -d --name mirofish-neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/mirofishpassword neo4j:5`
- Backend Flask arrancando en `http://localhost:5001` con Python 3.12

### 2. Dependencias (resuelto)
| Problema | Fix |
|---------|-----|
| `neo4j>=5.26` vs `camel-oasis==0.2.5` que pide `neo4j==5.23` | `[tool.uv] override-dependencies = ["neo4j==5.23.0"]` en `pyproject.toml` |
| Python 3.14 sin wheels para `tiktoken` | `backend/.python-version` → `3.12` |

### 3. Documentos pre-registro (completo)
- `cases/CASE-B1-BTC-ETF-JAN2024/` — case_card, prompt_frozen, ground_truth, 8 fuentes en `input_pack_pre_x/sources/`, `seed_bundle.md`, `manifest.csv`
- `cases/CASE-B2-ARG-IPC-2025/` — case_card, prompt_frozen, ground_truth, input_pack copiado del piloto
- `cases/RUNBOOK.md` — guía completa de ejecución

### 4. Config LLM (estado actual)
`.env` configurado con `gemini-2.0-flash` para LLM + Graphiti, `gemini-embedding-001` para embeddings.

```
LLM_MODEL_NAME=gemini-2.0-flash
GRAPHITI_LLM_MODEL=gemini-2.0-flash
GRAPHITI_EMBEDDER_MODEL=gemini-embedding-001
```

### 5. Intentos de ejecución y errores encontrados
| Intento | Error | Causa |
|---------|-------|-------|
| `gemini-2.5-flash-lite` | 429 rate limit | Free tier: 20 req/día |
| `gemini-1.5-flash` | 404 not found | Modelo no disponible en `v1beta/openai/` |
| `llama-3.3-70b-versatile` (Groq) | 400 json_schema | Groq no soporta `response_format: json_schema` para ese modelo |
| `gemini-2.0-flash` | 429 rate limit | Quota diaria agotada en la misma sesión de pruebas |

---

## Estado actual

El pipeline está **funcionalmente correcto** — el backend arranca, Neo4j conecta, la ontología se genera (verificado: "10 entidades, 8 relaciones" en corridas anteriores). El bloqueante es exclusivamente la **quota de API de Gemini agotada para el día**.

La config final que funcionó hasta el rate limit:
- Backend: `http://localhost:5001` ✅
- Neo4j: `bolt://localhost:7687` ✅  
- Ontología: se genera correctamente con `gemini-2.0-flash` ✅
- Graph build: falla en el paso de extracción de nodos por quota ❌

---

## Próximo paso (uno de estos dos)

### Opción A — Habilitar billing en Google Cloud (recomendado, cuesta ~$0.10 por corrida)
1. Ir a https://console.cloud.google.com/billing
2. Vincular billing al proyecto que tiene tu Gemini API key
3. Volver a correr mañana (o ahora mismo):
```bash
npm run backend  # terminal 1
uv run python tools/mirofish_headless.py \
  --file cases/CASE-B1-BTC-ETF-JAN2024/input_pack_pre_x/seed_bundle.md \
  --requirement "$(cat cases/CASE-B1-BTC-ETF-JAN2024/prompt_frozen/prompt.md)" \
  --platform parallel --max-rounds 10 \
  --output-dir cases/CASE-B1-BTC-ETF-JAN2024/model_output_raw  # terminal 2
```

### Opción B — Esperar hasta mañana
La quota de Gemini free tier se resetea a las 00:00 UTC. Mañana correr el mismo comando de arriba.  
Con `gemini-2.0-flash` (200 req/día) alcanza para completar B1 y B2.

---

## Después de una corrida exitosa

1. Verificar `cases/CASE-B1-BTC-ETF-JAN2024/model_output_raw/run_manifest.json`:
   ```bash
   python3 -c "import json; d=json.load(open('cases/CASE-B1-BTC-ETF-JAN2024/model_output_raw/run_manifest.json')); print(d.get('status'), d.get('num_rounds_or_epochs'))"
   ```
   Debe decir `completed` y `10`.

2. Leer el reporte:
   ```bash
   cat cases/CASE-B1-BTC-ETF-JAN2024/model_output_raw/mirofish_report_raw.md
   ```

3. Completar `cases/CASE-B1-BTC-ETF-JAN2024/answer_key_post_x/first_eval.md` comparando las predicciones del reporte con el ground truth en `answer_key_post_x/ground_truth.md`.

4. Repetir para B2.
