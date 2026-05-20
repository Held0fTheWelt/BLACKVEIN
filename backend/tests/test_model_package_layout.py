"""Model package layout contract."""

from __future__ import annotations

import importlib
from pathlib import Path

import app.models as models


def _models_root() -> Path:
    return Path(__file__).resolve().parents[1] / "app" / "models"


def test_model_root_contains_only_package_entrypoint() -> None:
    root_files = {
        path.name
        for path in _models_root().glob("*.py")
        if path.name != "__init__.py"
    }
    assert root_files == set()


def test_backend_and_world_engine_model_packages_match_exports() -> None:
    backend_files = {
        path.stem
        for path in (_models_root() / "backend").glob("*.py")
        if path.name != "__init__.py"
    }
    world_engine_files = {
        path.stem
        for path in (_models_root() / "world_engine").glob("*.py")
        if path.name != "__init__.py"
    }

    assert backend_files == set(models.BACKEND_MODEL_MODULES)
    assert world_engine_files == set(models.WORLD_ENGINE_MODEL_MODULES)
    assert backend_files.isdisjoint(world_engine_files)


def test_legacy_model_submodule_imports_resolve_to_new_packages() -> None:
    legacy_user = importlib.import_module("app.models.user")
    backend_user = importlib.import_module("app.models.backend.user")
    legacy_slot = importlib.import_module("app.models.game_save_slot")
    world_engine_slot = importlib.import_module("app.models.world_engine.game_save_slot")

    assert legacy_user is backend_user
    assert legacy_slot is world_engine_slot
