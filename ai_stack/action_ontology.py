"""Compatibility surface for the universal action-language adapter."""

from __future__ import annotations

from pathlib import Path

from story_runtime_core.language_adapter import infer_verb_and_action_kind as _infer


def clear_action_ontology_cache() -> None:
    """Kept for tests and callers; the universal ontology has no file cache."""
    return None


def ontology_path(module_id: str, *, content_modules_root: Path | None = None) -> Path:
    """Return a diagnostic pseudo-path for the AI semantic resolution seam."""
    root = Path(content_modules_root) if content_modules_root else Path()
    return root / str(module_id).strip() / "semantic_ai_resolution"


def infer_verb_and_action_kind(
    raw_text: str,
    *,
    module_id: str,
    player_input_kind: str,
    content_modules_root: Path | None = None,
) -> tuple[str, str]:
    return _infer(
        raw_text,
        module_id=module_id,
        player_input_kind=player_input_kind,
        content_modules_root=content_modules_root,
    )
