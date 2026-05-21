"""Attach optional ADR-0041 sidecar projections to the runtime payload."""

from __future__ import annotations

from typing import Any

from ai_stack.capabilities.capability_validator_plan import build_validator_execution_plan

from ..capability_projection import (
    _build_adr0041_plan_projection_sibling,
    _select_semantic_capabilities_from_runtime_context,
)
from ..feature_flags import resolve_adr0041_plan_projection_enabled


def attach_adr_sidecar_projections(
    projection_payload: dict[str, Any],
    *,
    capability_context: dict[str, Any],
    semantic_validator_dispatch_report: dict[str, Any],
) -> None:
    enabled_plan_projection, fp_warnings = resolve_adr0041_plan_projection_enabled()
    if enabled_plan_projection:
        sibling_sel, sibling_deriv = _select_semantic_capabilities_from_runtime_context(**capability_context)
        sibling_plan = build_validator_execution_plan(sibling_sel)
        projection_payload["adr0041_plan_projection"] = _build_adr0041_plan_projection_sibling(
            selection_result=sibling_sel,
            execution_plan=sibling_plan,
            dispatch_report=semantic_validator_dispatch_report,
            flag_warnings=fp_warnings,
            derivation_warnings=sibling_deriv,
        )
    auth_preview = semantic_validator_dispatch_report.get("adr0041_authority_preview")
    if isinstance(auth_preview, dict):
        projection_payload["validation_authority_preview"] = auth_preview
    bridge_obj = semantic_validator_dispatch_report.get("validation_authority_bridge")
    if isinstance(bridge_obj, dict):
        projection_payload["validation_authority_bridge"] = bridge_obj
        ho = bridge_obj.get("authority_handoff_candidate")
        if isinstance(ho, dict):
            projection_payload["authority_handoff_candidate"] = ho
    co_authority_decision = semantic_validator_dispatch_report.get("validation_co_authority_decision")
    if isinstance(co_authority_decision, dict):
        projection_payload["validation_co_authority_decision"] = co_authority_decision
    readiness_co_authority_preview = semantic_validator_dispatch_report.get(
        "readiness_co_authority_preview"
    )
    if isinstance(readiness_co_authority_preview, dict):
        projection_payload["readiness_co_authority_preview"] = readiness_co_authority_preview
    readiness_co_authority_enforcement = semantic_validator_dispatch_report.get(
        "readiness_co_authority_enforcement"
    )
    if isinstance(readiness_co_authority_enforcement, dict):
        projection_payload["readiness_co_authority_enforcement"] = readiness_co_authority_enforcement
        projection_payload["readiness_policy_input"] = readiness_co_authority_enforcement
    readiness_aggregation_decision = semantic_validator_dispatch_report.get(
        "readiness_aggregation_decision"
    )
    if isinstance(readiness_aggregation_decision, dict):
        projection_payload["readiness_aggregation_decision"] = readiness_aggregation_decision
