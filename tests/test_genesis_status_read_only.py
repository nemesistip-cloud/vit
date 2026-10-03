"""Regression checks for read-only Genesis status requests."""

import ast
import unittest
from pathlib import Path


class GenesisStatusReadOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source_path = (
            Path(__file__).resolve().parents[1]
            / "backend"
            / "app"
            / "api"
            / "routes"
            / "genesis.py"
        )
        cls.module = ast.parse(source_path.read_text(encoding="utf-8"))
        cls.handler = next(
            node
            for node in cls.module.body
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "get_genesis_status"
        )

    def test_status_endpoint_remains_a_get_route(self):
        route_decorators = [
            decorator
            for decorator in self.handler.decorator_list
            if isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and decorator.func.attr == "get"
        ]

        self.assertTrue(
            any(
                decorator.args
                and isinstance(decorator.args[0], ast.Constant)
                and decorator.args[0].value == "/status"
                for decorator in route_decorators
            )
        )

    def test_status_handler_does_not_persist_or_commit(self):
        persistence_calls = []
        for node in ast.walk(self.handler):
            if not isinstance(node, ast.Call):
                continue

            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            else:
                continue

            if name in {"_persist_genesis_state", "add", "commit", "flush", "delete"}:
                persistence_calls.append(name)

        self.assertEqual(persistence_calls, [])


if __name__ == "__main__":
    unittest.main()