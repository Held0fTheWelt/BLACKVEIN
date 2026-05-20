"""Apply outcome-level failures back onto runtime aspect records."""

from __future__ import annotations

from .contracts import _RuntimeAspectBuild
from .dependencies import *
from .outcome_failure_specs import _OUTCOME_FAILURE_SPECS
from .apply_specific_failures import (
    _apply_capability_failure, _apply_generic_failure,
    _apply_npc_agency_failure, _apply_voice_failure,
)

def _apply_outcome_failures(ctx: _RuntimeAspectBuild) -> None:
    if _apply_authority_failure(ctx):
        return
    if _apply_capability_failure(ctx):
        return
    if _apply_voice_failure(ctx):
        return
    if _apply_npc_agency_failure(ctx):
        return
    for spec in _OUTCOME_FAILURE_SPECS:
        failure_key, lane, contract_key, default_reason, skip_when_locked = spec
        if skip_when_locked and ctx.dramatic_rejection_locked:
            continue
        if _apply_generic_failure(ctx, failure_key, lane, contract_key, default_reason):
            return
    ctx.outcome = {**ctx.outcome, "voice_consistency_validation": ctx.validations["voice_consistency"]}
def _outcome_is_approved(ctx: _RuntimeAspectBuild) -> bool:
    return str(ctx.outcome.get("status") or "").strip().lower() == "approved"
def _apply_authority_failure(ctx: _RuntimeAspectBuild) -> bool:
    failure = ctx.failures.get("authority_failure")
    if not isinstance(failure, dict):
        return False
    reason = str(failure.get("failure_reason") or (failure.get("reasons") or ["authority_contract_violation"])[0])
    ctx.outcome = {
        **ctx.outcome,
        "status": "rejected",
        "reason": reason,
        "error_code": reason,
        "validator_lane": "runtime_aspect_ledger_authority_v1",
        "authority_contract_violation": True,
        "failure_class": "hard_contract_failure",
        "hard_boundary_failure": False,
        "recoverable_rejection": True,
        "runtime_aspect_failure": {
            "aspect_status": failure.get("status"),
            "failure_reason": reason,
            "offending_actor_id": failure.get("offending_actor_id"),
            "offending_block_id": failure.get("offending_block_id"),
            "expected_owner": failure.get("expected_owner"),
            "actual_owner": failure.get("actual_owner"),
            "missing_field": failure.get("missing_field"),
        },
    }
    if isinstance(ctx.failures.get("capability_failure"), dict):
        ctx.outcome["capability_failure"] = ctx.failures["capability_failure"]
    return True
