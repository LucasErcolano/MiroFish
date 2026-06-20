"""Business service package.

Historically this module eagerly re-exported every service, which meant
importing ``app.services`` required all optional third-party dependencies
for the whole backend. That made narrow imports like
``app.services.wiki_memory`` fragile in minimal test environments.

We now expose the public wiki-memory API eagerly and load the remaining
service re-exports only when their dependencies are available.
"""

from __future__ import annotations

from .wiki_memory import (
    CompileResult,
    WikiCompiler,
    WikiMeta,
    WikiPage,
    WikiPageType,
    WikiSection,
    WikiStore,
    WikiTimelineEntry,
)

__all__ = [
    "WikiStore",
    "WikiPage",
    "WikiPageType",
    "WikiSection",
    "WikiTimelineEntry",
    "WikiMeta",
    "WikiCompiler",
    "CompileResult",
]

_OPTIONAL_EXPORTS = [
    (".ontology_generator", ["OntologyGenerator"]),
    (".graph_builder", ["GraphBuilderService"]),
    (".text_processor", ["TextProcessor"]),
    (".zep_entity_reader", ["ZepEntityReader", "EntityNode", "FilteredEntities"]),
    (".oasis_profile_generator", ["OasisProfileGenerator", "OasisAgentProfile"]),
    (".simulation_manager", ["SimulationManager", "SimulationState", "SimulationStatus"]),
    (
        ".simulation_config_generator",
        [
            "SimulationConfigGenerator",
            "SimulationParameters",
            "AgentActivityConfig",
            "TimeSimulationConfig",
            "EventConfig",
            "PlatformConfig",
        ],
    ),
    (
        ".simulation_runner",
        [
            "SimulationRunner",
            "SimulationRunState",
            "RunnerStatus",
            "AgentAction",
            "RoundSummary",
        ],
    ),
    (
        ".zep_graph_memory_updater",
        ["ZepGraphMemoryUpdater", "ZepGraphMemoryManager", "AgentActivity"],
    ),
    (
        ".simulation_ipc",
        [
            "SimulationIPCClient",
            "SimulationIPCServer",
            "IPCCommand",
            "IPCResponse",
            "CommandType",
            "CommandStatus",
        ],
    ),
]

for _module_name, _symbols in _OPTIONAL_EXPORTS:
    try:
        _module = __import__(f"{__name__}{_module_name}", fromlist=_symbols)
    except ImportError:
        continue
    for _symbol in _symbols:
        globals()[_symbol] = getattr(_module, _symbol)
        __all__.append(_symbol)


