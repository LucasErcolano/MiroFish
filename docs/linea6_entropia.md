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

### Caveats metodológicos (importantes)

- **La entropía categórica solo es válida con generación de perfiles por LLM.**
  En `oasis_profile_generator.py`, `mbti`/`gender`/`country` salen del LLM cuando
  `use_llm=True` (camino de producción), pero el fallback `_generate_profile_rule_based`
  los asigna con `random.choice`. Con el fallback, la entropía categórica mide el
  RNG, no el modelo. Correr siempre con generación por LLM activada.
- **Para comparar modelos (Fase 2), las métricas de texto son el discriminador
  más fuerte.** Los campos derivados de entidades (`profession`/`country`/`topics`)
  vienen de las mismas entidades del seed en los 3 modelos, así que la entropía
  categórica puede moverse poco entre modelos. La señal que mejor discrimina entre
  modelos es la diversidad del **texto** (`persona`/`bio`): **Vendi Score** y
  **Self-BLEU/distinct-n**. La entropía categórica lidera la **selección de caso**
  (Fase 1, un solo modelo), donde sí varía caso a caso.

## 4. Herramientas

Biblioteca: `backend/app/research/entropy/` (métricas primarias en stdlib puro,
sin red; embeddings opcionales con numpy + embedder).

| CLI | Para qué |
|---|---|
| `backend/scripts/entropy_persona_analysis.py` | Diversidad entre personas + ranking de casos (Fase 1). |
| `backend/scripts/entropy_checkpoint_interview.py` | Entrevistas inicio/mitad/final + reporte de deriva (Fase 2, D3/D4). |
| `backend/scripts/export_run_bundle.py` | Export del dataset pregunta→planning→resultado (PD). |
| `backend/scripts/entropy_smoke.py` | Smoke end-to-end de todo el pipeline sobre datos sintéticos (sin red). |
| `scripts/run_linea6_trimodel_model_map.py` | Dry-run sin keys y ejecución paga para Qwen/Gemma/Llama dentro de una misma simulación vía `model_map_path`. |
| `scripts/extract_semantic_variance_metrics.py` | Extracción offline de varianza semántica/cluster entropy desde runs existentes con embeddings locales Ollama. |

## 4.1. Extensión trimodel vía model map

La variante incremental de Linea 6 ya no requiere tres corridas single-model
para todo: puede asignar Qwen, Gemma y Llama en una misma simulación Reddit con
un `model_map_path` generado por agente. El template manual vive en
`backtesting/case-b-s2-bolivia-2025-runoff/model_map_linea6_trimodel_template.yaml`.

Smoke sin keys:

```bash
python scripts/run_linea6_trimodel_model_map.py --out-root outputs/linea6_trimodel_dry_run
```

Ejecución paga, con backend propio y keys en env:

```bash
python scripts/run_linea6_trimodel_model_map.py --execute --start-backend --rounds 48
```

## 5. PD — Export de dataset (pregunta + planning + resultado)

Persiste cada corrida como un registro normalizado **prompt → plan → completion**
para dataset de entrenamiento / fine-tuning (JSONL, hasheado y deduplicado):

- `input.question`: el `simulation_requirement` + procedencia del seed (hashes de
  archivos, opcional el `extracted_text`).
- `plan`: el planning del modelo (razonamiento de config, time/event config,
  distribuciones de agent_configs, **las personas generadas completas**, outline
  del reporte). Las personas se embeben por defecto; `--no-personas` las omite
  para registros más chicos.
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

## 10. Bitácora de ejecución y selección de caso (run real)

### Fase 1 — smoke validado (DeepInfra, modelo exacto)

- Entorno real: Neo4j + backend Flask + Graphiti, `LLM_MODEL_NAME=google/gemma-3-27b-it`
  vía DeepInfra (OpenAI-compatible), embeddings `BAAI/bge-m3` (1024-dim).
- **Case A (Copa América, simple/autoverificable)** corrido end-to-end como smoke:
  ontología → grafo (Graphiti) → 17 personas → 1 ronda. Validó el pipeline completo
  **y** las métricas de Línea 6 sobre salida real de Gemma-3.
  - `n_personas=17`, `categorical_diversity_index=0.532`, `Self-BLEU=0.012`
    (≈0 → muy diversas), `distinct-2=0.965`, `Vendi(bge-m3)=3.735`.
  - Costo real: **~1¢**. El pipeline es barato; el presupuesto no es la restricción.

### Decisión: caso de comparación = **Case C (balotaje Bolivia 2025)**

En vez de rankear empíricamente A/B/C por entropía de personas, se **eligió Case C
por diseño** como caso de comparación de modelos para la Fase 2. Razón:

- El objetivo de la Fase 2 es **discriminar entre modelos**; conviene el escenario
  donde los modelos **más divergen**.
- Case C es el más **rico y abierto** (politico-social, 8 fuentes, ≥20 entidades
  relevantes, múltiples hipótesis causales en competencia, documento distractor),
  así que maximiza la superficie de divergencia entre modelos.
- Case A (evento simple) y Case B (cuantitativo estructurado) son más acotados y
  dejan menos margen de divergencia inter-modelo.
- Pragmática: Case A costó ~1¢ y quedó como punto de referencia validado; correr
  B y C solo para rankear agrega tiempo con poco valor de decisión dado el
  argumento cualitativo claro a favor de C.

### Modelos para Fase 2 (exactos, idealmente un solo proveedor)

DeepInfra **no** sirve el `Qwen3-8B` exacto (su Qwen3 denso más chico es 14B). El
único proveedor con los **tres exactos** (`qwen/qwen3-8b`, `google/gemma-3-27b-it`,
`meta-llama/llama-3.3-70b`) es **OpenRouter**. Gemma-3 y Llama-3.3 también están en
DeepInfra. Plan: correr en DeepInfra lo posible (Gemma-3, Llama-3.3) y financiar
**OpenRouter** solo para `Qwen3-8B`.

### Profundidad de simulación

Las corridas reales de los compañeros usaron **10 rondas** (`max_rounds=10`,
`total_simulation_hours=72`, plataforma `parallel`, modelo `gemini-2.5-flash-lite`).

## 11. Fase 2 — Gemma SÍ corre la simulación end-to-end (corrección del hallazgo previo)

> **Corrección (2026-06-22).** Una versión anterior de esta sección afirmaba que la
> sim se "colgaba en la ronda 1" con modelos grandes (deadlock local de OASIS) y que
> C+D eran inobtenibles para gemma/llama. **Re-investigado con evidencia directa: era
> un falso positivo.** Gemma-3-27B corre la simulación completa sin colgarse. C+D SÍ
> son obtenibles para gemma. Lo que sigue documenta la causa real.

### Síntoma original y causa real

El proceso quedaba a ~2.8% CPU, conexiones a DeepInfra idle, sin avanzar → se
interpretó como deadlock. La evidencia decisiva está en el `simulation.log` del run
que quedó "colgado": `模拟循环完成` / **`总耗时: 0.0s`** / `进入等待命令模式`. O sea:

1. **0 agentes activados en las rondas tempranas.** Con `max_rounds` corto (6, 10) las
   rondas caen en horas 0–7 (off-peak, multiplicador 0.05; además los `active_hours`
   por agente arrancan en h8). La cuenta `int(uniform(3,5)·0.05) = 0` → **0 agentes/ronda**.
   El loop pasó todas las rondas vacías al instante (`总耗时: 0.0s`) sin una sola llamada LLM.
   Recién en hora 8+ se activan agentes (~1–2.4/ronda; ~5.5 en el pico nocturno h19–22).
2. **Modo espera-de-comandos.** El runner sin `--no-wait` entra en el loop IPC y queda
   idle haciendo polling (~2.8% CPU, sin red) **por diseño** — lo que se leyó como cuelgue.

### Reproducción (aislada, mismo path que usa el backend — subprocess de `run_reddit_simulation.py`)

| Caso | Agentes concurrentes | Resultado |
|---|---|---|
| A (Copa América) | 3 | ✅ 8.2s, platform limpio |
| C (Bolivia) | 15 | ✅ 20.8s |
| C — estrés | 40 | ✅ 31.0s |
| **C — run completo (gemma)** | `--max-rounds 48 --no-wait` | ✅ **339.6s, exit 0, env cerrado limpio** |
| **C — run completo (llama-3.3-70B)** | `--max-rounds 48 --no-wait` | ✅ **716.2s, exit 0, env cerrado limpio** |

Los runs completos generaron contenido real ejercitando 7 tipos de acción (refresh,
create_post, create_comment, like_post, like_comment, dislike_post, sign_up) **sin
crashear el platform**: gemma 18 posts + 16 comments (13 autores); llama 10 posts + 57
comments (32 autores). **Tanto gemma como llama corren end-to-end** → el viejo reclamo
"ambos modelos grandes cuelgan" queda refutado empíricamente.

> **Acotación honesta:** no se ejercitaron los 13 tipos de acción (faltan follow/mute/
> search/trend/do_nothing). La afirmación correcta es "gemma corre end-to-end un run
> completo de 48 rondas sin colgarse", no "ningún path de acción puede romper OASIS".

### Bug latente real arreglado: muerte silenciosa del `platform_task`

`OasisEnv.step()` hace `asyncio.gather()` **solo** sobre las corrutinas de agentes, NO
sobre `platform_task`. Si `platform.running()` crashea procesando una acción, los agentes
quedan esperando para siempre la respuesta del channel y la excepción se traga sin log
→ **cuelgue silencioso indistinguible del estado idle de arriba**. `run_reddit_simulation.py`
ahora registra `platform_task.add_done_callback(...)` que imprime el traceback del crash,
convirtiendo ese cuelgue silencioso en una falla diagnosticable.

### Plan actualizado para la comparación de 3 modelos

- **A+B+C+D para los 3 modelos directo** (ya no hace falta limitar C+D a un modelo chico).
  Correr por modelo: `LLM_MODEL_NAME=<modelo>` + `run_reddit_simulation.py --no-wait
  --max-rounds 48` (cubre h8→h23: mañana→trabajo→pico, el arco que C+D necesitan) →
  `entropy_phase2_analysis.py`. **Gemma y Llama-3.3-70B hechos** (C+D):
  `runs/linea6/phase2_{gemma,llama}_full.json` (pooled) + `_postsonly.json`.
  Qwen3-8B ya tiene un run 2026-07-05 por el flujo backend original vía
  OpenRouter (`sim_e1c334c38a0c`): 48 rondas exit 0, 74 posts / 96 comments /
  361 trace / 19 users, analizado en
  `runs/linea6/phase2_qwen3_8b_original_partial_graph.json`. Caveat: Graphiti
  procesó 6/7 chunks antes de timeout, así que el grafo es parcial aunque la
  simulación y el análisis sí terminaron.

  **Señal inter-modelo limpia = composición de acciones** (de la `trace` table, sin artefactos):
  llama comenta abrumadoramente (**57 comments / 10 posts**), gemma postea (**18 posts / 16 comments**).
  Divergencia conductual clara en la selección de acción.

  **Diversidad de texto (C): ojo con el confound de composición.** La métrica `output_diversity`
  poolea posts+comments; los comments cortos/reactivos sobre un mismo tema solapan n-gramas casi
  sin importar el modelo. El gap pooled (gemma Self-BLEU 0.304 vs llama **0.903**) era **mayormente
  artefacto** (llama 85% comments). **Solo-posts** (`--no-comments`) el gap se achica mucho:
  gemma Self-BLEU 0.264 / distinct-2 0.752 vs llama 0.412 / 0.614 → llama algo más repetitivo,
  gap modesto. Muestra chica (10–18 posts) → preliminar. (Vendi posts-only 4.55 vs 3.61 está
  confundido por N: gemma tiene 18 posts, llama 10.)
- ⚠️ El run de llama reusó las personas de gemma (sim dir copiado) → su métrica **A** es la de
  gemma. Para un A limpio de llama: re-`prepare` con grafo propio. C (texto/acciones) sí es de llama.
- **Deriva temporal (D) NO es confiable con estos runs cortos:** solo-posts gemma tiene 2 personas
  con ≥2 posts y llama 0 (la métrica necesita ≥2 por autor). Para D hace falta un run más
  largo / más activo (más rondas en horas pico, o subir actividad sin cambiar el diseño del caso).

> Estado operativo y pasos para retomar: `runs/linea6/HANDOFF.md`.

## 12. Multi-provider paralelo (Prompture, 2026-07-05)

- `backend/app/utils/llm_client.py` ya aceptaba el formato `provider/model`
  (e.g. `openrouter/qwen/qwen3-8b`) cuando `prompture` está instalado. Esta sesión
  lo activó: `uv pip install 'prompture>=0.1.0'` dentro de `backend/.venv` (la
  dep sigue comentada en `requirements.txt`; instalarla es opt-in).
- Smoke de los 3 modelos contra OpenRouter via Prompture:
  - gemma `{"ok": true, "model": "gemma"}` 4.7s
  - llama `{"ok": true, "model": "llama"}` 2.8s
  - qwen `{"ok": true, "model": "qwen"}` 4.9s
- 3 backends paralelos en puertos 5010/5011/5012, cada uno con
  `LLM_MODEL_NAME=openrouter/<modelo>`, `LLM_BASE_URL=""` (Prompture pone el
  endpoint según provider), `GRAPHITI_LLM_BASE_URL=https://openrouter.ai/api/v1`
  y `GRAPHITI_LLM_MODEL=<modelo crudo>` para que el cliente OpenAI-compatible
  de Graphiti pueda llamarlo. Driver: `scripts/run_linea6_multiprovider_parallel.py`.
- Resultado del run (loop de 48 rondas, plataforma `reddit`):
  - `sim_6e49710b43e8` (gemma): 32 agentes, 2 posts, 0 comments, 80 trace.
    Gemma cerró las 48 rondas pero sólo escribió 2 posts — 27 retries 429
    en agent-config-gen. cat_div 0.859, output distinct-2 0.952, Self-BLEU 0.001,
    Vendi 1.285 (N chica).
  - `sim_8633c5a63557` (qwen): 25 agentes, 6 posts, 42 comments, 129 trace.
    Graphiti 5/7 batches (429 storm), pero la sim prosiguió con grafo parcial.
    cat_div 0.820, output distinct-2 0.430, Self-BLEU 0.641, Vendi 4.439.
  - `sim_9ef534050066` (llama): 26 agentes, 9 posts, 28 comments, 170 trace.
    cat_div 0.840, output distinct-2 0.271, Self-BLEU 0.819, Vendi 4.923.
- **Lectura:** la **dirección C+D se conserva**: llama < qwen < gemma en
  diversidad pooled (gemma queda con N=2 posts, así que su ventaja sobre
  qwen/llama no es concluyente en este set; el corte con Qwen/llama sigue
  mostrando a llama como el menos diverso). Drift endpoint-distance
  similar a lo previo: llama 0.266 > qwen 0.225, mismo orden que las
  corridas 1-a-1. Artefactos en `runs/linea6/multiprovider_parallel_20260705_184644/`.
- Cambios de código:
  - `backend/app/config.py`: `load_dotenv(override=True)` → `override=False` para
    que los process envs (FLASK_PORT/LLM_MODEL_NAME/GRAPHITI_*) ganen sobre .env
    en corridas multi-proceso. Crítico: sin esto, 3 backends con distintos
    `LLM_MODEL_NAME` no podían coexistir.
  - `backend/app/services/graph_builder.py`: `TimeoutError` cuenta como
    retryable aunque venga sin mensaje; el log ahora muestra `type(e).__name__`.
  - `backend/scripts/run_reddit_simulation.py` y `run_parallel_simulation.py`
    normalizan `openrouter/<modelo>` → `<modelo>` + `LLM_BASE_URL=openrouter` antes
    de instanciar el modelo CAMEL (que sólo entiende OpenAI-compatible).
  - `tools/mirofish_headless.py`: flag `--graph-chunk-size` que se traduce a
    `chunk_size` en `POST /api/graph/build`. Sin esto, el headless pisa 500
    chars y 59 batches por modelo se atragantan.
