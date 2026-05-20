"""Enforce runtime module placement and lazy canonical/transitional namespaces."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import app.runtime.package_classification as pc


def _runtime_root() -> Path:
    return Path(__file__).resolve().parents[2] / "app" / "runtime"


def test_runtime_root_modules_partition_matches_disk() -> None:
    root_stems = {
        p.stem
        for p in _runtime_root().glob("*.py")
        if p.stem not in ("__init__", "package_classification")
    }
    package_names = {
        p.name
        for p in _runtime_root().iterdir()
        if p.is_dir()
        and (p / "__init__.py").exists()
        and p.name not in ("__pycache__", "canonical", "transitional")
    }
    packaged_stems = {
        p.stem: package
        for package in package_names
        for p in (_runtime_root() / package).glob("*.py")
        if p.stem != "__init__"
    }

    assert root_stems == pc.GLOBAL_RUNTIME_MODULE_NAMES
    assert pc._ALL_RUNTIME_ROOT_MODULES == pc.GLOBAL_RUNTIME_MODULE_NAMES
    assert package_names == pc.RUNTIME_PACKAGE_NAMES
    assert packaged_stems == pc.RUNTIME_MODULE_PACKAGES
    assert root_stems | set(packaged_stems) == pc._ALL_RUNTIME_MODULE_NAMES
    assert pc._ALL_RUNTIME_MODULE_NAMES == (
        pc.CANONICAL_RUNTIME_MODULE_NAMES | pc.TRANSITIONAL_RUNTIME_MODULE_NAMES
    )


def test_runtime_module_import_paths_are_importable() -> None:
    for name in pc._ALL_RUNTIME_MODULE_NAMES:
        module = importlib.import_module(pc.runtime_module_import_path(name))
        assert module.__name__ == pc.runtime_module_import_path(name)


def test_canonical_lazy_import_loads_runtime_submodule() -> None:
    from app.runtime.canonical import runtime_models, validators

    assert hasattr(runtime_models, "SessionState")
    assert validators.__name__ == "app.runtime.validation.validators"


def test_transitional_lazy_import_loads_runtime_submodule() -> None:
    from app.runtime.transitional import turn_executor

    assert hasattr(turn_executor, "execute_turn")


def test_wrong_layer_namespace_raises() -> None:
    transitional = importlib.import_module("app.runtime.transitional")
    with pytest.raises(AttributeError):
        getattr(transitional, "runtime_models")

    canonical = importlib.import_module("app.runtime.canonical")
    with pytest.raises(AttributeError):
        getattr(canonical, "turn_executor")
