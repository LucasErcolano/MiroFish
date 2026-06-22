# Línea 6 — Comparación de modelos: Gemma-3-27B vs Llama-3.3-70B (Issue #28)

> Caso C (balotaje Bolivia 2025). Resultado de la sesión 2026-06-22. Qwen3-8B
> pendiente (sin crédito OpenRouter). **Hallazgo clave: NO hay deadlock de OASIS;
> ambos modelos grandes corren la sim completa.** Diagnóstico en `linea6_entropia.md` §11.
> (Los artefactos `.json` de métricas, los sim dirs y `prepare_only_AB.py` referenciados acá
> viven en `runs/linea6/` — local/gitignored; este doc de síntesis sí se versiona.)

## Qué se mantuvo constante vs qué varía

- **Constante**: grafo (`mirofish_ddd25234e70a42a0`), proyecto/requirement (`proj_3954cf6591cd`,
  balotaje Bolivia), document_text, locale **es**.
- **Varía**: solo el modelo (`LLM_MODEL_NAME`).
- **Cómo**: A+B vía `prepare` (personas + planning). C + composición de acciones vía sim de
  48 rondas (`run_reddit_simulation.py --max-rounds 48 --no-wait`). D no es confiable acá.

## A — Diversidad entre personas (prepare, español)

| Métrica | Gemma #1 | Gemma #2 | Llama | Lectura (vs jitter gemma-gemma) |
|---|---|---|---|---|
| `categorical_diversity_index` | 0.753 | 0.789 | 0.808 | **dentro del ruido** (jitter ~0.036 ≈ gap) |
| persona **Self-BLEU** (↓ = diverso) | 0.436 | 0.437 | 0.459 | casi igual (gemma reproduce clavado; llama apenas más repetitivo) |
| persona **Vendi** (bge-m3) | 8.36 | 8.48 | 9.22 | **probablemente real**: gap ~0.8 ≈ 6× el jitter (~0.13) → llama personas algo más diversas |
| largo medio de persona (chars) | ~4664 | ~4718 | ~1450 | **ROBUSTO (~3×, jitter ~1%): gemma escribe personas mucho más largas** |

Fuentes: `phase2_gemma_full.json` (gemma #1, run original headless), `phase2_gemma_standalone_es.json`
(gemma #2, standalone — 2da muestra para varianza), `phase2_llama_cleanAB_es.json` (llama, standalone).

> **Chequeo de varianza (hecho):** gemma se regeneró con el MISMO pipeline standalone como 2da
> muestra. Las dos corridas de gemma reproducen muy parejo (Self-BLEU 0.436/0.437, Vendi 8.36/8.48,
> len 4664/4718), lo que da una regla de ruido. Conclusión: **largo de persona** y **Vendi** son
> diferencias reales entre modelos; **cat_div** y **Self-BLEU** quedan dentro del ruido.
> (Nota: la 2da corrida de gemma murió durante el config-gen [4/6] — probable OOM por procesos
> acumulados — pero las 44 personas ya estaban generadas, que es todo lo que el chequeo de A necesita.)

> ⚠️ **Self-BLEU 0.000 fue un artefacto.** Un primer prepare de llama salió en **chino**
> (el driver standalone no seteaba locale → default `zh`); el Self-BLEU de texto chino
> (sin espacios) colapsa a ~0 por tokenización, no por diversidad real. Corregido con
> `set_locale('es')`. **Lección: cualquier prepare standalone debe fijar el locale es.**

## B — Planning (config generado por el modelo)

| | Gemma-3-27B | Llama-3.3-70B |
|---|---|---|
| stance distribution | neutral 30 / sup 9 / opp 4 / obs 1 | neutral 27 / sup 11 / opp 4 / obs 2 |
| `generation_reasoning` (chars) | 627 | 1157 |

Ambos mayormente neutrales. `reasoning_chars` es **inestable** (la corrida zh dio 220) → no
sobre-interpretar como señal de modelo.

## C — Diversidad de salida (sim de 48 rondas, cada modelo sobre SUS personas)

**Dirección consistente: los posts de llama son menos diversos que los de gemma, en TODOS los
cortes medidos** (pooled, posts-only, N-igual; sobre personas de gemma y propias de llama).

| Métrica (posts-only, **N=18 c/u**) | Gemma | Llama |
|---|---|---|
| distinct-2 (↑ = diverso) | 0.752 | 0.254 |
| Self-BLEU (↓ = diverso) | 0.264 | 0.822 |

Sims: `sim_d0caf4b44174` (gemma, 18 posts / 1 día / 30-min-ronda) y `sim_f1d62eb2d5f1`
(llama, 50 posts / 2 días / 60-min-ronda, su `time_config`).

> **Acotación honesta (el "~3×" NO es limpio):**
> - **equal-N ≠ equal-context.** Submuestreé a N=18 (saca el confound de *cantidad*), pero los 18
>   de llama salen de una conversación más larga/densa sobre una pregunta binaria angosta
>   ("¿Paz o Quiroga?") → el eco sube por densidad de conversación, no solo por modelo. La
>   *magnitud* (3×) no es separable de la asimetría de longitud de run.
> - **Sin regla de varianza.** A diferencia de A (2 muestras de gemma), C es **una corrida por
>   modelo**. La credibilidad está en el tamaño de efecto + dirección consistente, no en repetición.
> - **Sin mecanismo.** Tensión real medida: las **personas** de llama son MÁS diversas (Vendi 9.2
>   vs 8.4) pero sus **posts** MENOS → NO es "personas homogéneas → posts repetitivos". Claim
>   descriptivo (end-to-end, los posts de llama convergen más), sin causa atribuida.
> - El **único corte limpio** sería correr gemma con el mismo `time_config` de 2 días (ver §D).

## Composición de acciones — la señal inter-modelo MÁS limpia (sin pooling)

De la `trace` table de cada sim de 48 rondas (mismas personas de gemma, solo cambia el modelo):

| Acción | Gemma | Llama |
|---|---|---|
| create_post | 18 | 10 |
| create_comment | 16 | **57** |
| like_post | 12 | 12 |
| like_comment | 7 | 3 |
| dislike_post | 1 | 2 |
| refresh | 120 | 120 |

**Llama comenta abrumadoramente; gemma postea** (~3.5× en comments, ~2× en posts). Divergencia
conductual clara en la selección de acción — no es artefacto de pooling ni de longitud de texto.

> `refresh=120` idéntico en ambos NO es coincidencia: es una acción auto-inyectada por paso (de
> sistema), no una decisión del modelo. Las acciones de sistema se cancelan; la divergencia real
> está en las acciones **discrecionales** (posts/comments/likes), lo que refuerza el hallazgo.

## D — Deriva temporal intra-persona

**Ahora medible** con un run más largo. El run de llama clean-C (50 posts / 2 días) junta
suficientes posts por autor: **14 personas con deriva** posts-only (36 pooled), mean Self-BLEU
0.55, endpoint-dist 0.09 (deriva embedding chica inicio→fin). El run de gemma (18 posts / 1 día)
solo tiene 2 personas con ≥2 posts → **no comparable a esta escala**.

> Para una D comparable entre modelos hace falta correr gemma con un `time_config` de escala
> similar (p.ej. forzar 2 días / 60-min-ronda). Pendiente.

## Resumen

- **Lo más sólido** (efectos grandes, dirección consistente): (1) ambos modelos corren la sim
  end-to-end (no había deadlock); (2) composición de acciones (llama comenta, gemma postea, ~3.5×);
  (3) gemma escribe personas **~3× más largas**; (4) **persona Vendi** mayor en llama (9.2 vs 8.4,
  gap ~6× el jitter, con regla de varianza).
- **Dirección clara, magnitud no limpia:** los **posts de llama son menos diversos** en todos los
  cortes (a N=18: distinct-2 0.25 vs 0.75, Self-BLEU 0.82 vs 0.26). Pero single-run y la magnitud
  se confunde con la densidad de conversación (run de 2 días vs 1) → no afirmar "~3×" como limpio.
- **Dentro del ruido (no concluir dirección):** `cat_div` (jitter ≈ gap) y persona Self-BLEU
  (gemma reproduce 0.436/0.437; llama 0.459, gap chico).
- **Pendiente:** Qwen3-8B (OpenRouter); C limpia de llama (sim sobre personas propias); D (runs largos).

## Artefactos

A+B (personas propias, español):
- `phase2_gemma_full.json` — gemma A+B+C+D (run original).
- `phase2_gemma_standalone_es.json` — gemma A (2da muestra, chequeo de varianza).
- `phase2_llama_cleanAB_es.json` — llama A+B limpio.

C+D (cada modelo sobre SUS personas):
- gemma: `phase2_gemma_full.json` / `phase2_gemma-3-27b_postsonly.json` (sim `sim_d0caf4b44174`).
- llama: `phase2_llama_cleanC.json` / `phase2_llama_cleanC_postsonly.json` (sim `sim_f1d62eb2d5f1`).
- (histórico, personas de gemma reusadas) `phase2_llama_full.json` / `_postsonly.json` (sim `sim_d0caf4b44174_llama`).

Driver reutilizable: `prepare_only_AB.py`. Comparación N-igual de C: ver §C (submuestreo a 18 posts).
