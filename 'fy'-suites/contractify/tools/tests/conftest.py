"""Hermetic test defaults: Contractify unit tests must not depend on a full World of Shadows checkout.

ZIP extracts and partial trees still run ``pytest`` here when ``repo_root()`` is patched to a
synthetic layout that satisfies ``discovery`` / ``drift_analysis`` / ``hub_cli`` expectations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from contractify.tools.minimal_repo import build_minimal_contractify_test_repo


_MODULES_WITHOUT_REPO_PATCH = frozenset(
    {
        "contractify.tools.tests.test_models",
        "contractify.tools.tests.test_example_artifacts",
        "contractify.tools.tests.test_runtime_mvp_spine",
    }
)


@pytest.fixture(autouse=True)
def _hermetic_contractify_repo(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Patch ``repo_root()`` for every test module except pure unit tests."""
    if request.module.__name__ in _MODULES_WITHOUT_REPO_PATCH:
        yield
        return
    fake = build_minimal_contractify_test_repo(tmp_path)
    monkeypatch.setattr("contractify.tools.repo_paths.repo_root", lambda start=None: fake)
    monkeypatch.setattr("contractify.tools.hub_cli.repo_root", lambda start=None: fake)
    yield
