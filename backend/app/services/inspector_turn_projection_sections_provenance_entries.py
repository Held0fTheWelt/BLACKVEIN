"""Aufbau einzelner Provenance-Einträge (DS-040); Orchestrierung in `build_provenance_entries`."""

from __future__ import annotations

from typing import Any


def character_mind_provenance_summary(canonical_record: dict[str, Any]) -> list[dict[str, Any]] | None:
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


def append_provenance_entry(
    entries: list[dict[str, Any]],
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


def append_turn_baseline_provenance_entries(
    entries: list[dict[str, Any]],
    *,
    selected_scene_function: Any,
    pacing_mode: Any,
    val: dict[str, Any],
    com: dict[str, Any],
    graph: dict[str, Any],
    routing: dict[str, Any],
    dramatic: dict[str, Any],
) -> None:
    append_provenance_entry(
        entries,
        field="selected_scene_function",
        value=selected_scene_function,
        source_kind="runtime_derived",
        source_ref="diagnostics.selected_scene_function",
        derivation_rule="pass_through_single_turn_event",
        code_path="world-engine/app/story_runtime/manager.py:execute_turn.event",
        influence_targets=["validation_projection", "authority_projection"],
        decision_effect="drives scene-function framing for turn diagnostics",
    )
    append_provenance_entry(
        entries,
        field="pacing_mode",
        value=pacing_mode,
        source_kind="runtime_derived",
        source_ref="operator_canonical_turn_record.pacing_mode",
        derivation_rule="pass_through_from_runtime_state_projection",
        code_path="ai_stack/goc_turn_seams.py:build_operator_canonical_turn_record",
        influence_targets=["planner_state_projection"],
        decision_effect="informs pacing-related planner posture",
    )
    append_provenance_entry(
        entries,
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
    append_provenance_entry(
        entries,
        field="commit_applied",
        value=com.get("commit_applied"),
        source_kind="runtime_derived",
        source_ref="diagnostics.committed_result.commit_applied",
        derivation_rule="pass_through_single_turn_event",
        code_path="world-engine/app/story_runtime/manager.py:execute_turn.event",
        influence_targets=["authority_projection", "fallback_projection"],
        decision_effect="marks whether authoritative commit was applied",
    )
    append_provenance_entry(
        entries,
        field="execution_health",
        value=graph.get("execution_health"),
        source_kind="runtime_derived",
        source_ref="diagnostics.graph.execution_health",
        derivation_rule="graph_summary_projection",
        code_path="ai_stack/goc_turn_seams.py:build_operator_canonical_turn_record",
        influence_targets=["decision_trace_projection", "fallback_projection"],
        decision_effect="surfaces degraded or healthy runtime path",
    )
    append_provenance_entry(
        entries,
        field="legacy_fallback_used",
        value=dramatic.get("legacy_fallback_used"),
        source_kind="legacy_fallback",
        source_ref="diagnostics.validation_outcome.dramatic_effect_gate_outcome.legacy_fallback_used",
        derivation_rule="pass_through_if_supported_by_gate_outcome",
        code_path="ai_stack/goc_turn_seams.py:run_validation_seam",
        influence_targets=["fallback_projection", "gate_projection"],
        decision_effect="shows if legacy dramatic fallback affected gate posture",
    )
    append_provenance_entry(
        entries,
        field="routing_fallback_stage_reached",
        value=routing.get("fallback_stage_reached"),
        source_kind="fallback_default",
        source_ref="diagnostics.model_route.fallback_stage_reached",
        derivation_rule="routing_projection_from_model_route",
        code_path="world-engine/app/story_runtime/manager.py:execute_turn.event",
        influence_targets=["fallback_projection", "decision_trace_projection"],
        decision_effect="shows fallback chain depth for selected route",
    )


def append_dramatic_gate_provenance_entries(
    entries: list[dict[str, Any]], dramatic: dict[str, Any]
) -> None:
    rationale = dramatic.get("effect_rationale_codes")
    if isinstance(rationale, list):
        append_provenance_entry(
            entries,
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
            append_provenance_entry(
                entries,
                field="dramatic_effect_diagnostic_trace",
                value=compact,
                source_kind="runtime_derived",
                source_ref="diagnostics.validation_outcome.dramatic_effect_gate_outcome.diagnostic_trace",
                derivation_rule="pass_through_if_supported_by_gate_outcome",
                code_path="ai_stack/dramatic_effect_contract.py",
                influence_targets=["gate_projection", "provenance_projection"],
                decision_effect="bounded diagnostic trace steps for operators",
            )


def append_character_mind_provenance_entry(
    entries: list[dict[str, Any]], canonical_record: dict[str, Any]
) -> None:
    cm_summary = character_mind_provenance_summary(canonical_record)
    if cm_summary is None:
        return
    append_provenance_entry(
        entries,
        field="character_mind_provenance_summary",
        value=cm_summary,
        source_kind="runtime_derived",
        source_ref="operator_canonical_turn_record.character_mind_records[].provenance",
        derivation_rule="aggregate_field_provenance_per_character_mind_record",
        code_path="ai_stack/character_mind_contract.py",
        influence_targets=["planner_state_projection", "provenance_projection"],
        decision_effect="shows authored vs fallback provenance for tactical identity fields",
    )


def build_provenance_entries(
    canonical_record: dict[str, Any], last_turn: dict[str, Any]
) -> list[dict[str, Any]]:
    _ = last_turn
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
    append_turn_baseline_provenance_entries(
        entries,
        selected_scene_function=selected_scene_function,
        pacing_mode=pacing_mode,
        val=val,
        com=com,
        graph=graph,
        routing=routing,
        dramatic=dramatic,
    )
    append_dramatic_gate_provenance_entries(entries, dramatic)
    append_character_mind_provenance_entry(entries, canonical_record)
    return entries
