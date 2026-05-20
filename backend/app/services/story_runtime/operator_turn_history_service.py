"""Operator-facing turn history and agency diagnostics service.

Phase 5 surfaces canonical vitality telemetry so operators can answer why a turn
felt passive without reconstructing hidden runtime state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ai_stack.story_runtime.npc_agency.npc_agency_claim_readiness import assess_npc_agency_claim_readiness
from ai_stack.story_runtime.runtime_readiness_consumer import (
    build_adr0041_readiness_projection_echo,
    runtime_intelligence_projection_from_turn_aspect_ledger,
)


def _extract_vitality(event: dict[str, Any]) -> dict[str, Any]:
    telemetry = event.get("actor_survival_telemetry") if isinstance(event.get("actor_survival_telemetry"), dict) else {}
    vitality = telemetry.get("vitality_telemetry_v1") if isinstance(telemetry.get("vitality_telemetry_v1"), dict) else {}
    if vitality:
        return vitality
    gov = event.get("runtime_governance_surface") if isinstance(event.get("runtime_governance_surface"), dict) else {}
    fallback = gov.get("vitality_telemetry_v1") if isinstance(gov.get("vitality_telemetry_v1"), dict) else {}
    return fallback


def _extract_operator_hints(event: dict[str, Any]) -> dict[str, Any]:
    telemetry = event.get("actor_survival_telemetry") if isinstance(event.get("actor_survival_telemetry"), dict) else {}
    diagnosis = telemetry.get("passivity_diagnosis_v1")
    if isinstance(diagnosis, dict):
        return diagnosis
    return telemetry.get("operator_diagnostic_hints") if isinstance(telemetry.get("operator_diagnostic_hints"), dict) else {}


def _extract_npc_agency_breakdown(
    event: dict[str, Any],
    vitality: dict[str, Any],
) -> dict[str, Any]:
    realization = (
        vitality.get("npc_initiative_realization_v1")
        if isinstance(vitality.get("npc_initiative_realization_v1"), dict)
        else {}
    )
    ledger = event.get("turn_aspect_ledger") if isinstance(event.get("turn_aspect_ledger"), dict) else {}
    projection = (
        ledger.get("runtime_intelligence_projection")
        if isinstance(ledger.get("runtime_intelligence_projection"), dict)
        else {}
    )
    npc_agency = (
        projection.get("npc_agency")
        if isinstance(projection.get("npc_agency"), dict)
        else {}
    )
    planner_truth = {}
    commit = event.get("narrative_commit") if isinstance(event.get("narrative_commit"), dict) else {}
    if isinstance(commit.get("planner_truth"), dict):
        planner_truth = commit["planner_truth"]
    closure = (
        planner_truth.get("npc_agency_closure")
        if isinstance(planner_truth.get("npc_agency_closure"), dict)
        else {}
    )
    simulation = (
        planner_truth.get("npc_agency_simulation")
        if isinstance(planner_truth.get("npc_agency_simulation"), dict)
        else {}
    )
    long_horizon_state = (
        planner_truth.get("npc_long_horizon_state")
        if isinstance(planner_truth.get("npc_long_horizon_state"), dict)
        else simulation.get("npc_long_horizon_state")
        if isinstance(simulation.get("npc_long_horizon_state"), dict)
        else {}
    )
    private_plans = (
        planner_truth.get("npc_private_plans")
        if isinstance(planner_truth.get("npc_private_plans"), list)
        else simulation.get("npc_private_plans")
        if isinstance(simulation.get("npc_private_plans"), list)
        else []
    )
    conflict = (
        planner_truth.get("npc_plan_conflict_resolution")
        if isinstance(planner_truth.get("npc_plan_conflict_resolution"), dict)
        else simulation.get("npc_plan_conflict_resolution")
        if isinstance(simulation.get("npc_plan_conflict_resolution"), dict)
        else {}
    )
    runtime_npc_agency = {
        **npc_agency,
        "long_horizon_state_present": bool(
            npc_agency.get("long_horizon_state_present") or long_horizon_state
        ),
        "intention_threads_active": int(
            npc_agency.get("intention_threads_active")
            or len(long_horizon_state.get("intention_threads") or [])
        ),
        "intention_threads_carried_forward": int(
            npc_agency.get("intention_threads_carried_forward")
            or len(closure.get("carried_forward_intention_thread_ids") or [])
        ),
        "private_plan_resolution_present": bool(
            npc_agency.get("private_plan_resolution_present")
            or conflict.get("selected_private_plan_ids")
        ),
        "selected_private_plan_ids": list(
            npc_agency.get("selected_private_plan_ids")
            or conflict.get("selected_private_plan_ids")
            or []
        ),
        "withheld_private_plan_ids": list(
            npc_agency.get("withheld_private_plan_ids")
            or conflict.get("withheld_private_plan_ids")
            or []
        ),
        "private_plan_visibility_respected": npc_agency.get("private_plan_visibility_respected") is not False,
    }
    claim_readiness = assess_npc_agency_claim_readiness(
        simulation=simulation,
        closure=closure,
        runtime_aspect=runtime_npc_agency,
        operator_evidence={"operator_npc_agency_breakdown_present": True},
    )
    return {
        "schema_version": realization.get("schema_version"),
        "contract_status": npc_agency.get("contract_status") or realization.get("contract_status"),
        "independent_planning_used": bool(
            runtime_npc_agency.get("independent_planning_used")
            or realization.get("independent_planning_used")
        ),
        "candidate_actor_ids": list(runtime_npc_agency.get("candidate_actor_ids") or realization.get("candidate_actor_ids") or []),
        "planned_actor_ids": list(realization.get("planned_actor_ids") or runtime_npc_agency.get("planned_actor_ids") or []),
        "realized_actor_ids": list(
            realization.get("realized_initiative_actor_ids")
            or runtime_npc_agency.get("realized_actor_ids")
            or []
        ),
        "missing_required_actor_ids": list(
            realization.get("unrealized_required_initiative_actor_ids")
            or runtime_npc_agency.get("missing_required_actor_ids")
            or []
        ),
        "multi_npc_initiative_realized": bool(
            realization.get("multi_npc_initiative_realized")
            or runtime_npc_agency.get("multi_npc_initiative_realized")
        ),
        "closure_status": closure.get("closure_status") or runtime_npc_agency.get("closure_status"),
        "carry_forward_actor_ids": list(
            closure.get("unresolved_actor_ids")
            or runtime_npc_agency.get("carry_forward_actor_ids")
            or []
        ),
        "long_horizon_state_present": runtime_npc_agency["long_horizon_state_present"],
        "intention_threads_active": runtime_npc_agency["intention_threads_active"],
        "intention_threads_carried_forward": runtime_npc_agency["intention_threads_carried_forward"],
        "private_plan_resolution_present": runtime_npc_agency["private_plan_resolution_present"],
        "selected_private_plan_ids": runtime_npc_agency["selected_private_plan_ids"],
        "withheld_private_plan_ids": runtime_npc_agency["withheld_private_plan_ids"],
        "private_plan_count": len(private_plans),
        "private_plan_visibility_respected": runtime_npc_agency["private_plan_visibility_respected"],
        "claim_readiness": claim_readiness,
    }


def _derive_passivity_factors(vitality: dict[str, Any], quality_class: str, degradation_signals: list[str]) -> list[str]:
    factors: list[str] = []
    if vitality.get("fallback_used"):
        factors.append("fallback_used")
    if vitality.get("retry_exhausted"):
        factors.append("retry_exhausted")
    if vitality.get("degraded_commit"):
        factors.append("degraded_commit")
    if vitality.get("thin_edge_applied") and vitality.get("withheld_applied"):
        factors.append("thin_edge_withheld")
    if not vitality.get("response_present"):
        factors.append("no_visible_actor_response")
    if (vitality.get("selected_secondary_responder_ids") or []) and not vitality.get("multi_actor_realized"):
        factors.append("single_actor_only")
    if quality_class == "weak_but_legal" or "weak_signal_accepted" in degradation_signals:
        factors.append("weak_signal_accepted")
    if vitality.get("sparse_input_detected") and not vitality.get("sparse_input_recovery_applied"):
        factors.append("sparse_input_not_recovered")

    deduped: list[str] = []
    for factor in factors:
        if factor not in deduped:
            deduped.append(factor)
    return deduped


def _compute_rising_degraded_posture(rows: list[dict[str, Any]]) -> bool:
    flags = [1 if str(row.get("quality_class") or "") in {"degraded", "failed"} else 0 for row in rows]
    if len(flags) < 6:
        return False
    tail = flags[-5:]
    prior = flags[:-5]
    if not prior:
        return False
    return (sum(tail) / len(tail)) > (sum(prior) / len(prior))


def build_turn_history_summary_for_session(
    diagnostics: list[dict[str, Any]],
    limit: int = 100,
) -> dict[str, Any]:
    """Build operator-visible turn history summary from session diagnostics."""
    rows = []
    for event in diagnostics[-limit:]:
        if not isinstance(event, dict):
            continue
        row = _format_turn_history_row(event)
        if row:
            rows.append(row)

    return {
        "turn_history_version": "2.0",
        "total_turns": len(rows),
        "rows": rows,
        "rising_degraded_posture": _compute_rising_degraded_posture(rows),
        "agency_statistics": _compute_agency_statistics(rows),
        "degradation_summary": _compute_degradation_summary(rows),
    }


def _format_turn_history_row(event: dict[str, Any]) -> dict[str, Any] | None:
    """Format a single turn event into an operator dashboard row."""
    if not event.get("turn_number"):
        return None

    vitality = _extract_vitality(event)
    hints = _extract_operator_hints(event)
    governance = event.get("runtime_governance_surface") if isinstance(event.get("runtime_governance_surface"), dict) else {}
    path_summary = event.get("observability_path_summary") if isinstance(event.get("observability_path_summary"), dict) else {}

    quality_class = str(
        vitality.get("quality_class")
        or governance.get("quality_class")
        or ""
    ).strip().lower() or "healthy"

    degradation_signals = vitality.get("degradation_signals")
    if not isinstance(degradation_signals, list):
        degradation_signals = governance.get("degradation_signals") if isinstance(governance.get("degradation_signals"), list) else []
    signal_list = [str(signal).strip() for signal in degradation_signals if str(signal).strip()]

    passivity = list(hints.get("why_turn_felt_passive") or [])
    if not passivity:
        passivity = _derive_passivity_factors(vitality, quality_class, signal_list)

    vitality_breakdown = {
        "response_present": bool(vitality.get("response_present")),
        "initiative_present": bool(vitality.get("initiative_present")),
        "multi_actor_realized": bool(vitality.get("multi_actor_realized")),
        "selected_secondary_count": len(vitality.get("selected_secondary_responder_ids") or []),
        "realized_actor_count": len(vitality.get("realized_actor_ids") or []),
        "rendered_actor_count": len(vitality.get("rendered_actor_ids") or []),
        "sparse_input_recovery_applied": bool(vitality.get("sparse_input_recovery_applied")),
    }
    npc_agency_breakdown = _extract_npc_agency_breakdown(event, vitality)

    return {
        "turn_number": event.get("turn_number"),
        "turn_kind": event.get("turn_kind"),
        "turn_timestamp": event.get("turn_timestamp_iso"),
        "trace_id": event.get("trace_id"),
        "schema_version": vitality.get("schema_version"),
        "configured_responder": vitality.get("selected_primary_responder_id"),
        "configured_secondaries": list(vitality.get("selected_secondary_responder_ids") or []),
        "realized_actor_ids": list(vitality.get("realized_actor_ids") or []),
        "realized_secondary_responder_ids": list(vitality.get("realized_secondary_responder_ids") or []),
        "rendered_actor_ids": list(vitality.get("rendered_actor_ids") or []),
        "quality_class": quality_class,
        "degradation_signals": signal_list,
        "generation_ok": bool(vitality.get("generated_ok")),
        "fallback_used": bool(vitality.get("fallback_used")),
        "validation_ok": bool(vitality.get("validation_ok")),
        "commit_applied": bool(vitality.get("commit_applied")),
        "generated_spoken_line_count": int(vitality.get("generated_spoken_line_count") or 0),
        "validated_spoken_line_count": int(vitality.get("validated_spoken_line_count") or 0),
        "rendered_spoken_line_count": int(vitality.get("rendered_spoken_line_count") or 0),
        "generated_action_line_count": int(vitality.get("generated_action_line_count") or 0),
        "validated_action_line_count": int(vitality.get("validated_action_line_count") or 0),
        "rendered_action_line_count": int(vitality.get("rendered_action_line_count") or 0),
        "initiative_generated_count": int(vitality.get("initiative_generated_count") or 0),
        "initiative_preserved_count": int(vitality.get("initiative_preserved_count") or 0),
        "initiative_seizer_id": vitality.get("initiative_seizer_id"),
        "initiative_loser_id": vitality.get("initiative_loser_id"),
        "initiative_pressure_label": vitality.get("initiative_pressure_label"),
        "agency_level": hints.get("actor_agency_level", "unknown"),
        "diagnostic_hints": list(hints.get("hints") or []),
        "why_turn_felt_passive": passivity,
        "primary_passivity_factors": passivity[:3],
        "vitality_breakdown": vitality_breakdown,
        "npc_agency_breakdown": npc_agency_breakdown,
        "intent_surface_evidence": {
            "player_input_kind": path_summary.get("player_input_kind"),
            "player_action_committed": path_summary.get("player_action_committed"),
            "player_speech_committed": path_summary.get("player_speech_committed"),
            "narrator_response_expected": path_summary.get("narrator_response_expected"),
            "npc_response_expected": path_summary.get("npc_response_expected"),
            "semantic_move_kind": path_summary.get("semantic_move_kind"),
            "subtext_surface_mode": path_summary.get("subtext_surface_mode"),
            "subtext_hidden_intent_hypothesis": path_summary.get(
                "subtext_hidden_intent_hypothesis"
            ),
            "subtext_function": path_summary.get("subtext_function"),
            "subtext_sincerity_band": path_summary.get("subtext_sincerity_band"),
            "subtext_policy_rule_id": path_summary.get("subtext_policy_rule_id"),
            "subtext_contract_pass": path_summary.get("subtext_contract_pass"),
            "scene_director_selection_source": path_summary.get("scene_director_selection_source"),
            "planner_rationale_codes": path_summary.get("planner_rationale_codes")
            if isinstance(path_summary.get("planner_rationale_codes"), list)
            else [],
            "keyword_scene_candidates_used": path_summary.get(
                "keyword_scene_candidates_used"
            ),
            "npc_narrated_player_action_violation": path_summary.get(
                "npc_narrated_player_action_violation"
            ),
            "intent_surface_contract_pass": path_summary.get("intent_surface_contract_pass"),
            "player_input_attribution_pass": path_summary.get("player_input_attribution_pass"),
            "semantic_move_alignment_pass": path_summary.get("semantic_move_alignment_pass"),
            "npc_action_narration_boundary_pass": path_summary.get(
                "npc_action_narration_boundary_pass"
            ),
        },
        "adr0041_readiness_projection_echo": build_adr0041_readiness_projection_echo(
            runtime_intelligence_projection_from_turn_aspect_ledger(event)
        ),
    }


def _compute_agency_statistics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate statistics on actor agency across the turn history."""
    if not rows:
        return {}

    total = len(rows)
    full_agency = sum(1 for row in rows if row.get("agency_level") == "full_actor_agency")
    generation_failed = sum(1 for row in rows if row.get("agency_level") == "generation_failed")
    fallback_active = sum(1 for row in rows if row.get("agency_level") == "fallback_active")
    validation_constrained = sum(1 for row in rows if row.get("agency_level") == "validation_constrained")
    commit_blocked = sum(1 for row in rows if row.get("agency_level") == "commit_blocked")
    narration_only = sum(1 for row in rows if row.get("agency_level") == "narration_only")

    avg_generated_spoken = sum(int(row.get("generated_spoken_line_count") or 0) for row in rows) / total
    avg_validated_spoken = sum(int(row.get("validated_spoken_line_count") or 0) for row in rows) / total
    avg_rendered_spoken = sum(int(row.get("rendered_spoken_line_count") or 0) for row in rows) / total

    return {
        "total_turns": total,
        "full_actor_agency_turns": full_agency,
        "full_agency_percent": round((100.0 * full_agency / total), 1),
        "generation_failed_turns": generation_failed,
        "fallback_active_turns": fallback_active,
        "validation_constrained_turns": validation_constrained,
        "commit_blocked_turns": commit_blocked,
        "narration_only_turns": narration_only,
        "avg_generated_spoken_lines": round(avg_generated_spoken, 2),
        "avg_validated_spoken_lines": round(avg_validated_spoken, 2),
        "avg_rendered_spoken_lines": round(avg_rendered_spoken, 2),
    }


def _compute_degradation_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Identify and summarize degradation patterns in the turn history."""
    degraded_rows = [row for row in rows if str(row.get("quality_class") or "") in {"degraded", "failed"}]

    signal_counts: dict[str, int] = {}
    factor_counts: dict[str, int] = {}
    for row in rows:
        for signal in row.get("degradation_signals") or []:
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
        for factor in row.get("why_turn_felt_passive") or []:
            factor_counts[factor] = factor_counts.get(factor, 0) + 1

    return {
        "total_degraded_turns": len(degraded_rows),
        "degradation_signal_counts": signal_counts,
        "passivity_factor_counts": factor_counts,
        "latest_degraded_turns": [
            {
                "turn_number": row.get("turn_number"),
                "quality_class": row.get("quality_class"),
                "degradation_signals": row.get("degradation_signals") or [],
                "why_turn_felt_passive": row.get("why_turn_felt_passive") or [],
            }
            for row in degraded_rows[-5:]
        ],
    }


def operator_diagnostics_surface(
    session_diagnostics: list[dict[str, Any]],
    fallback_marker_check: bool = True,
) -> dict[str, Any]:
    """Build full operator diagnostic surface for agency troubleshooting."""
    history_summary = build_turn_history_summary_for_session(session_diagnostics)
    rows = history_summary.get("rows", [])

    fallback_turns = [row for row in rows if row.get("fallback_used")]
    failed_turns = [row for row in rows if not row.get("generation_ok")]
    failed_validation = [row for row in rows if not row.get("validation_ok")]
    failed_commit = [row for row in rows if not row.get("commit_applied")]

    return {
        "diagnostics_version": "2.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "turn_history": history_summary,
        "critical_issues": {
            "fallback_turns": len(fallback_turns),
            "generation_failures": len(failed_turns),
            "validation_failures": len(failed_validation),
            "commit_failures": len(failed_commit),
        },
        "vitality_breakdown": {
            "rows_with_response": sum(1 for row in rows if (row.get("vitality_breakdown") or {}).get("response_present")),
            "rows_with_initiative": sum(1 for row in rows if (row.get("vitality_breakdown") or {}).get("initiative_present")),
            "rows_with_multi_actor_realization": sum(
                1 for row in rows if (row.get("vitality_breakdown") or {}).get("multi_actor_realized")
            ),
        },
        "top_passivity_factors": _top_passivity_factors(rows),
        "operator_actions": _suggest_operator_actions(
            fallback_turns=fallback_turns,
            failed_turns=failed_turns,
            failed_validation=failed_validation,
            failed_commit=failed_commit,
            rows=rows,
        ),
        "documented_capabilities": {
            "full_actor_agency": "Responder output survived generation, validation, commit, and render.",
            "fallback_active": "Generation used fallback path; quality may be reduced.",
            "validation_constrained": "Validation constrained actor behavior.",
            "commit_blocked": "Turn was not committed.",
            "narration_only": "No actor-lane response reached visible output.",
            "generation_failed": "Generation failed and no usable actor output survived.",
        },
    }


def _top_passivity_factors(rows: list[dict[str, Any]], top_n: int = 5) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in rows:
        for factor in row.get("why_turn_felt_passive") or []:
            counts[factor] = counts.get(factor, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return [{"factor": factor, "count": count} for factor, count in ranked[:top_n]]


def _suggest_operator_actions(
    *,
    fallback_turns: list[dict[str, Any]],
    failed_turns: list[dict[str, Any]],
    failed_validation: list[dict[str, Any]],
    failed_commit: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> list[str]:
    """Suggest operator actions based on observed degradation patterns."""
    actions: list[str] = []

    if failed_turns:
        actions.append(
            f"Generation failed on {len(failed_turns)} turns; verify provider health and route policy."
        )
    if fallback_turns:
        actions.append(
            f"Fallback path executed on {len(fallback_turns)} turns; inspect primary model availability."
        )
    if failed_validation:
        actions.append(
            f"Validation failed on {len(failed_validation)} turns; inspect actor-lane and continuity constraints."
        )
    if failed_commit:
        actions.append(
            f"Commit failed on {len(failed_commit)} turns; inspect commit seam and persistence diagnostics."
        )

    single_actor_only_count = sum(
        1 for row in rows if "single_actor_only" in (row.get("why_turn_felt_passive") or [])
    )
    if single_actor_only_count:
        actions.append(
            f"{single_actor_only_count} turns nominated secondaries but realized a single actor; inspect responder realization policy."
        )

    sparse_not_recovered_count = sum(
        1 for row in rows if "sparse_input_not_recovered" in (row.get("why_turn_felt_passive") or [])
    )
    if sparse_not_recovered_count:
        actions.append(
            f"Sparse/evasive input failed recovery on {sparse_not_recovered_count} turns; inspect thin-edge and probing recovery behavior."
        )

    if not actions:
        actions.append("All sampled turns show healthy actor vitality posture.")

    return actions


__all__ = [
    "build_turn_history_summary_for_session",
    "operator_diagnostics_surface",
]
