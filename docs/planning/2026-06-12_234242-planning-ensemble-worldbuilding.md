# Planning Ensemble / Deliberative World-Building para MiroFish

> **Estado:** documento de diseño, no implementación.
>
> **Objetivo:** definir una nueva fase previa a la simulación donde MiroFish no solo recibe `graph/entities` ya hechos, sino que planifica cómo construirlos, criticarlos, verificarlos y materializarlos antes de que los agentes simulados empiecen a interactuar.

---

## 1. Idea central

Queremos agregar a MiroFish una capa de planificación deliberativa antes de la simulación.

Hoy el flujo conceptual puede pensarse así:

```text
seed data + prompt + graph/entities
        ↓
generación de profiles/config
        ↓
agentes empiezan a interactuar
        ↓
simulación
```

La propuesta es cambiarlo a:

```text
seed data + prompt
        ↓
planning fan-out: 3-5 planes independientes
        ↓
restate gate por planner
        ↓
planificación de RAG, entidades, grafo, agentes, eventos y plataforma
        ↓
cross-critique entre planes / críticos especializados
        ↓
enforcement de disenso, novedad y contraejemplos
        ↓
judge sintetiza un único plan ejecutable
        ↓
workflow artifact en YAML/JSON
        ↓
verifier intenta romper el plan
        ↓
si pasa: se materializan graph/entities/profiles/config
        ↓
agentes empiezan a interactuar
        ↓
simulación
```

En esta visión, el “plan” no es un texto narrativo. Es el contrato ejecutable entre:

1. los datos de entrada,
2. la interpretación del caso,
3. la construcción del mundo simulado,
4. y la ejecución de la simulación.

---

## 2. Definición de “plan”

Para esta feature, llamamos “plan” a todo lo que ocurre desde que MiroFish recibe:

- seed data,
- documentos,
- prompt del usuario,
- constraints del benchmark,
- metadata permitida,

hasta justo antes de que los agentes simulados empiecen a hablar entre sí.

Por lo tanto, el plan incluye:

- selección y política de fuentes/RAG,
- extracción de entidades,
- construcción del evidence graph,
- selección de agentes/personas,
- creación de agentes sintéticos si hacen falta,
- construcción del grafo social de simulación,
- eventos iniciales y programados,
- parámetros de plataforma,
- supuestos,
- incertidumbres,
- riesgos de leakage,
- contraejemplos,
- y validación pre-ejecución.

El plan no incluye:

- acciones reales de agentes durante rounds,
- posts generados por agentes ya simulando,
- conversaciones simuladas,
- outputs del report agent,
- ni resultados de la simulación.

---

## 3. Graph/entities también son parte del plan

Una decisión clave: `graph/entities` no deben tratarse necesariamente como inputs fijos.

Podemos hacer que también sean producto del planning.

Entrada mínima:

```text
seed data + prompt
```

Producto del planning:

```text
entity extraction plan
        ↓
evidence graph plan
        ↓
agent selection plan
        ↓
simulation social graph plan
```

Esto permite que distintos planners propongan distintas formas de convertir los documentos en un mundo simulado.

Ejemplos:

- Un planner puede proponer solo entidades explícitas y grafo conservador.
- Otro puede proponer agentes sintéticos marcados explícitamente.
- Otro puede priorizar actores puente aunque no sean los más mencionados.
- Otro puede construir comunidades polarizadas.
- Otro puede explorar un contrafactual donde la entidad más mencionada no sea causalmente central.

Esto es más potente que hacer fan-out solo sobre un grafo ya decidido.

---

## 4. Separación conceptual de grafos

Conviene no mezclar cuatro cosas distintas.

### 4.1 Entity extraction plan

Define qué entidades existen o importan.

Ejemplos:

- personas,
- instituciones,
- medios,
- partidos políticos,
- grupos sociales,
- ubicaciones causalmente relevantes,
- conceptos/eventos si son necesarios.

Debe especificar:

- qué tipos incluir,
- qué tipos excluir,
- criterios de ranking,
- mínimo/máximo de entidades,
- cómo manejar entidades ambiguas,
- cómo manejar entidades sin suficiente evidencia.

### 4.2 Evidence graph plan

Define el grafo documental: qué relaciones se extraen de los documentos.

Ejemplos de edges:

- `supports`,
- `opposes`,
- `influences`,
- `funds`,
- `reports_on`,
- `belongs_to`,
- `competes_with`,
- `mentions`,
- `amplifies`.

Debe diferenciar:

- edges explícitos en fuentes,
- edges inferidos,
- edges de baja confianza,
- edges prohibidos por falta de evidencia.

### 4.3 Agent selection plan

Define qué entidades se convierten en agentes de la simulación.

No toda entidad documental debe ser agente.

Algunas entidades pueden quedar como:

- contexto,
- instituciones pasivas,
- eventos,
- fuentes,
- temas,
- lugares,
- variables de entorno.

El plan debe explicar:

- qué entidades se vuelven agentes,
- por qué,
- qué roles cumplen,
- qué diversidad de postura tienen,
- qué actores centrales/periféricos/puente se incluyen,
- qué agentes sintéticos se permiten.

### 4.4 Simulation social graph plan

Define el grafo social que usarán los agentes durante la run.

Este grafo no tiene que ser idéntico al evidence graph.

El evidence graph dice:

```text
qué dicen las fuentes sobre el mundo
```

El simulation social graph dice:

```text
cómo se relacionan los agentes dentro del mundo simulado
```

Puede proyectar, resumir o transformar el evidence graph.

Debe incluir:

- nodos/agentes,
- relaciones sociales,
- pesos de influencia,
- confianza/oposición/afinidad,
- comunidades,
- puentes entre comunidades,
- incertidumbre por edge,
- evidencia o justificación.

---

## 5. Planner fan-out

Queremos generar 3-5 planes independientes.

Cada planner recibe el mismo input base:

- seed data,
- prompt,
- restricciones,
- documentos permitidos,
- metadata segura,
- configuración de plataforma deseada,
- constraints del benchmark.

Pero cada planner puede tener:

- rol distinto,
- prompt distinto,
- temperatura distinta,
- modelo distinto,
- estrategia distinta.

Ejemplo de planners:

```yaml
planning_ensemble:
  enabled: true
  planner_count: 5
  planners:
    - id: planner_factual
      role: source_fidelity
      goal: Maximizar fidelidad documental y minimizar inferencias.
    - id: planner_social_graph
      role: social_topology
      goal: Construir el mejor grafo social para dinámica multi-agente.
    - id: planner_adversarial
      role: leakage_and_assumption_attack
      goal: Detectar leakage, supuestos débiles y shortcuts.
    - id: planner_minimal
      role: minimal_executable_world
      goal: Proponer el mundo simulado más simple que todavía capture el fenómeno.
    - id: planner_counterfactual
      role: counterfactual_worldbuilding
      goal: Proponer una lectura alternativa y falsable del caso.
```

También debería permitirse que cada planner use una LLM diferente:

```yaml
planners:
  - id: planner_factual
    model: gemini-2.5-pro
  - id: planner_social_graph
    model: claude-sonnet
  - id: planner_adversarial
    model: deepseek-r1
  - id: planner_minimal
    model: gpt-4.1-mini
  - id: planner_counterfactual
    model: qwen3
```

Si hay menos modelos disponibles, igual se pueden usar prompts distintos sobre el mismo modelo.

Requisito mínimo sugerido:

- 3 planners mínimo,
- 5 planners ideal.

---

## 6. Restate gate

Antes de generar un plan completo, cada planner debe reformular el objetivo.

Este paso evita que el planner resuelva una tarea distinta o contamine el plan con supuestos no pedidos.

Cada planner debe producir algo así:

```json
{
  "planner_id": "planner_factual",
  "restate_objective": "...",
  "interpreted_task": "...",
  "success_criteria": ["..."],
  "out_of_scope": ["..."],
  "leakage_boundaries": ["..."]
}
```

El sistema debe verificar:

- que el planner entendió que todavía no debe simular,
- que el objetivo reformulado coincide con el prompt,
- que no incorporó datos prohibidos,
- que reconoce límites de fuentes,
- que entiende que debe planear RAG, entidades, grafo, agentes y configuración.

Si el restatement falla:

- se puede hacer retry,
- o descartar ese planner,
- o marcarlo como no confiable para el judge.

---

## 7. Contenido esperado de cada plan independiente

Cada planner debería producir un objeto estructurado, no markdown libre.

Ejemplo de shape:

```json
{
  "planner_id": "planner_social_graph",
  "model": "...",
  "role": "social_topology",
  "restate_objective": "...",
  "source_plan": {},
  "entity_extraction_plan": {},
  "evidence_graph_plan": {},
  "agent_selection_plan": {},
  "simulation_social_graph_plan": {},
  "event_plan": {},
  "platform_plan": {},
  "execution_parameters": {},
  "dissent": "...",
  "novelty": "...",
  "counterexample": "...",
  "uncertainties": [],
  "leakage_controls": [],
  "expected_failure_modes": []
}
```

Campos obligatorios:

- `restate_objective`,
- `source_plan`,
- `entity_extraction_plan`,
- `evidence_graph_plan`,
- `agent_selection_plan`,
- `simulation_social_graph_plan`,
- `event_plan`,
- `platform_plan`,
- `dissent`,
- `novelty`,
- `counterexample`,
- `uncertainties`,
- `leakage_controls`.

---

## 8. Cross-critique

Después de generar los planes independientes, agregamos una fase de crítica cruzada.

Hay dos diseños posibles:

### Opción A: planners se critican entre sí

Cada planner lee los planes de los demás y produce críticas.

Ventaja:

- más diversidad natural.

Desventaja:

- puede mezclar demasiado el rol de generación con el de evaluación.

### Opción B: críticos especializados

Usar críticos separados.

Críticos posibles:

- leakage critic,
- RAG critic,
- entity critic,
- social graph critic,
- synthetic agent critic,
- execution critic,
- counterfactual critic.

Ventaja:

- más control,
- mejor auditabilidad,
- más fácil exigir coverage.

Diseño recomendado: opción B.

Cada crítico produce:

```json
{
  "critic_id": "leakage_critic",
  "target_plan_id": "planner_factual",
  "attacked_assumptions": [],
  "risks": [],
  "leakage_findings": [],
  "missing_entities": [],
  "weak_edges": [],
  "agent_selection_failures": [],
  "counterexamples": [],
  "required_changes": []
}
```

La crítica debe atacar:

- supuestos injustificados,
- entidades omitidas,
- agentes redundantes,
- relaciones sociales inventadas,
- leakage temporal,
- leakage por answer key o labels,
- uso de manifests/seed bundles demasiado guiados,
- falta de diversidad de agentes,
- falta de actores puente,
- grafo demasiado denso o demasiado pobre,
- plan no ejecutable,
- contradicciones internas.

---

## 9. Enforcement: disenso, novedad y contraejemplo

No alcanza con pedir “varios planes”. El sistema debe forzar diversidad útil.

Cada plan debe tener tres campos obligatorios:

### 9.1 Dissent

Una objeción explícita a una lectura obvia/dominante.

Ejemplo:

```text
No deberíamos elegir solo actores con mayor centralidad documental; un actor periférico puede iniciar o redireccionar la cascada.
```

### 9.2 Novelty

Un elemento nuevo que no esté simplemente repetido en los otros planes.

Ejemplo:

```text
Agregar agentes puente entre comunidades como variable explícita de la simulación.
```

### 9.3 Counterexample

Una situación donde el plan fallaría.

Ejemplo:

```text
Si la difusión ocurre por medios institucionales y no por pares sociales, este grafo social subestima la propagación.
```

El verifier debe bloquear planes que tengan estos campos vacíos, genéricos o triviales.

---

## 10. Judge

El judge sintetiza un único plan ejecutable a partir de:

- planes independientes,
- restatements,
- críticas,
- disensos,
- novedades,
- contraejemplos,
- riesgos,
- incertidumbres.

No debe simplemente elegir un ganador ni promediar.

Debe producir trazabilidad:

```json
{
  "chosen_elements": [
    {
      "from_plan": "planner_factual",
      "element": "raw-source-only RAG policy",
      "why": "reduces leakage risk"
    },
    {
      "from_plan": "planner_social_graph",
      "element": "bridge agents between communities",
      "why": "improves social diffusion realism"
    }
  ],
  "rejected_elements": [
    {
      "from_plan": "planner_high_recall",
      "element": "include manifest.csv",
      "why": "too much benchmark help and possible leakage"
    }
  ],
  "uncertainties": [
    "true influence weights are underspecified",
    "some organizations may not be valid agents"
  ],
  "final_plan": {}
}
```

El judge debe preservar:

- qué eligió,
- de quién lo tomó,
- qué rechazó,
- por qué,
- qué incertidumbre queda.

---

## 11. Workflow artifact ejecutable

El resultado del judge debe guardarse como YAML o JSON versionado.

Nombre sugerido:

```text
planning_workflow.json
```

o:

```text
simulation_plan.yaml
```

Debe guardarse junto a los artefactos de la simulación, por ejemplo:

```text
backend/uploads/simulations/<simulation_id>/planning_workflow.json
```

Shape conceptual:

```yaml
workflow_artifact_version: 1
simulation_id: sim_x
project_id: proj_x
graph_id: graph_x

objective:
  original_prompt: "..."
  restated_objective: "..."
  success_criteria: []
  out_of_scope: []

source_plan:
  allowed_inputs:
    - raw_documents
    - user_prompt
  forbidden_inputs:
    - answer_key
    - future_data
    - benchmark_labels
    - manifest.csv unless explicitly allowed
    - seed_bundle.md unless explicitly allowed
  retrieval_strategy: []
  leakage_controls: []

entity_extraction_plan:
  included_entity_types: []
  excluded_entity_types: []
  ranking_policy: []
  minimum_entities: 0
  maximum_entities: 0
  ambiguity_policy: "..."

evidence_graph_plan:
  node_policy:
    require_source_evidence: true
  edge_policy:
    allowed_edge_types: []
    require_evidence: true
    allow_inferred_edges: true
    inferred_edge_label_required: true
  uncertainty_policy:
    mark_low_confidence_edges: true

agent_selection_plan:
  selection_rules: []
  required_agents: []
  optional_agents: []
  synthetic_agents:
    allowed: true
    rules: []

simulation_social_graph_plan:
  construction_method: []
  nodes: []
  edges: []
  communities: []
  bridge_nodes: []
  edge_weight_policy: {}

event_plan:
  initial_events: []
  scheduled_events: []
  shocks: []

platform_plan:
  twitter:
    enabled: true
    visibility_model: "..."
    virality_threshold: 10
  reddit:
    enabled: false

execution_parameters:
  rounds: 40
  random_seed: null
  agent_count_target: null

judge_trace:
  chosen_elements: []
  rejected_elements: []

uncertainties: []
risks: []
rejected_alternatives: []

verifier:
  status: pass
  blocking_issues: []
  warnings: []

execution_ready: true
```

---

## 12. Verifier

Antes de ejecutar, un verifier intenta romper el plan.

Debe combinar checks determinísticos y, opcionalmente, un LLM adversarial.

### 12.1 Checks determinísticos

Ejemplos:

- campos obligatorios presentes,
- JSON/YAML válido,
- `workflow_artifact_version` soportado,
- no se usan fuentes prohibidas,
- no aparecen strings tipo `answer_key`, `post_cutoff`, `benchmark_label` en fuentes usadas,
- hay suficientes entidades/agentes,
- los agentes requeridos tienen razón de inclusión,
- los agentes sintéticos están marcados como sintéticos,
- las relaciones inferidas están marcadas como inferidas,
- los edges tienen source/evidence o justificación,
- no hay contradicción entre plataforma y eventos,
- hay disenso,
- hay novedad,
- hay contraejemplo,
- hay incertidumbres explícitas,
- el plan tiene parámetros ejecutables.

### 12.2 Checks adversariales

Un verifier LLM puede recibir el plan final y tener una única tarea:

```text
Try to block this plan before simulation. Find leakage, invalid assumptions, non-executable fields, weak graph construction, missing agents, and ways this plan could create misleading simulation outputs.
```

Salida:

```json
{
  "status": "pass|fail",
  "blocking_issues": [],
  "warnings": [],
  "suggested_repairs": []
}
```

Si hay blocking issues, la simulación no debe empezar.

---

## 13. Integración conceptual con MiroFish

La integración ideal es insertar la nueva fase antes de la generación de profiles/config.

Flujo actual simplificado:

```text
SimulationManager.prepare_simulation
  ↓
ZepEntityReader.filter_defined_entities
  ↓
OasisProfileGenerator.generate_profiles_from_entities
  ↓
SimulationConfigGenerator.generate_config
  ↓
guardar simulation_config/profiles
  ↓
READY
```

Flujo propuesto:

```text
SimulationManager.prepare_simulation
  ↓
leer seed data / documentos / prompt / constraints
  ↓
PlanningWorkflow.build_plan
  ↓
guardar planning_workflow.json
  ↓
SimulationPlanVerifier.verify
  ↓
si fail: BLOCKED/FAILED antes de simular
  ↓
si pass: materializar entidades/grafos/agentes/config desde el plan
  ↓
OasisProfileGenerator.generate_profiles_from_plan
  ↓
SimulationConfigGenerator.generate_config_from_plan
  ↓
guardar simulation_config/profiles
  ↓
READY
```

Módulos sugeridos:

```text
backend/app/services/simulation_planning_workflow.py
backend/app/services/simulation_plan_schema.py
backend/app/services/simulation_plan_verifier.py
```

Responsabilidades:

### `simulation_planning_workflow.py`

- construir context pack seguro,
- correr planner fan-out,
- aplicar restate gate,
- correr cross-critique,
- llamar judge,
- guardar artifact.

### `simulation_plan_schema.py`

- definir schema/versionado,
- validar campos requeridos,
- normalizar output de LLM,
- convertir YAML/JSON a objeto interno.

### `simulation_plan_verifier.py`

- checks determinísticos,
- checks de leakage,
- checks de ejecutabilidad,
- checks de disenso/novedad/contraejemplo,
- opcionalmente LLM verifier adversarial.

---

## 14. Cómo se materializa el plan

El plan no debería quedarse como documentación.

Debe alimentar la ejecución.

Ejemplos:

### 14.1 Entity extraction

El `entity_extraction_plan` define cómo extraer o filtrar entidades.

Resultado materializado:

```text
planned_entities.json
```

### 14.2 Evidence graph

El `evidence_graph_plan` define qué relaciones documentales construir.

Resultado materializado:

```text
planned_evidence_graph.json
```

### 14.3 Agent selection

El `agent_selection_plan` define qué entidades se convierten en agentes.

Resultado materializado:

```text
planned_agents.json
```

### 14.4 Social graph

El `simulation_social_graph_plan` define relaciones entre agentes.

Resultado materializado:

```text
planned_social_graph.json
```

### 14.5 Profiles/config

El plan alimenta:

```text
reddit_profiles.json
twitter_profiles.csv
simulation_config.json
```

Esto permitiría auditar cómo se pasó de documentos a agentes.

---

## 15. Beneficios esperados

Esta feature debería mejorar MiroFish en varios frentes:

1. Más robustez:
   - no depende de una sola interpretación del prompt.

2. Menos leakage:
   - el plan declara fuentes permitidas/prohibidas y el verifier lo chequea.

3. Mejor trazabilidad:
   - queda claro por qué existen tales agentes y relaciones.

4. Mejor simulación multi-agente:
   - el grafo social se diseña explícitamente, no emerge accidentalmente de una lista de entidades.

5. Mejor experimentación:
   - se pueden comparar planes alternativos sin ejecutar toda la simulación.

6. Mejor reproducibilidad:
   - el artifact versionado permite reejecutar la misma world-building phase.

7. Mejor separación conceptual:
   - documentos/evidencia ≠ agentes ≠ grafo social ≠ simulación.

---

## 16. Riesgos y decisiones abiertas

### 16.1 Riesgo: demasiado costo LLM

Fan-out 3-5 planners + críticos + judge + verifier puede ser caro.

Mitigaciones:

- 3 planners por defecto,
- 5 solo en modo high-quality,
- críticos pequeños/baratos,
- judge fuerte,
- cachear context pack,
- permitir modelos distintos por rol.

### 16.2 Riesgo: planes demasiado largos

El artifact puede volverse enorme.

Mitigaciones:

- separar `planning_workflow.json` de artefactos materializados,
- guardar full traces comprimidos/opcionales,
- limitar campos del plan ejecutable,
- guardar críticas completas en archivos secundarios.

### 16.3 Riesgo: verifier bloquea demasiado

Si el verifier es demasiado estricto, nada corre.

Mitigaciones:

- distinguir `blocking_issues` de `warnings`,
- permitir modo `warn_only` para desarrollo,
- mantener fail-closed para benchmarks limpios.

### 16.4 Riesgo: confundir evidence graph con social graph

Mitigación:

- mantener nombres separados,
- schemas separados,
- exigir `evidence` o `inference_reason` por edge.

### 16.5 Pregunta abierta: qué se hace si el plan falla

Opciones:

1. bloquear y pedir intervención,
2. retry automático del judge con feedback del verifier,
3. retry de planners específicos,
4. degradar a flujo actual.

Para benchmarks serios, la recomendación es no degradar silenciosamente. Si falla el planning verifier, reportar `BLOCKED before simulation`.

---

## 17. Primera versión recomendada

Para una primera implementación, no intentaría resolver todo.

MVP recomendado:

1. Crear schema de `planning_workflow.json`.
2. Implementar 3 planners.
3. Exigir restate/dissent/novelty/counterexample.
4. Implementar críticas simples.
5. Implementar judge.
6. Implementar verifier determinístico.
7. Guardar artifact.
8. Todavía no materializar todo el graph desde cero; usar el artifact para guiar la selección/configuración.
9. Después extender a materialización completa de entities/evidence graph/social graph.

Secuencia incremental:

```text
V1: Planning artifact + verifier + no simulation if fail
V2: Plan-guided agent selection
V3: Plan-guided social graph
V4: Plan-guided entity/evidence graph construction
V5: Multi-model planners configurable por backend
V6: Full replay/audit of planning traces
```

---

## 18. Resumen corto

Queremos convertir la fase previa a la simulación en un proceso deliberativo, multi-plan, criticado y verificable.

El plan incluye todo lo previo a que los agentes hablen:

- RAG,
- entidades,
- evidence graph,
- selección de personas,
- agentes sintéticos,
- grafo social,
- eventos,
- plataforma,
- incertidumbres,
- leakage controls.

La simulación empieza recién después de que:

1. varios planners propusieron mundos posibles,
2. cada planner reformuló el objetivo,
3. críticos atacaron supuestos y leakage,
4. se forzó disenso/novedad/contraejemplo,
5. un judge sintetizó un plan único,
6. se guardó un artifact ejecutable,
7. un verifier intentó romperlo,
8. y el plan pasó validación.

La idea fuerte:

```text
No usar graph/entities como input fijo.
Hacer que graph/entities sean parte del world-building plan.
Después materializarlos y recién entonces simular.
```
