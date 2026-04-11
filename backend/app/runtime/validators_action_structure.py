"""Per-action structure checks for ``validate_action_structure`` (validators.py facade)."""

from __future__ import annotations

from typing import Any, Callable

from app.runtime.decision_policy import AIActionType
from app.runtime.reference_policy import ReferencePolicy

_ActionCollector = Callable[[dict, Any, Any, list[str]], None]


def collect_action_structure_errors(
    action: AIActionType,
    action_data: dict,
    module: Any,
    session: Any,
) -> list[str]:
    fn = _ACTION_STRUCTURE_COLLECTORS.get(action)
    if fn is None:
        return []
    errors: list[str] = []
    fn(action_data, module, session, errors)
    return errors


def _collect_state_update(action_data: dict, _m: Any, _s: Any, errors: list[str]) -> None:
    _errors_state_update(action_data, errors)


def _collect_relationship_shift(action_data: dict, _m: Any, _s: Any, errors: list[str]) -> None:
    _errors_relationship_shift(action_data, errors)


def _collect_scene_transition(action_data: dict, _m: Any, _s: Any, errors: list[str]) -> None:
    _errors_scene_transition(action_data, errors)


def _collect_trigger_assertion(
    action_data: dict, module: Any, session: Any, errors: list[str]
) -> None:
    _errors_trigger_assertion(action_data, module, session, errors)


def _collect_dialogue_impulse(action_data: dict, module: Any, _s: Any, errors: list[str]) -> None:
    _errors_dialogue_impulse(action_data, module, errors)


def _collect_conflict_signal(action_data: dict, _m: Any, _s: Any, errors: list[str]) -> None:
    _errors_conflict_signal(action_data, errors)


_ACTION_STRUCTURE_COLLECTORS: dict[AIActionType, _ActionCollector] = {
    AIActionType.STATE_UPDATE: _collect_state_update,
    AIActionType.RELATIONSHIP_SHIFT: _collect_relationship_shift,
    AIActionType.SCENE_TRANSITION: _collect_scene_transition,
    AIActionType.TRIGGER_ASSERTION: _collect_trigger_assertion,
    AIActionType.DIALOGUE_IMPULSE: _collect_dialogue_impulse,
    AIActionType.CONFLICT_SIGNAL: _collect_conflict_signal,
}


def _errors_state_update(action_data: dict, errors: list[str]) -> None:
    if not action_data.get("target_path"):
        errors.append("STATE_UPDATE requires 'target_path'")
    if action_data.get("next_value") is None:
        errors.append("STATE_UPDATE requires 'next_value'")


def _errors_relationship_shift(action_data: dict, errors: list[str]) -> None:
    if not action_data.get("target_path"):
        errors.append("RELATIONSHIP_SHIFT requires 'target_path'")
    if action_data.get("next_value") is None:
        errors.append("RELATIONSHIP_SHIFT requires 'next_value'")


def _errors_scene_transition(action_data: dict, errors: list[str]) -> None:
    if not action_data.get("scene_id"):
        errors.append("SCENE_TRANSITION requires 'scene_id'")


def _errors_trigger_assertion(
    action_data: dict, module: Any, session: Any, errors: list[str]
) -> None:
    if not action_data.get("trigger_ids"):
        errors.append("TRIGGER_ASSERTION requires 'trigger_ids'")
        return
    if module is None:
        return
    current_scene_id = session.current_scene_id if session else None
    for trigger_id in action_data["trigger_ids"]:
        ref_decision = ReferencePolicy.evaluate(
            "trigger",
            trigger_id,
            module,
            session=session,
            current_scene_id=current_scene_id,
        )
        if not ref_decision.allowed:
            errors.append(
                f"Trigger reference validation failed: {ref_decision.reason_message} "
                f"(reason: {ref_decision.reason_code})"
            )


def _errors_dialogue_impulse(action_data: dict, module: Any, errors: list[str]) -> None:
    if not action_data.get("character_id"):
        errors.append("DIALOGUE_IMPULSE requires 'character_id'")
    elif module is not None:
        char_id = action_data["character_id"]
        ref_decision = ReferencePolicy.evaluate("character", char_id, module)
        if not ref_decision.allowed:
            errors.append(
                f"Character reference validation failed: {ref_decision.reason_message} "
                f"(reason: {ref_decision.reason_code})"
            )
    if not action_data.get("impulse_text"):
        errors.append("DIALOGUE_IMPULSE requires 'impulse_text'")


def _errors_conflict_signal(action_data: dict, errors: list[str]) -> None:
    if not action_data.get("intensity") and action_data.get("intensity") != 0:
        errors.append("CONFLICT_SIGNAL requires 'intensity'")
