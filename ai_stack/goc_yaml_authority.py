"""Canonical YAML authority for God of Carnage (VERTICAL_SLICE_CONTRACT_GOC.md §6.1)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from ai_stack.goc_frozen_vocab import GOC_MODULE_ID

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def goc_module_yaml_dir() -> Path:
    return _repo_root() / "content" / "modules" / GOC_MODULE_ID


def load_goc_canonical_module_yaml() -> dict[str, Any]:
    """Load authoritative module.yaml for god_of_carnage from the repository tree."""
    if yaml is None:
        raise RuntimeError("PyYAML is required to load canonical GoC module YAML.")
    path = goc_module_yaml_dir() / "module.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Canonical GoC module.yaml not found at {path}")
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError("module.yaml must parse to a mapping.")
    mid = data.get("module_id")
    if mid != GOC_MODULE_ID:
        raise ValueError(f"module.yaml module_id mismatch: expected {GOC_MODULE_ID!r}, got {mid!r}")
    return data


@lru_cache(maxsize=1)
def cached_goc_yaml_title() -> str:
    mod = load_goc_canonical_module_yaml()
    title = mod.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Canonical module.yaml must define a non-empty string title.")
    return title.strip()


def detect_builtin_yaml_title_conflict(
    *,
    host_template_id: str | None,
    host_template_title: str | None,
) -> dict[str, Any] | None:
    """If a secondary builtin template contradicts YAML title, return a failure marker payload.

    VERTICAL_SLICE_CONTRACT_GOC.md §6.1 — builtins must not override YAML truth.
    """
    if not host_template_id or host_template_id != "god_of_carnage_solo":
        return None
    if not host_template_title:
        return None
    canonical = cached_goc_yaml_title()
    if host_template_title.strip() == canonical:
        return None
    return {
        "failure_class": "scope_breach",
        "note": "builtins_yaml_title_mismatch",
        "canonical_yaml_title": canonical,
        "host_template_title": host_template_title.strip(),
    }
