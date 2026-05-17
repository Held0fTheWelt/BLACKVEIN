"""Load and select authored director_surface_hints from content module hints/."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


def _safe_load_mapping(path: Path) -> dict[str, Any]:
    if yaml is None or not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data if isinstance(data, dict) else {}


def _hint_record_from_file(path: Path, payload: dict[str, Any]) -> dict[str, Any] | None:
    block = payload.get("director_surface_hint")
    if not isinstance(block, dict):
        return None
    hint_type = str(block.get("hint_type") or "").strip()
    text = str(block.get("text") or "").strip()
    if not hint_type or not text:
        return None
    source = str(block.get("source") or path.as_posix()).strip()
    record: dict[str, Any] = {
        "hint_type": hint_type,
        "text": text[:280],
        "source": source,
        "player_visible": bool(block.get("player_visible", False)),
    }
    hint_id = str(block.get("id") or "").strip()
    if hint_id:
        record["hint_id"] = hint_id
    return record


def _applies_when_matches(
    applies_when: dict[str, Any],
    *,
    scene_id: str,
    pacing_mode: str,
    guidance_phase_key: str,
) -> bool:
    if not applies_when:
        return True

    phase_keys = applies_when.get("guidance_phase_keys")
    if isinstance(phase_keys, list) and phase_keys:
        if guidance_phase_key not in {str(item).strip() for item in phase_keys}:
            return False

    scene_ids = applies_when.get("scene_ids")
    if isinstance(scene_ids, list) and scene_ids:
        if scene_id not in {str(item).strip() for item in scene_ids}:
            return False

    pacing_modes = applies_when.get("pacing_modes")
    if isinstance(pacing_modes, list) and pacing_modes:
        if pacing_mode not in {str(item).strip() for item in pacing_modes}:
            return False

    return True


def load_module_director_surface_hints(module_dir: Path) -> list[dict[str, Any]]:
    """Load all authored hints listed in hints/index.yaml (or hints/**/*.yaml)."""
    hints_root = module_dir / "hints"
    if not hints_root.is_dir():
        return []

    index_path = hints_root / "index.yaml"
    catalog = _safe_load_mapping(index_path).get("director_surface_hints_catalog")
    entries: list[str] = []
    if isinstance(catalog, dict):
        raw_entries = catalog.get("entries")
        if isinstance(raw_entries, list):
            entries = [str(item).strip() for item in raw_entries if str(item).strip()]

    paths: list[Path] = []
    if entries:
        for entry in entries:
            candidate = module_dir / entry
            if candidate.is_file():
                paths.append(candidate)
    else:
        paths = sorted(p for p in hints_root.rglob("*.yaml") if p.name != "index.yaml")

    loaded: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for path in paths:
        payload = _safe_load_mapping(path)
        record = _hint_record_from_file(path, payload)
        if not record:
            continue
        dedupe_key = (
            str(record.get("hint_id") or ""),
            str(record.get("hint_type") or ""),
            str(record.get("text") or ""),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        block = payload.get("director_surface_hint")
        applies_when = block.get("applies_when") if isinstance(block, dict) else {}
        record["_applies_when"] = applies_when if isinstance(applies_when, dict) else {}
        loaded.append(record)
    return loaded


def select_director_surface_hints(
    hints: list[dict[str, Any]],
    *,
    scene_id: str,
    pacing_mode: str,
    guidance_phase_key: str,
) -> list[dict[str, str | bool]]:
    """Return runtime-shaped hint dicts matching the current turn context."""
    selected: list[dict[str, str | bool]] = []
    for record in hints:
        applies_when = record.get("_applies_when")
        if not isinstance(applies_when, dict):
            applies_when = {}
        if not _applies_when_matches(
            applies_when,
            scene_id=scene_id.strip(),
            pacing_mode=pacing_mode.strip(),
            guidance_phase_key=guidance_phase_key.strip(),
        ):
            continue
        selected.append(
            {
                "hint_type": str(record.get("hint_type") or ""),
                "text": str(record.get("text") or "")[:280],
                "source": str(record.get("source") or ""),
                "player_visible": bool(record.get("player_visible", False)),
            }
        )
    return selected
