import os
import sys
from types import SimpleNamespace


_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_REPO_ROOT = os.path.abspath(os.path.join(_BACKEND_DIR, ".."))
for path in (_BACKEND_DIR, _REPO_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.graph.graphiti_backend import prepare_nodes_for_edge_resolution  # noqa: E402


def test_prepare_nodes_for_edge_resolution_bypasses_dedup_when_enabled():
    extracted_nodes = [
        SimpleNamespace(name="inflation", uuid="node-1"),
        SimpleNamespace(name="ipc", uuid="node-2"),
        SimpleNamespace(name="", uuid="node-3"),
    ]

    nodes, uuid_map = prepare_nodes_for_edge_resolution(extracted_nodes, bypass_node_dedup=True)

    assert nodes == extracted_nodes
    assert uuid_map == {"node-1": "node-1", "node-2": "node-2", "node-3": "node-3"}


def test_prepare_nodes_for_edge_resolution_requires_resolver_when_bypass_disabled():
    extracted_nodes = [SimpleNamespace(name="inflation", uuid="node-1")]

    try:
        prepare_nodes_for_edge_resolution(extracted_nodes, bypass_node_dedup=False)
    except NotImplementedError as exc:
        assert "resolver" in str(exc)
    else:
        raise AssertionError("expected NotImplementedError when bypass is disabled")
