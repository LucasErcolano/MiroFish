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
- **Cómo**: A+B vía `prepare` (personas + planning). C + D + composición de acciones vía sim
  (`run_reddit_simulation.py --no-wait`); para el corte limpio de C/D ambos modelos se corrieron
  **2 días** (gemma `--max-rounds 96`, llama `--max-rounds 48` por su `time_config` de 60-min).

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

## C — Diversidad de salida (cada modelo sobre SUS personas)

**Hallazgo robusto: los posts de llama son marcadamente menos diversos que los de gemma.**
Comparación **limpia** — ambos modelos corridos **2 días** (misma densidad de conversación),
**equal-N=39**, posts-only, personas propias, idioma es:

| Métrica (posts-only, **N=39 c/u, ambos 2 días**) | Gemma | Llama |
|---|---|---|
| distinct-2 (↑ = diverso) | 0.624 | **0.152** |
| Self-BLEU (↓ = diverso) | 0.408 | **0.902** |

Sims: `sim_gemma_2day` (gemma, 39 posts / 96 rondas / 30-min) y `sim_f1d62eb2d5f1`
(llama, 50 posts / 48 rondas / 60-min). El gap (~4× distinct-2, ~2.2× Self-BLEU) **persiste en
TODOS los cortes** (1 día, 2 días, equal-N; personas de gemma y propias de llama).

> **Por qué esto SÍ es limpio (a diferencia del primer corte):**
> - **Densidad de conversación controlada.** El confound era real: gemma a 1 día/18 posts daba
>   Self-BLEU 0.264, pero a 2 días/39 posts sube a 0.408 (conversación más larga → más eco, sin
>   importar el modelo). Con ambos a 2 días el confound se neutraliza y el gap **persiste**.
> - **Conservador:** gemma corrió 96 rondas (vs 48 de llama) → MÁS oportunidades de eco, y aún
>   así es más diverso. Si algo, subestima el gap.
> - **Sin regla de varianza** (a diferencia de A): una corrida por modelo. La credibilidad está en
>   el tamaño de efecto grande + dirección consistente en todos los cortes, no en repetición.
> - **Sin mecanismo.** Tensión real: las **personas** de llama son MÁS diversas (Vendi 9.2 vs 8.4)
>   pero sus **posts** MENOS → NO es "personas homogéneas → posts repetitivos". Claim descriptivo
>   (end-to-end, los posts de llama convergen más), sin causa atribuida.

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

## D — Deriva temporal intra-persona (ambos 2 días, posts-only)

**Corrobora C: las personas de gemma derivan más en el tiempo; las de llama son más estáticas.**

| | Gemma 2d | Llama 2d |
|---|---|---|
| personas con ≥2 posts | 6 | 14 |
| Self-BLEU intra-persona (↓ = más deriva) | **0.086** | 0.552 |
| endpoint-dist embedding (↑ = más deriva) | **0.405** | 0.089 |

Gemma cambia mucho lo que dice una misma persona a lo largo del run (Self-BLEU bajo, gran
movimiento embedding inicio→fin); llama repite más (Self-BLEU alto, deriva embedding chica) —
consistente con que la salida de llama es más repetitiva (C).

> Caveat: distinto N de personas con deriva (6 vs 14) y single-run. La dirección es consistente
> con C, no una medición independiente fuerte.

## Resumen

- **Lo más sólido** (efectos grandes, dirección consistente): (1) ambos modelos corren la sim
  end-to-end (no había deadlock); (2) **diversidad de salida**: posts de llama mucho menos
  diversos (a densidad pareja + N igual: distinct-2 0.62 vs 0.15, Self-BLEU 0.41 vs 0.90),
  corroborado por D (gemma deriva más en el tiempo); (3) composición de acciones (llama comenta,
  gemma postea, ~3.5×); (4) gemma escribe personas **~3× más largas**; (5) **persona Vendi** mayor
  en llama (9.2 vs 8.4, gap ~6× el jitter, con regla de varianza).
  - Caveats: C y D son **single-run** (sin regla de varianza como A); la dirección es consistente
    en todos los cortes pero la magnitud exacta no está validada por repetición.
- **Dentro del ruido (no concluir dirección):** `cat_div` (jitter ≈ gap) y persona Self-BLEU
  (gemma reproduce 0.436/0.437; llama 0.459, gap chico).
- **Pendiente:** Qwen3-8B (bloqueado por crédito OpenRouter). Repetir runs para varianza de C/D.

## Artefactos

A+B (personas propias, español):
- `phase2_gemma_full.json` — gemma A+B+C+D (run original).
- `phase2_gemma_standalone_es.json` — gemma A (2da muestra, chequeo de varianza).
- `phase2_llama_cleanAB_es.json` — llama A+B limpio.

C+D (cada modelo sobre SUS personas; comparación limpia = ambos 2 días):
- gemma 2-día: `phase2_gemma_2day_postsonly.json` (sim `sim_gemma_2day`, 39 posts) — **el corte limpio**.
- gemma 1-día: `phase2_gemma_full.json` / `phase2_gemma-3-27b_postsonly.json` (sim `sim_d0caf4b44174`).
- llama 2-día: `phase2_llama_cleanC.json` / `phase2_llama_cleanC_postsonly.json` (sim `sim_f1d62eb2d5f1`).
- (histórico, personas de gemma reusadas) `phase2_llama_full.json` / `_postsonly.json` (sim `sim_d0caf4b44174_llama`).

Driver reutilizable: `prepare_only_AB.py`. Comparación N-igual de C: ver §C (submuestreo a 18 posts).
