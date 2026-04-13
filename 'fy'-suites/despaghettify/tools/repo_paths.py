"""Resolve monorepo root and Despaghettify hub directory (always under ``'fy'-suites/despaghettify``)."""
from __future__ import annotations

from pathlib import Path

# Directory name at repo root (includes literal quote characters).
FY_SUITES_DIRNAME = "'fy'-suites"


def repo_root(*, start: Path | None = None) -> Path:
    """Walk ancestors until the World of Shadows repo root (pyproject + hub marker) is found."""
    p = (start or Path(__file__)).resolve()
    for ancestor in p.parents:
        toml = ancestor / "pyproject.toml"
        if not toml.is_file():
            continue
        try:
            if "world-of-shadows-hub" not in toml.read_text(encoding="utf-8", errors="replace"):
                continue
        except OSError:
            continue
        nested = ancestor / FY_SUITES_DIRNAME / "despaghettify" / "spaghetti-setup.md"
        if nested.is_file():
            return ancestor
    msg = f"Could not resolve repository root from {p}"
    raise RuntimeError(msg)


def despag_hub_dir(repo: Path | None = None) -> Path:
    """Absolute path to the Despaghettify hub (markdown, state, tools package)."""
    r = repo or repo_root()
    nested = r / FY_SUITES_DIRNAME / "despaghettify"
    if (nested / "spaghetti-setup.md").is_file():
        return nested
    msg = f"Despaghettify hub not found under {r / FY_SUITES_DIRNAME / 'despaghettify'}"
    raise RuntimeError(msg)


def despag_hub_rel_posix(repo: Path | None = None) -> str:
    """Repo-relative POSIX path to the hub (for CLI defaults and docs)."""
    hub = despag_hub_dir(repo)
    r = repo or repo_root()
    return hub.resolve().relative_to(r.resolve()).as_posix()


def despag_import_parent(repo: Path | None = None) -> Path:
    """Directory that must be on ``sys.path`` so ``import despaghettify`` resolves."""
    return despag_hub_dir(repo).parent
