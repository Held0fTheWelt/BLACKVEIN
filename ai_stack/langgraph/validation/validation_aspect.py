"""Capture the aggregate validation aspect for the runtime ledger."""

from __future__ import annotations

from .contracts import _RuntimeAspectBuild
from .dependencies import *
from .validation_status_fields import _VALIDATION_STATUS_FIELDS

def _capture_validation_aspect(ctx: _RuntimeAspectBuild) -> None:
    validation_failed = str(ctx.outcome.get("status") or "").strip().lower() != "approved"
    authority_failure = ctx.failures.get("authority_failure")
    capability_failure = ctx.failures.get("capability_failure")
    ctx.ledger = set_aspect_record(
        ctx.ledger,
        ASPECT_VALIDATION,
        make_aspect_record(
            applicable=True,
            status="failed" if validation_failed else "passed",
            expected={"validation_consumes_runtime_aspect_ledger": True},
            actual=_validation_aspect_actual(ctx),
            reasons=[str(ctx.outcome.get("reason"))] if validation_failed and ctx.outcome.get("reason") else [],
            source="validator",
            failure_class=ctx.outcome.get("failure_class") if validation_failed else None,
            failure_reason=str(ctx.outcome.get("reason")) if validation_failed and ctx.outcome.get("reason") else None,
            offending_actor_id=_first_failure_value(authority_failure, capability_failure, "offending_actor_id"),
            offending_block_id=authority_failure.get("offending_block_id") if isinstance(authority_failure, dict) else None,
            expected_owner=authority_failure.get("expected_owner") if isinstance(authority_failure, dict) else None,
            actual_owner=authority_failure.get("actual_owner") if isinstance(authority_failure, dict) else None,
            missing_field=authority_failure.get("missing_field") if isinstance(authority_failure, dict) else None,
        ),
    )
def _first_failure_value(first: Any, second: Any, key: str) -> Any:
    if isinstance(first, dict) and first.get(key) is not None:
        return first.get(key)
    if isinstance(second, dict):
        return second.get(key)
    return None
def _validation_aspect_actual(ctx: _RuntimeAspectBuild) -> dict[str, Any]:
    voice = ctx.validations["voice_consistency"]
    actual = {
        "validation_status": ctx.outcome.get("status"),
        "reason": ctx.outcome.get("reason"),
        "validator_lane": ctx.outcome.get("validator_lane"),
        "authority_contract_violation": bool(ctx.outcome.get("authority_contract_violation")),
        "capability_contract_violation": bool(ctx.outcome.get("capability_contract_violation")),
        "voice_consistency_contract_violation": bool(ctx.outcome.get("voice_consistency_contract_violation")),
        "voice_consistency_status": voice.get("status"),
        "voice_consistency_reason": voice.get("reason"),
        "recoverable_rejection": bool(ctx.outcome.get("recoverable_rejection")),
        "hard_boundary_failure": bool(ctx.outcome.get("hard_boundary_failure")),
    }
    for validation_key, status_key, contract_key in _VALIDATION_STATUS_FIELDS:
        validation = ctx.validations.get(validation_key)
        actual[status_key] = validation.get("status") if isinstance(validation, dict) else None
        actual[contract_key] = bool(ctx.outcome.get(contract_key))
    return actual
