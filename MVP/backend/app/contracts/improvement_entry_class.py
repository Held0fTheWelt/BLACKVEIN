"""Improvement path typed entry classes (``docs/ROADMAP_MVP_GoC.md`` §7.5–7.6, gate G8)."""

from __future__ import annotations

from enum import Enum
from typing import Any


class ImprovementEntryClass(str, Enum):
    """Roadmap improvement entry discriminant (bounded improvement loop)."""

    runtime_issue_improvement = "runtime_issue_improvement"
    module_completeness_improvement = "module_completeness_improvement"
    semantic_quality_improvement = "semantic_quality_improvement"


def default_improvement_entry_class() -> ImprovementEntryClass:
    """Explicit default when the client omits ``improvement_entry_class`` (not used for invalid strings)."""
    return ImprovementEntryClass.runtime_issue_improvement


def parse_improvement_entry_class(raw: str | None) -> ImprovementEntryClass:
    """Parse a roadmap improvement entry class; raises ``ValueError`` if missing or unknown."""
    if raw is None or not str(raw).strip():
        raise ValueError("improvement_entry_class_required")
    try:
        return ImprovementEntryClass(str(raw).strip())
    except ValueError as exc:
        raise ValueError(f"unknown_improvement_entry_class:{raw!r}") from exc


def resolve_improvement_entry_class_for_create(
    explicit_top_level: str | None,
    metadata: dict[str, Any] | None,
) -> ImprovementEntryClass:
    """Single resolution path for variant creation: top-level wins; metadata may supply; conflict is an error."""
    meta_raw: str | None = None
    if metadata and isinstance(metadata.get("improvement_entry_class"), str):
        m = str(metadata["improvement_entry_class"]).strip()
        meta_raw = m if m else None
    top = str(explicit_top_level).strip() if explicit_top_level and str(explicit_top_level).strip() else None
    if top and meta_raw and top != meta_raw:
        raise ValueError("improvement_entry_class_metadata_conflict")
    chosen = top or meta_raw
    if not chosen:
        return default_improvement_entry_class()
    return parse_improvement_entry_class(chosen)


def coalesce_improvement_entry_class_from_stored_record(raw: Any) -> str:
    """For persisted records: default only when the field is absent or blank; invalid stored values raise."""
    if raw is None:
        return default_improvement_entry_class().value
    if isinstance(raw, str) and not raw.strip():
        return default_improvement_entry_class().value
    return parse_improvement_entry_class(str(raw).strip()).value
