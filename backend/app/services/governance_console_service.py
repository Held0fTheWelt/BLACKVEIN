"""Admin Governance Console read-model services.

Read-only governance projections for Administration Tool pages.
"""

from __future__ import annotations

import os
from typing import Any

from ai_stack.capabilities import capability_catalog
from ai_stack.capabilities.capability_validator_dispatch import resolve_validator_dispatch_mode
from ai_stack.capabilities.capability_validator_registry import (
    TURN_CLASS_ENFORCED_VALIDATORS,
    VALIDATOR_REGISTRY_INVENTORY,
    build_available_semantic_validator_registry,
    get_registry_coverage_for_turn_class,
)
from ai_stack.live_runtime_commit_semantics import evaluate_session_opening_readiness
from ai_stack.runtime_aspect_ledger import (
    ADR0041_PLAN_PROJECTION_ENABLED_ENV,
    ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV,
    ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV,
    ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV,
    ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV,
    ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV,
    resolve_adr0041_plan_projection_enabled,
    resolve_adr0041_readiness_co_authority_preview_enabled,
    resolve_adr0041_runtime_readiness_consumer_enabled,
    resolve_adr0041_scoped_co_authority_enabled,
    resolve_adr0041_scoped_readiness_aggregation_enabled,
    resolve_adr0041_scoped_readiness_enforcement_enabled,
)
from ai_stack.runtime_readiness_consumer import (
    build_adr0041_readiness_projection_echo,
    degradation_signals_from_latest_turn,
    runtime_intelligence_projection_from_turn_aspect_ledger,
)
from app.services.ai_engineer_suite_service import get_rag_operations_status
from app.services.game_service import GameServiceError, get_story_state, list_story_sessions
from app.services.governance_runtime_service import evaluate_runtime_readiness
from app.services.mcp_operations_service import query_activity, query_diagnostics
from app.services.narrative_governance_service import NarrativeGovernanceError, runtime_gov_summary
from app.services.observability_governance_service import get_observability_config


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _first_session_id() -> str | None:
    try:
        sessions = list_story_sessions()
    except GameServiceError:
        return None
    items = sessions.get("items") if isinstance(sessions, dict) else None
    if not isinstance(items, list):
        return None
    for row in items:
        if isinstance(row, dict):
            sid = str(row.get("session_id") or "").strip()
            if sid:
                return sid
    return None


def _session_context(session_id: str | None) -> dict[str, Any]:
    selected = str(session_id or "").strip() or _first_session_id()
    if not selected:
        return {
            "session_id": None,
            "state": {},
            "latest_turn": {},
            "runtime_intelligence_projection": {},
            "degradation_signals": [],
            "warnings": ["No runtime session available for governance projection."],
        }
    try:
        state = get_story_state(selected)
    except GameServiceError as exc:
        return {
            "session_id": selected,
            "state": {},
            "latest_turn": {},
            "runtime_intelligence_projection": {},
            "degradation_signals": [],
            "warnings": [f"Failed to load state for session {selected}: {exc}"],
        }
    latest_turn = state.get("last_committed_turn") if isinstance(state.get("last_committed_turn"), dict) else {}
    rip = runtime_intelligence_projection_from_turn_aspect_ledger(latest_turn) or {}
    deg = degradation_signals_from_latest_turn(latest_turn)
    return {
        "session_id": selected,
        "state": state,
        "latest_turn": latest_turn,
        "runtime_intelligence_projection": rip,
        "degradation_signals": deg,
        "warnings": [],
    }


def _flag_row(name: str, enabled: bool, warnings: tuple[str, ...] | list[str]) -> dict[str, Any]:
    return {
        "flag": name,
        "enabled": bool(enabled),
        "classification": "env_only",
        "admin_surface": "admin_read_only",
        "danger_level": "dangerous_to_expose",
        "warnings": [str(w) for w in (warnings or []) if str(w).strip()],
    }


def _read_only_consumer_projection(
    *,
    opening_readiness: dict[str, Any],
    runtime_intelligence_projection: dict[str, Any],
    degradation_signals: list[Any],
) -> dict[str, Any]:
    aggregation = (
        runtime_intelligence_projection.get("readiness_aggregation_decision")
        if isinstance(runtime_intelligence_projection.get("readiness_aggregation_decision"), dict)
        else {}
    )
    aggregated_readiness = str(aggregation.get("aggregated_readiness") or "").strip() or "absent"
    source = "opening_readiness"
    reason = "read_only_admin_projection"
    if aggregated_readiness == "block":
        source = "opening_readiness_with_adr0041_warning"
        reason = "aggregation_would_veto_if_consumer_active"
    return {
        "schema_version": "runtime_readiness_consumer.admin_read_only.v1",
        "runtime_ready": bool(opening_readiness.get("runtime_session_ready")),
        "can_execute": bool(opening_readiness.get("can_execute")),
        "ready_for_play": bool(opening_readiness.get("can_execute")),
        "opening_generation_status": opening_readiness.get("opening_generation_status"),
        "adr0041_aggregation": aggregated_readiness,
        "adr0041_veto_applied": bool(aggregation.get("adr0041_veto_applied")),
        "source": source,
        "reason": reason,
        "consumer_path_active": False,
        "upstream_prerequisites_met": None,
        "read_only_projection": True,
        "mutating_readiness_consumer_anchor": "backend.app.api.v1.game_routes._player_session_bundle",
        "mutates_bundle_fields": [],
        "degradation_signals": [str(item) for item in degradation_signals if str(item).strip()],
        "warnings": [
            "Admin governance console renders read-only readiness projection.",
            "Final ADR-0041 readiness mutation remains exclusive to game_routes._player_session_bundle.",
        ],
    }


def get_runtime_readiness_authority(*, session_id: str | None = None) -> dict[str, Any]:
    readiness = evaluate_runtime_readiness()
    ctx = _session_context(session_id)
    latest_turn = ctx["latest_turn"]
    rip = ctx["runtime_intelligence_projection"]
    story_window = ctx["state"].get("story_window") if isinstance(ctx["state"].get("story_window"), dict) else {}
    opening_readiness = evaluate_session_opening_readiness(
        story_entries=list(story_window.get("entries") or []),
        visible_scene_output=latest_turn.get("visible_scene_output")
        if isinstance(latest_turn.get("visible_scene_output"), dict)
        else {},
        created=None,
    )
    overlay = _read_only_consumer_projection(
        opening_readiness=opening_readiness,
        runtime_intelligence_projection=rip,
        degradation_signals=ctx["degradation_signals"],
    )
    aggregation = rip.get("readiness_aggregation_decision") if isinstance(rip.get("readiness_aggregation_decision"), dict) else {}
    source_chain = [
        {"source": "opening_readiness", "status": "present"},
        {"source": "validation_seam", "status": "read_only_projection"},
        {"source": "adr0041_readiness_aggregation_decision", "status": "present" if aggregation else "absent"},
        {"source": "adr0041_runtime_readiness_consumer", "status": "active" if overlay.get("consumer_path_active") else "inactive"},
    ]
    return {
        "session_id": ctx["session_id"],
        "runtime_readiness_inventory": readiness,
        "opening_readiness": opening_readiness,
        "adr0041_runtime_readiness_consumer": overlay,
        "readiness_aggregation_decision": aggregation,
        "runtime_session_ready": bool(opening_readiness.get("runtime_session_ready")),
        "can_execute": bool(opening_readiness.get("can_execute")),
        "ready_for_play": bool(opening_readiness.get("can_execute")),
        "degradation_signals": list(ctx["degradation_signals"]),
        "source_of_truth_chain": source_chain,
        "invariants": {
            "adr0041_can_upgrade_reject_to_allow": False,
            "run_validation_seam_remains_canonical": True,
            "no_commit_or_validation_outcome_mutation": True,
        },
        "warnings": ctx["warnings"],
    }


def get_adr0041_authority_state(*, session_id: str | None = None) -> dict[str, Any]:
    ctx = _session_context(session_id)
    story_window = ctx["state"].get("story_window") if isinstance(ctx["state"].get("story_window"), dict) else {}
    rip = ctx["runtime_intelligence_projection"]
    report = rip.get("validator_dispatch_report") if isinstance(rip.get("validator_dispatch_report"), dict) else {}
    opening_readiness = evaluate_session_opening_readiness(
        story_entries=list(story_window.get("entries") or []),
        visible_scene_output=ctx["latest_turn"].get("visible_scene_output")
        if isinstance(ctx["latest_turn"].get("visible_scene_output"), dict)
        else {},
        created=None,
    )
    mode, mode_warnings = resolve_validator_dispatch_mode()
    scoped_co_auth, scoped_co_auth_warn = resolve_adr0041_scoped_co_authority_enabled()
    readiness_preview, readiness_preview_warn = resolve_adr0041_readiness_co_authority_preview_enabled()
    readiness_enforcement, readiness_enforcement_warn = resolve_adr0041_scoped_readiness_enforcement_enabled()
    readiness_aggregation, readiness_aggregation_warn = resolve_adr0041_scoped_readiness_aggregation_enabled()
    readiness_consumer, readiness_consumer_warn = resolve_adr0041_runtime_readiness_consumer_enabled()
    plan_projection, plan_projection_warn = resolve_adr0041_plan_projection_enabled()
    flags = [
        _flag_row("ADR0041_VALIDATOR_DISPATCH_MODE", mode.value, mode_warnings),
        _flag_row(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, scoped_co_auth, scoped_co_auth_warn),
        _flag_row(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, readiness_preview, readiness_preview_warn),
        _flag_row(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, readiness_enforcement, readiness_enforcement_warn),
        _flag_row(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, readiness_aggregation, readiness_aggregation_warn),
        _flag_row(ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV, readiness_consumer, readiness_consumer_warn),
        _flag_row(ADR0041_PLAN_PROJECTION_ENABLED_ENV, plan_projection, plan_projection_warn),
    ]
    return {
        "session_id": ctx["session_id"],
        "dispatch_mode": mode.value,
        "feature_flags": flags,
        "selected_turn_class": report.get("selected_turn_class"),
        "selected_capabilities": report.get("selected_capabilities") or [],
        "validators_would_run": report.get("validators_would_run") or [],
        "validators_unavailable": report.get("validators_unavailable") or [],
        "validators_skipped": report.get("validators_skipped") or [],
        "actually_executed_validators": report.get("actually_executed") or [],
        "validation_co_authority_decision": rip.get("validation_co_authority_decision")
        if isinstance(rip.get("validation_co_authority_decision"), dict)
        else None,
        "readiness_policy_input": rip.get("readiness_policy_input")
        if isinstance(rip.get("readiness_policy_input"), dict)
        else None,
        "readiness_aggregation_decision": rip.get("readiness_aggregation_decision")
        if isinstance(rip.get("readiness_aggregation_decision"), dict)
        else None,
        "runtime_readiness_consumer": _read_only_consumer_projection(
            opening_readiness=opening_readiness,
            runtime_intelligence_projection=rip,
            degradation_signals=ctx["degradation_signals"],
        ),
        "authority_bridge_status": rip.get("validation_authority_bridge")
        if isinstance(rip.get("validation_authority_bridge"), dict)
        else None,
        "authority_handoff_candidate": rip.get("authority_handoff_candidate")
        if isinstance(rip.get("authority_handoff_candidate"), dict)
        else None,
        "partial_transfer_ready": bool((rip.get("authority_handoff_candidate") or {}).get("partial_transfer_ready"))
        if isinstance(rip.get("authority_handoff_candidate"), dict)
        else False,
        "adr0041_readiness_projection_echo": build_adr0041_readiness_projection_echo(rip),
        "warnings": ctx["warnings"],
    }


def get_capability_matrix_status(*, session_id: str | None = None) -> dict[str, Any]:
    ctx = _session_context(session_id)
    rip = ctx["runtime_intelligence_projection"]
    dispatch_report = rip.get("validator_dispatch_report") if isinstance(rip.get("validator_dispatch_report"), dict) else {}
    selected = set(report_cap for report_cap in dispatch_report.get("selected_capabilities", []) if isinstance(report_cap, str))
    inventory_rows = list(VALIDATOR_REGISTRY_INVENTORY)
    rows: list[dict[str, Any]] = []
    for entry in capability_catalog():
        capability = str(entry.get("name") or "").strip()
        local_rows = [row for row in inventory_rows if row.capability == capability]
        local_proof = bool(local_rows)
        rows.append(
            {
                "capability_name": capability,
                "semantic_runtime_name": capability,
                "pi_label": None,
                "adr_owner": "ADR-0041",
                "maturity_status": "runtime_projection" if capability in selected else "local_helper",
                "implementation_status": "implemented" if local_proof else "planned_or_observer",
                "runtime_path_participation": capability in selected,
                "proof": {
                    "local": local_proof,
                    "staging": False,
                    "live": False,
                    "langfuse": False,
                    "mcp": False,
                },
                "current_authority_level": "runtime_projection" if capability in selected else "local_helper",
                "promotion_eligibility": False,
                "blockers": [] if local_proof else ["missing_runtime_validator_adapter"],
                "next_required_evidence": (
                    "staging_or_live_runtime_evidence_with_langfuse_mcp_scores"
                    if local_proof
                    else "implement_runtime_validator_adapter_and_local_contract_tests"
                ),
            }
        )
    return {
        "session_id": ctx["session_id"],
        "schema": "capability_matrix_status.v1",
        "evidence_policy": {
            "local_only_cannot_promote_live": True,
            "promotion_requires_policy_backed_evidence": True,
        },
        "rows": rows,
        "source_documents": [
            "docs/MVPs/capability_matrix_status_and_adr_relations.md",
            "docs/MVPs/capability_matrix_verification_log.md",
            "docs/MVPs/capability_matrix_live_claim_gates.md",
        ],
        "warnings": ctx["warnings"],
    }


def get_validator_registry_status() -> dict[str, Any]:
    registry = build_available_semantic_validator_registry()
    coverage_by_turn_class: dict[str, Any] = {}
    for turn_class in sorted(TURN_CLASS_ENFORCED_VALIDATORS.keys()):
        cov = get_registry_coverage_for_turn_class(turn_class, registry)
        coverage_by_turn_class[turn_class] = {
            "required_enforced_validator_ids": list(cov.required_enforced_validator_ids),
            "validator_ids_registered": list(cov.validator_ids_registered),
            "validator_ids_missing": list(cov.validator_ids_missing),
            "typical_observer_diagnostic_ids": list(cov.typical_observer_diagnostic_ids),
            "coverage_complete": cov.coverage_complete,
        }
    rows: list[dict[str, Any]] = []
    for item in VALIDATOR_REGISTRY_INVENTORY:
        available = item.validator_id in registry
        rows.append(
            {
                "validator_id": item.validator_id,
                "capability": item.capability,
                "status": item.current_status,
                "blocking_or_non_blocking": item.blocking_or_non_blocking,
                "judge_required": item.judge_required,
                "available": available,
                "passes_availability_gate": available and item.blocking_or_non_blocking == "blocking",
                "turn_class_coverage": [
                    tc for tc, data in coverage_by_turn_class.items() if item.validator_id in data["required_enforced_validator_ids"]
                ],
                "proof_tier": "local_only",
                "cost_tier": "judge" if item.judge_required else "deterministic",
                "last_local_evidence": item.source_file_or_symbol,
                "notes": item.notes,
            }
        )
    return {
        "schema": "validator_registry_status.v1",
        "rows": rows,
        "turn_class_coverage": coverage_by_turn_class,
        "invariants": {
            "unavailable_validators_are_not_passing": True,
            "observer_diagnostics_are_non_blocking": True,
        },
    }


def get_langfuse_mcp_evidence_status() -> dict[str, Any]:
    observability = get_observability_config()
    rag_status = get_rag_operations_status()
    activity_items, _ = query_activity(page=1, limit=10, suite=None, trace_id=None, errors_only=False)
    diagnostic_items, _ = query_diagnostics(page=1, limit=10, status="open")
    trace_ready = bool(observability.get("is_enabled") and observability.get("credential_configured"))
    environment = str(observability.get("environment") or "development")
    proof_tier = "local_only" if environment == "development" else ("staging_like" if environment == "staging" else "live_candidate")
    required_scores = [
        "non_mock_generation_pass",
        "fallback_absent",
        "usage_present",
        "rag_context_attached",
        "adr0041_fields_present",
    ]
    blockers: list[str] = []
    if not trace_ready:
        blockers.append("langfuse_trace_not_ready")
    if not activity_items:
        blockers.append("mcp_activity_missing")
    if diagnostic_items:
        blockers.append("mcp_open_diagnostics_present")
    return {
        "schema": "langfuse_mcp_evidence_status.v1",
        "credential_readiness": {
            "langfuse_enabled": bool(observability.get("is_enabled")),
            "credential_configured": bool(observability.get("credential_configured")),
            "health_status": observability.get("health_status"),
        },
        "tracing_enabled": trace_ready,
        "score_emission_enabled": False,
        "required_scores": required_scores,
        "present_scores": [],
        "latest_trace_activity": activity_items[:5],
        "mcp_diagnostics": diagnostic_items[:5],
        "proof_tier": proof_tier,
        "local_vs_staging_live": {
            "environment": environment,
            "local_only_evidence": environment == "development",
            "staging_or_live_evidence": environment in {"staging", "production"},
        },
        "rag_runtime_posture": {
            "operational_state": rag_status.get("operational_state"),
            "embedding_backend_available": (rag_status.get("embedding_backend") or {}).get("available"),
        },
        "false_green_blockers": blockers,
    }


def get_runtime_aspect_ledger_view(*, session_id: str | None = None, aspect_filter: str | None = None) -> dict[str, Any]:
    ctx = _session_context(session_id)
    latest_turn = ctx["latest_turn"]
    ledger = latest_turn.get("turn_aspect_ledger") if isinstance(latest_turn.get("turn_aspect_ledger"), dict) else {}
    rip = ctx["runtime_intelligence_projection"]
    selected_filter = str(aspect_filter or "").strip().lower()
    projection_filtered = dict(rip)
    if selected_filter:
        projection_filtered = {
            key: value for key, value in rip.items() if selected_filter in key.lower()
        }
    return {
        "session_id": ctx["session_id"],
        "latest_turn_number": latest_turn.get("turn_number"),
        "runtime_intelligence_projection": projection_filtered,
        "runtime_intelligence_projection_keys": sorted(rip.keys()),
        "degradation_signals": list(ctx["degradation_signals"]),
        "turn_aspect_ledger": ledger,
        "available_aspect_filters": sorted(rip.keys()),
        "applied_filter": selected_filter or None,
        "export_json": {
            "turn_aspect_ledger": ledger,
            "runtime_intelligence_projection": projection_filtered,
        },
        "warnings": ctx["warnings"],
    }


def get_narrative_systems_governance(*, module_id: str | None = None, session_id: str | None = None) -> dict[str, Any]:
    ctx = _session_context(session_id)
    selected_module = (
        str(module_id or "").strip()
        or str(ctx["state"].get("module_id") or "").strip()
        or "runtime_module"
    )
    rip = ctx["runtime_intelligence_projection"]
    summary: dict[str, Any] = {}
    warnings: list[str] = list(ctx["warnings"])
    try:
        summary = runtime_gov_summary(selected_module)
    except NarrativeGovernanceError as exc:
        warnings.append(str(exc))
    rows: list[dict[str, Any]] = []
    projection_keys = sorted(str(key) for key in rip.keys())
    for key in projection_keys:
        label = str(key).replace("_", " ").strip().title() or "Runtime Aspect"
        present = key in rip
        payload = rip.get(key)
        impact = "runtime" if isinstance(payload, dict) else "diagnostics_only"
        rows.append(
            {
                "system_id": key,
                "label": label,
                "current_status": "present_in_runtime_projection" if present else "not_observed",
                "runtime_aspect_key": key if present else None,
                "latest_validation": "unknown",
                "langfuse_mcp_mapping": "not_proven",
                "evidence_level": "local_only" if present else "none",
                "blockers": [] if present else ["missing_runtime_projection_signal"],
                "impact_scope": impact,
                "policy_file": None,
            }
        )
    if not rows:
        warnings.append("No runtime_intelligence_projection systems available for selected session/module.")
    return {
        "module_id": selected_module,
        "session_id": ctx["session_id"],
        "narrative_runtime_summary": summary,
        "systems": rows,
        "warnings": warnings,
    }


def get_feature_flag_governance() -> dict[str, Any]:
    mode, mode_warnings = resolve_validator_dispatch_mode()
    rows = [
        {
            "setting": "manage.ai_runtime_governance",
            "value": True,
            "classification": "backend_config_owned",
            "admin_surface": "admin_editable",
            "dangerous_to_expose": False,
            "warnings": [],
        },
        {
            "setting": "manage.narrative_governance",
            "value": True,
            "classification": "backend_config_owned",
            "admin_surface": "admin_editable",
            "dangerous_to_expose": False,
            "warnings": [],
        },
        {
            "setting": "manage.mcp_operations",
            "value": True,
            "classification": "backend_config_owned",
            "admin_surface": "admin_editable",
            "dangerous_to_expose": False,
            "warnings": [],
        },
        {
            "setting": "ADR0041_VALIDATOR_DISPATCH_MODE",
            "value": mode.value,
            "classification": "env_only",
            "admin_surface": "admin_read_only",
            "dangerous_to_expose": True,
            "warnings": list(mode_warnings),
        },
        {
            "setting": ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV,
            "value": _as_bool(os.getenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV)),
            "classification": "env_only",
            "admin_surface": "admin_read_only",
            "dangerous_to_expose": True,
            "warnings": [],
        },
        {
            "setting": ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV,
            "value": _as_bool(os.getenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV)),
            "classification": "env_only",
            "admin_surface": "admin_read_only",
            "dangerous_to_expose": True,
            "warnings": [],
        },
        {
            "setting": ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV,
            "value": _as_bool(os.getenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV)),
            "classification": "env_only",
            "admin_surface": "admin_read_only",
            "dangerous_to_expose": True,
            "warnings": [],
        },
        {
            "setting": ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV,
            "value": _as_bool(os.getenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV)),
            "classification": "env_only",
            "admin_surface": "admin_read_only",
            "dangerous_to_expose": True,
            "warnings": [],
        },
        {
            "setting": ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV,
            "value": _as_bool(os.getenv(ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV)),
            "classification": "env_only",
            "admin_surface": "admin_read_only",
            "dangerous_to_expose": True,
            "warnings": [],
        },
    ]
    return {"rows": rows}
