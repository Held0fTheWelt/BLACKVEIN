"""Structural guards for AI Engineer Suite service modules."""

from __future__ import annotations

import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SERVICE_FACADE = BACKEND_ROOT / "app" / "services" / "ai_stack" / "ai_engineer_suite_service.py"
IMPLEMENTATION_DIR = BACKEND_ROOT / "app" / "services" / "ai_stack" / "ai_engineer_suite"


def _facade_imported_modules() -> set[str]:
    tree = ast.parse(SERVICE_FACADE.read_text(encoding="utf-8"))
    modules: set[str] = set()
    prefix = "ai_engineer_suite."
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            if node.module.startswith(prefix):
                filename = f"{node.module.removeprefix(prefix)}.py"
                if filename != "common.py":
                    modules.add(filename)
    return modules


def test_ai_engineer_suite_facade_imports_named_modules() -> None:
    implementation_files = {
        path.name
        for path in IMPLEMENTATION_DIR.glob("*.py")
        if path.name not in {"__init__.py", "common.py"}
    }

    assert _facade_imported_modules() == implementation_files
    assert all("continuation" not in name for name in implementation_files)
    assert all(not name[0].isdigit() for name in implementation_files)
    assert all("mvp" not in name.lower() for name in implementation_files)


def test_ai_engineer_suite_modules_are_not_source_loaders() -> None:
    files = [SERVICE_FACADE, *IMPLEMENTATION_DIR.glob("*.py")]
    offenders = [
        path.name
        for path in files
        if "SOURCE =" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []
