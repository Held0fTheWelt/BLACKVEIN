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
REQUIREMENTS_TEST = BACKEND_ROOT / "requirements-test.txt"
REQUIREMENTS_PROD = BACKEND_ROOT / "requirements.txt"


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
