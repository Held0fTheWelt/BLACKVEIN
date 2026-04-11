"""Validate → construct deltas → apply for validated turn pipeline (DS-005 optional module)."""

from __future__ import annotations

from typing import Any

from app.content.module_models import ContentModule
from app.runtime.event_log import RuntimeEventLog
from app.runtime.runtime_models import MockDecision, SessionState, StateDelta
from app.runtime.turn_executor_decision_delta import apply_deltas, construct_deltas
from app.runtime.validators import ValidationOutcome, validate_decision


def validated_turn_validate_construct_and_apply(
    session: SessionState,
    current_turn: int,
    mock_decision: MockDecision,
    module: ContentModule,
    event_log: RuntimeEventLog,
) -> tuple[ValidationOutcome, list[StateDelta], list[StateDelta], dict[str, Any]]:
    """Run validation, delta construction, and apply; emit matching event_log entries."""
    validation_outcome = validate_decision(mock_decision, session, module)

    event_log.log(
        "decision_validated",
        f"Decision validated: {validation_outcome.status} "
        f"({len(validation_outcome.accepted_delta_indices)} accepted, "
        f"{len(validation_outcome.rejected_delta_indices)} rejected)",
        payload={
            "status": validation_outcome.status,
            "is_valid": validation_outcome.is_valid,
            "accepted_delta_count": len(validation_outcome.accepted_delta_indices),
            "rejected_delta_count": len(validation_outcome.rejected_delta_indices),
            "errors": validation_outcome.errors,
        },
    )

    accepted_deltas, rejected_deltas = construct_deltas(
        mock_decision, session, validation_outcome, current_turn
    )

    event_log.log(
        "deltas_generated",
        f"Deltas: {len(accepted_deltas)} accepted, {len(rejected_deltas)} rejected",
        payload={
            "accepted_count": len(accepted_deltas),
            "rejected_count": len(rejected_deltas),
            "accepted_deltas": [
                {
                    "id": d.id,
                    "delta_type": d.delta_type,
                    "target_path": d.target_path,
                    "target_entity": d.target_entity,
                    "previous_value": d.previous_value,
                    "next_value": d.next_value,
                    "source": d.source,
                }
                for d in accepted_deltas
            ],
            "rejected_delta_ids": [d.id for d in rejected_deltas],
        },
    )

    updated_state = apply_deltas(session.canonical_state, accepted_deltas)

    event_log.log(
        "deltas_applied",
        f"{len(accepted_deltas)} delta(s) applied to canonical state",
        payload={
            "applied_count": len(accepted_deltas),
            "delta_ids": [d.id for d in accepted_deltas],
        },
    )

    return validation_outcome, accepted_deltas, rejected_deltas, updated_state
