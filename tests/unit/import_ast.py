"""AST helpers for import-boundary tests."""

from __future__ import annotations

import ast
from pathlib import Path


def _is_type_checking_test(node: ast.If) -> bool:
    test = node.test
    return (
        isinstance(test, ast.Name)
        and test.id == "TYPE_CHECKING"
        or isinstance(test, ast.Attribute)
        and isinstance(test.value, ast.Name)
        and test.value.id == "typing"
        and test.attr == "TYPE_CHECKING"
    )


class _ImportCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.modules: set[str] = set()
        self._type_checking_depth = 0

    def visit_If(self, node: ast.If) -> None:
        if _is_type_checking_test(node):
            self._type_checking_depth += 1
            for child in node.body:
                self.visit(child)
            self._type_checking_depth -= 1
            for child in node.orelse:
                self.visit(child)
            return
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        if self._type_checking_depth == 0:
            for alias in node.names:
                self.modules.add(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if self._type_checking_depth == 0 and node.module is not None:
            self.modules.add(node.module)


def collect_import_modules(path: Path) -> set[str]:
    """Return top-level module names imported by a Python source file."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    collector = _ImportCollector()
    collector.visit(tree)
    return collector.modules


def module_matches_prefix(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(f"{prefix}.")


def modules_matching_prefixes(modules: set[str], prefixes: tuple[str, ...]) -> set[str]:
    return {
        module
        for module in modules
        if any(module_matches_prefix(module, prefix) for prefix in prefixes)
    }
