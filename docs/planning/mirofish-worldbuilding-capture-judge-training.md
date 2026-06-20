# Captura de Worldbuilding para entrenar el Judge de MiroFish

> Estado: idea de diseño, no implementación.
>
> Objetivo: antes de agregar el nuevo planning ensemble, hacer que cada ejecución actual de MiroFish guarde una traza completa de todo lo que compone la fase previa a la simulación. Esa traza serviría como dataset para entrenar, auditar o calibrar un futuro judge.

---

## 1. Idea central

Antes de implementar un judge nuevo o un planning ensemble deliberativo, conviene capturar lo que MiroFish ya hace hoy.

MiroFish ya toma decisiones de worldbuilding, aunque no las llame explícitamente “plan”:

- qué inputs/documentos usa;
- qué prompt recibe;
- qué entidades detecta o filtra;
- qué grafo documental usa o construye;
- qué entidades convierte en agentes;
- qué perfiles genera;
- qué configuración de simulación produce;
- qué parámetros de plataforma quedan activos;
- qué errores o warnings aparecen antes de simular.

La propuesta es agregar un modo de captura que no cambie el comportamiento actual, sino que registre todo eso en un artefacto estructurado por run.

La idea resumida:

```text
flujo actual de MiroFish
        ↓
captura de worldbuilding_trace.json
        ↓
simulación normal
        ↓
reporte / resultados / métricas
        ↓
labels humanos o automáticos
        ↓
dataset para entrenar el judge
```

---

## 2. Objetivo inmediato

El objetivo inmediato no es mejorar el worldbuilding todavía.

El objetivo es generar ejemplos reales de entrenamiento:

```text
entrada del caso
        ↓
decisiones actuales de worldbuilding
        ↓
artefactos producidos
        ↓
resultado final observado
        ↓
evaluación humana o automática
```

Con suficientes ejemplos, el futuro judge puede aprender a responder preguntas como:

- ¿este worldbuilding era suficiente antes de simular?
- ¿hubo leakage?
- ¿faltan entidades críticas?
- ¿se confundió evidence graph con social graph?
- ¿los agentes representan bien el fenómeno?
- ¿hay demasiados agentes sintéticos?
- ¿el grafo social está inventado sin justificación?
- ¿el plan debería haber sido bloqueado?
- ¿qué alternativa habría elegido?

---

## 3. Modo recomendado: `capture_only`

La primera versión debería ser un modo de captura pasiva.

Ejemplo conceptual de configuración:

```yaml
planning_capture:
  enabled: true
  mode: capture_only
  save_raw_artifacts: true
  save_llm_prompts: true
  save_llm_outputs: true
  save_graph_snapshot: true
  save_profiles_snapshot: true
  save_config_snapshot: true
  redact_secrets: true
```

En `capture_only`:

- no se agregan planners;
- no se agrega judge;
- no se bloquea la simulación;
- no se cambia la selección de entidades;
- no se cambia la generación de perfiles;
- no se altera el benchmark;
- solo se observa, registra y guarda.

Esto permite construir dataset sin contaminar las runs actuales.

---

## 4. Artefacto principal: `worldbuilding_trace.json`

Por cada ejecución, MiroFish debería guardar un artefacto estructurado.

Ubicación sugerida:

```text
backend/uploads/simulations/<simulation_id>/worldbuilding_trace.json
```

o, si la run usa directorios propios:

```text
runs/<run_id>/artifacts/worldbuilding_trace.json
```

Este archivo representa la traza observacional de la fase previa a la simulación.

No es todavía el futuro `planning_workflow.json` deliberativo. Es una foto factual de lo que el sistema actual hizo.

Shape conceptual:

```json
{
  "trace_version": 1,
  "simulation_id": "...",
  "project_id": "...",
  "created_at": "...",

  "input_context": {},
  "source_snapshot": {},
  "prompt_snapshot": {},
  "graph_snapshot": {},
  "entity_filtering_trace": {},
  "agent_selection_trace": {},
  "simulation_social_graph_trace": {},
  "profile_generation_trace": {},
  "simulation_config_trace": {},
  "pre_simulation_validation": {},
  "provenance": {},
  "artifact_manifest": {},
  "training_labels": null
}
```

---

## 5. Qué debería guardar la traza

### 5.1 Inputs crudos permitidos

Guardar una foto de los inputs que efectivamente vio el sistema.

Campos útiles:

- prompt original del usuario;
- task objective;
- plataforma solicitada: twitter, reddit, etc.;
- cantidad de rounds;
- modelo usado;
- seed si existe;
- idioma;
- project_id;
- graph_id;
- graph memory mode;
- documentos incluidos;
- documentos excluidos;
- hashes de archivos;
- paths relativos;
- flags relevantes.

Ejemplo:

```json
{
  "input_context": {
    "original_prompt": "...",
    "platform": "twitter",
    "rounds": 40,
    "language": "es",
    "graph_memory_enabled": true,
    "source_files": [
      {
        "path": "input_pack_pre_x/sources/POLL_01.md",
        "sha256": "...",
        "size_bytes": 12345,
        "included": true
      }
    ],
    "excluded_files": [
      {
        "path": "answer_key_post_x/answer.md",
        "reason": "forbidden_answer_key"
      }
    ]
  }
}
```

Esto es importante para entrenar leakage awareness. El judge necesita aprender qué inputs eran legítimos y cuáles eran ayuda indebida.

---

### 5.2 Snapshot de fuentes / RAG / graph memory

Guardar qué backend de conocimiento usó la run.

Campos útiles:

- backend: Graphiti, Zep, Neo4j, JSON, etc.;
- si el grafo fue construido desde cero;
- si el grafo fue reutilizado;
- cantidad de documentos ingeridos;
- cantidad de chunks;
- nodos antes/después;
- edges antes/después;
- modelo usado para graph build;
- modelo de embeddings;
- configuración de chunking;
- configuración de concurrencia;
- errores o warnings.

Ejemplo:

```json
{
  "source_snapshot": {
    "graph_backend": "graphiti",
    "graph_reused": false,
    "documents_ingested": 3,
    "chunks_created": 42,
    "nodes_before": 0,
    "nodes_after": 128,
    "edges_after": 312,
    "llm_model_for_graph": "...",
    "embedding_model": "...",
    "warnings": []
  }
}
```

---

### 5.3 Prompt snapshot

Guardar los prompts relevantes de la fase previa a la simulación.

Esto puede incluir:

- prompt original;
- prompt normalizado;
- prompts usados para extracción de entidades;
- prompts usados para generación de perfiles;
- prompts usados para configuración;
- system prompts relevantes;
- outputs crudos de LLM si son usados para construir artefactos.

Ejemplo:

```json
{
  "prompt_snapshot": {
    "original_user_prompt": "...",
    "normalized_task_prompt": "...",
    "llm_calls": [
      {
        "call_id": "profile_generation_001",
        "stage": "profile_generation",
        "model": "...",
        "input_hash": "...",
        "output_hash": "...",
        "redacted_prompt_path": "artifacts/llm_calls/profile_generation_001.prompt.txt",
        "redacted_output_path": "artifacts/llm_calls/profile_generation_001.output.json"
      }
    ]
  }
}
```

Los prompts y outputs pueden ser pesados, así que conviene guardarlos como archivos secundarios y referenciarlos desde el trace.

---

### 5.4 Entidades candidatas, aceptadas y rechazadas

Esta es una de las partes más valiosas para entrenar el judge.

Guardar:

- entidades candidatas;
- entidades aceptadas;
- entidades rechazadas;
- tipo de entidad;
- cantidad de menciones;
- evidencia asociada;
- score o centralidad si existe;
- función o etapa que la filtró;
- razón de inclusión/exclusión si existe;
- si fue explícita o inferida.

Ejemplo:

```json
{
  "entity_filtering_trace": {
    "candidate_count": 45,
    "accepted_count": 18,
    "rejected_count": 27,
    "candidate_entities": [
      {
        "id": "ent_1",
        "name": "Actor X",
        "type": "person",
        "source_mentions": 7,
        "evidence_refs": ["doc1:34", "doc2:88"],
        "status": "accepted",
        "reason": "high_mentions_and_relevant_to_prompt"
      },
      {
        "id": "ent_2",
        "name": "Organization Y",
        "type": "institution",
        "status": "rejected",
        "reason": "context_only_not_agent_candidate"
      }
    ]
  }
}
```

Si hoy el código no tiene `reason`, se puede empezar guardando lo observable:

- antes/después;
- función que aplicó el filtro;
- parámetros usados;
- conteos;
- logs;
- artefactos generados.

Más adelante se pueden agregar razones explícitas.

---

### 5.5 Evidence graph actual

Guardar el grafo documental que existe antes de la simulación.

Este grafo responde:

```text
qué dicen las fuentes sobre el mundo
```

Campos útiles:

- nodos;
- edges;
- tipos de relación;
- source/evidence;
- confidence si existe;
- inferred vs explicit;
- comunidades si existen;
- métricas de centralidad;
- componentes conectados.

Ejemplo:

```json
{
  "graph_snapshot": {
    "nodes": [
      {
        "id": "ent_1",
        "label": "Actor X",
        "type": "person"
      }
    ],
    "edges": [
      {
        "source": "Actor X",
        "target": "Institution Y",
        "relation": "criticizes",
        "evidence_refs": ["doc2:88"],
        "confidence": null,
        "inferred": false
      }
    ],
    "metrics": {
      "node_count": 128,
      "edge_count": 312,
      "connected_components": 4
    }
  }
}
```

Esto permite evaluar después si el worldbuilding confundió evidencia documental con relaciones sociales simuladas.

---

### 5.6 Agent selection actual

Guardar cómo se pasó de entidades/documentos a agentes simulados.

Campos útiles:

- agentes seleccionados;
- entidades descartadas;
- agentes sintéticos;
- rol de cada agente;
- plataforma donde participa;
- source_entity si existe;
- username;
- description;
- user_char;
- comunidad;
- motivo observable de inclusión;
- archivo de perfil donde quedó guardado.

Ejemplo:

```json
{
  "agent_selection_trace": {
    "configured_agent_count": 18,
    "agents": [
      {
        "agent_id": "agent_001",
        "username": "...",
        "source_entity": "Actor X",
        "synthetic": false,
        "role": "political_actor",
        "reason_observed": "generated_from_entity",
        "profile_file": "twitter_profiles.csv"
      },
      {
        "agent_id": "agent_009",
        "username": "...",
        "synthetic": true,
        "role": "bridge_voter",
        "reason_observed": "profile_generator_synthetic_fill"
      }
    ],
    "discarded_entities": []
  }
}
```

Para el judge, esto es especialmente importante: muchas simulaciones pueden fallar no por el modelo, sino porque faltaban agentes puente, sobraban agentes redundantes, o las entidades correctas quedaron como contexto pasivo.

---

### 5.7 Simulation social graph

Separar explícitamente este grafo del evidence graph.

El evidence graph responde:

```text
qué dicen las fuentes
```

El simulation social graph responde:

```text
cómo se relacionan los agentes dentro de la simulación
```

Campos útiles:

- agentes/nodos;
- follows/friends/affinity/opposition;
- pesos;
- comunidades;
- grado;
- si fue random, heurístico o derivado de evidencia;
- seed usada;
- métricas de densidad.

Ejemplo:

```json
{
  "simulation_social_graph_trace": {
    "construction_method": "oasis_profile_generator_default",
    "nodes": [],
    "edges": [
      {
        "from_agent": "agent_001",
        "to_agent": "agent_004",
        "relation": "follows",
        "weight": 0.7,
        "source": "generated"
      }
    ],
    "metrics": {
      "agent_count": 18,
      "edge_count": 94,
      "density": 0.31
    }
  }
}
```

Aunque hoy MiroFish no lo exponga claramente, se puede guardar lo disponible en perfiles, config y OASIS graph.

---

### 5.8 Profiles y config generados

Guardar snapshot completo o referenciado de los archivos que alimentan la simulación.

Artefactos típicos:

- `reddit_profiles.json`;
- `twitter_profiles.csv`;
- `simulation_config.json`;
- configs intermedias;
- outputs de scripts;
- logs de generación.

Ejemplo:

```json
{
  "profile_generation_trace": {
    "profile_generator": "OasisProfileGenerator",
    "output_files": [
      {
        "path": "twitter_profiles.csv",
        "sha256": "..."
      }
    ],
    "profile_count": 18,
    "model": "...",
    "warnings": []
  },
  "simulation_config_trace": {
    "config_generator": "SimulationConfigGenerator",
    "output_file": "simulation_config.json",
    "sha256": "...",
    "max_rounds": 40,
    "platform": "twitter"
  }
}
```

---

### 5.9 Estado pre-simulación

Guardar exactamente hasta dónde llegó la preparación.

Campos útiles:

- status final de preparación;
- etapa donde falló;
- error exacto;
- warnings;
- si llegó a generar profiles;
- si llegó a generar config;
- si llegó a instanciar OASIS graph;
- si llegó a `env.reset`;
- si llegó a `env.step`.

Ejemplo:

```json
{
  "pre_simulation_validation": {
    "status": "ready",
    "blocking_issues": [],
    "warnings": [],
    "profiles_generated": true,
    "simulation_config_generated": true,
    "oasis_graph_instantiated": true,
    "env_reset_completed": false,
    "env_step_completed": false
  }
}
```

La frontera debe ser clara: este artefacto termina antes de los rounds de simulación.

---

## 6. Separar traza factual de labels de entrenamiento

No conviene mezclar en el mismo archivo:

1. lo que el sistema vio e hizo;
2. la evaluación posterior de si eso fue bueno o malo.

Recomendación:

```text
worldbuilding_trace.json       # factual, generado durante la run
judge_training_label.json      # agregado después, por evaluación humana/automática
```

Ejemplo de label posterior:

```json
{
  "simulation_id": "...",
  "trace_file": "worldbuilding_trace.json",
  "label_version": 1,

  "overall_quality": 0.72,
  "leakage_detected": false,
  "agent_selection_quality": 0.6,
  "graph_quality": 0.8,
  "source_fidelity": 0.9,
  "simulation_usefulness": 0.65,

  "human_notes": [
    "Faltaron actores puente entre comunidad política y medios.",
    "Buen control de fuentes, no parece haber answer-key leakage."
  ],

  "preferred_alternative": null
}
```

Esto permite entrenar al judge con pares:

```text
input: worldbuilding_trace.json
output: evaluación / decisión / corrección
```

---

## 7. Dataset resultante para el judge

Con suficientes runs, se puede construir un dataset con distintos tipos de ejemplos.

### 7.1 Judge como evaluador

Input:

- prompt original;
- documentos permitidos;
- entidades elegidas;
- grafo documental;
- agentes seleccionados;
- grafo social;
- config;
- resultado observado.

Output esperado:

- score general;
- problemas detectados;
- riesgos;
- leakage;
- qué habría cambiado;
- si dejaría correr o bloquearía.

### 7.2 Judge como selector entre planes

Cuando más adelante exista planning ensemble, cada ejemplo puede contener:

Input:

- plan A;
- plan B;
- plan C;
- críticas;
- trazas/resultados de runs parecidas.

Output:

- elementos elegidos;
- elementos rechazados;
- plan final;
- justificación.

Pero para llegar a ese punto, primero hay que capturar trazas del sistema actual.

---

## 8. Qué no guardar o guardar con cuidado

No guardar dentro del trace pre-simulación:

- answer keys;
- labels post-evento;
- archivos post-cutoff;
- benchmark labels;
- secretos;
- API keys;
- tokens;
- datos que el modelo no debería haber visto;
- evaluación final mezclada con inputs.

Si existe answer key para evaluación, guardarla en otro namespace separado y posterior:

```json
{
  "evaluation_only": {
    "answer_key_path": "...",
    "sha256": "...",
    "loaded_after_simulation": true
  }
}
```

Pero nunca como parte del contexto pre-simulación.

---

## 9. Relación con el planning ensemble futuro

El documento de planning ensemble propone el futuro:

```text
planning fan-out
        ↓
critiques
        ↓
judge
        ↓
verifier
        ↓
planning_workflow.json
        ↓
materialización
```

Esta propuesta es el paso previo:

```text
flujo actual de MiroFish
        ↓
captura de worldbuilding_trace.json
        ↓
labels de calidad
        ↓
dataset para entrenar/calibrar el judge
```

Después, cuando exista el planning ensemble, el judge ya no nace de cero: se entrena o se evalúa contra trazas reales del comportamiento actual.

---

## 10. Diferencia entre `worldbuilding_trace.json` y `planning_workflow.json`

### `worldbuilding_trace.json`

- Observacional.
- Describe lo que MiroFish hizo hoy.
- No decide.
- No critica.
- No bloquea.
- Sirve para auditoría y dataset.

### `planning_workflow.json`

- Deliberativo.
- Describe lo que el nuevo sistema propone hacer.
- Incluye planners, críticas, judge y verifier.
- Puede bloquear antes de simular.
- Sirve como contrato ejecutable futuro.

Relación:

```text
worldbuilding_trace.json = datos históricos para aprender
planning_workflow.json = decisión futura guiada por el judge
```

---

## 11. MVP recomendado

Primera versión mínima:

1. Agregar flag `planning_capture.enabled`.
2. Crear writer de `worldbuilding_trace.json`.
3. Capturar input context.
4. Capturar source files incluidos/excluidos.
5. Capturar hash de artefactos principales.
6. Capturar entities antes/después del filtro si el flujo lo expone.
7. Capturar profiles generados.
8. Capturar simulation_config.
9. Capturar pre-simulation status.
10. Redactar secretos.
11. No cambiar la ejecución.

Segunda versión:

1. Capturar prompts/outputs LLM de worldbuilding.
2. Capturar graph snapshot completo.
3. Capturar social graph si está disponible.
4. Agregar `judge_training_label.json`.
5. Crear script para exportar dataset.

Tercera versión:

1. Agregar evaluación humana/asistida.
2. Comparar trazas entre runs.
3. Generar ejemplos preference-style.
4. Usar esas trazas para entrenar/calibrar el judge.

---

## 12. Resumen corto

La idea es convertir cada ejecución actual de MiroFish en un ejemplo de entrenamiento para el futuro judge.

Para eso, antes de implementar planners nuevos, conviene agregar un modo `capture_only` que guarde un `worldbuilding_trace.json` con todo lo que ocurre antes de que los agentes empiecen a actuar:

- prompt;
- fuentes permitidas/usadas;
- documentos excluidos;
- graph backend;
- entidades candidatas/filtradas;
- evidence graph;
- agentes seleccionados;
- perfiles generados;
- social graph/config;
- parámetros de simulación;
- prompts/outputs LLM relevantes;
- errores/warnings;
- hashes de artefactos;
- frontera clara de leakage;
- estado exacto antes de iniciar rounds.

Después se agrega un `judge_training_label.json` con la evaluación de calidad.

Con suficientes pares:

```text
worldbuilding_trace.json + judge_training_label.json
```

se puede entrenar un judge para evaluar, bloquear, comparar o sintetizar planes futuros.
