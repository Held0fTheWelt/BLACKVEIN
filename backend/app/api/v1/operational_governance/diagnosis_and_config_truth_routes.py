"""Diagnosis gate mapping and runtime config truth routes."""

from __future__ import annotations

from .common import *

# ============================================================================
# Diagnosis ↔ Gates Integration (Phase 2)
# ============================================================================


@api_v1_bp.route("/admin/system-diagnosis/gates", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_diagnosis_gates_mapping():
    """
    Get gates mapped to diagnosis checks.

    Returns all gates with their associated diagnosis check_id and check status.
    Useful for understanding which diagnosis checks drive gate status.
    """
    try:
        gates = get_all_gates()
        gates_with_checks = []

        for gate in gates:
            gate_id = gate.get("gate_id")
            check_id = get_check_id_for_gate(gate_id)
            gate_with_check = dict(gate)
            gate_with_check["diagnosis_check_id"] = check_id
            gates_with_checks.append(gate_with_check)

        return ok({
            "gates": gates_with_checks,
            "total_gates": len(gates_with_checks),
            "gates_with_diagnosis_mapping": sum(1 for g in gates_with_checks if g.get("diagnosis_check_id")),
        })
    except Exception as exc:
        return fail("readiness_error", "Failed to retrieve diagnosis-gates mapping.", 500, {"error": str(exc)})


@api_v1_bp.route("/admin/system-diagnosis/gates/<gate_id>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_diagnosis_gate_detail(gate_id: str):
    """
    Get gate detail with associated diagnosis check information.

    Shows which diagnosis check (if any) is linked to this gate.
    """
    try:
        gate = get_gate(gate_id)
        check_id = get_check_id_for_gate(gate_id)

        result = dict(gate)
        result["diagnosis_check_id"] = check_id
        if check_id:
            result["diagnosis_link"] = f"/api/v1/admin/system-diagnosis?refresh=1#{check_id}"

        return ok(result)
    except GovernanceError as err:
        return fail_from_error(err)
    except Exception as exc:
        return fail("readiness_error", "Failed to retrieve gate detail.", 500, {"error": str(exc)})


# ============================================================================
# Runtime Config Truth (Phase 5)
# ============================================================================


@api_v1_bp.route("/admin/runtime/config-truth", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_runtime_config_truth():
    """
    Get runtime configuration truth snapshot.

    Shows what's actually configured vs. effective vs. loaded:
    - Backend configured state (from database)
    - Backend effective config (currently in use)
    - World-Engine loaded state (from HTTP probe)
    - Play-Service connectivity (reachable?)
    - Story Runtime active state (from HTTP probe)

    Helps operators understand whether configured != effective != loaded.
    """
    try:
        truth = get_runtime_config_truth()
        return ok(truth)
    except Exception as exc:
        return fail("config_truth_error", "Failed to retrieve runtime config truth.", 500, {"error": str(exc)})

__all__ = (
    'admin_diagnosis_gates_mapping',
    'admin_diagnosis_gate_detail',
    'admin_runtime_config_truth',
)
