"""W2.4.3 — Parse and normalize role-structured AI output.

Handles conversion of AIRoleContract into canonical ParsedAIDecision
while preserving role sections for diagnostics.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.runtime.ai_decision import ParsedAIDecision
from app.runtime.ai_output import DialogueImpulse, ProposedDelta
from app.runtime.role_contract import (
    DirectorSection,
    InterpreterSection,
    ResponderSection,
    ResponseImpulse,
    StateChangeCandidate,
)


class ParsedRoleAwareDecision(BaseModel):
    """Canonical parsed decision with role sections preserved for diagnostics.

    This is a composition structure that wraps the core runtime decision
    with diagnostic role sections. Only ParsedAIDecision feeds runtime execution.

    Attributes:
        parsed_decision: Core runtime decision object (sole runtime authority)
        interpreter: Preserved interpreter section (diagnostic only)
        director: Preserved director section (diagnostic only)
        responder: Preserved responder section (diagnostic only)
    """

    parsed_decision: ParsedAIDecision
    interpreter: InterpreterSection
    director: DirectorSection
    responder: ResponderSection


def parse_role_contract(
    payload: dict[str, Any],
    raw_output: str,
) -> ParsedRoleAwareDecision:
    """Parse and normalize AIRoleContract into ParsedRoleAwareDecision.

    Converts role-structured output into canonical ParsedAIDecision while
    preserving all role sections for diagnostics.

    Args:
        payload: Structured payload dict with interpreter/director/responder keys
        raw_output: Original raw output text

    Returns:
        ParsedRoleAwareDecision with normalized ParsedAIDecision and role sections

    Raises:
        ValueError: If required role sections are missing or malformed
    """
    # Import here to avoid circular imports
    from app.runtime.role_contract import AIRoleContract

    # Validate payload is AIRoleContract-shaped
    try:
        role_contract = AIRoleContract(**payload)
    except Exception as e:
        raise ValueError(f"Failed to parse AIRoleContract: {e}") from None

    # Extract role sections
    interpreter = role_contract.interpreter
    director = role_contract.director
    responder = role_contract.responder

    # Normalize to ParsedAIDecision (canonical runtime decision)
    parsed_decision = _normalize_role_contract(
        interpreter, director, responder, raw_output
    )

    # Return composition with role sections preserved
    return ParsedRoleAwareDecision(
        parsed_decision=parsed_decision,
        interpreter=interpreter,
        director=director,
        responder=responder,
    )


def _normalize_role_contract(
    interpreter: InterpreterSection,
    director: DirectorSection,
    responder: ResponderSection,
    raw_output: str,
) -> ParsedAIDecision:
    """Normalize role sections into canonical ParsedAIDecision.

    Mapping rules (from spec section 3):
    - interpreter.scene_reading → scene_interpretation
    - director.conflict_steering → rationale
    - responder.state_change_candidates → proposed_deltas
    - responder.trigger_assertions → detected_triggers
    - responder.scene_transition_candidate → proposed_scene_id
    - responder.response_impulses (dialogue_urge only) → dialogue_impulses
    """
    # Map interpreter
    scene_interpretation = interpreter.scene_reading.strip()

    # Map director
    rationale = director.conflict_steering.strip()

    # Map responder state changes
    proposed_deltas = [
        ProposedDelta(
            target_path=candidate.target_path,
            next_value=candidate.proposed_value,
            rationale=candidate.rationale,
            delta_type=None,
        )
        for candidate in responder.state_change_candidates
    ]

    # Map responder triggers
    detected_triggers = responder.trigger_assertions

    # Map responder scene transition
    proposed_scene_id = responder.scene_transition_candidate

    # Map responder dialogue impulses (dialogue_urge only)
    dialogue_impulses = [
        DialogueImpulse(
            character_id=impulse.character_id,
            impulse_text=impulse.rationale,  # ResponseImpulse.rationale → DialogueImpulse.impulse_text
            intensity=impulse.intensity / 10.0 if impulse.intensity else 0.0,  # Scale 0-10 → 0.0-1.0
        )
        for impulse in responder.response_impulses
        if impulse.impulse_type == "dialogue_urge"
    ]

    return ParsedAIDecision(
        scene_interpretation=scene_interpretation,
        detected_triggers=detected_triggers,
        proposed_deltas=proposed_deltas,
        proposed_scene_id=proposed_scene_id,
        rationale=rationale,
        dialogue_impulses=dialogue_impulses,
        raw_output=raw_output,
        parsed_source="role_structured_payload",
    )


def _is_role_structured_payload(payload: dict[str, Any]) -> bool:
    """Strict format detection: all three role keys must be present.

    Returns True only if payload has all of:
    - "interpreter" (dict)
    - "director" (dict)
    - "responder" (dict)

    Otherwise returns False (no exception).
    """
    if not isinstance(payload, dict):
        return False

    required_keys = {"interpreter", "director", "responder"}
    present_keys = set(payload.keys())

    return required_keys.issubset(present_keys)
