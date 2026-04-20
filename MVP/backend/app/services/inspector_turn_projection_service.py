"""Canonical read-only Inspector Suite projection assembly for one turn."""

from __future__ import annotations

from typing import Any

from ai_stack.dramatic_effect_contract import SemanticPlannerSupportLevel
from ai_stack.goc_turn_seams import build_operator_canonical_turn_record
from ai_stack.semantic_planner_effect_surface import (
    resolve_dramatic_effect_evaluator,
    support_level_for_module,
)

from app.contracts.inspector_turn_projection import (
    build_inspector_turn_projection_root,
    make_supported_section,
    make_unavailable_section,
    make_unsupported_section,
)
from app.services.ai_stack_evidence_service import build_session_evidence_bundle

_COMPARISON_RESERVED_FIELDS: tuple[str, ...] = (
    "timeline_alignment",
    "cross_run_delta",
    "coverage_heatmap",
)

_LEGACY_GATE_SUMMARY_KEYS: frozenset[str] = frozenset(
    {
        "dominant_rejection_category",
        "scene_function_mismatch_score",
        "character_implausibility_score",
        "continuity_pressure_score",
        "fluency_risk_score",
    }
)

_SEMANTIC_FLOW_STAGES: tuple[tuple[str, str], ...] = (
    ("player_input", "Player input"),
    ("semantic_move", "Semantic move"),
    ("social_state", "Social state"),
    ("character_mind", "Character mind"),
    ("scene_plan", "Scene plan"),
    ("proposed_narrative", "Candidate / proposed narrative"),
    ("dramatic_effect_gate", "Dramatic effect gate"),
    ("validation", "Validation"),
    ("commit", "Commit"),
    ("visible_output", "Visible output"),
)

_PLANNER_BOUND_STAGES: frozenset[str] = frozenset(
    {"semantic_move", "social_state", "character_mind", "scene_plan"}
)

_SUPPORT_NOTE_FULL_GOC = (
    "Full GoC dramatic-effect evaluation path; bounded semantic planner contracts apply for this module."
)
_SUPPORT_NOTE_NON_GOC = (
    "Non-GoC module: dramatic-effect evaluation uses the canonical non-GoC evaluator; "
    "semantic planner maturity is GoC-local — do not assume GoC-equivalent semantics here."
)

_LAST_TURN_PLANNER_KEYS: tuple[str, ...] = (
    "semantic_move_record",
    "social_state_record",
    "character_mind_records",
    "scene_plan_record",
    "interpreted_move",
    "scene_assessment",
    "selected_responder_set",
    "pacing_mode",
    "silence_brevity_decision",
    "proposed_state_effects",
    "dramatic_effect_outcome",
    "continuity_impacts",
    "visibility_class_markers",
    "failure_markers",
    "fallback_markers",
    "transition_pattern",
    "turn_id",
    "turn_timestamp_iso",
    "turn_initiator_type",
    "turn_input_class",
    "turn_execution_mode",
)


def _non_empty_dict(value: Any) -> bool:
    return isinstance(value, dict) and bool(value)


def _non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _planner_fields_from_last_turn(last_turn: dict[str, Any]) -> dict[str, Any]:
    """Lift planner-shaped fields from a diagnostics row (top-level and graph.planner_state_projection)."""
    out: dict[str, Any] = {}
    for key in _LAST_TURN_PLANNER_KEYS:
        if key in last_turn and last_turn[key] is not None:
            out[key] = last_turn[key]
    graph = last_turn.get("graph")
    if isinstance(graph, dict):
        psp = graph.get("planner_state_projection")
        if isinstance(psp, dict):
            for key in (
                "semantic_move_record",
                "social_state_record",
                "character_mind_records",
                "scene_plan_record",
            ):
                if key not in out and psp.get(key) is not None:
                    out[key] = psp[key]
    if "interpreted_move" not in out and isinstance(last_turn.get("interpreted_input"), dict):
        out["interpreted_move"] = last_turn["interpreted_input"]
    return out


def _support_posture(*, module_id: Any) -> dict[str, Any] | None:
    if not isinstance(module_id, str) or not module_id.strip():
        return None
    mid = module_id.strip()
    level = support_level_for_module(mid)
    evaluator = resolve_dramatic_effect_evaluator(mid)
    note = _SUPPORT_NOTE_FULL_GOC if level == SemanticPlannerSupportLevel.full_goc else _SUPPORT_NOTE_NON_GOC
    return {
        "semantic_planner_support_level": level.value,
        "dramatic_effect_evaluator_class": type(evaluator).__name__,
        "support_note": note,
    }


def _build_semantic_decision_flow(
    *,
    support_level: SemanticPlannerSupportLevel,
    canonical_record: dict[str, Any],
    last_turn: dict[str, Any],
    gate_outcome: dict[str, Any],
    validation: dict[str, Any],
    committed: dict[str, Any],
) -> dict[str, Any]:
    """Backend-only semantic stage list with explicit per-stage presence (operator Mermaid input)."""

    def presence_for(stage_id: str) -> str:
        if stage_id in _PLANNER_BOUND_STAGES and support_level != SemanticPlannerSupportLevel.full_goc:
            return "unsupported"
        if stage_id == "player_input":
            raw = last_turn.get("raw_input")
            if isinstance(raw, str) and raw.strip():
                return "present"
            ii = last_turn.get("interpreted_input")
            if _non_empty_dict(ii):
                return "present"
            return "absent"
        if stage_id == "semantic_move":
            return "present" if _non_empty_dict(canonical_record.get("semantic_move_record")) else "absent"
        if stage_id == "social_state":
            return "present" if _non_empty_dict(canonical_record.get("social_state_record")) else "absent"
        if stage_id == "character_mind":
            return "present" if _non_empty_list(canonical_record.get("character_mind_records")) else "absent"
        if stage_id == "scene_plan":
            return "present" if _non_empty_dict(canonical_record.get("scene_plan_record")) else "absent"
        if stage_id == "proposed_narrative":
            if _non_empty_dict(last_turn.get("narrative_commit")):
                return "present"
            gen = (last_turn.get("model_route") or {}).get("generation")
            if isinstance(gen, dict) and any(
                gen.get(k) not in (None, "", [], {})
                for k in ("primary_text", "text", "narrative", "content", "structured_output")
            ):
                return "present"
            return "absent"
        if stage_id == "dramatic_effect_gate":
            return "present" if _non_empty_dict(gate_outcome) else "absent"
        if stage_id == "validation":
            if isinstance(validation, dict) and validation.get("status") is not None:
                return "present"
            return "absent"
        if stage_id == "commit":
            return "present" if isinstance(committed, dict) else "absent"
        if stage_id == "visible_output":
            vo = last_turn.get("visible_output_bundle")
            if isinstance(vo, dict) and bool(vo):
                return "present"
            if isinstance(vo, list) and bool(vo):
                return "present"
            return "absent"
        return "absent"

    stages_out: list[dict[str, Any]] = []
    for sid, label in _SEMANTIC_FLOW_STAGES:
        stages_out.append({"id": sid, "label": label, "presence": presence_for(sid)})

    edges: list[dict[str, str]] = []
    for idx in range(len(stages_out) - 1):
        edges.append({"from_stage": stages_out[idx]["id"], "to_stage": stages_out[idx + 1]["id"]})

    return {"stages": stages_out, "edges": edges}


def _last_turn_from_bundle(bundle: dict[str, Any]) -> dict[str, Any] | None:
    diagnostics = bundle.get("world_engine_diagnostics")
    if not isinstance(diagnostics, dict):
        return None
    rows = diagnostics.get("diagnostics")
    if not isinstance(rows, list) or not rows:
        return None
    tail = rows[-1]
    return tail if isinstance(tail, dict) else None


def _projectable_state(
    *,
    bundle: dict[str, Any],
    last_turn: dict[str, Any],
) -> dict[str, Any]:
    model_route = last_turn.get("model_route")
    routing = {}
    generation = {}
    if isinstance(model_route, dict):
        generation = model_route.get("generation") if isinstance(model_route.get("generation"), dict) else {}
        routing = {k: v for k, v in model_route.items() if k != "generation"}
    module_id = bundle.get("module_id")
    current_scene_id = bundle.get("current_scene_id")
    world_engine_story_session_id = bundle.get("world_engine_story_session_id")
    turn_number = last_turn.get("turn_number")
    state: dict[str, Any] = {
        "session_id": world_engine_story_session_id,
        "trace_id": last_turn.get("trace_id"),
        "module_id": module_id,
        "current_scene_id": current_scene_id,
        "turn_number": turn_number if isinstance(turn_number, int) else None,
        "retrieval": last_turn.get("retrieval") if isinstance(last_turn.get("retrieval"), dict) else {},
        "routing": routing,
        "generation": generation,
        "graph_diagnostics": last_turn.get("graph") if isinstance(last_turn.get("graph"), dict) else {},
        "visible_output_bundle": last_turn.get("visible_output_bundle"),
        "diagnostics_refs": last_turn.get("diagnostics_refs"),
        "experiment_preview": last_turn.get("experiment_preview"),
        "validation_outcome": (
            last_turn.get("validation_outcome")
            if isinstance(last_turn.get("validation_outcome"), dict)
            else {}
        ),
        "committed_result": (
            last_turn.get("committed_result") if isinstance(last_turn.get("committed_result"), dict) else {}
        ),
        "selected_scene_function": last_turn.get("selected_scene_function"),
    }
    state.update(_planner_fields_from_last_turn(last_turn))
    return state


def _character_mind_provenance_summary(canonical_record: dict[str, Any]) -> list[dict[str, Any]] | None:
    records = canonical_record.get("character_mind_records")
    if not isinstance(records, list) or not records:
        return None
    rows: list[dict[str, Any]] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        ck = item.get("character_key")
        prov = item.get("provenance")
        if not isinstance(prov, dict):
            field_sources = {}
        else:
            field_sources = {
                str(fk): (fv.get("source") if isinstance(fv, dict) else None)
                for fk, fv in prov.items()
                if isinstance(fk, str)
            }
        rows.append({"character_key": ck, "field_sources": field_sources})
    return rows or None


def _build_provenance_entries(canonical_record: dict[str, Any], last_turn: dict[str, Any]) -> list[dict[str, Any]]:
    val = canonical_record.get("validation_outcome")
    if not isinstance(val, dict):
        val = {}
    com = canonical_record.get("committed_result")
    if not isinstance(com, dict):
        com = {}
    graph = canonical_record.get("graph_diagnostics_summary")
    if not isinstance(graph, dict):
        graph = {}
    routing = canonical_record.get("routing")
    if not isinstance(routing, dict):
        routing = {}
    selected_scene_function = canonical_record.get("selected_scene_function")
    pacing_mode = canonical_record.get("pacing_mode")
    dramatic = val.get("dramatic_effect_gate_outcome")
    if not isinstance(dramatic, dict):
        dramatic = {}

    entries: list[dict[str, Any]] = []

    def add_entry(
        *,
        field: str,
        value: Any,
        source_kind: str,
        source_ref: str,
        derivation_rule: str,
        code_path: str,
        influence_targets: list[str],
        decision_effect: str,
        rejected_alternatives: list[Any] | None = None,
    ) -> None:
        if value is None:
            entries.append(
                {
                    "field": field,
                    "status": "unavailable",
                    "value": None,
                    "source_kind": source_kind,
                    "source_ref": source_ref,
                    "derivation_rule": derivation_rule,
                    "code_path": code_path,
                    "influence_targets": influence_targets,
                    "decision_effect": decision_effect,
                    "rejected_alternatives": rejected_alternatives or [],
                    "status_reason": f"unavailable:{field}",
                }
            )
            return
        entries.append(
            {
                "field": field,
                "status": "supported",
                "value": value,
                "source_kind": source_kind,
                "source_ref": source_ref,
                "derivation_rule": derivation_rule,
                "code_path": code_path,
                "influence_targets": influence_targets,
                "decision_effect": decision_effect,
                "rejected_alternatives": rejected_alternatives or [],
                "status_reason": None,
            }
        )

    add_entry(
        field="selected_scene_function",
        value=selected_scene_function,
        source_kind="runtime_derived",
        source_ref="diagnostics.selected_scene_function",
        derivation_rule="pass_through_single_turn_event",
        code_path="world-engine/app/story_runtime/manager.py:execute_turn.event",
        influence_targets=["validation_projection", "authority_projection"],
        decision_effect="drives scene-function framing for turn diagnostics",
    )
    add_entry(
        field="pacing_mode",
        value=pacing_mode,
        source_kind="runtime_derived",
        source_ref="operator_canonical_turn_record.pacing_mode",
        derivation_rule="pass_through_from_runtime_state_projection",
        code_path="ai_stack/goc_turn_seams.py:build_operator_canonical_turn_record",
        influence_targets=["planner_state_projection"],
        decision_effect="informs pacing-related planner posture",
    )
    add_entry(
        field="validation_status",
        value=val.get("status"),
        source_kind="runtime_derived",
        source_ref="diagnostics.validation_outcome.status",
        derivation_rule="pass_through_single_turn_event",
        code_path="world-engine/app/story_runtime/manager.py:execute_turn.event",
        influence_targets=["validation_projection", "authority_projection"],
        decision_effect="determines approval/rejection presentation",
        rejected_alternatives=dramatic.get("rejection_reasons")
        if isinstance(dramatic.get("rejection_reasons"), list)
        else [],
    )
    add_entry(
        field="commit_applied",
        value=com.get("commit_applied"),
        source_kind="runtime_derived",
        source_ref="diagnostics.committed_result.commit_applied",
        derivation_rule="pass_through_single_turn_event",
        code_path="world-engine/app/story_runtime/manager.py:execute_turn.event",
        influence_targets=["authority_projection", "fallback_projection"],
        decision_effect="marks whether authoritative commit was applied",
    )
    add_entry(
        field="execution_health",
        value=graph.get("execution_health"),
        source_kind="runtime_derived",
        source_ref="diagnostics.graph.execution_health",
        derivation_rule="graph_summary_projection",
        code_path="ai_stack/goc_turn_seams.py:build_operator_canonical_turn_record",
        influence_targets=["decision_trace_projection", "fallback_projection"],
        decision_effect="surfaces degraded or healthy runtime path",
    )
    legacy_fallback = dramatic.get("legacy_fallback_used")
    add_entry(
        field="legacy_fallback_used",
        value=legacy_fallback,
        source_kind="legacy_fallback",
        source_ref="diagnostics.validation_outcome.dramatic_effect_gate_outcome.legacy_fallback_used",
        derivation_rule="pass_through_if_supported_by_gate_outcome",
        code_path="ai_stack/goc_turn_seams.py:run_validation_seam",
        influence_targets=["fallback_projection", "gate_projection"],
        decision_effect="shows if legacy dramatic fallback affected gate posture",
    )
    add_entry(
        field="routing_fallback_stage_reached",
        value=routing.get("fallback_stage_reached"),
        source_kind="fallback_default",
        source_ref="diagnostics.model_route.fallback_stage_reached",
        derivation_rule="routing_projection_from_model_route",
        code_path="world-engine/app/story_runtime/manager.py:execute_turn.event",
        influence_targets=["fallback_projection", "decision_trace_projection"],
        decision_effect="shows fallback chain depth for selected route",
    )

    rationale = dramatic.get("effect_rationale_codes")
    if isinstance(rationale, list):
        add_entry(
            field="effect_rationale_codes",
            value=list(rationale),
            source_kind="runtime_derived",
            source_ref="diagnostics.validation_outcome.dramatic_effect_gate_outcome.effect_rationale_codes",
            derivation_rule="pass_through_if_supported_by_gate_outcome",
            code_path="ai_stack/dramatic_effect_gate.py",
            influence_targets=["gate_projection", "provenance_projection"],
            decision_effect="bounded rationale codes attached to dramatic-effect evaluation",
        )

    trace = dramatic.get("diagnostic_trace")
    if isinstance(trace, list):
        compact = []
        for step in trace[:32]:
            if isinstance(step, dict):
                compact.append(
                    {"code": step.get("code"), "detail": (step.get("detail") or "")[:200]}
                )
        if compact:
            add_entry(
                field="dramatic_effect_diagnostic_trace",
                value=compact,
                source_kind="runtime_derived",
                source_ref="diagnostics.validation_outcome.dramatic_effect_gate_outcome.diagnostic_trace",
                derivation_rule="pass_through_if_supported_by_gate_outcome",
                code_path="ai_stack/dramatic_effect_contract.py",
                influence_targets=["gate_projection", "provenance_projection"],
                decision_effect="bounded diagnostic trace steps for operators",
            )

    cm_summary = _character_mind_provenance_summary(canonical_record)
    if cm_summary is not None:
        add_entry(
            field="character_mind_provenance_summary",
            value=cm_summary,
            source_kind="runtime_derived",
            source_ref="operator_canonical_turn_record.character_mind_records[].provenance",
            derivation_rule="aggregate_field_provenance_per_character_mind_record",
            code_path="ai_stack/character_mind_contract.py",
            influence_targets=["planner_state_projection", "provenance_projection"],
            decision_effect="shows authored vs fallback provenance for tactical identity fields",
        )

    return entries


def _gate_projection_payload(gate_outcome: dict[str, Any]) -> dict[str, Any]:
    """Canonical dramatic-effect pass-through with legacy scores isolated."""
    legacy: dict[str, Any] = {}
    canonical: dict[str, Any] = {}
    for key, value in gate_outcome.items():
        if key in _LEGACY_GATE_SUMMARY_KEYS:
            legacy[key] = value
        else:
            canonical[key] = value
    if legacy:
        canonical["legacy_compatibility_summary"] = legacy
    return canonical


def _build_sections(
    *,
    bundle: dict[str, Any],
    canonical_record: dict[str, Any] | None,
    last_turn: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if canonical_record is None or last_turn is None:
        missing_reason = "no_turn_diagnostics_for_session"
        return {
            "turn_identity": make_unavailable_section(reason=missing_reason),
            "planner_state_projection": make_unavailable_section(reason=missing_reason),
            "decision_trace_projection": make_unavailable_section(reason=missing_reason),
            "gate_projection": make_unavailable_section(reason=missing_reason),
            "validation_projection": make_unavailable_section(reason=missing_reason),
            "authority_projection": make_unavailable_section(reason=missing_reason),
            "fallback_projection": make_unavailable_section(reason=missing_reason),
            "provenance_projection": make_unavailable_section(reason=missing_reason),
            "comparison_ready_fields": make_supported_section(
                {
                    "supported_now": [],
                    "reserved_for_future": list(_COMPARISON_RESERVED_FIELDS),
                    "status_note": "comparison engine not implemented in m1",
                }
            ),
        }

    turn_meta = canonical_record.get("turn_metadata")
    if not isinstance(turn_meta, dict):
        turn_meta = {}
    module_id = bundle.get("module_id")
    support_level = support_level_for_module(str(module_id if isinstance(module_id, str) else ""))
    posture = _support_posture(module_id=module_id)

    planner_data: dict[str, Any] = {
        "semantic_move_record": canonical_record.get("semantic_move_record"),
        "social_state_record": canonical_record.get("social_state_record"),
        "character_mind_records": canonical_record.get("character_mind_records"),
        "scene_plan_record": canonical_record.get("scene_plan_record"),
        "interpreted_move": canonical_record.get("interpreted_move"),
        "scene_assessment": canonical_record.get("scene_assessment"),
        "selected_responder_set": canonical_record.get("selected_responder_set"),
        "selected_scene_function": canonical_record.get("selected_scene_function"),
        "pacing_mode": canonical_record.get("pacing_mode"),
        "silence_brevity_decision": canonical_record.get("silence_brevity_decision"),
    }
    if posture is not None:
        planner_data["support_posture"] = posture
    _core_keys = (
        "semantic_move_record",
        "social_state_record",
        "character_mind_records",
        "scene_plan_record",
        "interpreted_move",
        "scene_assessment",
        "selected_responder_set",
        "selected_scene_function",
        "pacing_mode",
        "silence_brevity_decision",
    )
    _core_empty = not any(planner_data.get(k) is not None for k in _core_keys)
    if _core_empty and posture is None:
        planner_section = make_unavailable_section(
            reason="planner_surface_not_emitted_by_runtime_diagnostics_event",
            data=planner_data,
        )
    else:
        planner_section = make_supported_section(planner_data)

    graph = canonical_record.get("graph_diagnostics_summary")
    if not isinstance(graph, dict):
        graph = {}
    routing = canonical_record.get("routing")
    if not isinstance(routing, dict):
        routing = {}
    nodes = graph.get("nodes_executed") if isinstance(graph.get("nodes_executed"), list) else []
    flow_edges: list[dict[str, str]] = []
    for idx in range(len(nodes) - 1):
        src = nodes[idx]
        dst = nodes[idx + 1]
        if isinstance(src, str) and isinstance(dst, str):
            flow_edges.append({"from": src, "to": dst})

    validation = canonical_record.get("validation_outcome")
    if not isinstance(validation, dict):
        validation = {}
    gate_outcome = validation.get("dramatic_effect_gate_outcome")
    if not isinstance(gate_outcome, dict):
        gate_outcome = {}
    committed = canonical_record.get("committed_result")
    if not isinstance(committed, dict):
        committed = {}
    generation = (last_turn.get("model_route") or {}).get("generation")
    if not isinstance(generation, dict):
        generation = {}

    gate_data = _gate_projection_payload(gate_outcome) if gate_outcome else {}
    gate_section = (
        make_supported_section(gate_data)
        if gate_outcome
        else make_unavailable_section(
            reason="gate_outcome_not_present_in_validation_payload",
            data=gate_data,
        )
    )

    semantic_flow = _build_semantic_decision_flow(
        support_level=support_level,
        canonical_record=canonical_record,
        last_turn=last_turn,
        gate_outcome=gate_outcome,
        validation=validation,
        committed=committed,
    )

    section_data: dict[str, dict[str, Any]] = {
        "turn_identity": make_supported_section(
            {
                "backend_session_id": bundle.get("backend_session_id"),
                "world_engine_story_session_id": bundle.get("world_engine_story_session_id"),
                "module_id": bundle.get("module_id"),
                "current_scene_id": bundle.get("current_scene_id"),
                "turn_number_backend": bundle.get("turn_counter_backend"),
                "turn_number_world_engine": turn_meta.get("turn_number"),
                "turn_trace_id": turn_meta.get("trace_id"),
            }
        ),
        "planner_state_projection": planner_section,
        "decision_trace_projection": make_supported_section(
            {
                "graph_name": graph.get("graph_name"),
                "graph_version": graph.get("graph_version"),
                "execution_health": graph.get("execution_health"),
                "fallback_path_taken": graph.get("fallback_path_taken"),
                "nodes_executed": nodes,
                "node_outcomes": graph.get("node_outcomes"),
                "route_mode": routing.get("route_mode"),
                "route_reason_code": routing.get("route_reason_code") or routing.get("route_reason"),
                "fallback_chain": routing.get("fallback_chain"),
                "fallback_stage_reached": routing.get("fallback_stage_reached"),
                "graph_path_summary": (bundle.get("last_turn_repro_metadata") or {}).get("graph_path_summary"),
                "adapter_invocation_mode": (bundle.get("last_turn_repro_metadata") or {}).get(
                    "adapter_invocation_mode"
                ),
                "semantic_decision_flow": semantic_flow,
                "graph_execution_flow": {
                    "flow_nodes": [node for node in nodes if isinstance(node, str)],
                    "flow_edges": flow_edges,
                },
                "flow_nodes": [node for node in nodes if isinstance(node, str)],
                "flow_edges": flow_edges,
            }
        ),
        "gate_projection": gate_section,
        "validation_projection": make_supported_section(
            {
                "status": validation.get("status"),
                "reason": validation.get("reason"),
                "validator_lane": validation.get("validator_lane"),
                "dramatic_quality_gate": validation.get("dramatic_quality_gate"),
                "dramatic_effect_weak_signal": validation.get("dramatic_effect_weak_signal"),
            }
        ),
        "authority_projection": make_supported_section(
            {
                "authoritative_surface": "world_engine_session_commit_state",
                "commit_applied": committed.get("commit_applied"),
                "committed_effect_count": len(committed.get("committed_effects", []))
                if isinstance(committed.get("committed_effects"), list)
                else 0,
                "experiment_preview": canonical_record.get("experiment_preview"),
                "authority_boundary_note": (
                    "diagnostic projections are read-only and cannot mutate runtime truth"
                ),
                "non_authoritative_inputs": [
                    "graph_diagnostics",
                    "retrieval",
                    "model_route",
                    "visible_output_bundle",
                ],
            }
        ),
        "fallback_projection": make_supported_section(
            {
                "fallback_path_taken": graph.get("fallback_path_taken"),
                "execution_health": graph.get("execution_health"),
                "routing_fallback_chain": routing.get("fallback_chain"),
                "routing_fallback_stage_reached": routing.get("fallback_stage_reached"),
                "model_fallback_used": generation.get("fallback_used"),
                "legacy_fallback_used": gate_outcome.get("legacy_fallback_used"),
                "legacy_fallback_reason": (
                    gate_outcome.get("legacy_fallback_reason") or gate_outcome.get("legacy_fallback_rationale")
                ),
            }
        ),
        "provenance_projection": make_supported_section(
            {
                "entries": _build_provenance_entries(canonical_record=canonical_record, last_turn=last_turn),
                "note": "deterministic projections only; no narrative synthesis",
            }
        ),
        "comparison_ready_fields": make_supported_section(
            {
                "supported_now": {
                    "turn_number": turn_meta.get("turn_number"),
                    "turn_trace_id": turn_meta.get("trace_id"),
                    "graph_version": graph.get("graph_version"),
                    "execution_health": graph.get("execution_health"),
                    "fallback_path_taken": graph.get("fallback_path_taken"),
                    "validation_status": validation.get("status"),
                    "validation_reason": validation.get("reason"),
                    "gate_result": gate_data.get("gate_result"),
                    "empty_fluency_risk": gate_data.get("empty_fluency_risk"),
                    "character_plausibility_posture": gate_data.get("character_plausibility_posture"),
                    "continuity_support_posture": gate_data.get("continuity_support_posture"),
                    "continues_or_changes_pressure": gate_data.get("continues_or_changes_pressure"),
                    "supports_scene_function": gate_data.get("supports_scene_function"),
                    "legacy_fallback_used": gate_data.get("legacy_fallback_used"),
                    "semantic_planner_support_level": posture.get("semantic_planner_support_level")
                    if posture
                    else None,
                    "commit_applied": committed.get("commit_applied"),
                    "selected_scene_function": canonical_record.get("selected_scene_function"),
                    "pacing_mode": canonical_record.get("pacing_mode"),
                },
                "reserved_for_future": list(_COMPARISON_RESERVED_FIELDS),
            }
        ),
    }
    if gate_section["status"] == "unavailable":
        section_data["gate_projection"] = make_unsupported_section(
            reason="dramatic_gate_not_supported_for_this_turn_payload",
            data=gate_data,
        )
    return section_data


def build_inspector_turn_projection(
    *,
    session_id: str,
    trace_id: str,
    mode: str = "canonical",
) -> dict[str, Any]:
    """Return canonical single-turn projection and optional raw evidence envelope."""
    bundle = build_session_evidence_bundle(session_id=session_id, trace_id=trace_id)
    if bundle.get("error") == "backend_session_not_found":
        return bundle

    last_turn = _last_turn_from_bundle(bundle)
    canonical_record: dict[str, Any] | None = None
    if isinstance(last_turn, dict):
        canonical_record = build_operator_canonical_turn_record(
            _projectable_state(bundle=bundle, last_turn=last_turn)
        )

    sections = _build_sections(bundle=bundle, canonical_record=canonical_record, last_turn=last_turn)
    projection_status = "ok" if last_turn is not None else "partial"
    if bundle.get("world_engine_story_session_id") in (None, ""):
        projection_status = "partial"

    payload = build_inspector_turn_projection_root(
        trace_id=bundle.get("trace_id"),
        backend_session_id=str(bundle.get("backend_session_id") or session_id),
        world_engine_story_session_id=bundle.get("world_engine_story_session_id"),
        projection_status=projection_status,
        sections=sections,
        warnings=list(bundle.get("degraded_path_signals") or []),
        raw_evidence_refs={
            "source": "world_engine_diagnostics_session_bridge",
            "mode": mode,
        },
    )
    if mode == "raw":
        payload["raw_evidence"] = {
            "world_engine_state": bundle.get("world_engine_state"),
            "world_engine_diagnostics": bundle.get("world_engine_diagnostics"),
            "execution_truth": bundle.get("execution_truth"),
            "cross_layer_classifiers": bundle.get("cross_layer_classifiers"),
            "bridge_errors": bundle.get("bridge_errors"),
        }
    return payload
