# Experimental Memory Service (Spike S1)

Dual-layer memory system for MiroFish simulations, implemented as an alternative to the Zep-based baseline memory.

## Architecture

The experimental memory uses a **Core Memory + Archival Memory** approach inspired by Karpathy's LLM-Wiki and MemGPT:

```
┌─────────────────────────────────────────────────┐
│          ExperimentalMemoryService              │
│                                                  │
│  ┌──────────────┐    ┌─────────────────────┐    │
│  │  Core Memory  │    │  Archival Memory     │    │
│  │  (JSON file)  │    │  (ChromaDB vector)    │    │
│  │              │    │                       │    │
│  │ - persona    │    │ - episodic memories   │    │
│  │ - objectives │    │ - semantic search     │    │
│  │ - key_events │    │ - entity normalization │    │
│  └──────────────┘    └─────────────────────┘    │
│                                                  │
│  EmbeddingClient ──► vectorizes queries/docs     │
│  (falls back to keyword search if unavailable)   │
└─────────────────────────────────────────────────┘
```

### Core Memory (`core_memory.json`)

A small, structured JSON file stored per simulation:

| Field | Type | Description |
|-------|------|-------------|
| `persona` | string | Agent identity/bio, initialized from agent profile |
| `objectives` | list | Topics the agent focuses on |
| `key_events` | list | Notable events tracked across rounds |

Auto-populated from agent profiles (Reddit JSON or Twitter CSV) on first load. Updated in-place via `save_core_memory()`.

### Archival Memory (ChromaDB)

Persistent vector store using `chromadb.PersistentClient`, stored at:
```
<DATA_DIR>/simulations/<simulation_id>/chroma_db/
```

Collection name: `archival_memory`.

**Embedding**: Uses `EmbeddingClient` (configured via `Config.get_graph_search_embedder_config()`). If the embedder is unavailable, falls back to **keyword search** (term overlap scoring).

**Entity Normalization**: When storing memories, agent names are canonicalized: if the text doesn't start with the agent name, it's prepended as `Agent [<name>]: <text>`.

**Migration**: On init, if `experimental_memory.json` (old JSON format) exists, it's automatically migrated to ChromaDB and the old file is renamed to `.migrated`.

## Interface (MemoryProvider)

Both `ZepMemoryProvider` (baseline) and `ExperimentalMemoryService` (experimental) implement:

```python
class MemoryProvider(ABC):
    def add_memories(self, activities: List[Dict[str, Any]]) -> None
    def retrieve(self, query: str, k: int = 5) -> Dict[str, Any]
    def get_stats(self) -> Dict[str, Any]
```

### `retrieve()` output format

| Mode | Return structure |
|------|-----------------|
| **Experimental** | `{"core_memory": {...}, "archival_memory": [...], "_meta": {"mode": "experimental", "results_count": N, "latency_ms": X}}` |
| **Baseline (Zep)** | `{"facts": [...], "episodes": [...], ...}` (Zep API response) |

> The `_meta` field is experimental-specific; baseline returns native Zep format. For A/B comparison, the `results.json` captures high-level metrics (results count, latency, mode) rather than raw response structure.

## Mode Switching

Memory mode is controlled by environment variables, resolved via `MemoryMode` enum:

| Priority | Variable | Effect |
|----------|----------|--------|
| 1 | `MEMORY_MODE=experimental` | Active experimental mode |
| 2 | `MEMORY_MODE=baseline` | Active baseline mode |
| 3 | `USE_EXPERIMENTAL_MEMORY=true` | Backward compat → experimental |
| 4 | (default) | Baseline |

`MemoryFactory.create_provider()` inspects the resolved mode and returns the appropriate provider. Mode switches are logged via `log_mode_switch()`.

## Metrics

`MemoryMetrics` (singleton) tracks per-retrieval events:

- **Per-agent**: retrieval count, total results, average latency
- **Per-round**: retrieval count, total results
- **Global**: total retrievals, total results, average latency, mode breakdown
- **Log**: last 1000 `MemoryRetrievalLog` entries (timestamped, query, provider class)

Access via `get_metrics()`.

```python
from app.services.memory_mode import get_metrics

summary = get_metrics().get_summary()
# {"total_retrievals": 12, "total_results": 58, "avg_latency_ms": 85.3,
#  "mode_breakdown": {"experimental": 6, "baseline": 6}, ...}
```

## File Layout

```
backend/app/services/
├── experimental_memory.py   # ExperimentalMemoryService implementation
├── memory_factory.py         # MemoryFactory — creates provider by mode
├── memory_mode.py            # MemoryMode enum, MemoryMetrics, resolve logic
├── memory_provider.py         # ABC interface
└── zep_memory_provider.py    # Baseline (Zep) implementation
```

Per-simulation data:
```
<DATA_DIR>/simulations/<simulation_id>/
├── core_memory.json           # Core memory state
├── chroma_db/                 # ChromaDB persistent storage
└── experimental_memory.json.migrated  # Old format backup (after migration)
```

## Configuration in Experiment YAML

```yaml
# Baseline config
memory_mode: baseline
extra_env:
  MEMORY_MODE: baseline
  USE_EXPERIMENTAL_MEMORY: "false"

# Experimental config
memory_mode: experimental
extra_env:
  MEMORY_MODE: experimental
  USE_EXPERIMENTAL_MEMORY: "true"
```

## Risks & Known Issues

1. **Embedding unavailable**: If `EmbeddingClient` can't connect (no Ollama/embedding server), falls back to keyword search. Keyword search is significantly less precise.
2. **ChromaDB format**: ChromaDB stores data in platform-specific binary format. Snapshots from one OS/arch may not load on another.
3. **No cross-simulation isolation beyond directory**: Each simulation gets its own ChromaDB path, but there's no access-control boundary.
4. **Fallback count**: `fallback_count` is tracked in-memory only — not persisted across restarts.

## Related

- Experiment harness: [`docs/experiment_harness.md`](experiment_harness.md)
- Baseline config: [`configs/memory_baseline.yaml`](../configs/memory_baseline.yaml)
- Experimental config: [`configs/memory_experimental.yaml`](../configs/memory_experimental.yaml)
- Example case config: [`configs/experiments/example_case.yaml`](../configs/experiments/example_case.yaml)