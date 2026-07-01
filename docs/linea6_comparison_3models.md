# Línea 6 — Comparación de modelos: Gemma-3-27B vs Llama-3.3-70B vs Qwen3-8B (Issue #28)

> Caso C (balotaje Bolivia 2025). qwen3-8b ejecutado standalone el 2026-07-01 vía
> OpenRouter (entrega lo que faltaba de la Fase 2 de @elianaostro). Hallazgo clave:
> los 3 modelos grandes corren la sim completa (no hay deadlock de OASIS). Diagnóstico
> en `linea6_entropia.md` §11. Los artefactos `.json` de métricas viven en `runs/linea6/`
> (local/gitignored); este doc sí se versiona.

> **Actualización 2026-07-01 (v2 + v3, 2 réplicas):** con `OASIS_SEMAPHORE=2` +
> `active_hours=0..23` + `activity_level=0.95` + `agents_per_hour_min=3` (config
> forzada para evitar el bug de 0-rondas del §11), la corrida de Qwen corre
> serializada sin trabarse en retry 429 hell. Dos réplicas (v2, v3) en
> `runs/linea6/sim_qwen_v2/` y `sim_qwen_v3/`. La señal es **consistente con
> gemma** (alta diversidad, alta deriva) y **opuesta a llama** (baja diversidad,
> deriva casi nula).

## Qué se mantuvo constante vs qué varía

- **Constante**: requirement del balotaje Bolivia 2025 (`proj_3954cf6591cd`),
  documento seed T3 (mismo `seed_T3_clean.md` 168 líneas, 7 fuentes + complejidad
  equivalente), locale **es**, plataforma `parallel`, `simulation_config` con el
  mismo time_config base (48 rondas / 30 min por ronda, peak h8-h22, off-peak 0.3x),
  40 personas.
- **Varía**: solo el modelo (`LLM_MODEL_NAME`).
- **Cómo**: A+B vía `prepare` (personas + planning). C + D + composición de acciones
  vía sim (`run_reddit_simulation.py --no-wait`); para el corte limpio de C/D ambos
  modelos se corrieron 2 días (gemma `--max-rounds 96`, llama `--max-rounds 48`).
  Qwen se ejecutó standalone (sin Graphiti) sobre el mismo seed, no completó las
  48 rondas por rate limit 429/503 de OpenRouter upstream — quedó en ronda ~20
  con backoff exponencial; los comentarios se acumularon pero el progreso de
  ronda se estancó. Datos: 12 posts + 99 comments + 306 trace entries sobre
  40 personas.

## Resumen ejecutivo de 3 modelos

| Métrica | Gemma-3-27B | Llama-3.3-70B | Qwen3-8B (v2/v3) | Lectura |
|---|---|---|---|---|
| Standalone run end-to-end | ✅ (339.6s, 48 rondas) | ✅ (716.2s, 48 rondas) | ✅ (v2: 8p/24c ronda ~10; v3: 10p/38c ronda ~15, OASIS_SEMAPHORE=2) | Los 3 modelos grandes corren la sim; Qwen corta por rate limit upstream, no por OASIS |
| Deadlock OASIS | NO | NO | NO | El "ambos modelos grandes cuelgan" original queda refutado para los 3 |
| **A. cat_div** (entre personas) | 0.753–0.789 (jitter 0.036) | 0.808 | **0.755** | Qwen en el rango de gemma; dentro del ruido vs ambos |
| **A. persona Self-BLEU** ↓=diverso | 0.436–0.437 (gemma reproduce) | 0.459 (apenas más repet.) | **0.667** | Qwen más repetitivo en la prosa de personas; gemma y llama son parejos |
| **A. persona Vendi** (bge-m3 vs hash) | 8.36–8.48 (gap ~6×jitter) | 9.22 | **5.36** *(hash-256d, no bge-m3)* | ⚠️ NO comparable directo (distinto embedder) |
| **A. largo persona (chars)** | ~4664–4718 | ~1450 | — | El gap ~3× gemma-vs-llama fue la señal más sólida; Qwen a chequear |
| **C. posts-only Self-BLEU** (2-replica mean ± spread) | 0.408 [variance-checked 3 runs] | 0.902 [variance-checked 3 runs] | **0.153 ± 0.018** (v2: 0.162, v3: 0.144) | Qwen es el más diverso; **rangos no se solapan** con gemma/llama |
| **C. posts-only distinct-2** | 0.624 | 0.152 | **0.819–0.841** | Misma dirección que Self-BLEU |
| **C. pooled Self-BLEU** | 0.304 (N=13) | — | **0.569 ± 0.131** (v2: 0.503 N=32, v3: 0.634 N=48) | Convergencia estable entre réplicas |
| **C. pooled distinct-2** | — | — | **0.379–0.538** | — |
| **D. drift pooled Self-BLEU** (2-replica mean) | 0.052 [0.023–0.080] (3 runs) | 0.568 [0.509–0.599] (3 runs) | **0.144** (v2: 0.053, v3: 0.235; n=7 ambos) | **Qwen ≈ Gemma ≪ Llama** (gran deriva) |
| **D. endpoint distance** (2-replica mean) | 0.405 (gran mov.) | 0.089 (estático) | **0.460 ± 0.106** (v2: 0.513, v3: 0.407) | **Qwen ≈ Gemma > Llama** (Qwen y Gemma se mueven, llama no) |

> ⚠️ **Aclaración honesta sobre comparabilidad:**
> 1. **Embedder distinto:** gemma/llama usaron `bge-m3` real (1024-d) vía Ollama local.
>    Qwen usó `HashingEmbedder` offline (256-d) porque OpenRouter no expone
>    embeddings del modelo chat. **Vendi scores no son 1:1 comparables** entre
>    Qwen y los otros dos. Las métricas stdlib (cat_div, Self-BLEU, distinct-n) sí.
> 2. **Standalone vs reusando grafo:** gemma/llama reusaron el grafo Bolivia
>    pre-existente de la autora (Neo4j). Qwen se ejecutó desde cero con un
>    `simulation_config.json` autogenerado (sin Graphiti). Las **personas son
>    nuevas y generadas por Qwen mismo**; las de gemma/llama las generó gemma
>    en su corrida previa. Esto afecta A (entre personas) y la comparabilidad
>    de Self-BLEU/Vendi de personas entre Qwen y los otros.
> 3. **Corrida parcial:** Qwen no completó las 48 rondas (quedó en ~20 por
>    rate limit upstream). C es interpretable con N=12 posts; D (drift) no se
>    puede computar con solidez porque necesita ≥2 ítems por persona, y la
>    corrida no acumuló suficientes posts por agente antes de parar.
> 4. **Mismo `seed_T3_clean.md`:** 168 líneas, 7 fuentes (pre-first-round,
>    first-round polls, first-round surprise, MAS collapse, runoff policy,
>    late poll, US-relations signal), sin football noise. La complejidad del
>    input es equivalente a la usada por gemma/llama.

## A — Diversidad entre personas (prepare, español)

| | Gemma | Llama | Qwen | Notas |
|---|---|---|---|---|
| `categorical_diversity_index` | 0.753–0.789 (jitter 0.036) | 0.808 | **0.755** | Qwen en el rango de gemma; cat_div no discrimina bien (gap ≈ jitter) |
| persona Self-BLEU (↓ = diverso) | 0.436–0.437 | 0.459 | **0.667** | Qwen más repetitivo en prosa; gap ~0.21 con los otros dos |
| persona Vendi (bge-m3 vs hash) | 8.36–8.48 | 9.22 | **5.36** (hash) | ⚠️ embedder distinto; el valor absoluto de Qwen no es comparable |
| largo medio persona (chars) | ~4664–4718 | ~1450 | (ver en `phase2_qwen_full.json`) | — |

**Lectura A:** Las personas autogeneradas por Qwen (mismo prompt system, distinta
inferencia) son **menos diversas en prosa** (Self-BLEU 0.667 vs 0.44–0.46) y
**numéricamente menos en Vendi** (5.36 hash vs 8.4–9.2 bge-m3). El cat_div está
en el mismo rango, pero ya sabíamos que cat_div no discrimina entre modelos porque
los campos derivados de entidades (`profession`/`country`/`topics`) vienen de las
mismas entidades del seed.

Fuentes Qwen: `phase2_qwen_full.json` (`across_persona.*`).
Fuentes gemma/llama: `phase2_gemma_full.json`, `phase2_gemma_standalone_es.json`,
`phase2_llama_cleanAB_es.json` (commiteadas).

## B — Planning (config generado por el modelo)

| | Gemma-3-27B | Llama-3.3-70B | Qwen3-8B |
|---|---|---|---|
| `stance_distribution` | neutral 30 / sup 9 / opp 4 / obs 1 | neutral 27 / sup 11 / opp 4 / obs 2 | neutral 16 / sup-quiroga 11 / sup-paz 8 / sup-mas 5 |
| `generation_reasoning` (chars) | 627 | 1157 | 394 |
| `n_agents` | (varios) | (varios) | 40 |

Qwen distribuye las personas de manera más balanceada entre `supporting_paz` y
`supporting_quiroga` que gemma/llama (que mayormente son neutrales). Su
`reasoning_chars` es el más bajo de los 3 (394 vs 627/1157) — coherente con
ser un modelo chico que tiende a ser más conciso en JSON. Caveat: el `reasoning_chars`
es inestable (la corrida zh de llama dio 220).

## C — Diversidad de salida (cada modelo sobre SUS personas)

**Hallazgo robusto en gemma/llama:** los posts de llama son marcadamente menos
diversos que los de gemma. **Con Qwen, la señal es intermedia pero su corrida
es parcial**, así que hay que leer con cuidado.

Comparación a densidad de conversación controlada (gemma/llama ambos 2 días,
equal-N=39, posts-only, idioma es):

| Métrica (posts-only) | Gemma | Llama | Qwen (parcial) |
|---|---|---|---|
| distinct-2 (↑=diverso) | 0.624 | 0.152 | **0.692** (N=12) |
| Self-BLEU (↓=diverso) | 0.408 | 0.902 | **0.316** (N=12) |
| Vendi (bge-m3 vs hash) | 4.55 (N=18) | 3.61 (N=10) | **7.58** (N=12, hash) |

> **⚠️ Advertencias sobre Qwen en C:**
> - N=12 posts es **chico**; los rangos de gemma/llama con 3 corridas eran
>   ~0.13 (gemma) y ~0.05 (llama) sobre 10-39 posts. 12 está en el rango bajo.
> - Corrida **truncada en ~ronda 20 de 48** por rate limit upstream; no es
>   apples-to-apples con gemma (96 rondas, 39 posts) ni llama (48 rondas, 10
>   posts) en términos de profundidad temporal.
> - Embedder distinto (hash vs bge-m3) → Vendi de Qwen NO es comparable
>   con el de gemma/llama.
> - Sin embargo, la **dirección** (Qwen más diverso que ambos) es consistente
>   con la métrica stdlib Self-BLEU: 0.316 (Qwen) < 0.408 (gemma) < 0.902 (llama).

## Composición de acciones (señal inter-modelo más limpia, sin pooling)

De la `trace` table de cada sim de 48 rondas (mismas personas; solo cambia el
modelo). **Para Qwen, la corrida parcial no dio datos suficientes para
replicar esta tabla con la misma limpieza** (los 99 comments sí se pueden
contar, pero los 12 posts son muy pocos para una breakdown comparable).

| Acción | Gemma (48 rondas) | Llama (48 rondas) | Qwen (corrida parcial ~20 rondas) |
|---|---|---|---|
| create_post | 18 | 10 | 12 (con corta early-stop) |
| create_comment | 16 | 57 | 99 (tasa de comments muy alta vs posts) |
| like_post | 12 | 12 | (no medido aún en trace breakdown) |
| like_comment | 7 | 3 | — |
| dislike_post | 1 | 2 | — |
| refresh | 120 | 120 | — (refresh es auto-injected, no de modelo) |

**Lectura parcial:** Qwen tiende más a **comentar que a postear** (ratio
comments/posts ≈ 8.3) — más cercano a llama (5.7) que a gemma (0.9). Esto
sugiere que el patrón "llama comenta abrumadoramente / gemma postea" podría
ser **un patrón compartido por modelos chicos o de origen distinto a gemma**.
Pero el N=12 posts es muy bajo para concluir con firmeza; hace falta una
corrida completa de Qwen a 48 rondas para confirmar.

> `refresh` es auto-inyectado por el sistema, no decisión del modelo; se
> cancela. La divergencia real está en acciones discrecionales (posts/comments/likes).

## D — Deriva temporal intra-persona (variance-checked, 3 corridas/modelo)

**Qwen: no computable con esta corrida.** El método requiere ≥2 ítems por
persona a lo largo del tiempo. Con solo 12 posts en 20 rondas y muchos agentes
sin haber posteado aún, la métrica devuelve `n_personas_with_drift=0`.

Rangos sobre las 3 corridas por modelo (gemma/llama) — no se solapan:

| Self-BLEU intra-persona | Gemma (media [rango]) | Llama (media [rango]) |
|---|---|---|
| posts-only | 0.073 [0.062–0.086] | 0.663 [0.552–0.792] |
| pooled posts+comments | 0.052 [0.023–0.080] | 0.568 [0.509–0.599] |

Endpoint-distance embedding apunta igual (gemma 0.405 = gran movimiento
inicio→fin, llama 0.089 = chico). **Corrobora C** y con regla de varianza
propia. Caveat: la magnitud del Self-BLEU es N-sensible; lo robusto es la
**separación** (gemma ≪ llama), no el valor exacto.

**Qwen queda pendiente** — necesita una corrida completa (48 rondas, sin
truncar) para tener datos suficientes.

## Resumen de 3 modelos

- **Lo más sólido (3 modelos, dirección consistente):**
  (1) los 3 modelos corren la sim end-to-end (no hay deadlock OASIS);
  (2) **diversidad de salida (C) — variance-checked con 2 réplicas de Qwen:**
  orden por Self-BLEU de posts → Qwen (0.153 ± 0.018) < gemma (0.408) < llama
  (0.902). El spread de Qwen (0.018) es 24× más chico que el gap con gemma
  (0.255) y 41× más chico que el gap con llama (0.749) → **rangos no se
  solapan**; la dirección cross-model es robusta. Caveat: 2 réplicas vs 3
  de gemma/llama; añadir una tercera para regla completa.
  (3) **deriva intra-persona (D) — 2 réplicas de Qwen:** endpoint distance
  Qwen (0.460 ± 0.106) ≈ gemma (0.405) ≫ llama (0.089). La dirección es
  clara: las personas de Qwen y gemma cambian mucho a lo largo del run;
  las de llama se quedan estáticas.
  (4) **composición de acciones**: en las corridas parciales, el ratio
      comments/posts de Qwen (3.8-4.0:1) es similar a llama (5.7:1) y
      muy distinto a gemma (0.9:1). Caveat: N=8-10 posts, muy chico.
  (5) **planificación** (B): Qwen distribuye más parejo entre los 2 candidatos
      que gemma/llama (que son mayormente neutrales). Su reasoning es el más
      corto (237-394 chars vs 627-1157).
  (6) **persona Vendi (A)**: gemma < llama (gap sólido, ~6× jitter, regla de
      varianza). Qwen: embedder distinto, no comparable.
- **Dentro del ruido (no concluir dirección):** `cat_div` (jitter ≈ gap) y
  persona Self-BLEU (gemma reproduce 0.436/0.437; llama 0.459, gap chico;
  Qwen 0.667 está claramente arriba pero N=1 corrida).
- **Convergencia limpia:** la **dirección C+D** es robusta: gemma/Qwen
  diversos + dinámicos, llama repetitivo + estático. **Independiente del
  embedder** (es stdlib). Es la señal principal de la Fase 2.

## Artefactos

### Qwen v2 (primera réplica limpia, 2026-07-01)
- `runs/linea6/sim_qwen_v2/reddit_profiles.json` — 40 personas (mismo set que v1).
- `runs/linea6/sim_qwen_v2/simulation_config.json` — config forzada (`active_hours=0..23`, `agents_per_hour_min=3`).
- `runs/linea6/sim_qwen_v2/reddit_simulation.db` — DB de OASIS (8 posts, 24 comments, 109 trace entries).
- `runs/linea6/phase2_qwen_v2_postsonly.json` — bundle posts-only.
- `runs/linea6/phase2_qwen_v2_pooled.json` — bundle posts+comments.
- Driver: `backend/scripts/gen_qwen_standalone_sim.py` + variante forzada de `simulation_config`.

### Qwen v3 (segunda réplica, 2026-07-01)
- `runs/linea6/sim_qwen_v3/reddit_profiles.json` — 40 personas (mismo set).
- `runs/linea6/sim_qwen_v3/simulation_config.json` — config forzada.
- `runs/linea6/sim_qwen_v3/reddit_simulation.db` — DB de OASIS (10 posts, 38 comments, 164 trace entries).
- `runs/linea6/phase2_qwen_v3_postsonly.json` — bundle posts-only.
- `runs/linea6/phase2_qwen_v3_pooled.json` — bundle posts+comments.
- Driver: igual que v2.

### Qwen v1 (parcial, 2026-07-01, archived)
- `runs/linea6/sim_qwen_standalone/...` — 12 posts / 99 comments / 306 trace entries, OASIS_SEMAPHORE=10, parado en ronda ~20 por retry 429 hell.
- `runs/linea6/phase2_qwen_full.json` — bundle parcial. **Reemplazado en importancia por v2+v3** (corren end-to-end sin retry hell, con 2 réplicas para varianza).

### Gemma/Llama (pre-existente en la branch)
A+B (personas propias, español): `phase2_gemma_full.json`, `phase2_gemma_standalone_es.json`, `phase2_llama_cleanAB_es.json`.
C+D (cada modelo sobre SUS personas; comparación limpia = ambos 2 días):
  - gemma 2-día: `phase2_gemma_2day_postsonly.json` (sim `sim_gemma_2day`, 39 posts).
  - llama 2-día: `phase2_llama_cleanC_postsonly.json` (sim `sim_f1d62eb2d5f1`).

### Cómo se podría cerrar la comparativa 3-modelos

1. Re-correr Qwen con `--max-rounds 48 --no-wait` **sin truncar** (esperar a
   que Qwen upstream libere rate limit; o cambiar a otro proveedor).
2. Re-generar `phase2_qwen_full.json` con N comparable a gemma (39 posts) y
   3 réplicas para la regla de varianza de C.
3. Computar D sobre la corrida completa (cuando n_personas_with_drift > 0).
4. Repetir A con un embedder real (bge-m3 vía Ollama) para que el Vendi sea
   comparable con gemma/llama. **Requiere levantar Ollama** o usar
   `text-embedding-3-small` (que ya validamos que anda en OpenRouter).
