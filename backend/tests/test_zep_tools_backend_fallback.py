from app.services.zep_tools import ZepToolsService


class ProviderWithoutBackend:
    pass


class ProviderWithBackend:
    def __init__(self, backend):
        self.backend = backend


def test_zep_tools_uses_graph_backend_when_memory_provider_has_no_backend(monkeypatch):
    sentinel_backend = object()

    monkeypatch.setenv("USE_EXPERIMENTAL_MEMORY", "true")
    monkeypatch.setattr(
        "app.services.memory_factory.MemoryFactory.create_provider",
        staticmethod(lambda **kwargs: ProviderWithoutBackend()),
    )
    monkeypatch.setattr(
        "app.services.zep_tools.get_graph_backend",
        lambda api_key=None: sentinel_backend,
    )

    service = ZepToolsService(api_key="test-key", simulation_id="sim-test")

    assert service.backend is sentinel_backend


def test_zep_tools_prefers_provider_backend(monkeypatch):
    provider_backend = object()
    fallback_backend = object()

    monkeypatch.delenv("USE_EXPERIMENTAL_MEMORY", raising=False)
    monkeypatch.setattr(
        "app.services.memory_factory.MemoryFactory.create_provider",
        staticmethod(lambda **kwargs: ProviderWithBackend(provider_backend)),
    )
    monkeypatch.setattr(
        "app.services.zep_tools.get_graph_backend",
        lambda api_key=None: fallback_backend,
    )

    service = ZepToolsService(api_key="test-key", simulation_id="sim-test")

    assert service.backend is provider_backend
