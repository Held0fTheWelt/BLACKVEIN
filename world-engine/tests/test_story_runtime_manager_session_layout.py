"""Granular story runtime manager session package tests."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from app.story_runtime import StoryRuntimeManager
from app.story_runtime import manager as manager_package


MANAGER_ROOT = Path(__file__).resolve().parents[1] / "app" / "story_runtime" / "manager"

SESSION_MODULES = {
    "manager_init_and_persistence",
    "recoverable_rejection_and_sessions",
    "session_lifecycle",
    "session_loop_governance",
    "session_memory_policies",
    "session_payloads",
    "session_state_api",
}


@pytest.mark.runtime
def test_session_related_manager_modules_live_in_session_package() -> None:
    root_files = {path.name for path in MANAGER_ROOT.glob("*.py")}
    session_files = {path.name for path in (MANAGER_ROOT / "session").glob("*.py")}

    misplaced_files = sorted(f"{module_name}.py" for module_name in SESSION_MODULES if f"{module_name}.py" in root_files)

    assert misplaced_files == []
    assert (MANAGER_ROOT / "session" / "__init__.py").is_file()
    assert {f"{module_name}.py" for module_name in SESSION_MODULES}.issubset(session_files)


@pytest.mark.runtime
@pytest.mark.parametrize("module_name", sorted(SESSION_MODULES))
def test_session_manager_slices_import_from_session_package(module_name: str) -> None:
    module = importlib.import_module(f"app.story_runtime.manager.session.{module_name}")

    assert module.__name__ == f"app.story_runtime.manager.session.{module_name}"
    assert getattr(module, "__all__", None)


@pytest.mark.runtime
def test_manager_package_keeps_public_session_exports() -> None:
    payloads = importlib.import_module("app.story_runtime.manager.session.session_payloads")
    policies = importlib.import_module("app.story_runtime.manager.session.session_memory_policies")

    assert manager_package.StorySession is payloads.StorySession
    assert manager_package.story_session_to_payload is payloads.story_session_to_payload
    assert manager_package.story_session_from_payload is policies.story_session_from_payload


@pytest.mark.runtime
def test_runtime_manager_uses_session_mixins_from_session_package() -> None:
    mixin_modules = {base.__module__ for base in StoryRuntimeManager.__mro__}

    assert {
        "app.story_runtime.manager.session.manager_init_and_persistence",
        "app.story_runtime.manager.session.recoverable_rejection_and_sessions",
        "app.story_runtime.manager.session.session_lifecycle",
        "app.story_runtime.manager.session.session_loop_governance",
        "app.story_runtime.manager.session.session_state_api",
    }.issubset(mixin_modules)
