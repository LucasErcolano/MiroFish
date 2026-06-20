"""
End-to-end test of the attribute flattening fix against a real Neo4j instance.

This bypasses the LLM extraction step (which costs money) and instead creates
a real `EntityNode` and `EntityEdge` with a deliberately pathological
`attributes` payload (nested dicts, lists of dicts, datetimes), then calls
the *actual* graphiti-core save path (`add_nodes_and_edges_bulk_tx`) that
triggers the `CypherTypeError: Encountered: Map{}` bug.

Without the fix: this raises neo4j.exceptions.CypherTypeError.
With the fix:   the nodes/edges are saved and the attributes are stored as
                JSON-serialized strings under each top-level key.

Run from /tmp/MiroFish with the venv active:
    /tmp/.mvpvenv/bin/python backend/tests/test_e2e_flatten_fix.py
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SKIP_FLASK_INIT", "1")

# Use a unique graph_id so this test doesn't pollute previous runs
TEST_GRAPH_ID = f"test_flatten_{uuid.uuid4().hex[:8]}"

from neo4j import AsyncGraphDatabase
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------
# Setup: real Neo4j driver (wrapped by graphiti-core for proper interface)
# --------------------------------------------------------------------------

from dotenv import dotenv_values
ENV = dotenv_values("/tmp/MiroFish/.env")
NEO4J_URI = ENV.get("GRAPHITI_URI", "bolt://172.17.0.1:7687")
NEO4J_USER = ENV.get("GRAPHITI_USER", "neo4j")
NEO4J_PASSWORD = "mirofishpassword"
NEO4J_DATABASE = ENV.get("GRAPHITI_DATABASE", "neo4j")

# Use graphiti-core's Neo4jDriver wrapper -- it sets `provider` class attr
# and exposes the proper async session/transaction interface the bulk save expects.
from graphiti_core.driver.neo4j_driver import Neo4jDriver
print(f"Connecting to Neo4j at {NEO4J_URI} as {NEO4J_USER}")
driver = Neo4jDriver(
    uri=NEO4J_URI,
    user=NEO4J_USER,
    password=NEO4J_PASSWORD,
    database=NEO4J_DATABASE,
)
print(f"  driver.provider = {driver.provider}")

# --------------------------------------------------------------------------
# Import the real graphiti-core pieces
# --------------------------------------------------------------------------

from graphiti_core.nodes import EntityNode, EpisodicNode, EpisodeType
from graphiti_core.edges import EntityEdge
from graphiti_core.embedder import EmbedderClient
from graphiti_core.utils.bulk_utils import add_nodes_and_edges_bulk_tx
from graphiti_core.driver.driver import GraphProvider


# Fake embedder (no LLM, no API calls)
class FakeEmbedder(EmbedderClient):
    async def create(self, input_data: list[str]) -> list[list[float]]:
        # Return a tiny deterministic vector (1-dim) -- Neo4j will accept it
        return [[0.0] for _ in input_data]

    async def create_batch(self, input_data: list[str]) -> list[list[float]]:
        return [[0.0] for _ in input_data]


# Fake EpisodicNode (we don't need it for the bulk save, but the function
# expects one for episodic_edges construction)
episodic = EpisodicNode(
    uuid=str(uuid.uuid4()),
    name="test_episode",
    group_id=TEST_GRAPH_ID,
    labels=[],
    source=EpisodeType.text,
    content="test content",
    source_description="text",
    created_at=datetime.now(timezone.utc),
    valid_at=datetime.now(timezone.utc),
)

# --------------------------------------------------------------------------
# Step 1: try the bulk save WITHOUT our flattening fix (simulating the
# pre-patch behaviour). This is the reproduction of the original bug.
# --------------------------------------------------------------------------
print("\n" + "=" * 70)
print("REPRODUCTION: save EntityNode with nested dict attributes")
print("=" * 70)

# Use the SAME structure the LLM extraction produces when the model
# generates an attribute that is itself a structured object.
evil_node_attrs = {
    "rol": "CEO",                                              # ok primitive
    "direccion": {                                              # NESTED DICT -- the bug
        "calle": "Av. Corrientes 1234",
        "ciudad": "Buenos Aires",
        "codigo_postal": "C1043",
    },
    "subsidiarias": [                                            # LIST OF DICTS -- the bug
        {"nombre": "Acme SA", "pais": "AR"},
        {"nombre": "Acme USA", "pais": "US"},
    ],
    "fecha_fundacion": "2020-01-15",                             # OK string (no datetime
                                                                   # to avoid client-side
                                                                   # ValueError that masks
                                                                   # the CypherTypeError)
    "metadata": {"nested": {"deep": {"a": 1, "b": [2, 3]}}},
}

evil_edge_attrs = {
    "fact": "Acme was founded in 2020 by John Smith",
    "context": {"location": "Buenos Aires", "year": 2020},       # NESTED DICT
    "tags": ["primary", "founding"],                             # ok
}

evil_node = EntityNode(
    uuid=str(uuid.uuid4()),
    name="Acme Corp",
    group_id=TEST_GRAPH_ID,
    labels=["Company"],
    summary="A test entity with pathological attributes",
    attributes=evil_node_attrs,
)
evil_node.name_embedding = [0.0]

evil_edge = EntityEdge(
    uuid=str(uuid.uuid4()),
    source_node_uuid=evil_node.uuid,
    target_node_uuid=evil_node.uuid,  # self-loop is fine for test
    name="FOUNDED_BY",
    fact="Acme was founded in 2020 by John Smith",
    group_id=TEST_GRAPH_ID,
    episodes=[episodic.uuid],
    created_at=datetime.now(timezone.utc),
    attributes=evil_edge_attrs,
)
evil_edge.fact_embedding = [0.0]


async def attempt_save_without_fix():
    """Demonstrates the original bug."""
    session = driver.session(database=NEO4J_DATABASE)
    try:
        await add_nodes_and_edges_bulk_tx(
            session,
            [episodic], [], [evil_node], [evil_edge], FakeEmbedder(), driver=driver
        )
    finally:
        await session.close()


async def attempt_save_with_fix():
    """Saves the same data after applying our flattening fix."""
    from app.graph.graphiti_backend import _apply_flatten_pass
    _apply_flatten_pass([evil_node], [evil_edge])
    print("After fix, node.attributes:", evil_node.attributes)
    print("After fix, edge.attributes:", evil_edge.attributes)
    session = driver.session(database=NEO4J_DATABASE)
    try:
        await add_nodes_and_edges_bulk_tx(
            session,
            [episodic], [], [evil_node], [evil_edge], FakeEmbedder(), driver=driver
        )
    finally:
        await session.close()


async def verify_persisted():
    """Read back the node/edge from Neo4j and verify the attributes are intact."""
    from graphiti_core.models.nodes.node_db_queries import get_entity_node_return_query
    from graphiti_core.nodes import get_entity_node_from_record
    from graphiti_core.models.edges.edge_db_queries import get_entity_edge_return_query
    from graphiti_core.edges import get_entity_edge_from_record

    session = driver.session(database=NEO4J_DATABASE)
    try:
        # Node
        query = (
            "MATCH (n:Entity {uuid: $uuid}) "
            "RETURN "
            + get_entity_node_return_query(driver.provider)
        )
        result = await session.run(query, uuid=evil_node.uuid, routing_="r")
        records = [r async for r in result]
        assert len(records) == 1, f"expected 1 node record, got {len(records)}"
        node = get_entity_node_from_record(records[0], driver.provider)
        print("\n--- Read back from Neo4j: ---")
        print("  name:", node.name)
        print("  summary:", node.summary)
        print("  attributes:", node.attributes)

        # Edge -- the return fragment uses aliases (n)-[e]-(m)
        eq_query = (
            "MATCH (n)-[e:RELATES_TO {uuid: $uuid}]->(m) "
            "RETURN "
            + get_entity_edge_return_query(driver.provider)
        )
        result = await session.run(eq_query, uuid=evil_edge.uuid, routing_="r")
        records = [r async for r in result]
        assert len(records) == 1, f"expected 1 edge record, got {len(records)}"
        edge = get_entity_edge_from_record(records[0], driver.provider)
        print("  edge.fact:", edge.fact)
        print("  edge.attributes:", edge.attributes)

        # Verify our flattened JSON-serialized dicts are present and parseable
        import json
        assert "direccion" in node.attributes, "direccion missing from persisted attrs"
        assert isinstance(node.attributes["direccion"], str), \
            f"direccion should be JSON string, got {type(node.attributes['direccion'])}"
        parsed = json.loads(node.attributes["direccion"])
        assert parsed["calle"] == "Av. Corrientes 1234", \
            f"round-trip lost data: {parsed}"
        print(f"\n  ✅ direccion round-trip OK: {parsed}")

        assert "subsidiarias" in node.attributes
        assert isinstance(node.attributes["subsidiarias"], list)
        assert all(isinstance(s, str) for s in node.attributes["subsidiarias"])
        subs = [json.loads(s) for s in node.attributes["subsidiarias"]]
        assert subs[0]["nombre"] == "Acme SA"
        print(f"  ✅ subsidiarias round-trip OK: {subs}")

        assert "context" in edge.attributes
        ctx = json.loads(edge.attributes["context"])
        assert ctx["location"] == "Buenos Aires"
        print(f"  ✅ edge.context round-trip OK: {ctx}")
    finally:
        await session.close()


async def cleanup():
    session = driver.session(database=NEO4J_DATABASE)
    try:
        await session.run(
            "MATCH (n {group_id: $gid}) DETACH DELETE n",
            gid=TEST_GRAPH_ID,
        )
    finally:
        await session.close()


async def main():
    print(f"\nUsing test graph_id: {TEST_GRAPH_ID}")
    try:
        # Try without fix -- should fail with CypherTypeError
        print("\n[1] Attempting save WITHOUT fix (expected to fail)...")
        try:
            await attempt_save_without_fix()
            print("  ⚠️  Save succeeded without fix -- bug not reproduced?")
            print("     (Possible if your Neo4j version auto-flattens)")
        except Exception as e:
            err_type = type(e).__name__
            err_msg = str(e)[:200]
            if "Map" in err_msg or "primitive" in err_msg or "CypherTypeError" in err_type:
                print(f"  ✅ Bug reproduced: {err_type}: {err_msg}")
            else:
                print(f"  ❌ Different error: {err_type}: {err_msg}")
                raise

        # Try with fix -- should succeed
        print("\n[2] Attempting save WITH fix (expected to succeed)...")
        await attempt_save_with_fix()
        print("  ✅ Save with fix succeeded")

        # Verify data integrity
        print("\n[3] Verifying data integrity from Neo4j...")
        await verify_persisted()
        print("  ✅ All data round-tripped correctly")

    finally:
        # Clean up
        print("\n[cleanup] removing test nodes/edges from Neo4j...")
        await cleanup()
        await driver.close()
        print("  done.")


if __name__ == "__main__":
    asyncio.run(main())
