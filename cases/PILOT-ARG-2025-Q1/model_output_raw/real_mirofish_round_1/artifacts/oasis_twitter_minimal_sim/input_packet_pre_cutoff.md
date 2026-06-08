# Frozen prompt (exact)

Usando exclusivamente los documentos provistos fechados hasta el 31 de enero de 2025, simulá la evolución político-económica argentina durante 2025.

Respondé en formato estructurado:

1. Predicción electoral:
- Rango nacional estimado de voto para LLA.
- Probabilidad de tres escenarios:
  A) LLA <35%
  B) LLA 35-42%
  C) LLA >42%
- Impacto esperado sobre Diputados/Senado y capacidad de blindar vetos.

2. Predicción macroeconómica:
- Rango estimado de inflación acumulada 2025.
- Probabilidad de tres escenarios:
  A) <30%
  B) 30-40%
  C) >40%

3. Mecanismo causal:
- Explicar qué variable domina la percepción pública.
- Explicar cómo interactúan inflación, salarios, desempleo, reservas, oposición y gobernabilidad.

4. Riesgos:
- Principal riesgo que podría invalidar la predicción.
- Señales tempranas que deberían monitorearse.

5. Evidencia:
- Cada claim importante debe citar el source_id del input usado.
- No usar información posterior al 31/01/2025.
- Si falta evidencia, decirlo explícitamente.


# System constraints

# System constraints — PILOT-ARG-2025-Q1

- No usar web/browsing durante la corrida.
- No usar herramientas externas, memoria persistente, RAG externo ni documentos fuera del input pack.
- No usar ni inferir ground truth posterior al corte x = 2025-01-31.
- Formular todo resultado sobre 2025 como predicción ex ante.
- Citar cada afirmación importante con source_id del input.
- Si MiroFish intenta recuperar contexto previo, limpiar o deshabilitar memoria antes de correr.
- El output crudo no debe editarse después de la corrida.


# Pre-cutoff seed bundle

# Seed Bundle — Argentina 2025 pre-cutoff

Cutoff: 2025-01-31.

## S1 — Macroeconomía
- BBVA Research describía para 2025 un escenario de desinflación, recuperación de actividad y continuidad del ajuste fiscal, con riesgos asociados a reservas, tipo de cambio y sostenibilidad social/política de la estabilización [S1_BBVA_2024Q4].
- El BCRA anunció el 16/01/2025 que desde el 1 de febrero de 2025 el sendero de desplazamiento del tipo de cambio oficial bajaría a 1% mensual, reforzando el ancla cambiaria dentro del esquema de estabilización [S2_BCRA_CRAWL_20250116].
- INDEC informaba que diciembre de 2024 cerró con IPC mensual de 2,7% y una inflación interanual todavía muy elevada, lo que dejaba a 2025 con una herencia inflacionaria significativa pero una tendencia mensual menor que al inicio del programa [S3_INDEC_IPC_202412].

## S2 — Política e instituciones
- El oficialismo llegaba al año electoral con necesidad de aumentar bancas para sostener reformas, mejorar gobernabilidad y reducir dependencia de acuerdos circunstanciales en Congreso [S4_MERCOPRESS_PIIE_20250128; S6_AQ_SNAPSHOT_202501].
- La elección legislativa de 2025 era tratada por analistas pre-corte como un test de medio término para la agenda de Milei, con interacción entre resultados económicos, negociación con el FMI y capacidad legislativa [S4_MERCOPRESS_PIIE_20250128].
- La fragmentación opositora y la relación con gobernadores/bloques legislativos aparecían como variables claves para convertir apoyo electoral en poder institucional [S4_MERCOPRESS_PIIE_20250128; S6_AQ_SNAPSHOT_202501].

## S3 — Opinión pública y tensiones sociales
- La aprobación presidencial se mantenía competitiva pese al costo social del ajuste, pero las preocupaciones por empleo, ingresos y bienestar material seguían siendo políticamente sensibles [S5_BATIMES_POLL_202501].
- La percepción pública podía depender menos del nivel anual acumulado de inflación heredado y más de la trayectoria mensual, recuperación de salarios reales, empleo y expectativas de estabilidad [S1_BBVA_2024Q4; S3_INDEC_IPC_202412; S5_BATIMES_POLL_202501].
- Tensiones persistentes pre-corte: reservas netas, sostenibilidad del crawling peg, salario real, desempleo, oposición legislativa, negociación con FMI y tolerancia social al ajuste [S1_BBVA_2024Q4; S2_BCRA_CRAWL_20250116; S4_MERCOPRESS_PIIE_20250128].

## S4 — Variables que el sistema debe considerar
- Inflación
- Salarios reales
- Desempleo
- Reservas BCRA
- Crawling peg
- Fragmentación opositora
- Gobernabilidad legislativa
