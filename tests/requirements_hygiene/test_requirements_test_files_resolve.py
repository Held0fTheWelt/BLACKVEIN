"""Static validation of backend/requirements-test.txt (no backend app imports).

These tests run from the repository root with only pytest installed, so CI and
contributors can verify the requirement file graph before a full backend install.

Run (repo root):

    python -m pip install pytest
    python -m pytest tests/requirements_hygiene/ -q
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"
REQUIREMENTS_TEST = BACKEND_ROOT / "requirements-test.txt"
REQUIREMENTS_PROD = BACKEND_ROOT / "requirements.txt"
REQUIREMENTS_DEV = BACKEND_ROOT / "requirements-dev.txt"


def _walk_requirement_files(entry: Path) -> list[Path]:
    """Resolve -r includes recursively; all paths must exist."""
    if not entry.is_file():
        pytest.fail(f"requirements file missing: {entry}")

    resolved: list[Path] = []
    stack: list[Path] = [entry.resolve()]

    while stack:
        path = stack.pop()
        if path in resolved:
            continue
        resolved.append(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("-r ") or line.startswith("--requirement "):
                _, _, rest = line.partition(" ")
                inc = rest.strip().strip('"').strip("'")
                if not inc:
                    pytest.fail(f"empty -r in {path}")
                nxt = (path.parent / inc).resolve()
                if not nxt.is_file():
                    pytest.fail(f"missing -r target {nxt} referenced from {path}")
                stack.append(nxt)
    return resolved


def test_requirements_test_file_exists() -> None:
    assert REQUIREMENTS_TEST.is_file(), "backend/requirements-test.txt must exist"
    assert REQUIREMENTS_PROD.is_file(), "backend/requirements.txt must exist"


def test_requirements_test_includes_production_file() -> None:
    """Nested -r must pull backend/requirements.txt (clean-env single-command install)."""
    text = REQUIREMENTS_TEST.read_text(encoding="utf-8")
    assert re.search(r"^\s*-r\s+requirements\.txt\s*$", text, re.MULTILINE), (
        "requirements-test.txt must contain '-r requirements.txt' so one pip install "
        "from backend/ pulls production deps"
    )


def test_all_nested_requirement_files_exist() -> None:
    chain = _walk_requirement_files(REQUIREMENTS_TEST)
    assert REQUIREMENTS_PROD.resolve() in chain, "requirements.txt must be reachable from requirements-test.txt"


def test_requirements_test_lists_pytest_stack() -> None:
    lower = REQUIREMENTS_TEST.read_text(encoding="utf-8").lower()
    assert "pytest" in lower
    assert "pytest-asyncio" in lower or "pytest_asyncio" in lower
    assert "pytest-cov" in lower or "pytest_cov" in lower
    assert "pytest-timeout" in lower or "pytest_timeout" in lower


def test_requirements_test_lists_flask_explicitly() -> None:
    """Backend conftest imports Flask; operators must see it in requirements-test."""
    text = REQUIREMENTS_TEST.read_text(encoding="utf-8")
    assert re.search(
        r"(?m)^\s*flask\s*[>=<]",
        text,
        re.IGNORECASE,
    ), "requirements-test.txt must name flask explicitly (in addition to -r requirements.txt)"


def test_requirements_txt_declares_flask() -> None:
    """Production file must keep Flask — otherwise -r chain loses the app runtime."""
    text = REQUIREMENTS_PROD.read_text(encoding="utf-8")
    assert re.search(
        r"(?m)^\s*flask\s*[>=<]",
        text,
        re.IGNORECASE,
    ), "backend/requirements.txt must declare flask for backend tests"


def _dependency_lines(path: Path) -> list[str]:
    """Return stripped requirement lines (skip comments, blank, and ``-r`` includes)."""
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r ") or line.startswith("--requirement "):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def test_root_pyproject_dependencies_include_backend_pytest_closure() -> None:
    """Root ``pip install -e .`` must ship the backend Flask + pytest pins (agent default).

    Autonomous sandboxes install only the hub editable; ``[project.dependencies]`` must
    mirror ``backend/requirements.txt``, pytest lines from ``backend/requirements-dev.txt``,
    and anyio / exceptiongroup from ``backend/requirements-test.txt`` so no second pip step
    is required for ``python tests/run_tests.py --suite backend``.
    """
    assert ROOT_PYPROJECT.is_file()
    hub_text = ROOT_PYPROJECT.read_text(encoding="utf-8")
    assert "dependencies = [" in hub_text, "root pyproject.toml must declare [project] dependencies"

    prod_lines = _dependency_lines(REQUIREMENTS_PROD)
    assert prod_lines, "backend/requirements.txt must list production dependencies"
    for dep in prod_lines:
        if dep == "pyyaml>=6.0,<7":
            # Hub uses a stricter floor (historical root pin) while staying within backend's range.
            assert "pyyaml>=6.0.1,<7" in hub_text or dep in hub_text, (
                "root pyproject.toml must pin pyyaml compatible with backend/requirements.txt "
                "(expected pyyaml>=6.0.1,<7 or pyyaml>=6.0,<7)"
            )
            continue
        assert dep in hub_text, (
            f"root pyproject.toml dependencies must include the same pin as backend/requirements.txt: {dep!r}"
        )

    dev_lines = _dependency_lines(REQUIREMENTS_DEV)
    # requirements-dev starts with ``-r requirements.txt``; remainder is pytest stack.
    pytestish = [d for d in dev_lines if d.lower().startswith("pytest")]
    assert pytestish, "backend/requirements-dev.txt must list pytest-related packages after -r"
    for dep in pytestish:
        assert dep in hub_text, (
            f"root pyproject.toml dependencies must include pytest stack line from requirements-dev.txt: {dep!r}"
        )

    # requirements-test.txt pins async helpers used by backend tests on 3.10.
    test_only = _dependency_lines(REQUIREMENTS_TEST)
    for marker in ("anyio>=", "exceptiongroup>="):
        matching = [d for d in test_only if d.startswith(marker)]
        assert matching, f"backend/requirements-test.txt must declare {marker}"
        assert matching[0] in hub_text, (
            f"root pyproject.toml dependencies must include {matching[0]!r} from requirements-test.txt"
        )
