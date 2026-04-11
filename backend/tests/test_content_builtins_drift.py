"""Cross-surface SSOT: world-engine builtins must semantically match backend canonical output."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from app.content import builtins as backend_builtins


def _load_world_engine_builtins():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "world-engine" / "app" / "content" / "builtins.py"
    spec = importlib.util.spec_from_file_location("world_engine_content_builtins", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.contract
def test_world_engine_builtins_matches_backend_semantics():
    world_engine_builtins = _load_world_engine_builtins()
    backend_templates = backend_builtins.load_builtin_templates()
    world_engine_templates = world_engine_builtins.load_builtin_templates()
    assert set(world_engine_templates) == set(backend_templates)
    for template_id, backend_template in backend_templates.items():
        assert world_engine_templates[template_id].model_dump() == backend_template.model_dump()
