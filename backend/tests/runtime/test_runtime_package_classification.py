"""Enforce runtime root module partitioning and lazy canonical/transitional namespaces."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import app.runtime.package_classification as pc


def _runtime_root() -> Path:
    return Path(__file__).resolve().parents[2] / "app" / "runtime"


def test_runtime_root_modules_partition_matches_disk() -> None:
    stems = {
        p.stem
        for p in _runtime_root().glob("*.py")
        if p.stem not in ("__init__", "package_classification")
    }
    assert stems == pc._ALL_RUNTIME_ROOT_MODULES
    assert stems == pc.CANONICAL_RUNTIME_MODULE_NAMES | pc.TRANSITIONAL_RUNTIME_MODULE_NAMES


def test_canonical_lazy_import_loads_runtime_submodule() -> None:
    from app.runtime.canonical import runtime_models, validators

    assert hasattr(runtime_models, "SessionState")
    assert validators.__name__ == "app.runtime.validators"


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
