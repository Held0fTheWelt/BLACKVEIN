"""Bridge from InterpretedCommandPlan to at most one explicit runtime command."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.runtime.input_interpreter import (
    PARSER_VERSION,
    InputPrimaryMode,
    InterpretedCommandPlan,
    truncate_for_diagnostics,
)

MIN_SELECTED_CONFIDENCE = 0.55
MIN_LEADER_GAP = 0.07

# Ingress-side rejection codes (WS may also surface engine errors separately).
REJECTION_MISSING_INPUT = "missing_input"
REJECTION_NO_INTERPRETABLE_INTENT = "no_interpretable_intent"
REJECTION_AMBIGUOUS_INTENT = "ambiguous_intent"
REJECTION_UNSUPPORTED_INTENT = "unsupported_intent"


class LastInputInterpretationRecord(BaseModel):
    """Compact, bounded diagnostics stored on RuntimeInstance.metadata under last_input_interpretation."""

    parser_version: str = PARSER_VERSION
    actor_participant_id: str | None = None
    input_source: str = ""
    primary_mode: str = InputPrimaryMode.unknown.value
    plan_confidence: float = 0.0
    resolved_action: str | None = None
    rejection_code: str | None = None
    rejection_reason: str | None = None
    engine_rejection_reason: str | None = None
    candidate_summaries: list[dict[str, Any]] = Field(default_factory=list)
    rationale: str = ""

    def as_metadata_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class PlayerMessageIngressResult(BaseModel):
    """Structured outcome from normalization / interpretation (no side effects)."""

    command: dict[str, Any] | None = None
    rejection_code: str | None = None
    rejection_reason: str | None = None
    diagnostics: LastInputInterpretationRecord


def candidate_summaries_from_plan(plan: InterpretedCommandPlan, limit: int = 3) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in plan.candidates[:limit]:
        out.append(
            {
                "action": c.action,
                "confidence": round(c.confidence, 3),
                "reason": truncate_for_diagnostics(c.reason),
            }
        )
    return out


def diagnostics_from_plan(
    plan: InterpretedCommandPlan,
    *,
    actor_participant_id: str | None = None,
    input_source: str,
    rejection_code: str | None,
    rejection_reason: str | None,
    resolved_action: str | None,
    engine_rejection_reason: str | None = None,
) -> LastInputInterpretationRecord:
    return LastInputInterpretationRecord(
        parser_version=plan.parser_version,
        actor_participant_id=actor_participant_id,
        input_source=input_source,
        primary_mode=plan.primary_mode.value,
        plan_confidence=round(plan.confidence, 3),
        resolved_action=resolved_action,
        rejection_code=rejection_code,
        rejection_reason=rejection_reason,
        engine_rejection_reason=engine_rejection_reason,
        candidate_summaries=candidate_summaries_from_plan(plan),
        rationale=truncate_for_diagnostics(plan.rationale, max_len=200),
    )


def diagnostics_explicit(
    *,
    actor_participant_id: str | None = None,
    input_source: str,
    resolved_action: str,
    rationale: str = "Explicit structured command.",
) -> LastInputInterpretationRecord:
    return LastInputInterpretationRecord(
        parser_version="explicit_payload_v1",
        actor_participant_id=actor_participant_id,
        input_source=input_source,
        primary_mode=InputPrimaryMode.action.value,
        plan_confidence=1.0,
        resolved_action=resolved_action,
        rejection_code=None,
        rejection_reason=None,
        engine_rejection_reason=None,
        candidate_summaries=[],
        rationale=truncate_for_diagnostics(rationale, max_len=200),
    )


def diagnostics_missing_input(actor_participant_id: str | None = None) -> LastInputInterpretationRecord:
    return LastInputInterpretationRecord(
        parser_version=PARSER_VERSION,
        actor_participant_id=actor_participant_id,
        input_source="none",
        primary_mode=InputPrimaryMode.unknown.value,
        plan_confidence=0.0,
        resolved_action=None,
        rejection_code=REJECTION_MISSING_INPUT,
        rejection_reason="Provide action, input_text, player_input, or input.",
        candidate_summaries=[],
        rationale="No usable fields in payload.",
    )


def _payload_valid_for_action(action: str, payload: dict[str, Any]) -> bool:
    if action == "say" or action == "emote":
        return bool(str(payload.get("text", "")).strip())
    if action == "move":
        return bool(str(payload.get("target_room_id", "")).strip())
    if action == "inspect":
        return bool(str(payload.get("target_id", "")).strip())
    if action == "use_action":
        return bool(str(payload.get("action_id", "")).strip())
    return False


def resolve_plan_to_command(plan: InterpretedCommandPlan) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """
    Select at most one executable command from the interpretation plan.

    Returns:
        (command_dict, rejection_code, rejection_reason)
    """
    if not plan.candidates:
        if plan.primary_mode is InputPrimaryMode.silence:
            return (
                None,
                REJECTION_NO_INTERPRETABLE_INTENT,
                "Silence or non-lexical input does not map to a command.",
            )
        return (
            None,
            REJECTION_NO_INTERPRETABLE_INTENT,
            "No bounded interpretation produced an executable command.",
        )

    ordered = sorted(plan.candidates, key=lambda c: -c.confidence)
    best = ordered[0]
    second_conf = ordered[1].confidence if len(ordered) > 1 else 0.0

    if "competing_candidates" in plan.ambiguity_markers and len(ordered) > 1:
        if abs(best.confidence - second_conf) < MIN_LEADER_GAP * 2:
            return (
                None,
                REJECTION_AMBIGUOUS_INTENT,
                "Multiple interpretation hypotheses are too close to disambiguate safely.",
            )

    if best.confidence < MIN_SELECTED_CONFIDENCE:
        return (
            None,
            REJECTION_NO_INTERPRETABLE_INTENT,
            "Interpretation confidence is below the execution threshold.",
        )

    if len(ordered) > 1 and (best.confidence - second_conf) < MIN_LEADER_GAP:
        return (
            None,
            REJECTION_AMBIGUOUS_INTENT,
            "Top interpretation candidates are not separated enough to select safely.",
        )

    if not _payload_valid_for_action(best.action, best.payload):
        return (
            None,
            REJECTION_UNSUPPORTED_INTENT,
            f"Resolved action {best.action!r} has an invalid or empty payload.",
        )

    cmd = {"action": best.action, **best.payload}
    return (cmd, None, None)


def merge_engine_outcome(
    diagnostics: LastInputInterpretationRecord,
    *,
    actor_participant_id: str | None = None,
    engine_accepted: bool,
    engine_reason: str | None,
) -> LastInputInterpretationRecord:
    """Return a copy with engine outcome fields set (same schema)."""
    data = diagnostics.model_dump()
    if actor_participant_id is not None:
        data["actor_participant_id"] = actor_participant_id
    data["engine_rejection_reason"] = None if engine_accepted else (engine_reason or "Command rejected by runtime.")
    return LastInputInterpretationRecord.model_validate(data)
