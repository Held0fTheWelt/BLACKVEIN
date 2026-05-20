"""Granular runtime package import checks.

These tests make each runtime package selectable as its own pytest slice, while the
module parametrization keeps individual runtime modules visible in test reports.
"""

from __future__ import annotations

import importlib

import pytest

import app.runtime.package_classification as pc


def _package_marker_name(package_name: str) -> str:
    return f"runtime_{package_name}"


def _module_marker_name(module_name: str) -> str:
    package_name = pc.RUNTIME_MODULE_PACKAGES.get(module_name, "global")
    return _package_marker_name(package_name)


@pytest.mark.runtime
@pytest.mark.parametrize(
    "package_name",
    [
        pytest.param(
            package_name,
            marks=getattr(pytest.mark, _package_marker_name(package_name)),
            id=package_name,
        )
        for package_name in sorted(pc.RUNTIME_PACKAGE_NAMES)
    ],
)
def test_runtime_package_imports_as_individual_slice(package_name: str) -> None:
    package = importlib.import_module(f"app.runtime.{package_name}")
    assert package.__name__ == f"app.runtime.{package_name}"


@pytest.mark.runtime
@pytest.mark.parametrize(
    "module_name",
    [
        pytest.param(
            module_name,
            marks=getattr(pytest.mark, _module_marker_name(module_name)),
            id=module_name,
        )
        for module_name in sorted(pc._ALL_RUNTIME_MODULE_NAMES)
    ],
)
def test_runtime_module_imports_from_declared_package(module_name: str) -> None:
    import_path = pc.runtime_module_import_path(module_name)
    module = importlib.import_module(import_path)
    assert module.__name__ == import_path
