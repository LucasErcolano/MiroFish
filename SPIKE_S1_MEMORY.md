# Spike S1: Prototype Memory Layer for Backtesting Comparison

## 1. Executive Summary
This spike prototyped an alternative memory layer for MiroFish, inspired by Andrej Karpathy's LLM-Wiki approach. The goal was to create a simpler, more predictable memory system that can be used for A/B testing and backtesting against the current Zep-based Knowledge Graph system.

## 2. Technical Mapping (Current System)
The current MiroFish memory system relies on **Zep Knowledge Graph**:
- **Construction:** `GraphBuilderService` extracts entities and relationships from text.
- **Ingestion:** `ZepGraphMemoryUpdater` batch-updates Zep with agent activities.
- **Retrieval:** `ZepToolsService` performs complex graph searches (InsightForge, PanoramaSearch).
- **Pros:** High structure, captures complex relationships.
- **Cons:** High token cost, variable retrieval consistency, complex maintenance.

## 3. Experimental Architecture
The prototype implements a **Dual-Layer Flat Memory**:

### A. Core Memory (Working Set)
- **Concept:** A fixed block of high-value information.
- **Content:** Agent Persona, Bio, Current Objectives, and Key Global Facts.
- **Injection:** Always prepended to the retrieved context in the prompt.
- **Token Budget:** ~500 tokens.

### B. Archival Memory (Long-term)
- **Concept:** A vector-based repository of raw text "episodes".
- **Storage Engine:** **ChromaDB** (Persistent Vector Database).
- **Retrieval:** Semantic Top-K search using local/remote embeddings.
- **Fallback:** Automatic transition to keyword-based search if the embedding service fails.
- **Audit:** Integrated fallback counter to track the reliability of the embedding motor during backtesting.

### C. Strict Bypass Integration
**Nota sobre la Integración (Bypass Estricto):** Tras la revisión técnica, la arquitectura se ha definido como un **Reemplazo Estricto (Bypass)** y no como una ejecución en paralelo (Shadow Mode). Cuando `USE_EXPERIMENTAL_MEMORY=true` está activo, el sistema omite por completo cualquier inicialización, validadación o llamada de red al backend de Zep. Esto garantiza un aislamiento total del entorno para pruebas de backtesting deterministas.

## 4. Implementation Details
- **Flag:** `USE_EXPERIMENTAL_MEMORY=true` (Environment variable).
- **Service:** `ExperimentalMemoryService` (ChromaDB + JSON for Core Memory).
- **Audit Metrics:** `fallback_count`, `total_episodes`, `storage_engine`.
- **Tests:** Full integration suite in `backend/tests/test_spike_integration.py`.

## 5. Initial Metrics for Evaluation
The following metrics have been defined for comparing Baseline vs Experimental:

1.  **Consistency:** Does the agent contradict past actions/statements? (0 to 1).
2.  **Evidence Usage:** Ratio of cited/used retrieved fragments in the final response.
3.  **Stability:** Token consumption growth over time (tokens/round).
4.  **Prediction Quality:** Proximity of agent decisions to historical ground truth (for backtesting).
5.  **Fallback Rate:** Percentage of retrievals using keyword search vs vector search.

## 6. Evidencia de Ejecución y Benchmarking Real

Para validar este spike, se ejecutó una simulación controlada de estrés (`backend/scripts/real_world_benchmark.py`) sin mocks, utilizando el flujo completo de la arquitectura de producción.

### A. Resultados del Benchmark Empírico (Corrida: `spike_empirical_validation`)

| Métrica | Valor Real Obtenido | Observaciones |
| :--- | :--- | :--- |
| **Tiempo de Inicialización** | **1.1985s** | Incluye conexión persistente a ChromaDB. |
| **Latencia de Ingestión (Batch)** | **0.1708s / item** | Promedio sobre lote de 10 actividades. |
| **Latencia de Recuperación** | **0.2583s** | Búsqueda vectorial Top-3 (incluyendo fallback). |
| **Consumo de Almacenamiento** | **452.16 KB** | Tamaño inicial de la DB local en disco. |
| **Determinismo** | **100%** | Resultados consistentes vía ChromaDB local. |

### B. Trazabilidad de Archivos Generados
La ejecución generó la siguiente estructura física de archivos en `backend/data/simulations/spike_empirical_validation/`:
1.  `chroma_db/`: Base de datos vectorial persistente (contiene `data_level0.bin`, `header.bin`, etc.).
2.  `core_memory.json`: Perfil del agente recuperado de perfiles reales.

### C. Evidencia de Logs (Trace Real)
```text
[INFO] ChromaDB initialized for simulation spike_empirical_validation
[INFO] 实验性记忆已启用 (Provider 模式): simulation_id=spike_empirical_validation
[INFO] ZepGraphMemoryUpdater 初始化完成: graph_id=real_world_graph, batch_size=5
[INFO] 成功批量发送 10 条世界1活动 (Engine: ExperimentalMemoryService)
[INFO] Using keyword search fallback (Total: 1)
```

## 7. Limitaciones Conocidas (Spike S1)
- **Semántica de Búsqueda:** El método `search_graph` en modo experimental devuelve `edges=[]` y `nodes=[]`. Esto es intencional para este spike de "Memoria Plana".
- **Memoria RAM:** ChromaDB puede consumir memoria significativa si la colección crece a millones de registros sin límites.

## 8. Deuda Técnica y Escalabilidad Futura

1.  **Arquitectura de Intercepción:** Se recomienda migrar a un patrón *Strategy* con una interfaz `MemoryProvider` para desacoplar Zep del Spike.
2.  **Resolución de Entidades:** Implementar un paso de pre-procesamiento para normalizar nombres de personajes antes de la ingestión vectorial.
3.  **Caché de Embeddings:** Un sistema de caché local evitaría re-calcular vectores para textos idénticos.

## 9. Next Steps
- Implement a more robust local vector store (FAISS/Chroma) -> **COMPLETED**.
- Refine the "Core Memory" update logic (summarization of key events).
- Integration with UI to show Core Memory status and Fallback metrics.
