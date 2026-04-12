"""W2.3.5 — Modular lore and direction context injection for AI/runtime context assembly.

Selectively injects only relevant module guidance instead of dumping broad static
content every turn. Enables the runtime to surface lore, direction, scene guidance,
and character guidance only when they matter for the current situation.

LoreDirectionContext is distinct from:
- short-term turn context (immediate turn state)
- session history (historical progression)
- progression summary (aggregate structural signals)
- relationship-axis context (interpersonal dynamics)
- future AI request assembly (full prompt building)
"""

from __future__ import annotations

from app.content.module_models import ContentModule
from app.runtime.lore_direction_context_types import LoreDirectionContext, ModuleGuidanceUnit
from app.runtime.narrative_threads import NarrativeThreadSet
from app.runtime.progression_summary import ProgressionSummary
from app.runtime.relationship_context import RelationshipAxisContext
from app.runtime.session_history import SessionHistory


def derive_lore_direction_context(
    module: ContentModule,
    current_scene_id: str,
    history: SessionHistory,
    progression_summary: ProgressionSummary,
    relationship_context: RelationshipAxisContext,
    thread_set: NarrativeThreadSet | None = None,
) -> LoreDirectionContext:
    """Derive selective lore and direction context from module and runtime signals.

    Deterministically selects only the most relevant guidance units based on:
    - Current scene
    - Recent triggers and characters
    - Progression level (early/middle/late/ended)
    - Active relationship axes and conflicts
    - Ending state
    - Task 1C: progression momentum, stall count, recent canonical consequences

    Args:
        module: The ContentModule to extract guidance from.
        current_scene_id: The current scene/phase ID.
        history: Session history for trigger analysis.
        progression_summary: Progression state for phase-appropriate guidance.
        relationship_context: Active relationships for relevant guidance.
        thread_set: Task 1D optional derived threads (same pass; None if no commit this derivation).

    Returns:
        A bounded LoreDirectionContext with only relevant guidance.
    """
    from app.runtime.lore_direction_context_derivation import assemble_lore_direction_context_payload

    selected_units, selection_rationale, total_units = assemble_lore_direction_context_payload(
        module,
        current_scene_id,
        history,
        progression_summary,
        relationship_context,
        thread_set=thread_set,
    )
    return LoreDirectionContext(
        selected_units=selected_units,
        total_available_units=total_units,
        selection_rationale=selection_rationale,
        module_id=module.metadata.module_id,
        derived_from_turn=progression_summary.last_turn_covered,
    )
