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
) -> LoreDirectionContext:
    """Derive selective lore and direction context from module and runtime signals.

    Deterministically selects only the most relevant guidance units based on:
    - Current scene
    - Recent triggers and characters
    - Progression level (early/middle/late/ended)
    - Active relationship axes and conflicts
    - Ending state

    Args:
        module: The ContentModule to extract guidance from.
        current_scene_id: The current scene/phase ID.
        history: Session history for trigger analysis.
        progression_summary: Progression state for phase-appropriate guidance.
        relationship_context: Active relationships for relevant guidance.

    Returns:
        A bounded LoreDirectionContext with only relevant guidance.
    """
    selected_units = []
    selection_rationale = []
    total_units = 0

    # Count total available guidance units
    total_units = (
        len(module.characters)
        + len(module.relationship_axes)
        + len(module.trigger_definitions)
        + len(module.scene_phases)
        + len(module.ending_conditions)
        + len(module.phase_transitions)
    )

    # 1. Scene/Phase guidance (highest priority)
    if current_scene_id and current_scene_id in module.scene_phases:
        phase = module.scene_phases[current_scene_id]
        selected_units.append(
            ModuleGuidanceUnit(
                unit_type="phase",
                unit_id=phase.id,
                guidance_text=phase.description,
                applicability_scope="scene",
                relevance_signals=["current_scene"],
            )
        )
        selection_rationale.append(f"current_scene={current_scene_id}")

    # 2. Character guidance for characters involved in recent triggers
    recent_character_mentions = set()
    if history.entries:
        # Look at last 5 entries for character mentions from triggers
        for entry in history.entries[-5:]:
            for trigger_name in entry.detected_triggers:
                # Extract character mentions from trigger names
                parts = trigger_name.lower().split("_")
                for part in parts:
                    if part in module.characters:
                        recent_character_mentions.add(part)

        for char_id in sorted(recent_character_mentions):
            if char_id in module.characters and len(selected_units) < 15:
                char = module.characters[char_id]
                selected_units.append(
                    ModuleGuidanceUnit(
                        unit_type="character",
                        unit_id=char.id,
                        guidance_text=char.baseline_attitude,
                        applicability_scope="character",
                        relevance_signals=["recent_trigger_involvement"],
                    )
                )
        if recent_character_mentions:
            selection_rationale.append(f"recent_characters={','.join(sorted(recent_character_mentions))}")

    # 3. Relationship axis guidance for active relationships
    for axis_pair in relationship_context.highest_salience_axis or []:
        axis_id = None
        # Try to find relationship axis by name/character pair
        for rel_id, rel_axis in module.relationship_axes.items():
            if len(selected_units) < 15:
                selected_units.append(
                    ModuleGuidanceUnit(
                        unit_type="relationship",
                        unit_id=rel_axis.id,
                        guidance_text=rel_axis.description,
                        applicability_scope="relationship",
                        relevance_signals=["active_relationship"],
                    )
                )
                break

    if relationship_context.highest_salience_axis:
        selection_rationale.append(f"salient_relationship={relationship_context.highest_salience_axis}")

    # 4. Trigger guidance for recent triggers
    if history.entries:
        recent_triggers = set()
        for entry in history.entries[-3:]:
            recent_triggers.update(entry.detected_triggers)

        for trigger_name in sorted(recent_triggers):
            if trigger_name in module.trigger_definitions and len(selected_units) < 15:
                trigger = module.trigger_definitions[trigger_name]
                selected_units.append(
                    ModuleGuidanceUnit(
                        unit_type="trigger",
                        unit_id=trigger.id,
                        guidance_text=trigger.description,
                        applicability_scope="trigger",
                        relevance_signals=["recent_trigger"],
                    )
                )

        if recent_triggers:
            selection_rationale.append(f"recent_triggers={','.join(sorted(recent_triggers))}")

    # 5. Phase transition guidance if approaching phase boundary
    if current_scene_id and current_scene_id in module.scene_phases:
        phase = module.scene_phases[current_scene_id]
        for trans_id, transition in module.phase_transitions.items():
            if transition.from_phase == phase.id and len(selected_units) < 15:
                selected_units.append(
                    ModuleGuidanceUnit(
                        unit_type="transition",
                        unit_id=trans_id,
                        guidance_text=transition.transition_action or "Phase transition",
                        applicability_scope="scene",
                        relevance_signals=["phase_transition"],
                    )
                )

    # 6. Ending guidance if ending reached
    if progression_summary.ending_reached and progression_summary.ending_id:
        if progression_summary.ending_id in module.ending_conditions:
            ending = module.ending_conditions[progression_summary.ending_id]
            selected_units.append(
                ModuleGuidanceUnit(
                    unit_type="ending",
                    unit_id=ending.id,
                    guidance_text=ending.description,
                    applicability_scope="ending",
                    relevance_signals=["ending_reached"],
                )
            )
            selection_rationale.append(f"ending_reached={progression_summary.ending_id}")

    # 7. Escalation/conflict guidance if relationships escalating
    if relationship_context.has_escalation_markers:
        # Add general conflict guidance if available
        for axis_id, axis in module.relationship_axes.items():
            if axis.escalation and len(selected_units) < 15:
                selected_units.append(
                    ModuleGuidanceUnit(
                        unit_type="relationship",
                        unit_id=f"{axis_id}_escalation",
                        guidance_text=str(axis.escalation),
                        applicability_scope="relationship",
                        relevance_signals=["escalation_active"],
                    )
                )
                break
        selection_rationale.append("escalation_detected")

    return LoreDirectionContext(
        selected_units=selected_units[:15],  # Enforce bounded limit
        total_available_units=total_units,
        selection_rationale=selection_rationale,
        module_id=module.metadata.module_id,
        derived_from_turn=progression_summary.last_turn_covered,
    )
