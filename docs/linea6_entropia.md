# Línea 6 — Diversidad y entropía de agentes (métricas intrínsecas de LLM)

> Issue #28. Cuarta línea de investigación. Mide el **funcionamiento intrínseco**
> de los LLM dentro de MiroFish con métricas de diversidad/entropía, para
> **comparar los 3 modelos** de forma cuantitativa y reproducible. No mide
> calidad predictiva (eso lo cubren las otras líneas + backtesting): mide cuánta
> variedad/estructura genera cada modelo al poblar y correr el mundo simulado.

## 1. Resumen

Dos preguntas:

1. **Entre personas** — ¿qué tan diversas son las personas/agentes que genera
   cada modelo?
2. **Intra-persona en el tiempo** — ¿cómo cambian las respuestas de una misma
   persona a lo largo de la simulación (inicio / mitad / final)?

Restricción dura: para comparar modelos usamos **solo métricas agnósticas al
modelo**. Nada de logprobs/perplexity como métrica principal (no todos los
proveedores los exponen de forma confiable). La entropía token-level queda como
extra opcional.

## 2. Diseño experimental (2 fases, separadas por costo)

### Fase 1 — Selección de caso (barata, solo `prepare`)

La generación de perfiles usa el `LLMClient` global (`LLM_MODEL_NAME`), **no** el
backend CAMEL por agente. Por eso esta fase **no corre la simulación completa**:
alcanza con `create` → `prepare` y leer los perfiles generados.

1. Configurar el modelo global = **Gemma-3-27B-it** (ver §6).
2. Correr `create` + `prepare` (vía `tools/mirofish_headless.py` o la UI) en los
   **3 casos**: A (#10), B (#11), C (#12).
3. Medir diversidad entre personas con `entropy_persona_analysis.py`.
4. **El caso con mayor `categorical_diversity_index` es el caso de comparación.**

```bash
python backend/scripts/entropy_persona_analysis.py \
  --case A=backend/uploads/simulations/<sim_A> \
  --case B=backend/uploads/simulations/<sim_B> \
  --case C=backend/uploads/simulations/<sim_C> \
  --with-embeddings --output runs/linea6/case_selection.json
```

### Fase 2 — Comparación de modelos (cara, corrida completa)

Sobre el caso elegido, correr la simulación completa **una vez por modelo**
(modelo global por corrida; no se usa el `model_map` por agente):

- Por cada modelo: repetir la diversidad entre personas (Fase 1) **y** medir la
  deriva intra-persona entrevistando a cada agente en inicio/mitad/final.

```bash
# 1) entrevistas por checkpoint (sim corriendo en background)
python backend/scripts/entropy_checkpoint_interview.py \
  --base-url http://localhost:5001 --simulation-id <sid> --platform twitter \
  --profiles backend/uploads/simulations/<sid>/twitter_profiles.csv \
  --total-rounds <N> --live \
  --responses-out runs/linea6/<model>_<sid>_responses.json

# 2) reporte de deriva temporal (offline)
python backend/scripts/entropy_checkpoint_interview.py \
  --analyze --responses-out runs/linea6/<model>_<sid>_responses.json \
  --report-out runs/linea6/<model>_<sid>_drift.json
```

## 3. Métricas

| Sub-pregunta | Métrica | Módulo | Notas |
|---|---|---|---|
| Entre personas | **Entropía de Shannon categórica** (mbti, gender, profession, country, age-bucket, topics) | `metrics.profile_categorical_report` | **Primaria**, sin embedder. Lidera la selección de caso vía `categorical_diversity_index` (media de entropía normalizada). |
| Entre personas | **Vendi Score** (nº efectivo de personas distintas) | `embeddings.vendi_score` | Secundaria. Embedder + numpy. |
| Entre personas | distinct-n, Self-BLEU, type-token ratio | `metrics`, `analysis.lexical_diversity` | Apoyo léxico sobre `persona`/`bio`. Self-BLEU es **inverso** (alto = repetitivo). |
| Intra-persona | **Self-BLEU** entre checkpoints | `temporal.temporal_drift_report` | Inverso de deriva, sin embedder. |
| Intra-persona | **Deriva de embeddings** (paso / longitud de camino / inicio→fin) | `temporal` + `embeddings.embedding_drift` | Embedder opcional. |
| Intra-persona | **Jensen-Shannon** de stance/sentimiento entre momentos | `temporal.stance_js_divergence` | El caller provee las etiquetas. |

Referencias: Vendi Score (Friedman & Dieng 2022), Semantic Entropy (Kuhn et al.
2023 / Farquhar et al. 2024), Self-BLEU, Distinct-n (Li et al. 2016).

## 4. Herramientas

Biblioteca: `backend/app/research/entropy/` (métricas primarias en stdlib puro,
sin red; embeddings opcionales con numpy + embedder).

| CLI | Para qué |
|---|---|
| `backend/scripts/entropy_persona_analysis.py` | Diversidad entre personas + ranking de casos (Fase 1). |
| `backend/scripts/entropy_checkpoint_interview.py` | Entrevistas inicio/mitad/final + reporte de deriva (Fase 2, D3/D4). |
| `backend/scripts/export_run_bundle.py` | Export del dataset pregunta→planning→resultado (PD). |
| `backend/scripts/entropy_smoke.py` | Smoke end-to-end de todo el pipeline sobre datos sintéticos (sin red). |

## 5. PD — Export de dataset (pregunta + planning + resultado)

Persiste cada corrida como un registro normalizado **prompt → plan → completion**
para dataset de entrenamiento / fine-tuning (JSONL, hasheado y deduplicado):

- `input.question`: el `simulation_requirement` + procedencia del seed (hashes de
  archivos, opcional el `extracted_text`).
- `plan`: el planning del modelo (razonamiento de config, time/event config,
  distribuciones de agent_configs, outline del reporte).
- `result`: el `full_report.md` + resumen del run_state.

```bash
python backend/scripts/export_run_bundle.py \
  --run-dir runs/headless/<run-id> \
  --out-bundle runs/headless/<run-id>/bundle.json \
  --dataset datasets/mirofish_runs.jsonl
```

## 6. Configuración de modelos

Los 3 modelos (de `configs/model_map_s2.yaml`). Para comparar a nivel corrida se
**cambia el modelo global** entre corridas (no hace falta routing por agente):

| Modelo | `LLM_MODEL_NAME` | Proveedor | `LLM_BASE_URL` (confirmar) | Key |
|---|---|---|---|---|
| Qwen3-8B | `qwen/qwen3-8b` | OpenRouter | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |
| Gemma-3-27B-it | `google/gemma-3-27b-it` | DeepInfra | `https://api.deepinfra.com/v1/openai` | `DEEPINFRA_API_KEY` |
| Llama-3.3-70B | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | DeepInfra | `https://api.deepinfra.com/v1/openai` | `DEEPINFRA_API_KEY` |

Fase 1 usa Gemma como modelo global. Ejemplo:

```bash
export LLM_BASE_URL='https://api.deepinfra.com/v1/openai'
export LLM_MODEL_NAME='google/gemma-3-27b-it'
export LLM_API_KEY="$DEEPINFRA_API_KEY"
```

## 7. Restricciones conocidas

- **Entrevistas mid-run**: existen vía la API HTTP `POST /api/simulation/interview[/batch]`
  (respaldada por IPC), pero **el headless runner no las expone**. Por eso el
  harness de checkpoints (D3) habla directo con esa API y requiere el **env de la
  simulación corriendo**.
  - **Fallback** si el timing en vivo no es confiable: `prepare` una vez, correr
    copias a `N/3`, `2N/3`, `N` rondas y llamar al harness con
    `--checkpoint start|mid|end` después de cada una (mismo `--responses-out`).
- La generación de perfiles usa el `LLMClient` global → Fase 1 fija el modelo con
  `LLM_MODEL_NAME`.
- Métricas de logprob/perplexity: solo opcionales y dependientes del proveedor.

## 8. Tests y smoke

Métricas (system python3 + numpy, sin venv ni red):

```bash
python3 -m unittest tests.test_entropy_metrics tests.test_run_bundle tests.test_checkpoints_temporal -v
```

Smoke end-to-end del pipeline (sin red):

```bash
python3 backend/scripts/entropy_smoke.py
```

> Nota: `tests/test_report_agent_resilience.py` requiere el entorno del backend
> (Flask) y se corre con `uv` adentro de `backend/`, no con el python del sistema.

## 9. Estructura

```
backend/app/research/
  entropy/
    metrics.py        # entropía/diversidad stdlib (primaria)
    embeddings.py     # Vendi / drift (numpy, opcional)
    embedder.py       # adapter real (EmbeddingClient) + fallback offline
    personas.py       # carga de *_profiles.(json|csv)
    analysis.py       # reporte entre personas + ranking de casos
    checkpoints.py    # plan + parseo + schema de entrevistas
    temporal.py       # deriva intra-persona
  dataset/
    run_bundle.py     # export pregunta→planning→resultado (PD)
backend/scripts/
  entropy_persona_analysis.py
  entropy_checkpoint_interview.py
  export_run_bundle.py
  entropy_smoke.py
tests/
  test_entropy_metrics.py
  test_run_bundle.py
  test_checkpoints_temporal.py
```
