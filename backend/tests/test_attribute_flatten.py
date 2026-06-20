"""
Unit tests for the Neo4j attribute flattening fix.

Root cause: graphiti-core 0.28.2's bulk_utils.add_nodes_and_edges_bulk_tx does
`entity_data.update(node.attributes or {})` for the Neo4j branch, and the
resulting Cypher does `SET n = $entity_data`. If any value in `attributes`
is a dict (nested), list-of-dicts, datetime, set, or any other non-primitive,
Neo4j rejects it with:
  "Property values can only be of primitive types or arrays thereof.
   Encountered: Map{}"

These tests verify the fix in graphiti_backend.py:
- _flatten_for_neo4j() coerces any value to a Neo4j-safe primitive or
  list-of-primitives.
- _flatten_attributes() applies that coercion to a dict, logging every key
  that had to be coerced.
- _apply_flatten_pass() mutates Pydantic v2 model fields in-place.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SKIP_FLASK_INIT", "1")

import json
import unittest
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from pathlib import Path

from app.graph.graphiti_backend import (
    _flatten_for_neo4j,
    _flatten_attributes,
    _apply_flatten_pass,
)


def _is_neo4j_safe(v):
    """Recursively check that a value is one of: primitive | list of primitives."""
    if v is None or isinstance(v, (str, int, float, bool)):
        return True
    if isinstance(v, list):
        return all(_is_neo4j_safe(x) for x in v)
    return False


class TestFlattenForNeo4j(unittest.TestCase):

    def test_primitives_passthrough(self):
        for v, t in [("hello", str), (42, int), (3.14, float),
                     (True, bool), (False, bool), (None, type(None))]:
            self.assertEqual(_flatten_for_neo4j(v), v, f"failed for {v!r}")
            self.assertIs(type(_flatten_for_neo4j(v)), t, f"type changed for {v!r}")

    def test_dict_becomes_json_string(self):
        d = {"a": 1, "b": "two", "c": [1, 2, 3]}
        result = _flatten_for_neo4j(d)
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), d)

    def test_nested_dict_becomes_json_string(self):
        d = {"outer": {"inner": {"deep": [1, 2, {"x": "y"}]}}}
        result = _flatten_for_neo4j(d)
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), d)

    def test_list_of_dicts_becomes_list_of_json_strings(self):
        d_list = [{"a": 1}, {"b": 2}, {"c": [3, 4]}]
        result = _flatten_for_neo4j(d_list)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        for i, item in enumerate(result):
            self.assertIsInstance(item, str)
            self.assertEqual(json.loads(item), d_list[i])

    def test_list_of_ints_passthrough(self):
        self.assertEqual(_flatten_for_neo4j([1, 2, 3]), [1, 2, 3])

    def test_tuple_becomes_list(self):
        result = _flatten_for_neo4j((1, 2, 3))
        self.assertIsInstance(result, list)
        self.assertEqual(result, [1, 2, 3])

    def test_set_becomes_sorted_list(self):
        result = _flatten_for_neo4j({"c", "a", "b"})
        self.assertIsInstance(result, list)
        self.assertEqual(result, ["a", "b", "c"])

    def test_frozenset_becomes_sorted_list(self):
        result = _flatten_for_neo4j(frozenset([3, 1, 2]))
        self.assertEqual(result, [1, 2, 3])

    def test_datetime_becomes_isoformat_string(self):
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = _flatten_for_neo4j(dt)
        self.assertIsInstance(result, str)
        self.assertEqual(result, "2024-01-15T10:30:45")

    def test_date_becomes_isoformat_string(self):
        d = date(2024, 1, 15)
        result = _flatten_for_neo4j(d)
        self.assertIsInstance(result, str)
        self.assertEqual(result, "2024-01-15")

    def test_uuid_becomes_string(self):
        u = UUID("12345678-1234-5678-1234-567812345678")
        result = _flatten_for_neo4j(u)
        self.assertIsInstance(result, str)
        self.assertEqual(result, str(u))

    def test_decimal_becomes_string(self):
        d = Decimal("99.95")
        result = _flatten_for_neo4j(d)
        self.assertIsInstance(result, str)

    def test_path_becomes_string(self):
        p = Path("/tmp/foo/bar")
        result = _flatten_for_neo4j(p)
        self.assertIsInstance(result, str)
        self.assertEqual(result, str(p))

    def test_mixed_list(self):
        inp = [datetime(2024, 1, 1), "x", {"y": 2}]
        result = _flatten_for_neo4j(inp)
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], str)  # datetime -> str
        self.assertEqual(result[1], "x")
        self.assertIsInstance(result[2], str)  # dict -> json str
        self.assertEqual(json.loads(result[2]), {"y": 2})

    def test_neo4j_safety_property(self):
        """The strong claim: any input -> Neo4j-safe output."""
        adversarial = [
            {"a": [1, {"b": [2, {"c": 3}]}]},
            [{"x": [{"y": "z"}]}],
            [[1, 2], [3, 4]],
            {"set": {1, 2, 3}, "list": [{"a": 1}]},
            datetime.now(),
            {"recursive": {"recursive": {"recursive": "deep"}}},
        ]
        for v in adversarial:
            self.assertTrue(
                _is_neo4j_safe(_flatten_for_neo4j(v)),
                f"output of {v!r} is not Neo4j-safe: {_flatten_for_neo4j(v)!r}",
            )


class TestFlattenAttributes(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(_flatten_attributes({}), {})
        self.assertEqual(_flatten_attributes(None), {})

    def test_flat_attrs_unchanged(self):
        attrs = {"rol": "CEO", "antiguedad": 5, "activo": True}
        result = _flatten_attributes(attrs)
        self.assertEqual(result, attrs)

    def test_real_world_mix(self):
        """A real attributes dict pulled from an LLM extraction."""
        attrs = {
            "rol": "CEO",                                    # passthrough
            "fecha_fundacion": "2020-01-15",                 # string passthrough
            "direccion": {"calle": "Av. Corrientes 1234",    # nested dict
                          "ciudad": "Buenos Aires"},
            "subsidiarias": [{"nombre": "Acme SA",            # list of dicts
                              "pais": "AR"},
                             {"nombre": "Acme USA",
                              "pais": "US"}],
            "contactos": [{"email": "a@b.com",                # list of dicts
                           "tags": ["ceo", "fundador"]}],
            "created": datetime(2024, 1, 15),                # datetime
            "tags": {"fundador", "tech", "ai"},               # set
            "metadata": {"nested": {"a": 1, "b": [2, 3]}},   # deep
        }
        result = _flatten_attributes(attrs)
        # Every value must be Neo4j-safe
        for k, v in result.items():
            self.assertTrue(_is_neo4j_safe(v), f"key {k!r} -> {v!r} not safe")
        # Round-trip: parse JSON-stringified dicts back
        self.assertEqual(json.loads(result["direccion"]),
                         {"calle": "Av. Corrientes 1234", "ciudad": "Buenos Aires"})
        self.assertEqual([json.loads(s) for s in result["subsidiarias"]],
                         [{"nombre": "Acme SA", "pais": "AR"},
                          {"nombre": "Acme USA", "pais": "US"}])
        # Set -> sorted list
        self.assertEqual(result["tags"], ["ai", "fundador", "tech"])
        # Datetime -> ISO str
        self.assertEqual(result["created"], "2024-01-15T00:00:00")


class TestApplyFlattenPass(unittest.TestCase):
    """The flattener must mutate Pydantic v2 model fields correctly."""

    def test_mutates_pydantic_v2_field(self):
        from pydantic import BaseModel, Field
        from typing import Any, Dict, Optional

        class FakeNode(BaseModel):
            uuid: str = "test-uuid"
            attributes: Dict[str, Any] = Field(default_factory=dict)

        class FakeEdge(BaseModel):
            uuid: str = "test-edge"
            attributes: Dict[str, Any] = Field(default_factory=dict)

        node = FakeNode(attributes={
            "name": "Acme",
            "address": {"street": "Main 123"},
            "tags": {"a", "b"},
        })
        edge = FakeEdge(attributes={
            "fact": "Acme was founded in 2020",
            "meta": {"source": "wikipedia", "nested": {"x": 1}},
        })

        _apply_flatten_pass([node], [edge])

        # Node attributes now all primitives
        for k, v in node.attributes.items():
            self.assertTrue(_is_neo4j_safe(v), f"node {k!r} not safe")
        self.assertIsInstance(node.attributes["address"], str)
        self.assertEqual(json.loads(node.attributes["address"]),
                         {"street": "Main 123"})
        self.assertEqual(node.attributes["tags"], ["a", "b"])

        # Same for edge
        for k, v in edge.attributes.items():
            self.assertTrue(_is_neo4j_safe(v), f"edge {k!r} not safe")
        self.assertIsInstance(edge.attributes["meta"], str)
        self.assertEqual(json.loads(edge.attributes["meta"])["source"], "wikipedia")

    def test_handles_empty_lists(self):
        from pydantic import BaseModel, Field
        from typing import Any, Dict

        class FakeNode(BaseModel):
            attributes: Dict[str, Any] = Field(default_factory=dict)

        node = FakeNode(attributes={})
        # Should not raise
        _apply_flatten_pass([node], [])
        self.assertEqual(node.attributes, {})

    def test_handles_frozen_pydantic_via_object_setattr(self):
        """If a model has model_config frozen=True, we bypass via object.__setattr__."""
        from pydantic import BaseModel, ConfigDict, Field
        from typing import Any, Dict

        class FrozenNode(BaseModel):
            model_config = ConfigDict(frozen=True)
            attributes: Dict[str, Any] = Field(default_factory=dict)

        node = FrozenNode(attributes={"x": {"y": 1}})
        # Should not raise, even though model is frozen
        _apply_flatten_pass([node], [])
        self.assertIsInstance(node.attributes["x"], str)


if __name__ == "__main__":
    unittest.main(verbosity=2)
