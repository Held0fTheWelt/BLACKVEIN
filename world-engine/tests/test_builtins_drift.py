"""Cross-surface SSOT: world-engine builtins must semantically match backend canonical."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.content import builtins as world_engine_builtins

REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL = REPO_ROOT / "backend" / "app" / "content" / "builtins.py"


def _load_backend_builtins():
    spec = importlib.util.spec_from_file_location("backend_content_builtins", CANONICAL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builtins_matches_backend_canonical():
    assert CANONICAL.is_file()
    backend_builtins = _load_backend_builtins()
    backend_templates = backend_builtins.load_builtin_templates()
    world_engine_templates = world_engine_builtins.load_builtin_templates()
    assert set(world_engine_templates) == set(backend_templates)
    for template_id, backend_template in backend_templates.items():
        assert world_engine_templates[template_id].model_dump() == backend_template.model_dump()
