"""Project root resolution helpers shared by fy suites."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence


def _marker_match(path: Path, marker_text: str | None) -> bool:
    if marker_text is None:
        return True
    try:
        return marker_text in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def resolve_project_root(
    *,
    start: Path | None = None,
    env_var: str | None = None,
    marker_file: str = "pyproject.toml",
    marker_text: str | None = None,
    manifest_names: Sequence[str] = ("fy-manifest.yaml", "fy-manifest.yml"),
) -> Path:
    """Resolve project root from environment override or ancestor traversal."""
    if env_var:
        forced = os.environ.get(env_var, "").strip()
        if forced:
            forced_path = Path(forced).expanduser().resolve()
            if forced_path.is_dir():
                marker = forced_path / marker_file
                if marker.is_file() and _marker_match(marker, marker_text):
                    return forced_path
                for mf in manifest_names:
                    if (forced_path / mf).is_file():
                        return forced_path

    probe = (start or Path(__file__)).resolve()
    for ancestor in probe.parents:
        marker = ancestor / marker_file
        if marker.is_file() and _marker_match(marker, marker_text):
            return ancestor
        if any((ancestor / name).is_file() for name in manifest_names):
            return ancestor
    msg = f"Could not resolve project root from {probe}"
    raise RuntimeError(msg)
