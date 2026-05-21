"""Structural guards for operational governance route modules."""

from __future__ import annotations

import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROUTE_ANCHOR = BACKEND_ROOT / "app" / "api" / "v1" / "operational_governance_routes.py"
IMPLEMENTATION_DIR = BACKEND_ROOT / "app" / "api" / "v1" / "operational_governance"


def _imported_implementation_modules() -> set[str]:
    tree = ast.parse(ROUTE_ANCHOR.read_text(encoding="utf-8"))
    modules: set[str] = set()
    prefix = "operational_governance."
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.level == 1 and node.module.startswith(prefix):
                filename = f"{node.module.removeprefix(prefix)}.py"
                if filename != "common.py":
                    modules.add(filename)
    return modules


def test_operational_governance_anchor_imports_named_modules() -> None:
    implementation_files = {
        path.name
        for path in IMPLEMENTATION_DIR.glob("*.py")
        if path.name not in {"__init__.py", "common.py"}
    }

    assert _imported_implementation_modules() == implementation_files
    assert all("continuation" not in name for name in implementation_files)
    assert all(not name[0].isdigit() for name in implementation_files)
    assert all("mvp" not in name.lower() for name in implementation_files)


def test_operational_governance_modules_are_not_source_loaders() -> None:
    files = [ROUTE_ANCHOR, *IMPLEMENTATION_DIR.glob("*.py")]
    offenders = [
        path.name
        for path in files
        if "SOURCE =" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_operational_governance_function_names_use_clear_language() -> None:
    bad_names: list[str] = []
    for path in IMPLEMENTATION_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and "mvp" in node.name.lower():
                bad_names.append(f"{path.name}:{node.name}")

    assert bad_names == []
