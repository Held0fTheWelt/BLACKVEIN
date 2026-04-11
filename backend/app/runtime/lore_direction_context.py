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

from typing import Optional

from pydantic import BaseModel, Field

from app.content.module_models import ContentModule
from app.runtime.narrative_threads import NarrativeThreadSet
from app.runtime.progression_summary import ProgressionSummary
from app.runtime.relationship_context import RelationshipAxisContext
from app.runtime.session_history import SessionHistory


class ModuleGuidanceUnit(BaseModel):
    """A single unit of selectable module guidance.

    Represents a discrete piece of lore, direction, or guidance that can be
    injected into context when relevant.

    Attributes:
        unit_type: Category of guidance (character, relationship, trigger, scene, phase, ending).
        unit_id: Identifier from the module (e.g., character ID, trigger ID).
        guidance_text: The actual guidance content (description, baseline, etc.).
        applicability_scope: Where this applies (scene, character, relationship, etc.).
        relevance_signals: What runtime signals make this relevant.
    """

    unit_type: str  # character, relationship, trigger, scene, phase, ending, transition
    unit_id: str  # ID from module (character id, trigger id, phase id, etc.)
    guidance_text: str  # The actual guidance content
    applicability_scope: str  # character, relationship, scene, trigger, phase
    relevance_signals: list[str] = Field(default_factory=list)  # What makes this relevant


class LoreDirectionContext(BaseModel):
    """Bounded, selectively injected module guidance for current situation.

    Contains only the most relevant lore and direction guidance for the current
    runtime situation, deterministically selected from module content.

    Attributes:
        selected_units: Most relevant guidance units (bounded to 15).
        total_available_units: Count of all guidance units available from module.
        selection_rationale: What signals drove the selection.
        module_id: Which module this guidance comes from.
        derived_from_turn: When this context was computed.
    """

    selected_units: list[ModuleGuidanceUnit] = Field(default_factory=list)
    total_available_units: int = 0
    selection_rationale: list[str] = Field(default_factory=list)
    module_id: str = ""
    derived_from_turn: int = 0


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
