"""Collect validation failures from authority, capability, and narrative lanes."""

from __future__ import annotations

from .contracts import _RuntimeAspectBuild
from .dependencies import *
from .dramatic_failure_specs import _DRAMATIC_FAILURE_SPECS

def _collect_failure_records(ctx: _RuntimeAspectBuild) -> None:
    ctx.failures["authority_failure"] = _authority_failure(ctx)
    ctx.failures["capability_failure"] = _capability_failure(ctx)
    for key, default, reason_key, codes_key, output_codes_key in _DRAMATIC_FAILURE_SPECS:
        ctx.failures[f"{key}_failure"] = _dramatic_failure(
            ctx.validations.get(key),
            default,
            reason_key=reason_key,
            codes_key=codes_key,
            output_codes_key=output_codes_key,
        )
    ctx.failures["npc_agency_failure"] = _npc_agency_failure(ctx.validations.get("npc_initiative"))
def _authority_failure(ctx: _RuntimeAspectBuild) -> dict[str, Any] | None:
    if ctx.npc_authority.get("status") == "failed":
        return ctx.npc_authority
    if ctx.narrator_authority.get("status") == "failed":
        return ctx.narrator_authority
    return None
def _capability_failure(ctx: _RuntimeAspectBuild) -> dict[str, Any] | None:
    if ctx.cap_violation:
        return {
            "failure_reason": str(ctx.cap_violation.get("reason") or "forbidden_capability_realized"),
            "violated_capabilities": ctx.capability_selection.get("violated_capabilities") or [],
            "missing_required_capabilities": ctx.capability_selection.get("missing_required_capabilities") or [],
            "offending_actor_id": ctx.cap_violation.get("offending_actor_id"),
        }
    if ctx.cap_missing_first:
        return {
            "failure_reason": "capability_missing_required",
            "violated_capabilities": ctx.capability_selection.get("violated_capabilities") or [],
            "missing_required_capabilities": ctx.capability_selection.get("missing_required_capabilities") or [],
            "selected_capability": ctx.cap_missing_first,
        }
    return None
def _dramatic_failure(
    validation: Any,
    default_reason: str,
    *,
    reason_key: str | None = "feedback_code",
    codes_key: str = "failure_codes",
    output_codes_key: str = "failure_codes",
) -> dict[str, Any] | None:
    if not isinstance(validation, dict):
        return None
    if str(validation.get("status") or "").strip().lower() != "rejected":
        return None
    codes = [str(code) for code in (validation.get(codes_key) or []) if str(code).strip()]
    reason = str(validation.get(reason_key) or "").strip() if reason_key else ""
    return {
        "failure_reason": reason or (codes[0] if codes else default_reason),
        output_codes_key: codes,
        "failure_class": "recoverable_dramatic_failure",
    }
def _npc_agency_failure(validation: Any) -> dict[str, Any] | None:
    if not isinstance(validation, dict):
        return None
    if str(validation.get("status") or "").strip().lower() == "approved":
        return None
    codes = [str(code) for code in (validation.get("error_codes") or []) if str(code).strip()]
    forbidden = bool(validation.get("forbidden_planned_actor_ids") or validation.get("forbidden_realized_actor_ids"))
    return {
        "failure_reason": str(
            validation.get("feedback_code") or (codes[0] if codes else "npc_initiative_validation_failed")
        ),
        "error_codes": codes,
        "missing_required_actor_ids": validation.get("missing_required_actor_ids") or [],
        "forbidden_planned_actor_ids": validation.get("forbidden_planned_actor_ids") or [],
        "forbidden_realized_actor_ids": validation.get("forbidden_realized_actor_ids") or [],
        "failure_class": "hard_contract_failure" if forbidden else "recoverable_dramatic_failure",
    }
