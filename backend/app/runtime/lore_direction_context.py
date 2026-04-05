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

from app.content.module_models import ContentModule, RelationshipAxis
from app.runtime.narrative_threads import NarrativeThreadSet
from app.runtime.progression_summary import ProgressionSummary
from app.runtime.relationship_context import RelationshipAxisContext
from app.runtime.session_history import SessionHistory

_MAX_SALIENT_AXES_FOR_LORE = 3
_STATE_CHANGED_PREFIX = "state_changed:"


def _module_axes_matching_pair(
    module: ContentModule, char_a: str, char_b: str
) -> list[tuple[str, RelationshipAxis]]:
    """Deterministic module axes whose metadata references both character ids."""
    a, b = char_a.lower(), char_b.lower()
    matches: list[tuple[str, RelationshipAxis]] = []
    for rid, rax in sorted(module.relationship_axes.items(), key=lambda x: x[0]):
        blob = f"{rid} {rax.name} {' '.join(rax.relationships)}".lower()
        if a in blob and b in blob:
            matches.append((rid, rax))
    return matches


def _append_relationship_units_for_pair(
    selected_units: list[ModuleGuidanceUnit],
    module: ContentModule,
    char_a: str,
    char_b: str,
    *,
    relevance: list[str],
) -> None:
    for _rid, rax in _module_axes_matching_pair(module, char_a, char_b):
        if len(selected_units) >= 15:
            return
        if any(u.unit_id == rax.id and u.unit_type == "relationship" for u in selected_units):
            continue
        selected_units.append(
            ModuleGuidanceUnit(
                unit_type="relationship",
                unit_id=rax.id,
                guidance_text=rax.description,
                applicability_scope="relationship",
                relevance_signals=list(relevance),
            )
        )


def _character_ids_from_recent_consequences(consequences: list[str]) -> set[str]:
    """Parse ``state_changed:characters.<id>...`` paths only (bounded, deterministic)."""
    out: set[str] = set()
    for c in consequences:
        if not c.startswith(_STATE_CHANGED_PREFIX):
            continue
        path = c[len(_STATE_CHANGED_PREFIX) :].strip()
        if not path.startswith("characters."):
            continue
        rest = path[len("characters.") :]
        if not rest:
            continue
        cid = rest.split(".", 1)[0].strip().lower()
        if len(cid) > 1:
            out.add(cid)
    return out


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
    selected_units: list[ModuleGuidanceUnit] = []
    selection_rationale: list[str] = []

    total_units = (
        len(module.characters)
        + len(module.relationship_axes)
        + len(module.trigger_definitions)
        + len(module.scene_phases)
        + len(module.ending_conditions)
        + len(module.phase_transitions)
    )

    # Task 1C: bounded continuity signals (deterministic tags)
    selection_rationale.append(f"momentum={progression_summary.progression_momentum}")
    if progression_summary.stalled_turn_count > 0:
        selection_rationale.append(f"stalled_turns={progression_summary.stalled_turn_count}")
    if progression_summary.recent_canonical_consequences:
        sc = sum(1 for x in progression_summary.recent_canonical_consequences if x.startswith(_STATE_CHANGED_PREFIX))
        if sc > 0:
            selection_rationale.append("consequence_profile=state_delta_heavy")

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

    # 2. Character guidance for characters involved in recent triggers + consequence paths
    recent_character_mentions: set[str] = set()
    if history.entries:
        for entry in history.entries[-5:]:
            for trigger_name in entry.detected_triggers:
                parts = trigger_name.lower().split("_")
                for part in parts:
                    if part in module.characters:
                        recent_character_mentions.add(part)

    recent_character_mentions.update(
        _character_ids_from_recent_consequences(progression_summary.recent_canonical_consequences)
    )

    for char_id in sorted(recent_character_mentions):
        if char_id in module.characters and len(selected_units) < 15:
            char = module.characters[char_id]
            rel_signals = ["recent_trigger_involvement"]
            if char_id in _character_ids_from_recent_consequences(
                progression_summary.recent_canonical_consequences
            ):
                rel_signals.append("recent_canonical_consequence_path")
            selected_units.append(
                ModuleGuidanceUnit(
                    unit_type="character",
                    unit_id=char.id,
                    guidance_text=char.baseline_attitude,
                    applicability_scope="character",
                    relevance_signals=rel_signals,
                )
            )
    if recent_character_mentions:
        selection_rationale.append(f"recent_characters={','.join(sorted(recent_character_mentions))}")

    # 3. Relationship axis guidance — Task 1C / §4: use tuple as pair or top salient_axes (bounded)
    hs = relationship_context.highest_salience_axis
    if hs is not None:
        _append_relationship_units_for_pair(
            selected_units,
            module,
            hs[0],
            hs[1],
            relevance=["active_relationship", "highest_salience_pair"],
        )
        selection_rationale.append(f"salient_relationship={hs}")

    seen_pairs: set[tuple[str, str]] = set()
    if hs is not None:
        seen_pairs.add(tuple(sorted((hs[0], hs[1]))))

    for ax in relationship_context.salient_axes[:_MAX_SALIENT_AXES_FOR_LORE]:
        if len(selected_units) >= 15:
            break
        pair = tuple(sorted((ax.character_a, ax.character_b)))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        _append_relationship_units_for_pair(
            selected_units,
            module,
            ax.character_a,
            ax.character_b,
            relevance=["active_relationship", "salient_axis_top"],
        )

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
    transitions_added = 0
    if current_scene_id and current_scene_id in module.scene_phases:
        phase = module.scene_phases[current_scene_id]
        for trans_id, transition in sorted(module.phase_transitions.items(), key=lambda x: x[0]):
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
                transitions_added += 1
                if transitions_added >= 2:
                    break

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

    # 6b. Approaching resolution (momentum) — one ending preview, bounded
    if (
        progression_summary.progression_momentum == "resolving"
        and not progression_summary.ending_reached
        and module.ending_conditions
        and len(selected_units) < 15
    ):
        selection_rationale.append("approaching_resolution")
        eid, ec = sorted(module.ending_conditions.items(), key=lambda x: x[0])[0]
        if not any(u.unit_id == ec.id and u.unit_type == "ending" for u in selected_units):
            selected_units.append(
                ModuleGuidanceUnit(
                    unit_type="ending",
                    unit_id=ec.id,
                    guidance_text=ec.description,
                    applicability_scope="ending",
                    relevance_signals=["momentum_resolving"],
                )
            )

    # 7. Escalation/conflict guidance if relationships escalating
    if relationship_context.has_escalation_markers:
        for axis_id, axis in sorted(module.relationship_axes.items(), key=lambda x: x[0]):
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

    # 8. Stalled momentum — reinforce scene phase direction without new unit explosion
    if progression_summary.progression_momentum == "stalled" and progression_summary.stalled_turn_count >= 2:
        selection_rationale.append("continuity_stalled_scene_hold")

    # Task 1D: bounded thread tags (only when threads were updated this derivation)
    if thread_set is not None and thread_set.active:
        top = thread_set.active[0]
        selection_rationale.append(f"thread_kind={top.thread_kind}")
        selection_rationale.append(f"thread_status={top.status}")

    return LoreDirectionContext(
        selected_units=selected_units[:15],
        total_available_units=total_units,
        selection_rationale=selection_rationale,
        module_id=module.metadata.module_id,
        derived_from_turn=progression_summary.last_turn_covered,
    )
