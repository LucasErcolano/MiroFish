# S1 - Backtesting Case C: PILOT-ARG-2025-Q1

## Ficha del caso

| Campo | Valor |
|-------|-------|
| **Dominio** | Política, macroeconomía y comportamiento electoral argentino |
| **Fecha de corte x** | 31 de enero de 2025 |
| **Horizonte Δ** | Feb–oct 2025 (electoral), feb–dic 2025 (inflación/gobernabilidad) |
| **Pregunta** | Predecir rango de voto LLA, probabilidad de 3 escenarios electorales (<35%, 35-42%, >42%), rango de inflación acumulada 2025 (<30%, 30-40%, >40%), mecanismo causal dominante, riesgos principales y evidencia |
| **Desenlace real** | LLA obtuvo ~40.7% en legislativas de octubre 2025, fortaleciendo posición en el Congreso (Escenario B confirmado). Inflación acumulada 2025 resultó en rango ~30-35% (Escenario B/A borderline). |

## Inputs permitidos

13 documentos crudos de `cases/PILOT-ARG-2025-Q1/input_pack_pre_x/sources/`, todos fechados ≤ 31/01/2025.

Este run usó solo 1 input (TOP1):

1. `POLL_01_CB_Consultora_Diciembre_2024.pdf` — Encuesta CB Consultora, diciembre 2024. Aprobación de gestión, economía del hogar, tolerancia social al ajuste, comparaciones de liderazgo (Milei vs Macri, Menem, De la Rúa, Kirchner).

Los 12 documentos restantes (informes macro del BCRA, BBVA, etc.) no se incluyeron en este run por restricciones de concurrencia API. Un run con TOP3 o full inputs podría mejorar cobertura macro.

## Configuración del run

| Parámetro | Valor |
|-----------|-------|
| **Flujo** | `frontend_replay_backend_api` (headless → backend API → Graphiti → OASIS → Report) |
| **LLM** | `google/gemma-4-26B-A4B-it` via DeepInfra API |
| **Embeddings** | `BAAI/bge-m3` (1024 dims) via DeepInfra API |
| **Graph backend** | Graphiti + Neo4j 5.23.0 |
| **OASIS rounds** | 40/40 completados |
| **Agents** | 18 (Politician, PollingFirm, Organization, LegislativeBody) |
| **Twitter actions** | 121 |
| **Platform** | twitter |
| **Duración OASIS** | ~203 segundos |
| **Duración total** | ~15 minutos |
| **Costo estimado** | ~$0.05 USD |

## Rubrica de evaluación (1-5)

### 1. Especificidad — ¿La predicción es concreta y operacionalizable?

**Puntaje: 3/5**

**A favor:**
- Define 3 escenarios electorales con rangos numéricos claros (<35%, 35-42%, >42%)
- Define 3 escenarios de inflación con rangos (<30%, 30-40%, >40%)
- Identifica el Escenario B (35-42%) como "escenario central" para LLA
- Identifica el Escenario B (30-40%) como "escenario central" para inflación

**En contra:**
- **No asigna probabilidades numéricas** a cada escenario (los etiqueta solo como "baja", "central", "riesgo" sin cuantificar)
- No estima un punto central o mediana dentro del rango (ej: "LLA ~38%")
- No desglosa impacto en Diputados vs Senado con escaños estimados
- El prompt pedía "rango nacional estimado de voto" y la respuesta da escenarios pero no una estimación puntual con intervalo de confianza

### 2. Plausibilidad — ¿El escenario predicho es coherente con la evidencia disponible?

**Puntaje: 4/5**

**A favor:**
- El Escenario B electoral (35-42%) es altamente plausible y resultó correcto (~40.7%)
- El Escenario B de inflación (30-40%) es razonable y cercano al resultado real
- El mecanismo causal (inflación → percepción → apoyo electoral) es correcto
- La identificación de reservas del BCRA como ancla es correcta
- La tensión entre ajuste y desgaste social es bien capturada

**En contra:**
- No menciona el papel del dólar oficial/crawling peg que fue clave en la dinámica 2025
- Subestima la resiliencia del apoyo electoral ante inflación moderada (LLA retuvo apoyo pese a ~30% inflación)

### 3. Cobertura — ¿Aborda todos los aspectos de la pregunta?

**Puntaje: 3/5**

**A favor:**
- Cubre predicción electoral (escenarios A/B/C)
- Cubre predicción macroeconómica (inflación, 3 escenarios)
- Cubre mecanismo causal (inflación–percepción–voto)
- Cubre riesgos y señales tempranas
- Cita evidencia de la encuesta CB Consultora

**En contra:**
- **No da probabilidades explícitas** para los escenarios (el prompt pedía "Probabilidad de tres escenarios")
- **No detalla impacto sobre Diputados/Senado** con estimación de escaños (el prompt pedía específicamente esto)
- No cuantifica la interacción entre variables (reservas, desempleo, salarios) con estimaciones
- La sección de "evidencia" cita la encuesta CB pero no datos macro del input (probablemente porque solo se usó POLL_01, no los informes BCRA/BBVA)

### 4. Consistencia causal — ¿Los mecanismos causales son lógicos y coherentes?

**Puntaje: 4/5**

**A favor:**
- Cadena causal clara: inflación → brecha salarial → percepción de gestión → apoyo electoral
- Identifica correctamente la variable dominante (inflación mensual ↔ intención de voto)
- Mecanismo de riesgo bien articulado: escasez de reservas → presión cambiaria → inflación → desgaste social
- Reconoce la mediación de la "memoria histórica" en la percepción (comparaciones con De la Rúa, Kirchner)

**En contra:**
- No modela feedback loops (ej: ¿cómo afecta la victoria electoral a la política económica?)
- Presenta la relación inflación-voto como más lineal de lo que fue en la realidad (la relación se rompió parcialmente en 2025 — LLA creció pese a inflación persistente)

### 5. Ausencia de información posterior al corte — ¿Evita datos o eventos posteriores a x?

**Puntaje: 4/5**

**A favor:**
- La evidencia citada proviene exclusivamente de la encuesta CB Consultora (diciembre 2024, ≤ x)
- No menciona eventos posteriores a enero 2025
- Las comparaciones históricas (Macri, Menem, De la Rúa, Kirchner) son todas previas al corte
- No hay filtración de datos del desenlace real

**En contra:**
- Algunas formulaciones son vagamente prescientes ("consolidación de hegemonía") que podrían reflejar conocimiento posterior del modelo de entrenamiento, aunque no hay evidencia directa de data leakage
- Las proyecciones macro son genéricas y podrían coincidir con cualquier escenario de ajuste, no necesariamente derivadas solo de los inputs

### 6. Utilidad estratégica — ¿El output es útil para tomar decisiones?

**Puntaje: 3/5**

**A favor:**
- Señales de alerta temprana son operacionalizables (brecha cambiaria, coordinación sindical, comparativas históricas de liderazgo)
- Identifica umbrales de riesgo claros (inflación >40%, convergencia de actores)
- Distingue entre escenarios de ruptura y estabilidad

**En contra:**
- Sin probabilidades numéricas, es difícil priorizar entre escenarios
- No da timelines específicos para las señales de alerta (¿cuándo monitorear cada indicador?)
- No sugiere acciones concretas ante cada escenario
- La ausencia de estimación de escaños limita la utilidad para estrategia legislativa

## Puntaje total

| Criterio | Puntaje |
|----------|---------|
| Especificidad | 3/5 |
| Plausibilidad | 4/5 |
| Cobertura | 3/5 |
| Consistencia causal | 4/5 |
| Ausencia de info posterior | 4/5 |
| Utilidad estratégica | 3/5 |
| **Total** | **21/30 (70%)** |

## Análisis de acierto predictivo

| Dimensión | Predicción MiroFish | Realidad | Acierto |
|-----------|-------------------|----------|---------|
| Voto LLA | Escenario B: 35-42% (central) | ~40.7% | ✅ Correcto (cae en B) |
| Inflación 2025 | Escenario B: 30-40% (central) | ~30-35% | ✅ Correcto (cae en A/B borde) |
| Variable dominante | Inflación → percepción → voto | Inflación fue clave pero relación fue no lineal | ⚠️ Parcialmente correcto |
| Riesgo principal | Agotamiento de reservas → presión cambiaria | No ocurrió; reservas se estabilizaron | ❌ No se materializó |

## Notas para S2

1. **Run con más inputs**: El TOP1 usó solo la encuesta CB. Un run con TOP3 (agregando BCRA REM + BBVA Outlook) mejoraría cobertura macro y permitiría estimaciones más precisas de inflación y reservas.
2. **Probabilidades numéricas**: El prompt pedía probabilidades explícitas. El modelo generó escenarios con etiquetas cualitativas ("baja", "central", "riesgo") pero no números. Considerar ajustar el prompt o el report template para forzar probabilidades.
3. **Estimación de escaños**: El prompt pedía impacto en Diputados/Senado. El reporte no lo abordó. Puede requerir una sección dedicada en el template de reporte.
4. **Calibración temporal**: Las señales de alerta serían más útiles con timelines (ej: "monitorear brecha cambiaria en Q2-Q3 2025").
5. **Evaluación inter-rater**: Esta evaluación fue hecha por una sola persona. Para S2, al menos dos evaluadores deberían aplicar la rúbrica independientemente.
