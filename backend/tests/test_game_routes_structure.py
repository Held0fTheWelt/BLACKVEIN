"""Structural guards for the decomposed game route module."""

from __future__ import annotations

import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
GAME_ROUTE_MODULE = BACKEND_ROOT / "app" / "api" / "v1" / "game_routes.py"
GAME_ROUTE_IMPLEMENTATION_DIR = BACKEND_ROOT / "app" / "api" / "v1" / "game"


def _loader_implementation_files() -> tuple[str, ...]:
    tree = ast.parse(GAME_ROUTE_MODULE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "_IMPLEMENTATION_FILES":
                return tuple(item.value for item in node.value.elts)
    raise AssertionError("game_routes.py does not declare _IMPLEMENTATION_FILES")


def test_game_route_loader_references_existing_named_implementation_files() -> None:
    implementation_files = _loader_implementation_files()
    disk_files = tuple(
        sorted(path.name for path in GAME_ROUTE_IMPLEMENTATION_DIR.glob("*.py"))
    )

    assert sorted(implementation_files) == list(disk_files)
    assert len(implementation_files) == len(set(implementation_files))
    assert all("continuation" not in name for name in implementation_files)
    assert all(not name[0].isdigit() for name in implementation_files)
