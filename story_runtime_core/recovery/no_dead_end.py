"""Deterministic no-dead-end recovery contract.

This module does not judge prose quality. It builds and validates structured
runtime evidence that a blocked, failed, ambiguous, or fallback turn remains
playable without polluting committed story truth.
"""

from __future__ import annotations

import hashlib
from typing import Any


NO_DEAD_END_RECOVERY_SCHEMA_VERSION = "no_dead_end_recovery.v1"
NO_DEAD_END_RECOVERY_VALIDATION_VERSION = "no_dead_end_recovery_validation.v1"

RECOVERY_CLASS_COMMITTED_SUCCESS = "committed_success"
RECOVERY_CLASS_PARTIAL_SUCCESS = "partial_success"
RECOVERY_CLASS_BLOCKED_PLAYABLE = "blocked_playable"
RECOVERY_CLASS_REDIRECTED_PLAYABLE = "redirected_playable"
RECOVERY_CLASS_CLARIFICATION_NEEDED = "clarification_needed"
RECOVERY_CLASS_SAFE_FALLBACK_PLAYABLE = "safe_fallback_playable"
RECOVERY_CLASS_UNRECOVERABLE_SYSTEM_ERROR = "unrecoverable_system_error"

RECOVERY_CLASSES = frozenset(
    {
        RECOVERY_CLASS_COMMITTED_SUCCESS,
        RECOVERY_CLASS_PARTIAL_SUCCESS,
        RECOVERY_CLASS_BLOCKED_PLAYABLE,
        RECOVERY_CLASS_REDIRECTED_PLAYABLE,
        RECOVERY_CLASS_CLARIFICATION_NEEDED,
        RECOVERY_CLASS_SAFE_FALLBACK_PLAYABLE,
        RECOVERY_CLASS_UNRECOVERABLE_SYSTEM_ERROR,
    }
)

PLAYABLE_RECOVERY_CLASSES = frozenset(
    {
        RECOVERY_CLASS_COMMITTED_SUCCESS,
        RECOVERY_CLASS_PARTIAL_SUCCESS,
        RECOVERY_CLASS_BLOCKED_PLAYABLE,
        RECOVERY_CLASS_REDIRECTED_PLAYABLE,
        RECOVERY_CLASS_CLARIFICATION_NEEDED,
        RECOVERY_CLASS_SAFE_FALLBACK_PLAYABLE,
    }
)

TECHNICAL_LEAK_TOKENS = frozenset(
    {
        "traceback",
        "exception",
        "runtimeerror",
        "typeerror",
        "stack trace",
        "graph execution",
        "validation_outcome",
        "commit_applied",
    }
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _text(value).lower()


def _bool(value: Any) -> bool:
    return bool(value) is True


def stable_recovery_id(*, story_session_id: str, turn_number: int, reason: str, recovery_class: str) -> str:
    seed = "|".join(
        [
            _text(story_session_id) or "session",
            str(int(turn_number or 0)),
            _text(reason) or "no_reason",
            _text(recovery_class) or "unknown",
        ]
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"no_dead_end:{digest}"


def _input_fingerprint(player_input: str) -> dict[str, Any]:
    text = str(player_input or "")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None
    return {
        "present": bool(text.strip()),
        "length": len(text),
        "sha256": digest,
    }


def _visible_texts(bundle: dict[str, Any] | None) -> list[str]:
    if not isinstance(bundle, dict):
        return []
    texts: list[str] = []
    for key in ("gm_narration", "spoken_lines", "action_lines"):
        values = bundle.get(key)
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str) and value.strip():
                texts.append(value)
            elif isinstance(value, dict):
                text = _text(value.get("text") or value.get("line") or value.get("player_display_text"))
                if text:
                    texts.append(text)
    blocks = bundle.get("scene_blocks")
    if isinstance(blocks, list):
        for block in blocks:
            if not isinstance(block, dict):
                continue
            text = _text(block.get("player_display_text") or block.get("text"))
            if text:
                texts.append(text)
    return texts


def detect_technical_leak_absent(visible_output_bundle: dict[str, Any] | None) -> bool:
    text = "\n".join(_visible_texts(visible_output_bundle)).lower()
    if not text:
        return True
    return not any(token in text for token in TECHNICAL_LEAK_TOKENS)


def classify_recovery(
    *,
    reason: str,
    validation_outcome: dict[str, Any] | None = None,
    narrative_commit: dict[str, Any] | None = None,
    committed_result: dict[str, Any] | None = None,
    turn_kind: str | None = None,
    recoverable_outcome: bool = False,
) -> str:
    """Classify a turn outcome without reading generated narration."""
    reason_text = _lower(reason)
    validation = validation_outcome if isinstance(validation_outcome, dict) else {}
    commit = narrative_commit if isinstance(narrative_commit, dict) else {}
    result = committed_result if isinstance(committed_result, dict) else {}
    kind = _lower(turn_kind)

    if kind == "unrecoverable_system_error" or _bool(validation.get("hard_boundary_failure")):
        return RECOVERY_CLASS_UNRECOVERABLE_SYSTEM_ERROR
    if reason_text == "graph_execution_exception" or "graph_exception" in kind:
        return RECOVERY_CLASS_SAFE_FALLBACK_PLAYABLE
    if any(token in reason_text for token in ("ambiguous", "unknown", "clarification", "missing_target")):
        return RECOVERY_CLASS_CLARIFICATION_NEEDED
    if recoverable_outcome or _bool(validation.get("recoverable_rejection")) or result.get("commit_applied") is False:
        if any(token in reason_text for token in ("redirect", "alternate", "reroute")):
            return RECOVERY_CLASS_REDIRECTED_PLAYABLE
        return RECOVERY_CLASS_BLOCKED_PLAYABLE
    if commit.get("allowed") is False or _lower(commit.get("situation_status")) == "blocked":
        return RECOVERY_CLASS_BLOCKED_PLAYABLE
    if _lower(commit.get("situation_status")) in {"partial", "constrained"}:
        return RECOVERY_CLASS_PARTIAL_SUCCESS
    return RECOVERY_CLASS_COMMITTED_SUCCESS


def _next_step_options(*, recovery_class: str, reason: str) -> list[dict[str, Any]]:
    reason_text = _text(reason) or "continue"
    if recovery_class == RECOVERY_CLASS_COMMITTED_SUCCESS:
        return [
            {
                "option_id": "continue_from_committed_state",
                "option_kind": "continue",
                "source": "no_dead_end_recovery",
                "reason": reason_text,
            }
        ]
    if recovery_class == RECOVERY_CLASS_PARTIAL_SUCCESS:
        return [
            {
                "option_id": "press_partial_success",
                "option_kind": "continue",
                "source": "no_dead_end_recovery",
                "reason": reason_text,
            },
            {
                "option_id": "adjust_from_partial_result",
                "option_kind": "alternate_action",
                "source": "no_dead_end_recovery",
                "reason": reason_text,
            },
        ]
    if recovery_class == RECOVERY_CLASS_CLARIFICATION_NEEDED:
        return [
            {
                "option_id": "clarify_target_or_intent",
                "option_kind": "clarification",
                "source": "no_dead_end_recovery",
                "reason": reason_text,
            }
        ]
    if recovery_class == RECOVERY_CLASS_SAFE_FALLBACK_PLAYABLE:
        return [
            {
                "option_id": "retry_from_current_position",
                "option_kind": "retry",
                "source": "no_dead_end_recovery",
                "reason": reason_text,
            },
            {
                "option_id": "simplify_next_move",
                "option_kind": "alternate_action",
                "source": "no_dead_end_recovery",
                "reason": reason_text,
            },
        ]
    if recovery_class in {RECOVERY_CLASS_BLOCKED_PLAYABLE, RECOVERY_CLASS_REDIRECTED_PLAYABLE}:
        return [
            {
                "option_id": "try_alternate_action",
                "option_kind": "alternate_action",
                "source": "no_dead_end_recovery",
                "reason": reason_text,
            },
            {
                "option_id": "inspect_current_scene",
                "option_kind": "perception",
                "source": "no_dead_end_recovery",
                "reason": reason_text,
            },
        ]
    return []


def _truth_scope(
    *,
    recovery_class: str,
    recoverable_outcome: bool,
    committed_result: dict[str, Any] | None,
) -> str:
    result = committed_result if isinstance(committed_result, dict) else {}
    if recoverable_outcome or result.get("commit_applied") is False:
        return "none"
    if recovery_class == RECOVERY_CLASS_BLOCKED_PLAYABLE:
        return "blocked_attempt_only"
    if recovery_class == RECOVERY_CLASS_PARTIAL_SUCCESS:
        return "partial_turn"
    if recovery_class == RECOVERY_CLASS_COMMITTED_SUCCESS:
        return "full_turn"
    if recovery_class == RECOVERY_CLASS_REDIRECTED_PLAYABLE:
        return "redirected_attempt"
    return "none"


def build_no_dead_end_recovery_record(
    *,
    story_session_id: str,
    module_id: str | None,
    turn_number: int,
    turn_kind: str,
    player_input: str,
    reason: str,
    validation_outcome: dict[str, Any] | None = None,
    narrative_commit: dict[str, Any] | None = None,
    committed_result: dict[str, Any] | None = None,
    visible_output_bundle: dict[str, Any] | None = None,
    recoverable_outcome: bool = False,
) -> dict[str, Any]:
    """Build no-dead-end evidence for a player-visible turn outcome."""
    validation = validation_outcome if isinstance(validation_outcome, dict) else {}
    result = committed_result if isinstance(committed_result, dict) else {}
    recovery_class = classify_recovery(
        reason=reason,
        validation_outcome=validation,
        narrative_commit=narrative_commit,
        committed_result=result,
        turn_kind=turn_kind,
        recoverable_outcome=recoverable_outcome,
    )
    next_steps = _next_step_options(recovery_class=recovery_class, reason=reason)
    truth_scope = _truth_scope(
        recovery_class=recovery_class,
        recoverable_outcome=recoverable_outcome,
        committed_result=result,
    )
    commits_truth = truth_scope != "none"
    technical_leak_absent = detect_technical_leak_absent(visible_output_bundle)
    record = {
        "schema_version": NO_DEAD_END_RECOVERY_SCHEMA_VERSION,
        "recovery_id": stable_recovery_id(
            story_session_id=story_session_id,
            turn_number=turn_number,
            reason=reason,
            recovery_class=recovery_class,
        ),
        "story_session_id": _text(story_session_id),
        "module_id": _text(module_id),
        "turn_number": int(turn_number or 0),
        "turn_kind": _text(turn_kind) or "player",
        "recovery_required": recovery_class != RECOVERY_CLASS_COMMITTED_SUCCESS,
        "recovery_class": recovery_class,
        "obstacle_kind": _text(validation.get("failure_class")) or _obstacle_kind_for_class(recovery_class),
        "obstacle_reason": _text(reason) or _text(validation.get("reason")) or "continue",
        "attempt": _input_fingerprint(player_input),
        "playability": {
            "player_visible": bool(visible_output_bundle),
            "attempt_preserved": bool(_text(player_input)),
            "fictional_explanation_required": recovery_class != RECOVERY_CLASS_COMMITTED_SUCCESS,
            "technical_leak_absent": technical_leak_absent,
            "next_step_affordance_present": bool(next_steps),
            "actor_agency_preserved": True,
        },
        "commit_policy": {
            "commit_applied": bool(result.get("commit_applied")) if "commit_applied" in result else not recoverable_outcome,
            "commits_story_truth": commits_truth,
            "committed_truth_scope": truth_scope,
            "false_truth_feedback_allowed": False,
        },
        "next_step_options": next_steps,
        "source_inputs": {
            "validation_status": _text(validation.get("status")),
            "recoverable_rejection": bool(validation.get("recoverable_rejection")),
            "hard_boundary_failure": bool(validation.get("hard_boundary_failure")),
            "commit_reason_code": _text((narrative_commit or {}).get("commit_reason_code"))
            if isinstance(narrative_commit, dict)
            else "",
        },
    }
    record["validation"] = validate_no_dead_end_recovery_record(record)
    return record


def _obstacle_kind_for_class(recovery_class: str) -> str:
    if recovery_class == RECOVERY_CLASS_SAFE_FALLBACK_PLAYABLE:
        return "runtime_graph_exception"
    if recovery_class == RECOVERY_CLASS_CLARIFICATION_NEEDED:
        return "ambiguous_or_unknown_target"
    if recovery_class == RECOVERY_CLASS_UNRECOVERABLE_SYSTEM_ERROR:
        return "unrecoverable_system_error"
    if recovery_class == RECOVERY_CLASS_COMMITTED_SUCCESS:
        return "none"
    if recovery_class == RECOVERY_CLASS_PARTIAL_SUCCESS:
        return "partial_success_constraint"
    return "validation_or_scene_constraint"


def validate_no_dead_end_recovery_record(record: dict[str, Any] | None) -> dict[str, Any]:
    """Validate structural no-dead-end evidence."""
    failures: list[str] = []
    rec = record if isinstance(record, dict) else {}
    if rec.get("schema_version") != NO_DEAD_END_RECOVERY_SCHEMA_VERSION:
        failures.append("schema_version_missing")
    recovery_class = _text(rec.get("recovery_class"))
    if recovery_class not in RECOVERY_CLASSES:
        failures.append("invalid_recovery_class")
    attempt = rec.get("attempt") if isinstance(rec.get("attempt"), dict) else {}
    if not bool(attempt.get("present")) and recovery_class != RECOVERY_CLASS_COMMITTED_SUCCESS:
        failures.append("attempt_not_preserved")
    playability = rec.get("playability") if isinstance(rec.get("playability"), dict) else {}
    next_steps = rec.get("next_step_options") if isinstance(rec.get("next_step_options"), list) else []
    if recovery_class in PLAYABLE_RECOVERY_CLASSES and not next_steps:
        failures.append("next_step_missing")
    if recovery_class in PLAYABLE_RECOVERY_CLASSES and playability.get("next_step_affordance_present") is not True:
        failures.append("next_step_affordance_not_marked")
    if playability.get("technical_leak_absent") is not True:
        failures.append("technical_leak_detected")
    if recovery_class == RECOVERY_CLASS_UNRECOVERABLE_SYSTEM_ERROR and next_steps:
        failures.append("unrecoverable_has_playable_next_step")
    commit_policy = rec.get("commit_policy") if isinstance(rec.get("commit_policy"), dict) else {}
    if commit_policy.get("committed_truth_scope") == "none" and commit_policy.get("commits_story_truth") is True:
        failures.append("false_truth_commit_policy")
    return {
        "schema_version": NO_DEAD_END_RECOVERY_VALIDATION_VERSION,
        "status": "rejected" if failures else "approved",
        "failure_codes": failures,
        "recoverable_no_dead_end": recovery_class in PLAYABLE_RECOVERY_CLASSES and not failures,
    }
