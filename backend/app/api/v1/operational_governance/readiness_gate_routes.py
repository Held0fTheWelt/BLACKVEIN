"""Release readiness gate routes."""

from __future__ import annotations

from .common import *

# ============================================================================
# Release Readiness Gates — Canonical Schema (Phase 1)
# ============================================================================


@api_v1_bp.route("/admin/ai-stack/release-readiness/gates", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_readiness_gates_list():
    """Get all release readiness gates in canonical schema."""
    try:
        status_filter = request.args.get("status", None)
        service_filter = request.args.get("service", None)

        if status_filter:
            gates = get_gates_by_status(status_filter)
        elif service_filter:
            gates = get_gates_by_service(service_filter)
        else:
            ensure_all_gates_exist()
            gates = get_all_gates()

        enriched_gates = []
        for gate in gates:
            row = dict(gate)
            check_id = get_check_id_for_gate(row.get("gate_id", ""))
            if check_id:
                row["diagnosis_check_id"] = check_id
                row["diagnosis_link"] = f"/manage/diagnosis#{check_id}"
            enriched_gates.append(row)

        summary = get_summary()
        return ok({"gates": enriched_gates, "summary": summary})
    except GovernanceError as err:
        return fail_from_error(err)
    except Exception as exc:
        return fail("readiness_error", "Failed to retrieve gates.", 500, {"error": str(exc)})


@api_v1_bp.route("/admin/ai-stack/release-readiness/gates/<gate_id>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_readiness_gate_detail(gate_id: str):
    """Get details for a specific readiness gate."""
    try:
        gate = get_gate(gate_id)
        return ok(gate)
    except GovernanceError as err:
        return fail_from_error(err)
    except Exception as exc:
        return fail("readiness_error", "Failed to retrieve gate.", 500, {"error": str(exc)})


@api_v1_bp.route("/admin/ai-stack/release-readiness/gates", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_readiness_gate_create_or_update():
    """Create or update a readiness gate."""
    try:
        body = _body()
        gate_id = body.get("gate_id")
        if not gate_id:
            raise governance_error("gate_id_required", "gate_id is required", 400, {})

        gate = create_or_update_gate(
            gate_id=gate_id,
            gate_name=body.get("gate_name", ""),
            owner_service=body.get("owner_service", ""),
            status=body.get("status", "open"),
            reason=body.get("reason", ""),
            expected_evidence=body.get("expected_evidence", ""),
            actual_evidence=body.get("actual_evidence"),
            evidence_path=body.get("evidence_path"),
            truth_source=body.get("truth_source", "live_endpoint"),
            remediation=body.get("remediation", ""),
            remediation_steps=body.get("remediation_steps"),
            checked_by=_actor_identifier(),
        )
        return ok(gate)
    except GovernanceError as err:
        return fail_from_error(err)
    except Exception as exc:
        return fail("readiness_error", "Failed to create/update gate.", 500, {"error": str(exc)})


@api_v1_bp.route("/admin/ai-stack/release-readiness/gates/<gate_id>/status", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_readiness_gate_update_status(gate_id: str):
    """Update a gate's status and evidence."""
    try:
        body = _body()
        status = body.get("status")
        if not status:
            raise governance_error("status_required", "status is required", 400, {})

        gate = update_gate_status(
            gate_id=gate_id,
            status=status,
            reason=body.get("reason", ""),
            actual_evidence=body.get("actual_evidence"),
            evidence_path=body.get("evidence_path"),
            checked_by=_actor_identifier(),
        )
        return ok(gate)
    except GovernanceError as err:
        return fail_from_error(err)
    except Exception as exc:
        return fail("readiness_error", "Failed to update gate status.", 500, {"error": str(exc)})


@api_v1_bp.route("/admin/ai-stack/release-readiness/gates/<gate_id>", methods=["DELETE"])
@limiter.limit("10 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_readiness_gate_delete(gate_id: str):
    """Delete a readiness gate (cleanup only)."""
    try:
        result = delete_gate(gate_id, checked_by=_actor_identifier())
        return ok(result)
    except GovernanceError as err:
        return fail_from_error(err)
    except Exception as exc:
        return fail("readiness_error", "Failed to delete gate.", 500, {"error": str(exc)})


@api_v1_bp.route("/admin/ai-stack/release-readiness/summary", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_readiness_summary():
    """Get readiness gates summary (closure percentage, gate counts)."""
    try:
        summary = get_summary()
        return ok(summary)
    except Exception as exc:
        return fail("readiness_error", "Failed to retrieve summary.", 500, {"error": str(exc)})

__all__ = (
    'admin_readiness_gates_list',
    'admin_readiness_gate_detail',
    'admin_readiness_gate_create_or_update',
    'admin_readiness_gate_update_status',
    'admin_readiness_gate_delete',
    'admin_readiness_summary',
)
