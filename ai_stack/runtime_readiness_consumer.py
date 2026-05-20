"""ADR-0041 runtime readiness consumer: single veto-only overlay on base readiness.

``run_validation_seam`` / opening evaluation remains canonical for allow vs reject.
ADR-0041 may only **reduce** readiness (allow → block) when all feature flags and a
``readiness_aggregation_decision`` are present. ADR-0041 must never upgrade a reject to allow.

This module does not mutate ``validation_outcome`` or commit gates.

**Governance:** The only production mutator of player-facing ``runtime_session_ready`` /
``can_execute`` via ADR-0041 is ``backend.app.api.v1.game_routes._player_session_bundle``.
Any additional consumer requires explicit ADR / governance; do not call
``resolve_runtime_readiness_with_adr0041`` from other backend routes or services.
"""

from __future__ import annotations

from typing import Any

from ai_stack.capabilities.capability_validator_dispatch import (
    ValidatorDispatchMode,
    resolve_validator_dispatch_mode,
)
from ai_stack.runtime_aspect_ledger import (
    ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV,
    resolve_adr0041_readiness_co_authority_preview_enabled,
    resolve_adr0041_runtime_readiness_consumer_enabled,
    resolve_adr0041_scoped_co_authority_enabled,
    resolve_adr0041_scoped_readiness_aggregation_enabled,
    resolve_adr0041_scoped_readiness_enforcement_enabled,
)

RUNTIME_READINESS_CONSUMER_SCHEMA_VERSION = "runtime_readiness_consumer.v1"
ADR0041_READINESS_PROJECTION_ECHO_SCHEMA_VERSION = "adr0041_readiness_projection_echo.v1"

# Canonical symbol for audits / static guard tests (must match ``_player_session_bundle`` wiring).
ADR0041_MUTATING_FINAL_READINESS_CONSUMER_PATH = (
    "backend.app.api.v1.game_routes._player_session_bundle"
)
_BLOCKING_DEGRADATION_TOKENS: frozenset[str] = frozenset(
    {
        "fallback",
        "degraded",
        "empty_output",
        "empty_visible_output",
        "missing_visible_output",
        "graph_execution_exception",
        "recoverable_graph_exception",
        "validation_rejected",
        "hard_boundary_failure",
    }
)


def adr0041_readiness_consumer_upstream_prerequisites_met() -> tuple[bool, tuple[str, ...]]:
    """All ADR-0041 flags required before aggregation (and thus consumer) may apply."""
    warnings: list[str] = []
    mode, mode_warnings = resolve_validator_dispatch_mode()
    warnings.extend(mode_warnings)
    if mode is not ValidatorDispatchMode.PLAN_ENFORCED:
        return False, tuple(warnings)
    checks = (
        resolve_adr0041_scoped_co_authority_enabled(),
        resolve_adr0041_readiness_co_authority_preview_enabled(),
        resolve_adr0041_scoped_readiness_enforcement_enabled(),
        resolve_adr0041_scoped_readiness_aggregation_enabled(),
    )
    for enabled, ws in checks:
        warnings.extend(ws)
        if not enabled:
            return False, tuple(warnings)
    return True, tuple(warnings)


def resolve_runtime_readiness_with_adr0041(
    *,
    base_runtime_session_ready: bool,
    base_can_execute: bool,
    opening_generation_status: str,
    runtime_intelligence_projection: dict[str, Any] | None,
    degradation_signals: list[Any] | None = None,
    retrieval_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Combine base session readiness with ADR-0041 aggregation (veto-only).

    Returns JSON-safe dict including ``runtime_ready`` and ``can_execute`` (final booleans),
    diagnostics fields, and safety flags.
    """
    consumer_on, cw = resolve_adr0041_runtime_readiness_consumer_enabled()
    upstream_ok, uw = adr0041_readiness_consumer_upstream_prerequisites_met()
    warnings = [*cw, *uw]

    agg: dict[str, Any] | None = None
    if isinstance(runtime_intelligence_projection, dict):
        raw = runtime_intelligence_projection.get("readiness_aggregation_decision")
        if isinstance(raw, dict):
            agg = raw

    adr0041_aggregation = "absent"
    adr0041_veto_applied = False
    blockers: list[str] = []
    if isinstance(agg, dict):
        raw_agg = str(agg.get("aggregated_readiness") or "").strip()
        adr0041_aggregation = raw_agg if raw_agg else "absent"
        adr0041_veto_applied = bool(agg.get("adr0041_veto_applied"))
        bl = agg.get("blockers")
        if isinstance(bl, list):
            blockers = [str(x) for x in bl if str(x).strip()]

    deg = degradation_signals if isinstance(degradation_signals, list) else []
    degradation_active = bool(deg)
    degradation_tokens = {
        str(signal).strip().lower()
        for signal in deg
        if str(signal).strip()
    }
    degradation_blockers = sorted(
        token for token in degradation_tokens if token in _BLOCKING_DEGRADATION_TOKENS
    )
    degradation_blocking_signal = bool(degradation_blockers)
    retrieval_auth = (
        retrieval_payload.get("retrieval_authority")
        if isinstance(retrieval_payload, dict) and isinstance(retrieval_payload.get("retrieval_authority"), dict)
        else {}
    )
    retrieval_authority_level = str(retrieval_auth.get("authority_level") or "").strip().lower()
    retrieval_unverified = retrieval_authority_level in {"", "retrieved_unverified", "diagnostic_only"}

    if base_runtime_session_ready and base_can_execute:
        base_readiness = "allow"
    elif (not base_runtime_session_ready) and (not base_can_execute):
        base_readiness = "reject"
    else:
        base_readiness = "unknown"

    consumer_path_active = bool(consumer_on and upstream_ok and isinstance(agg, dict))

    final_rs = bool(base_runtime_session_ready)
    final_ce = bool(base_can_execute)
    source = "base_readiness"

    if not consumer_path_active:
        if not consumer_on:
            reason = "adr0041_runtime_readiness_consumer_disabled"
        elif not upstream_ok:
            reason = "adr0041_upstream_prerequisites_not_met"
        elif not isinstance(agg, dict):
            reason = "readiness_aggregation_decision_absent"
        else:
            reason = "base_readiness_only"
    else:
        source = "adr0041_scoped_consumer"
        aggregated = str(agg.get("aggregated_readiness") or "").strip()

        if base_readiness == "unknown":
            if aggregated == "block":
                final_rs = False
                final_ce = False
                reason = (
                    "adr0041_veto_under_unknown_base"
                    if not degradation_active
                    else "adr0041_veto_under_unknown_base_with_degradation"
                )
            else:
                final_rs = bool(base_runtime_session_ready)
                final_ce = bool(base_can_execute)
                reason = (
                    "unknown_base_no_upgrade_degraded"
                    if degradation_active
                    else "unknown_base_no_upgrade"
                )
        elif base_readiness == "reject":
            final_rs = False
            final_ce = False
            reason = "base_reject_no_adr0041_upgrade"
        else:
            final_rs = bool(base_runtime_session_ready) and aggregated != "block"
            final_ce = bool(base_can_execute) and aggregated != "block"
            if aggregated == "block":
                reason = "adr0041_veto_over_base_allow"
            elif degradation_blocking_signal:
                final_rs = False
                final_ce = False
                reason = "adr0041_degradation_veto_over_base_allow"
            elif aggregated == "allow":
                reason = "base_allow_adr0041_allow"
            else:
                reason = "base_allow_adr0041_unchanged_or_other"

    return {
        "schema_version": RUNTIME_READINESS_CONSUMER_SCHEMA_VERSION,
        "runtime_ready": final_rs,
        "can_execute": final_ce,
        "ready_for_play": final_ce,
        "base_readiness": base_readiness,
        "adr0041_aggregation": adr0041_aggregation,
        "adr0041_veto_applied": adr0041_veto_applied,
        "source": source,
        "reason": reason,
        "blockers": blockers,
        "warnings": [str(w) for w in warnings if str(w).strip()],
        "consumer_flag": ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV,
        "consumer_enabled": bool(consumer_on),
        "consumer_path_active": consumer_path_active,
        "upstream_prerequisites_met": bool(upstream_ok),
        "degradation_active": degradation_active,
        "degradation_blocking_signal": degradation_blocking_signal,
        "degradation_blockers": degradation_blockers,
        "opening_generation_status": str(opening_generation_status or "").strip() or None,
        "retrieval_authority_level": retrieval_authority_level or "unknown",
        "retrieval_unverified": retrieval_unverified,
        "validation_outcome_changed": False,
        "commit_gate_changed": False,
        "proof_level": "local_only",
        "live_or_staging_evidence": False,
        "mutating_readiness_consumer_anchor": ADR0041_MUTATING_FINAL_READINESS_CONSUMER_PATH,
        "mutates_bundle_fields": ["runtime_session_ready", "can_execute"],
    }


def build_adr0041_readiness_projection_echo(
    runtime_intelligence_projection: dict[str, Any] | None,
) -> dict[str, Any]:
    """Read-only echo of ADR-0041 readiness surfaces from a ledger ``runtime_intelligence_projection``.

    Does not run aggregation or alter booleans. ``adr0041_runtime_readiness_consumer`` is
    only produced when assembling the player session bundle; it is not stored on the ledger.
    """
    rip = runtime_intelligence_projection if isinstance(runtime_intelligence_projection, dict) else {}

    def _pick(key: str) -> dict[str, Any] | None:
        val = rip.get(key)
        return val if isinstance(val, dict) else None

    return {
        "schema_version": ADR0041_READINESS_PROJECTION_ECHO_SCHEMA_VERSION,
        "read_only": True,
        "source": "runtime_intelligence_projection",
        "readiness_policy_input": _pick("readiness_policy_input"),
        "readiness_aggregation_decision": _pick("readiness_aggregation_decision"),
        "readiness_co_authority_enforcement": _pick("readiness_co_authority_enforcement"),
        "readiness_co_authority_preview": _pick("readiness_co_authority_preview"),
        "adr0041_runtime_readiness_consumer": {
            "note": (
                "Final veto overlay is attached only on the HTTP player session bundle under "
                "governance.adr0041_runtime_readiness_consumer; not persisted on this projection."
            ),
            "value": None,
        },
    }


def runtime_intelligence_projection_from_turn_aspect_ledger(
    latest_turn: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Extract ``runtime_intelligence_projection`` from a committed turn ledger root."""
    if not isinstance(latest_turn, dict):
        return None
    ledger = latest_turn.get("turn_aspect_ledger")
    if not isinstance(ledger, dict):
        return None
    rip = ledger.get("runtime_intelligence_projection")
    return rip if isinstance(rip, dict) else None


def degradation_signals_from_latest_turn(latest_turn: dict[str, Any] | None) -> list[Any]:
    """Best-effort degradation hints from last committed turn (non-authoritative)."""
    if not isinstance(latest_turn, dict):
        return []
    for key in ("degradation_signals", "runtime_degradation_signals"):
        sig = latest_turn.get(key)
        if isinstance(sig, list):
            return list(sig)
    nc = latest_turn.get("narrative_commit")
    if isinstance(nc, dict):
        sig = nc.get("degradation_signals")
        if isinstance(sig, list):
            return list(sig)
    rgs = latest_turn.get("runtime_governance_surface")
    if isinstance(rgs, dict):
        sig = rgs.get("degradation_signals")
        if isinstance(sig, list):
            return list(sig)
    return []
