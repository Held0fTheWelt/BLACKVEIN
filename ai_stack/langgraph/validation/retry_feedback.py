"""Retry-feedback helpers derived from validation evaluations."""

from __future__ import annotations

from .dependencies import *
from .retry_fields import (
    _ATTEMPT_RECORD_FEEDBACK_KEYS,
    _RETRY_FAILURE_FIELDS,
    _RETRY_TRIGGER_SOURCES,
    _VALIDATION_EVAL_UPDATE_KEYS,
)

def build_validation_retry_feedback(
    *,
    outcome: dict[str, Any],
    decision: Any,
    actor_lane_validation: dict[str, Any],
    attempt_index: int,
) -> dict[str, Any]:
    feedback = {
        "codes": list(decision.feedback_codes),
        "attempt_index": attempt_index,
        "trigger_source": _retry_trigger_source(outcome),
        "validation_status_before_retry": outcome.get("status"),
        "failure_reason_before_retry": str(outcome.get("reason") or "").strip(),
        "actor_lane_status_before_retry": actor_lane_validation.get("status")
        if isinstance(actor_lane_validation, dict)
        else None,
    }
    for outcome_key, feedback_key in _RETRY_FAILURE_FIELDS:
        feedback[feedback_key] = _dict_copy_or_none(outcome.get(outcome_key))
    return feedback
def build_retry_attempt_record_update(
    *,
    validation_feedback: dict[str, Any],
    outcome: dict[str, Any],
    context_synthesis_retry: dict[str, Any],
) -> dict[str, Any]:
    update = {key: validation_feedback.get(key) for key in _ATTEMPT_RECORD_FEEDBACK_KEYS}
    update.update(
        {
            "validation_status_after_retry": outcome.get("status"),
            "failure_reason_after_retry": outcome.get("reason"),
            "context_synthesis_retry": context_synthesis_retry,
            "resolved_failure": (
                str(outcome.get("status") or "").strip().lower() == "approved"
                or (
                    bool(validation_feedback.get("failure_reason_before_retry"))
                    and str(outcome.get("reason") or "").strip()
                    != str(validation_feedback.get("failure_reason_before_retry") or "")
                )
            ),
        }
    )
    return update
def copy_validation_eval_to_update(update: dict[str, Any], validation_eval: dict[str, Any]) -> None:
    for key in _VALIDATION_EVAL_UPDATE_KEYS:
        value = validation_eval.get(key)
        if isinstance(value, dict):
            update[key] = value
    dramatic_irony = validation_eval.get("dramatic_irony_validation")
    if isinstance(dramatic_irony, dict) and isinstance(dramatic_irony.get("record"), dict):
        update["dramatic_irony_record"] = dramatic_irony["record"]
def _dict_or_none(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None
def _dict_copy_or_none(value: Any) -> dict[str, Any] | None:
    return dict(value) if isinstance(value, dict) else None
def _list_or_empty(value: Any) -> list[Any]:
    return list(value or []) if isinstance(value, list) else []
def _retry_trigger_source(outcome: dict[str, Any]) -> str:
    for key, source in _RETRY_TRIGGER_SOURCES:
        if isinstance(outcome.get(key), dict):
            return source
    return "validation"
