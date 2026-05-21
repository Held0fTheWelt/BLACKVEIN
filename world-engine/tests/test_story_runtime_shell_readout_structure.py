"""Structural guards for story runtime shell readout modules."""

from __future__ import annotations

import ast
from pathlib import Path


WORLD_ENGINE_ROOT = Path(__file__).resolve().parents[1]
SHELL_READOUT_FACADE = WORLD_ENGINE_ROOT / "app" / "story_runtime_shell_readout.py"
IMPLEMENTATION_DIR = WORLD_ENGINE_ROOT / "app" / "shell_readout"


def _facade_imported_modules() -> set[str]:
    tree = ast.parse(SHELL_READOUT_FACADE.read_text(encoding="utf-8"))
    modules: set[str] = set()
    prefix = "shell_readout."
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            if node.module.startswith(prefix):
                filename = f"{node.module.removeprefix(prefix)}.py"
                if filename != "common.py":
                    modules.add(filename)
    return modules


def test_shell_readout_facade_imports_named_modules() -> None:
    implementation_files = {
        path.name
        for path in IMPLEMENTATION_DIR.glob("*.py")
        if path.name not in {"__init__.py", "common.py"}
    }

    assert _facade_imported_modules() == implementation_files
    assert all("continuation" not in name for name in implementation_files)
    assert all(not name[0].isdigit() for name in implementation_files)
    assert all("mvp" not in name.lower() for name in implementation_files)


def test_shell_readout_modules_are_not_source_loaders() -> None:
    files = [SHELL_READOUT_FACADE, *IMPLEMENTATION_DIR.glob("*.py")]
    offenders = [
        path.name
        for path in files
        if "SOURCE =" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []
