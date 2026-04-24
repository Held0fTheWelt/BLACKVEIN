"""Map system diagnosis checks to canonical readiness gates."""

from __future__ import annotations

from typing import Any

from app.extensions import db
from app.models.governance_core import ReadinessGate
from app.services.readiness_gates_service import (
    create_or_update_gate,
    get_gates_by_status,
    get_gate,
)


# Mapping: diagnosis check_id -> gate_id
DIAGNOSIS_CHECK_TO_GATE_MAPPING = {
    "backend_api": "gate_backend_api_health",
    "database": "gate_database_connectivity",
    "play_service_configuration": "gate_play_service_config",
    "play_service_health": "gate_play_service_health",
    "play_service_readiness": "gate_play_service_readiness",
    "published_experiences_feed": "gate_published_experiences_available",
    "ai_stack_release_readiness": "gate_ai_stack_readiness",
}

# Mapping: gate_id -> gate definition (name, owner, truth_source)
GATE_DEFINITIONS = {
    "gate_backend_api_health": {
        "gate_name": "Backend API Health",
        "owner_service": "backend",
        "truth_source": "live_endpoint",
        "expected_evidence": "/api/v1/health endpoint responding with status=ok",
    },
    "gate_database_connectivity": {
        "gate_name": "Database Connectivity",
        "owner_service": "backend",
        "truth_source": "live_endpoint",
        "expected_evidence": "SQLite database accessible and responsive",
    },
    "gate_play_service_config": {
        "gate_name": "Play Service Configuration",
        "owner_service": "backend",
        "truth_source": "static_policy",
        "expected_evidence": "PLAY_SERVICE_INTERNAL_URL and credentials configured",
    },
    "gate_play_service_health": {
        "gate_name": "Play Service Health",
        "owner_service": "play-service",
        "truth_source": "live_endpoint",
        "expected_evidence": "/api/health endpoint on play-service responding",
    },
    "gate_play_service_readiness": {
        "gate_name": "Play Service Readiness",
        "owner_service": "play-service",
        "truth_source": "live_endpoint",
        "expected_evidence": "/api/health/ready endpoint indicating readiness",
    },
    "gate_published_experiences_available": {
        "gate_name": "Published Experiences Available",
        "owner_service": "backend",
        "truth_source": "database",
        "expected_evidence": "At least one published experience in database",
    },
    "gate_ai_stack_readiness": {
        "gate_name": "AI Stack Release Readiness",
        "owner_service": "ai-stack",
        "truth_source": "live_endpoint",
        "expected_evidence": "Release readiness report aggregate is ready or partial",
    },
}


def get_gate_id_for_check(check_id: str) -> str | None:
    """Get gate_id for a given diagnosis check_id."""
    return DIAGNOSIS_CHECK_TO_GATE_MAPPING.get(check_id)


def get_check_id_for_gate(gate_id: str) -> str | None:
    """Get check_id for a given gate_id (reverse lookup)."""
    for check_id, gid in DIAGNOSIS_CHECK_TO_GATE_MAPPING.items():
        if gid == gate_id:
            return check_id
    return None


def map_check_to_gate(check: dict[str, Any], checked_by: str = "system") -> dict[str, Any]:
    """
    Enrich a diagnosis check with gate information.

    Returns check dict with gate_id and gate_status added, or original check if no mapping.
    """
    check_id = check.get("id")
    if not check_id:
        return check

    gate_id = get_gate_id_for_check(check_id)
    if not gate_id:
        return check

    # Try to get existing gate, or create with default status based on check
    gate = None
    try:
        gate = get_gate(gate_id)
    except Exception:
        # Gate doesn't exist; create it with status based on check
        check_status = check.get("status", "fail")
        if check_status == "running":
            gate_status = "closed"
        elif check_status == "initialized":
            gate_status = "partial"
        else:
            gate_status = "open"

        gate_def = GATE_DEFINITIONS.get(gate_id, {})
        gate = create_or_update_gate(
            gate_id=gate_id,
            gate_name=gate_def.get("gate_name", gate_id),
            owner_service=gate_def.get("owner_service", "backend"),
            status=gate_status,
            reason=check.get("message", ""),
            expected_evidence=gate_def.get("expected_evidence", ""),
            actual_evidence=check.get("message", ""),
            evidence_path=f"/api/v1/admin/system-diagnosis?refresh=1#{check_id}",
            truth_source=gate_def.get("truth_source", "live_endpoint"),
            checked_by=checked_by,
        )

    # Add gate_id and gate_status to check
    enriched = dict(check)
    enriched["gate_id"] = gate_id
    enriched["gate_status"] = gate.get("status")
    return enriched


def enrich_diagnosis_with_gates(
    diagnosis: dict[str, Any],
    checked_by: str = "system",
) -> dict[str, Any]:
    """
    Enrich diagnosis payload with gate information.

    Adds gate_id to each check, updates gate status based on check results,
    and adds partial_gate_count to diagnosis.
    """
    enriched = dict(diagnosis)

    # Enrich each check with gate_id
    enriched_groups = []
    for group in diagnosis.get("groups", []):
        enriched_group = dict(group)
        enriched_checks = [
            map_check_to_gate(check, checked_by=checked_by)
            for check in group.get("checks", [])
        ]
        enriched_group["checks"] = enriched_checks
        enriched_groups.append(enriched_group)

    enriched["groups"] = enriched_groups

    # Calculate partial_gate_count
    partial_gates = get_gates_by_status("partial")
    enriched["partial_gate_count"] = len(partial_gates)

    return enriched


def ensure_all_gates_exist() -> None:
    """Create all gate definitions if they don't already exist (bootstrap)."""
    for gate_id, gate_def in GATE_DEFINITIONS.items():
        try:
            get_gate(gate_id)
        except Exception:
            # Gate doesn't exist; create it
            create_or_update_gate(
                gate_id=gate_id,
                gate_name=gate_def["gate_name"],
                owner_service=gate_def["owner_service"],
                status="open",
                expected_evidence=gate_def.get("expected_evidence", ""),
                truth_source=gate_def.get("truth_source", "live_endpoint"),
                checked_by="system_bootstrap",
            )
