"""W2.0.5 — Derive the next canonical runtime situation from committed state.

After a turn completes, the runtime must evaluate whether the current scene continues,
transitions to a valid next scene, or reaches an ending condition.

This module provides the derivation logic that inspects committed SessionState against
ContentModule rules to produce the next active situation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.content.module_models import ContentModule
from app.runtime.scene_legality import SceneTransitionLegality
from app.runtime.runtime_models import EventLogEntry, SessionState, SessionStatus


class NextSituation(BaseModel):
    """Result of situation derivation after a committed turn.

    Attributes:
        current_scene_id: Active scene ID (may be same as before or new)
        situation_status: "continue" | "transitioned" | "ending_reached"
        ending_id: ID of ending reached, if situation_status == "ending_reached"
        ending_outcome: Outcome details if ending reached
        is_terminal: True if ending reached
        derivation_reason: Explanation of how situation was derived
    """

    current_scene_id: str
    situation_status: str  # "continue", "transitioned", "ending_reached"
    ending_id: str | None = None
    ending_outcome: dict[str, Any] | None = None
    is_terminal: bool = False
    derivation_reason: str = ""


def derive_next_situation(
    session: SessionState,
    module: ContentModule,
    detected_triggers: list[str] | None = None,
) -> NextSituation:
    """Derive the next canonical situation from the committed post-turn state.

    Evaluates transitions and endings in order:
    1. Check for active ending conditions
    2. If no ending, check for valid scene transitions
    3. If no transition, continue in current scene

    Condition evaluation:
    - If detected_triggers provided, evaluate conditions against it
    - If conditions are empty, transition/ending always active (unconditional)
    - If conditions are present but detected_triggers is None, skip

    Args:
        session: Post-turn committed SessionState with updated canonical_state
        module: Loaded ContentModule with transition and ending definitions
        detected_triggers: List of trigger IDs detected in the current turn (optional)

    Returns:
        NextSituation with status, scene_id, and derivation reason

    Raises:
        ValueError: If current_scene_id is not in module
    """
    current_scene_id = session.current_scene_id

    # Validate current scene exists
    if current_scene_id not in module.scene_phases:
        raise ValueError(f"Current scene '{current_scene_id}' not in module")

    # Step 1: Check for ending conditions (highest priority, via canonical rules)
    ending_id, legality_decision = SceneTransitionLegality.check_ending_legal(
        module, session=session, detected_triggers=detected_triggers
    )
    if ending_id is not None:
        ending = module.ending_conditions[ending_id]
        return NextSituation(
            current_scene_id=current_scene_id,
            situation_status="ending_reached",
            ending_id=ending.id,
            ending_outcome=ending.outcome,
            is_terminal=True,
            derivation_reason=f"Ending condition '{ending.id}' satisfied: {legality_decision.reason}",
        )

    # Step 2: Check for valid transitions from current scene (via canonical rules)
    # Try each transition from current scene
    for transition_id, transition in module.phase_transitions.items():
        if transition.from_phase == current_scene_id:
            legality_decision = SceneTransitionLegality.check_transition_legal(
                current_scene_id, transition.to_phase, module,
                session=session, detected_triggers=detected_triggers
            )
            if legality_decision.allowed:
                return NextSituation(
                    current_scene_id=transition.to_phase,
                    situation_status="transitioned",
                    derivation_reason=f"Transition from '{current_scene_id}' to '{transition.to_phase}': {legality_decision.reason}",
                )

    # Step 3: Continue in current scene (default)
    return NextSituation(
        current_scene_id=current_scene_id,
        situation_status="continue",
        derivation_reason=f"No transition or ending triggered; continuing in '{current_scene_id}'",
    )


def _check_ending_condition(
    ending, session: SessionState, detected_triggers: list[str] | None = None
) -> bool:
    """Check if an ending condition is satisfied by current state.

    Evaluates ending conditions:
    - If no trigger_conditions defined, ending is always active (unconditional)
    - If trigger_conditions defined and detected_triggers provided, all conditions must be detected
    - If trigger_conditions defined but detected_triggers is None, ending cannot fire

    Args:
        ending: EndingCondition object
        session: Current SessionState
        detected_triggers: List of trigger IDs detected in current turn (optional)

    Returns:
        True if ending conditions are satisfied
    """
    # Unconditional ending (no conditions defined) always triggers
    if not ending.trigger_conditions:
        return True

    # Conditional ending: all conditions must be detected
    if detected_triggers is not None:
        # All required trigger conditions must be in detected_triggers
        return all(condition_id in detected_triggers for condition_id in ending.trigger_conditions)

    # Conditions defined but no detected_triggers provided: cannot evaluate
    return False


def _check_transition_condition(
    transition,
    session: SessionState,
    module: ContentModule,
    detected_triggers: list[str] | None = None,
) -> bool:
    """Check if a transition condition is satisfied.

    Evaluates transition conditions:
    - Validates that target scene exists
    - If no trigger_conditions defined, transition is always active (unconditional)
    - If trigger_conditions defined and detected_triggers provided, all conditions must be detected
    - If trigger_conditions defined but detected_triggers is None, transition cannot fire

    Args:
        transition: PhaseTransition object
        session: Current SessionState
        module: ContentModule for scene lookups
        detected_triggers: List of trigger IDs detected in current turn (optional)

    Returns:
        True if transition target exists and conditions are satisfied
    """
    # Validate target exists
    if transition.to_phase not in module.scene_phases:
        return False

    # Unconditional transition (no conditions defined) always allowed
    if not transition.trigger_conditions:
        return True

    # Conditional transition: all conditions must be detected
    if detected_triggers is not None:
        # All required trigger conditions must be in detected_triggers
        return all(condition_id in detected_triggers for condition_id in transition.trigger_conditions)

    # Conditions defined but no detected_triggers provided: cannot evaluate
    return False


def log_situation_outcome(
    situation: NextSituation,
    session_id: str,
    turn_number: int,
) -> list[EventLogEntry]:
    """Generate event log entries for a situation outcome.

    Creates audit trail events for what happened after turn execution:
    - scene_continued: narrative continues in current scene
    - scene_transitioned: narrative moves to a new scene
    - ending_reached: terminal outcome achieved

    Args:
        situation: NextSituation result from derive_next_situation()
        session_id: Session identifier
        turn_number: Current turn number

    Returns:
        List of EventLogEntry objects (usually 1, may be multiple if needed)
    """
    entries: list[EventLogEntry] = []
    order_index = 0

    if situation.situation_status == "ending_reached":
        entry = EventLogEntry(
            event_type="ending_reached",
            order_index=order_index,
            summary=f"Story ending reached: {situation.ending_id}",
            payload={
                "ending_id": situation.ending_id,
                "ending_outcome": situation.ending_outcome or {},
                "derivation_reason": situation.derivation_reason,
            },
            session_id=session_id,
            turn_number=turn_number,
        )
        entries.append(entry)

    elif situation.situation_status == "transitioned":
        entry = EventLogEntry(
            event_type="scene_transitioned",
            order_index=order_index,
            summary=f"Scene transition: entering {situation.current_scene_id}",
            payload={
                "to_scene_id": situation.current_scene_id,
                "derivation_reason": situation.derivation_reason,
            },
            session_id=session_id,
            turn_number=turn_number,
        )
        entries.append(entry)

    elif situation.situation_status == "continue":
        entry = EventLogEntry(
            event_type="scene_continued",
            order_index=order_index,
            summary=f"Narrative continues in {situation.current_scene_id}",
            payload={
                "scene_id": situation.current_scene_id,
                "derivation_reason": situation.derivation_reason,
            },
            session_id=session_id,
            turn_number=turn_number,
        )
        entries.append(entry)

    return entries


def apply_situation_outcome(
    session: SessionState,
    situation: NextSituation,
) -> SessionState:
    """Apply situation outcome to update canonical session state.

    Updates session based on outcome:
    - Updates current_scene_id if situation moved to a different scene
    - Updates status to ENDED if terminal outcome was reached
    - Preserves immutability (returns new session, original unchanged)

    Args:
        session: Current SessionState
        situation: NextSituation from derive_next_situation()

    Returns:
        Updated SessionState (original unchanged)
    """
    updated_session = session.model_copy(deep=True)

    # Update scene if changed (transition) or continue (stays same)
    # situation.current_scene_id reflects the next scene or current scene
    updated_session.current_scene_id = situation.current_scene_id

    # Mark as ended if terminal outcome reached
    if situation.is_terminal:
        updated_session.status = SessionStatus.ENDED
        updated_session.updated_at = datetime.now(timezone.utc)

    return updated_session
