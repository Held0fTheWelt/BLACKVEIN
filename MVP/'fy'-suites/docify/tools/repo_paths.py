"""Resolve monorepo root and Docify hub directory paths."""
from __future__ import annotations

from pathlib import Path

from fy_platform.core.project_resolver import resolve_project_root

FY_SUITES_DIRNAME = "'fy'-suites"


def repo_root(*, start: Path | None = None) -> Path:
    """Return project root via shared resolver with manifest-friendly fallback."""
    return resolve_project_root(start=start, marker_text=None)


def docify_hub_dir(repo: Path | None = None) -> Path:
    """Return the Docify hub directory (``'fy'-suites/docify``)."""
    r = repo or repo_root()
    return r / FY_SUITES_DIRNAME / "docify"


def docify_hub_rel_posix(repo: Path | None = None) -> str:
    """Hub directory as a repo-relative POSIX path for messages."""
    r = repo or repo_root()
    return docify_hub_dir(r).relative_to(r).as_posix()
