"""W2.0.5 — Derive the next canonical runtime situation from committed state.

After a turn completes, the runtime must evaluate whether the current scene continues,
transitions to a valid next scene, or reaches an ending condition.

This module provides the derivation logic that inspects committed SessionState against
ContentModule rules to produce the next active situation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.content.module_models import ContentModule
from app.runtime.w2_models import SessionState


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
) -> NextSituation:
    """Derive the next canonical situation from the committed post-turn state.

    Evaluates transitions and endings in order:
    1. Check for active ending conditions
    2. If no ending, check for valid scene transitions
    3. If no transition, continue in current scene

    Args:
        session: Post-turn committed SessionState with updated canonical_state
        module: Loaded ContentModule with transition and ending definitions

    Returns:
        NextSituation with status, scene_id, and derivation reason

    Raises:
        ValueError: If current_scene_id is not in module
    """
    current_scene_id = session.current_scene_id

    # Validate current scene exists
    if current_scene_id not in module.scene_phases:
        raise ValueError(f"Current scene '{current_scene_id}' not in module")

    # Step 1: Check for ending conditions (highest priority)
    for ending_id, ending in module.ending_conditions.items():
        if _check_ending_condition(ending, session):
            return NextSituation(
                current_scene_id=current_scene_id,
                situation_status="ending_reached",
                ending_id=ending.id,
                ending_outcome=ending.outcome,
                is_terminal=True,
                derivation_reason=f"Ending condition '{ending.id}' satisfied",
            )

    # Step 2: Check for valid transitions from current scene
    for transition_id, transition in module.phase_transitions.items():
        if transition.from_phase == current_scene_id:
            if _check_transition_condition(transition, session, module):
                next_scene_id = transition.to_phase
                if next_scene_id not in module.scene_phases:
                    # Skip invalid transitions
                    continue
                return NextSituation(
                    current_scene_id=next_scene_id,
                    situation_status="transitioned",
                    derivation_reason=f"Transition from '{current_scene_id}' to '{next_scene_id}' conditions met",
                )

    # Step 3: Continue in current scene (default)
    return NextSituation(
        current_scene_id=current_scene_id,
        situation_status="continue",
        derivation_reason=f"No transition or ending triggered; continuing in '{current_scene_id}'",
    )


def _check_ending_condition(ending, session: SessionState) -> bool:
    """Check if an ending condition is satisfied by current state.

    For W2.0.5, minimal evaluation: only endings with no trigger_conditions are active.
    Later versions add state-based evaluation.

    Args:
        ending: EndingCondition object
        session: Current SessionState

    Returns:
        True only if ending has no trigger conditions (always triggered)
    """
    # For W2.0.5: only endings with no conditions are active
    # Condition-based endings require W2.0.6+ state evaluation
    if not ending.trigger_conditions:
        return True
    return False


def _check_transition_condition(
    transition,
    session: SessionState,
    module: ContentModule,
) -> bool:
    """Check if a transition condition is satisfied.

    For W2.0.5, validate that target exists; condition evaluation deferred to W2.0.6+.

    Args:
        transition: PhaseTransition object
        session: Current SessionState
        module: ContentModule for scene lookups

    Returns:
        True if transition target exists and has no conditions (unconditional transition)
    """
    # Validate target exists
    if transition.to_phase not in module.scene_phases:
        return False

    # For W2.0.5: only unconditional transitions are allowed
    # Condition-based transitions require W2.0.6+ state evaluation
    if not transition.trigger_conditions:
        return True  # No conditions = transition allowed

    # Transitions with conditions deferred to W2.0.6+
    return False
