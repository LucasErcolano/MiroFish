# Case B Backtesting Runbook

Casos: B1 (Bitcoin ETF, enero 2024) y B2 (Argentina IPC, 2025).
Branch: `feat/case-b-backtesting`

---

## Qué es esto

MiroFish corre una simulación social multi-agente sobre los documentos que le pasás. Los agentes debaten en Twitter/Reddit simulado y el ReportAgent sintetiza una predicción. Este runbook ejecuta esa simulación contra dos casos históricos con ground truth pre-registrado para medir la calidad predictiva del sistema.

---

## 1. Prerequisitos

### 1.1 Neo4j (backend de grafo)

MiroFish necesita Neo4j corriendo en `bolt://localhost:7687` antes de iniciar el backend.

**Opción A — Docker (recomendado):**
```bash
docker run -d \
  --name mirofish-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/mirofishpassword \
  neo4j:5
```

Verificar que arrancó: `docker logs mirofish-neo4j | tail -5` — debe decir `Started`.

**Opción B — Neo4j Desktop:**
Descargá de https://neo4j.com/download/ y creá un proyecto con password `mirofishpassword`.

### 1.2 Ollama o embeddings via API

El backend Graphiti necesita un modelo de embeddings. La opción más simple es usar la API de Gemini para embeddings:

```bash
# Verificar que Ollama está corriendo (si lo usás para embeddings locales)
curl http://localhost:11434/api/tags
```

Si usás Gemini para embeddings (recomendado — no necesita GPU):
- Model: `gemini-embedding-001`
- Dimensiones: 3072
- URL: `https://generativelanguage.googleapis.com/v1beta/openai/`

### 1.3 Gemini API Key

Necesitás una API key de Google AI Studio:
1. Ir a https://aistudio.google.com/app/apikey
2. Crear key (gratis, límite generoso)
3. Guardarla — la vas a exportar como variable de entorno

### 1.4 Dependencias Python

```bash
# Desde la raíz del proyecto
cd /home/elianaostro/Documents/MiroFish
uv sync  # instala todo desde pyproject.toml
```

Si falta camel-oasis:
```bash
cd backend && uv add camel-ai==0.2.78 oasis==0.2.5
```

---

## 2. Configuración del entorno

Copiá `.env.example` a `.env` en la raíz y completá los valores. O exportá directamente en tu shell:

```bash
# === LLM principal ===
export LLM_API_KEY="AIza..."         # tu Gemini API key
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
export LLM_MODEL_NAME="gemini-2.5-flash-lite"

# === Graphiti (grafo de conocimiento) ===
export GRAPH_BACKEND="graphiti"
export GRAPHITI_URI="bolt://localhost:7687"
export GRAPHITI_USER="neo4j"
export GRAPHITI_PASSWORD="mirofishpassword"
export GRAPHITI_DATABASE="neo4j"

# LLM para Graphiti (puede ser la misma key)
export GRAPHITI_LLM_API_KEY="AIza..."
export GRAPHITI_LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
export GRAPHITI_LLM_MODEL="gemini-2.5-flash-lite"
export GRAPHITI_LLM_CLIENT_MODE="generic"

# Embeddings para Graphiti (vía Gemini)
export GRAPHITI_EMBEDDER_API_KEY="AIza..."
export GRAPHITI_EMBEDDER_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
export GRAPHITI_EMBEDDER_MODEL="gemini-embedding-001"
export GRAPHITI_EMBEDDER_DIM="3072"

# Reranker (puede ser el mismo modelo que LLM)
export GRAPHITI_RERANKER_API_KEY="AIza..."
export GRAPHITI_RERANKER_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
export GRAPHITI_RERANKER_MODEL="gemini-2.5-flash-lite"
```

**Alternativa si no querés usar Graphiti:** cambiar a backend Zep (más simple, sin Neo4j):
```bash
export GRAPH_BACKEND="zep"
export ZEP_API_KEY="tu-zep-api-key"
```
Zep Cloud gratuito: https://www.getzep.com/

---

## 3. Iniciar el backend

El headless runner llama a la API Flask en `http://localhost:5001`. El backend **debe estar corriendo** antes de ejecutar el runner.

```bash
# Terminal 1 — dejar corriendo
npm run backend
# o directamente:
cd backend && uv run python run.py
```

Esperar a ver: `Running on http://0.0.0.0:5001`. Si hay errores de conexión a Neo4j, verificar que el container esté arriba.

---

## 4. Ejecutar Case B1 — Bitcoin ETF (enero 2024)

### Paso 4.1 — Verificar que los archivos pre-registro están completos

```bash
ls cases/CASE-B1-BTC-ETF-JAN2024/
# debe mostrar: case_card.md, input_pack_pre_x/, prompt_frozen/, model_output_raw/, answer_key_post_x/

ls cases/CASE-B1-BTC-ETF-JAN2024/input_pack_pre_x/sources/
# debe mostrar los 8 documentos fuente (MARKET_01..., RISK_01..., ANALYST_01..., FLOW_01..., SOCIAL_01...)
```

### Paso 4.2 — Correr el headless runner

```bash
# Terminal 2 (con el backend ya corriendo en terminal 1)
cd /home/elianaostro/Documents/MiroFish

python tools/mirofish_headless.py \
  --file cases/CASE-B1-BTC-ETF-JAN2024/input_pack_pre_x/seed_bundle.md \
  --requirement "$(cat cases/CASE-B1-BTC-ETF-JAN2024/prompt_frozen/prompt.md)" \
  --platform parallel \
  --max-rounds 10 \
  --output-dir cases/CASE-B1-BTC-ETF-JAN2024/model_output_raw
```

**Tiempo estimado:** 15–45 minutos (depende de velocidad de Gemini y rondas de simulación).

**Qué hace el runner:**
1. Sube el `seed_bundle.md` al backend y genera la ontología del grafo
2. Construye el grafo de conocimiento (async, poll hasta completar)
3. Crea agentes de simulación basados en el grafo
4. Corre la simulación OASIS en plataforma `parallel` (Twitter + Reddit simultáneo)
5. Genera el reporte de predicción con ReportAgent
6. Guarda todo en `model_output_raw/`

### Paso 4.3 — Verificar que el run fue real (no BLOCKED)

```bash
cat cases/CASE-B1-BTC-ETF-JAN2024/model_output_raw/run_manifest.json | python3 -m json.tool | grep -E '"status"|"num_rounds|"is_real'
```

Debe mostrar:
```json
"status": "completed",
"is_real_mirofish_system": true,
"num_rounds_or_epochs": 10
```

Si muestra `"status": "BLOCKED"`, revisar `"reason"` en el mismo JSON para diagnosticar.

---

## 5. Ejecutar Case B2 — Argentina IPC 2025

B2 usa el mismo `input_pack_pre_x` del piloto (documentos macro Argentina, cutoff 31 ene 2025).

```bash
python tools/mirofish_headless.py \
  --file cases/CASE-B2-ARG-IPC-2025/input_pack_pre_x/seed_bundle.md \
  --requirement "$(cat cases/CASE-B2-ARG-IPC-2025/prompt_frozen/prompt.md)" \
  --platform parallel \
  --max-rounds 10 \
  --output-dir cases/CASE-B2-ARG-IPC-2025/model_output_raw
```

> B2 puede correr en paralelo con B1 en una segunda terminal si tenés suficientes créditos de API. Usar un backend separado o correr secuencialmente.

---

## 6. Evaluar los resultados

### Paso 6.1 — Leer el reporte raw

```bash
cat cases/CASE-B1-BTC-ETF-JAN2024/model_output_raw/mirofish_report_raw.md
```

### Paso 6.2 — Completar `first_eval.md`

Para cada caso, crear `answer_key_post_x/first_eval.md` comparando predicción vs. ground truth:

```markdown
# First Eval — CASE-B1

## Tabla predicción vs. real

| Δ | Predicción MiroFish | Ground truth | Métrica | Resultado |
|---|--------------------|--------------|---------| ---------|
| Δ1 (1 día) | $XX,XXX | $44,900 | Error abs % | PASS/FAIL |
| Δ2 (3 días) | $XX–$XX | $43,500 | ¿Real en rango? | PASS/FAIL |
| Δ3 (1 sem) | dirección + bucket | bajista mod. | Dirección correcta | PASS/FAIL |
| Δ4 (1 mes) | sentimiento | neutro/alcista | Solo dirección | PASS/FAIL |

## Veredicto
Score: X/4

## Análisis
[¿Captó la dinámica sell-the-news? ¿Cuál fue el mecanismo causal que citó?]
```

### Criterios de evaluación (pre-registrados en `answer_key_post_x/ground_truth.md`)

**B1:**
| Δ | Umbral PASS |
|---|------------|
| Δ1 | Error absoluto precio puntual ≤ 10% |
| Δ2 | Precio real dentro del rango; rango ≤ $6,000 de ancho |
| Δ3 | Dirección bajista (hard criterion) + bucket mod. −5–15% |
| Δ4 | Dirección neutro/alcista a 1 mes |

**B2:**
| Δ | Umbral PASS |
|---|------------|
| Δ1 | Error absoluto IPC mensual ≤ 1.5pp |
| Δ2 | Real cae en rango predicho; rango ≤ 4pp de ancho |
| Δ3 | Bucket correcto (moderada 2–4%) |
| Δ4 | Acumulada 2025 en rango 30–40% |

---

## 7. Diagnóstico de errores comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `Connection refused localhost:5001` | Backend no está corriendo | `npm run backend` en otra terminal |
| `MiroFishRunnerError: graph task ended with status failed` | Neo4j no disponible o Graphiti error | Verificar `docker ps` y logs de backend |
| `MiroFishRunnerError: HTTP 413` | Seed bundle demasiado grande | Reducir fuentes o usar solo `seed_bundle.md` |
| `TimeoutError: graph task polling timed out` | LLM demasiado lento | Aumentar `--poll-timeout 7200` |
| `status: BLOCKED` en manifest | Cualquier error de API | Revisar `reason` en `run_manifest.json` |
| Gemini 429 rate limit | Demasiados requests | Agregar segunda API key o esperar |

---

## 8. Flags útiles del runner

```bash
# Smoke test (1 ronda, verificar que todo conecta)
python tools/mirofish_headless.py \
  --file cases/CASE-B1-BTC-ETF-JAN2024/input_pack_pre_x/seed_bundle.md \
  --requirement "Haz una predicción corta de BTC." \
  --max-rounds 1 \
  --output-dir /tmp/smoke_test_b1

# Sin actualización de memoria de grafo (más rápido, sin persistencia)
python tools/mirofish_headless.py \
  --file ... --requirement "..." \
  --no-graph-memory-update \
  --output-dir ...

# Aumentar timeout si la simulación es lenta
python tools/mirofish_headless.py \
  --file ... --requirement "..." \
  --poll-timeout 7200 \
  --output-dir ...
```

---

## 9. Checklist de aceptación (del plan original)

- [x] Branch `feat/case-b-backtesting` creado
- [x] `origin/chore/pilot-arg-2025-q1-artifacts` mergeado — runner disponible
- [x] Todos los archivos pre-registro commiteados antes de correr
- [x] B1 `input_pack_pre_x/` con 8 fuentes fechadas ≤ 9 ene 2024
- [x] B2 `input_pack_pre_x/` reutiliza fuentes del piloto
- [ ] `model_output_raw/` contiene output real del headless runner (B1)
- [ ] `model_output_raw/` contiene output real del headless runner (B2)
- [ ] `answer_key_post_x/ground_truth.md` confirmado post-run
- [ ] `first_eval.md` completado con tabla predicción vs. real (B1)
- [ ] `first_eval.md` completado con tabla predicción vs. real (B2)
- [ ] Curva de degradación analizada: ¿baja precisión al aumentar Δ?
