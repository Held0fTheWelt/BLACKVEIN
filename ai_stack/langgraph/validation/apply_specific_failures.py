"""Apply lane-specific failure records to ledger aspects."""

from __future__ import annotations

from .contracts import _RuntimeAspectBuild
from .dependencies import *
from .outcome_status import _outcome_is_approved

def _apply_capability_failure(ctx: _RuntimeAspectBuild) -> bool:
    failure = ctx.failures.get("capability_failure")
    if not isinstance(failure, dict):
        return False
    reason = str(failure.get("failure_reason") or "capability_missing_required")
    ctx.outcome = {
        **ctx.outcome,
        "status": "rejected",
        "reason": reason,
        "error_code": reason,
        "validator_lane": "runtime_aspect_ledger_capability_v1",
        "capability_contract_violation": bool(ctx.cap_violation),
        "failure_class": "hard_contract_failure" if ctx.cap_violation else "recoverable_contract_gap",
        "hard_boundary_failure": False,
        "recoverable_rejection": True,
        "capability_failure": failure,
    }
    return True
def _apply_voice_failure(ctx: _RuntimeAspectBuild) -> bool:
    voice_validation = ctx.validations["voice_consistency"]
    if voice_validation.get("status") != "rejected" or not _outcome_is_approved(ctx):
        return False
    ctx.outcome = {
        **ctx.outcome,
        "status": "rejected",
        "reason": "voice_consistency_drift",
        "error_code": "voice_consistency_drift",
        "validator_lane": "runtime_voice_consistency_v2"
        if ctx.hooks.voice_semantic_failure_present(voice_validation)
        else "runtime_voice_consistency_v1",
        "voice_consistency_validation": voice_validation,
        "voice_consistency_contract_violation": True,
        "failure_class": "recoverable_dramatic_failure",
        "hard_boundary_failure": False,
        "recoverable_rejection": True,
    }
    return True
def _apply_npc_agency_failure(ctx: _RuntimeAspectBuild) -> bool:
    failure = ctx.failures.get("npc_agency_failure")
    if not isinstance(failure, dict) or ctx.dramatic_rejection_locked or not _outcome_is_approved(ctx):
        return False
    reason = str(failure.get("failure_reason") or "npc_initiative_validation_failed")
    ctx.outcome = {
        **ctx.outcome,
        "status": "rejected",
        "reason": reason,
        "error_code": reason,
        "validator_lane": "npc_initiative_validation_v1",
        "npc_agency_contract_violation": True,
        "failure_class": failure.get("failure_class"),
        "hard_boundary_failure": False,
        "recoverable_rejection": True,
        "npc_agency_failure": failure,
    }
    return True
def _apply_generic_failure(
    ctx: _RuntimeAspectBuild,
    failure_key: str,
    validator_lane: str,
    contract_key: str,
    default_reason: str,
) -> bool:
    failure = ctx.failures.get(failure_key)
    if not isinstance(failure, dict) or not _outcome_is_approved(ctx):
        return False
    reason = str(failure.get("failure_reason") or default_reason)
    ctx.outcome = {
        **ctx.outcome,
        "status": "rejected",
        "reason": reason,
        "error_code": reason,
        "validator_lane": validator_lane,
        contract_key: True,
        "failure_class": failure.get("failure_class"),
        "hard_boundary_failure": False,
        "recoverable_rejection": True,
        failure_key: failure,
    }
    return True
