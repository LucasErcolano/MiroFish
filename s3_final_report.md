# MiroFish - Spike 3 (S3): Optimización Topológica y Deep Search

## Contexto de la Spike
Durante las simulaciones previas de la Spike 2, identificamos dos oportunidades arquitectónicas clave:
1. **Ineficiencia Topológica:** La generación de nodos semánticamente idénticos o clones incrementa los costos de llamadas a LLMs sin aportar diversidad de debate.
2. **Cuello de Botella en la Ingesta:** La curaduría de la información limitaba la automatización y la escalabilidad del sistema.

El objetivo de la Spike 3 fue atacar estos problemas introduciendo:
1. Deduplicación Pre-Inserción en el almacenamiento Graphiti (Neo4j).
2. Un pipeline de Deep Search Autónomo con restricción estricta de *Data Leakage* (`max_date`).

## Implementaciones Realizadas

### 1. Deduplicación Semántica (Optimización de Grafo)
Modificamos la capa de persistencia `graphiti_backend.py` y los servicios de lectura `zep_entity_reader.py`.
- Se implementó una verificación de similitud semántica antes de instanciar un nodo.
- El umbral de similitud (ej. 0.85) fusiona las entidades en tiempo de ejecución.
- Los nodos irrelevantes sin conectividad (sin aristas) se descartan para mantener la simulación limpia de *lurkers* vacíos.

### 2. Deep Search Autónomo con Tavily (Prevención Data Leakage)
Integramos la API de Tavily en `deep_search.py` para automatizar la obtención de contexto previo a las simulaciones.
- Se agregó el campo `max_date` para blindar las simulaciones de backtesting.
- El sistema busca, consolida y suministra la información encontrada como contexto a la red semántica inicial.

## Pipeline de Pruebas y Backtesting

Para validar las implementaciones, ejecutamos dos simulaciones end-to-end de 40 rondas orquestadas por el framework de redes sociales OASIS y los modelos Llama 3.3 70B como agentes predictivos del IPC Argentina (2025), limitando el conocimiento a Diciembre de 2024.

### Resultados Comparativos de Error Absoluto Medio (MAE)

| Escenario | Configuración | Baseline (S2) | MAE Resultante | Variación Absoluta |
| :--- | :--- | :---: | :---: | :---: |
| **Baseline (S2)** | Ingesta Manual (Sin Deduplicación) | - | **2.31%** | - |
| **Simulación A** | Ingesta Manual + **Deduplicación Pre-Inserción** | 2.31% | **1.475%** | **📉 -0.835%** (Mejora) |
| **Simulación B** | **Deep Search Autónomo** Puro (Cutoff: 31-12-2024) | 2.31% | **2.475%** | **📈 +0.165%** (Empeora) |

### Conclusiones Críticas

1. **La Optimización Topológica Funciona:**
   La Simulación A demostró que limitar la cantidad de nodos redundantes en Neo4j permite un comportamiento grupal de la IA mucho más limpio y enfocado, destrozando nuestro Baseline previo y marcando un **récord histórico de MAE (1.475%)** en el proyecto.

2. **Desafíos del Deep Search 100% Autónomo:**
   La Simulación B comprobó que confiar plenamente el contexto semilla a un rastreo automático con `max_date` degradó los resultados. La falta de reportes estructurados provocó que la red OASIS generara poquísimos agentes calificados (apenas 2 entidades irrelevantes debatieron), resultando en predicciones peores que la inyección manual estructurada.

**Próximos pasos recomendados (S4):** Implementar el Deep Search sólo como un mecanismo de *RAG enriquecedor* complementario a documentos anclas subidos por humanos, y enfocarse en la métrica de Entropía Topológica de la red para predecir la confiabilidad del consenso.
