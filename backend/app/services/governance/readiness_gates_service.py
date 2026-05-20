"""Service layer for managing canonical readiness gates."""

from __future__ import annotations

from typing import Any

from app.extensions import db
from app.governance.errors import governance_error
from app.models.governance_core import ReadinessGate, SettingAuditEvent
from app.utils.time_utils import utc_now
from uuid import uuid4


def get_all_gates() -> list[dict[str, Any]]:
    """Retrieve all readiness gates in canonical schema."""
    gates = ReadinessGate.query.order_by(ReadinessGate.gate_id).all()
    return [gate.to_dict() for gate in gates]


def get_gates_by_status(status: str) -> list[dict[str, Any]]:
    """Retrieve gates filtered by status (closed|partial|open)."""
    if status not in ("closed", "partial", "open"):
        raise governance_error(
            "invalid_status",
            f"Status must be closed, partial, or open. Got: {status}",
            400,
            {},
        )

    gates = ReadinessGate.query.filter_by(status=status).order_by(ReadinessGate.gate_id).all()
    return [gate.to_dict() for gate in gates]


def get_gates_by_service(owner_service: str) -> list[dict[str, Any]]:
    """Retrieve gates for a specific owner service."""
    gates = ReadinessGate.query.filter_by(owner_service=owner_service).order_by(ReadinessGate.gate_id).all()
    return [gate.to_dict() for gate in gates]


def get_gate(gate_id: str) -> dict[str, Any]:
    """Retrieve a single gate by ID."""
    gate = ReadinessGate.query.get(gate_id)
    if not gate:
        raise governance_error(
            "gate_not_found",
            f"Gate {gate_id} not found",
            404,
            {},
        )
    return gate.to_dict()


def create_or_update_gate(
    gate_id: str,
    gate_name: str,
    owner_service: str,
    status: str = "open",
    reason: str = "",
    expected_evidence: str = "",
    actual_evidence: str | None = None,
    evidence_path: str | None = None,
    truth_source: str = "live_endpoint",
    remediation: str = "",
    remediation_steps: list[str] | None = None,
    checked_by: str = "system",
) -> dict[str, Any]:
    """Create or update a readiness gate."""
    if status not in ("closed", "partial", "open"):
        raise governance_error(
            "invalid_status",
            f"Status must be closed, partial, or open. Got: {status}",
            400,
            {},
        )

    if truth_source not in ("live_endpoint", "static_policy", "file_store", "database"):
        raise governance_error(
            "invalid_truth_source",
            f"Truth source must be live_endpoint, static_policy, file_store, or database. Got: {truth_source}",
            400,
            {},
        )

    gate = ReadinessGate.query.get(gate_id)
    is_new = gate is None

    if is_new:
        gate = ReadinessGate(gate_id=gate_id)
        db.session.add(gate)

    gate.gate_name = gate_name
    gate.owner_service = owner_service
    gate.status = status
    gate.reason = reason
    gate.expected_evidence = expected_evidence
    gate.actual_evidence = actual_evidence
    gate.evidence_path = evidence_path
    gate.truth_source = truth_source
    gate.remediation = remediation
    gate.remediation_steps_json = remediation_steps or []
    gate.last_checked_at = utc_now()
    gate.checked_by = checked_by
    gate.updated_at = utc_now()

    db.session.commit()

    _audit(
        "readiness_gate_updated" if not is_new else "readiness_gate_created",
        "readiness",
        gate_id,
        checked_by,
        f"Gate {gate_id} ({gate_name}) status: {status}",
        {"status": status, "reason": reason, "truth_source": truth_source},
    )

    return gate.to_dict()


def update_gate_status(
    gate_id: str,
    status: str,
    reason: str = "",
    actual_evidence: str | None = None,
    evidence_path: str | None = None,
    checked_by: str = "system",
) -> dict[str, Any]:
    """Update a gate's status and evidence."""
    gate = ReadinessGate.query.get(gate_id)
    if not gate:
        raise governance_error(
            "gate_not_found",
            f"Gate {gate_id} not found",
            404,
            {},
        )

    if status not in ("closed", "partial", "open"):
        raise governance_error(
            "invalid_status",
            f"Status must be closed, partial, or open. Got: {status}",
            400,
            {},
        )

    gate.status = status
    gate.reason = reason
    gate.actual_evidence = actual_evidence
    gate.evidence_path = evidence_path
    gate.last_checked_at = utc_now()
    gate.checked_by = checked_by
    gate.updated_at = utc_now()

    db.session.commit()

    _audit(
        "readiness_gate_status_updated",
        "readiness",
        gate_id,
        checked_by,
        f"Gate {gate_id} status changed to {status}",
        {"status": status, "reason": reason, "evidence_path": evidence_path},
    )

    return gate.to_dict()


def get_summary() -> dict[str, Any]:
    """Get readiness gates summary (counts by status)."""
    total = ReadinessGate.query.count()
    closed = ReadinessGate.query.filter_by(status="closed").count()
    partial = ReadinessGate.query.filter_by(status="partial").count()
    open_gates = ReadinessGate.query.filter_by(status="open").count()

    return {
        "total_gates": total,
        "closed_gates": closed,
        "partial_gates": partial,
        "open_gates": open_gates,
        "closure_percent": int((closed / total * 100) if total > 0 else 0),
    }


def delete_gate(gate_id: str, checked_by: str = "system") -> dict[str, Any]:
    """Delete a gate (only for cleanup; shouldn't normally happen)."""
    gate = ReadinessGate.query.get(gate_id)
    if not gate:
        raise governance_error(
            "gate_not_found",
            f"Gate {gate_id} not found",
            404,
            {},
        )

    db.session.delete(gate)
    db.session.commit()

    _audit(
        "readiness_gate_deleted",
        "readiness",
        gate_id,
        checked_by,
        f"Gate {gate_id} deleted",
        {},
    )

    return {"deleted": True, "gate_id": gate_id}


def _audit(
    event_type: str,
    scope: str,
    target_ref: str,
    actor: str,
    summary: str,
    metadata: dict[str, Any],
) -> None:
    """Record an audit event."""
    event = SettingAuditEvent(
        audit_event_id=f"audit_{uuid4().hex}",
        event_type=event_type,
        scope=scope,
        target_ref=target_ref,
        changed_by=actor,
        changed_at=utc_now(),
        summary=summary,
        metadata_json=metadata,
    )
    db.session.add(event)
    db.session.commit()
