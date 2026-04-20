"""Manifest loading and suite-specific config extraction."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def manifest_path(project_root: Path) -> Path:
    """Return canonical manifest path under project root."""
    return project_root / "fy-manifest.yaml"


def load_manifest(project_root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Load manifest if present; return (manifest, warnings)."""
    path = manifest_path(project_root)
    if not path.is_file():
        alt = project_root / "fy-manifest.yml"
        if not alt.is_file():
            return None, []
        path = alt
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return None, [f"manifest_load_error: {exc}"]
    if raw is None:
        return None, ["manifest_empty"]
    if not isinstance(raw, dict):
        return None, ["manifest_not_object"]
    warnings: list[str] = []
    if "manifestVersion" not in raw:
        warnings.append("manifest_missing_manifestVersion")
    return raw, warnings


def suite_config(manifest: dict[str, Any] | None, suite_name: str) -> dict[str, Any]:
    """Return suite-specific config map from manifest."""
    if not manifest:
        return {}
    suites = manifest.get("suites")
    if not isinstance(suites, dict):
        return {}
    cfg = suites.get(suite_name)
    return cfg if isinstance(cfg, dict) else {}


def roots_for_suite(
    *,
    manifest: dict[str, Any] | None,
    suite_name: str,
    key: str = "roots",
) -> list[str]:
    """Read suite root list from manifest config if present."""
    cfg = suite_config(manifest, suite_name)
    raw = cfg.get(key)
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for value in raw:
        if isinstance(value, str) and value.strip():
            out.append(value.strip())
    return out
