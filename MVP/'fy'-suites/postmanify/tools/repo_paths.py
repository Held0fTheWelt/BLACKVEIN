"""Resolve monorepo root and Postmanify hub directory."""
from __future__ import annotations

from pathlib import Path

from fy_platform.core.project_resolver import resolve_project_root

FY_SUITES_DIRNAME = "'fy'-suites"


def repo_root(*, start: Path | None = None) -> Path:
    """
    Implement ``repo_root`` for the surrounding module workflow.

    Module context: ``'fy'-suites/postmanify/tools/repo_paths.py`` — keep this routine
    aligned with sibling helpers in the same package.

    Args:
        start: Start for this call. Declared type: ``Path | None``. (keyword-only)

    Returns:
        Value typed as ``Path`` for downstream use.

    Raises:
        RuntimeError: An invariant was violated or the environment rejected the operation.

    """
    return resolve_project_root(start=start, marker_text=None)


def postmanify_hub_dir(repo: Path | None = None) -> Path:
    """
    Implement ``postmanify_hub_dir`` for the surrounding module workflow.

    Module context: ``'fy'-suites/postmanify/tools/repo_paths.py`` — keep this routine
    aligned with sibling helpers in the same package.

    Args:
        repo: Repo for this call. Declared type: ``Path | None``. (positional or keyword)

    Returns:
        Value typed as ``Path`` for downstream use.

    """
    r = repo or repo_root()
    return r / FY_SUITES_DIRNAME / "postmanify"
