"""Langfuse status and degradation helpers.

Builds Langfuse health status and fallback degradation records for runtime observability.
"""
from __future__ import annotations

from ._deps import *

def _langfuse_status_for_output(name: str, output: dict[str, Any]) -> str:
    if name == "story.graph.path_summary":
        return (
            f"route={output.get('route_model_called')} invoke={output.get('invoke_model_called')} "
            f"fallback={output.get('fallback_model_called')} validation={output.get('validation_called')} "
            f"commit={output.get('commit_called')} quality={output.get('quality_class')}"
        )
    if name == "story.phase.model_route":
        return (
            f"route={output.get('route_id') or 'unknown'} provider={output.get('selected_provider') or 'unknown'} "
            f"model={output.get('selected_model') or 'unknown'} mode={output.get('generation_execution_mode') or 'unknown'}"
        )
    if name == "story.phase.model_invoke":
        return (
            f"called={output.get('called')} attempted={output.get('attempted')} success={output.get('success')} "
            f"adapter={output.get('adapter') or 'unknown'} api_model={output.get('api_model') or 'unknown'} "
            f"error={output.get('error') or 'none'} parser_error={output.get('parser_error') or 'none'}"
        )
    if name == "story.phase.primary_parse":
        err = output.get("parser_error") or "none"
        short_err = (err[:80] + "...") if err != "none" and len(err) > 80 else err
        return (
            f"api_success={output.get('api_success')} "
            f"parser_error_present={output.get('parser_error_present')} "
            f"structured_output={output.get('structured_output_present')} "
            f"parser_error={short_err}"
        )
    if name == "story.phase.model_fallback":
        return (
            f"called={output.get('called')} fallback_used={output.get('fallback_used')} "
            f"fallback_model={output.get('fallback_model') or 'unknown'} error={output.get('generation_error') or 'none'}"
        )
    if name == "story.phase.retrieval":
        return (
            f"called={output.get('called')} status={output.get('status') or 'unknown'} "
            f"route={output.get('retrieval_route') or 'unknown'} hits={output.get('hit_count')} "
            f"profile={output.get('profile') or 'unknown'} context_attached={output.get('context_attached')}"
        )
    if name == "story.phase.validation":
        return (
            f"called={output.get('called')} status={output.get('status') or 'unknown'} "
            f"actor_lane={output.get('actor_lane_validation_status') or 'unknown'} "
            f"intent={output.get('player_input_kind') or 'unknown'} "
            f"sem={output.get('semantic_move_kind') or 'unknown'} "
            f"violation={output.get('npc_narrated_player_action_violation')}"
        )
    if name == "story.phase.commit":
        return (
            f"called={output.get('called')} commit_applied={output.get('commit_applied')} "
            f"quality={output.get('quality_class') or 'unknown'} degradation={output.get('degradation_summary') or 'none'} "
            f"selection={output.get('scene_director_selection_source') or 'unknown'}"
        )
    if name == "story.phase.intent_interpretation":
        return (
            f"kind={output.get('player_input_kind') or 'unknown'} "
            f"action={output.get('player_action_committed')} speech={output.get('player_speech_committed')} "
            f"narrator_expected={output.get('narrator_response_expected')} npc_expected={output.get('npc_response_expected')}"
        )
    return name

def _finish_langfuse_span(
    span: Any,
    *,
    output: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    level: str = "DEFAULT",
    status_message: str | None = None,
) -> None:
    if span is None:
        return
    try:
        span.update(
            output=output,
            metadata=metadata or {},
            level=level,
            status_message=status_message,
        )
    except Exception:
        logger.debug("Langfuse span update failed", exc_info=True)
    try:
        span.end()
    except Exception:
        logger.debug("Langfuse span end failed", exc_info=True)

def _compute_action_consequence_diagnostics(path_summary: dict[str, Any]) -> dict[str, Any]:
    """Build the public action_consequence_diagnostics payload.

    STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P4: every player turn must
    expose deterministic numeric values for the action/local-context contract. Opening
    turns and pure-speech turns use ``not_applicable``; degraded/fallback paths use
    ``evaluated_degraded`` but still emit real numeric values.
    """
    turn_number = int(path_summary.get("turn_number") or 0)
    if turn_number == 0:
        return {
            "status": "not_applicable",
            "reason": "opening_turn",
            "local_context_transition_present": 1.0,
            "narrator_consequence_present": 1.0,
            "new_location_established": 1.0,
            "perception_result_present": 1.0,
            "action_consequence_contract_pass": 1.0,
            "npc_consequence_takeover_absent": 1.0,
        }
    intent_kind = str(path_summary.get("player_input_kind") or "").strip().lower()
    action_intents = {"action", "perception", "object_interaction", "physical_action", "movement_action", "perception_action"}
    is_action_resolution = intent_kind in action_intents and bool(
        path_summary.get("authoritative_action_surface") or path_summary.get("player_action_frame_present")
    )
    lct = path_summary.get("local_context_transition") if isinstance(path_summary.get("local_context_transition"), dict) else None
    ncp = path_summary.get("narrator_consequence_plan") if isinstance(path_summary.get("narrator_consequence_plan"), dict) else None
    quality_class = str(path_summary.get("quality_class") or "").strip().lower()
    fallback_used = bool(path_summary.get("generation_fallback_used")) or quality_class in {"degraded", "failed"}
    if intent_kind not in action_intents:
        return {
            "status": "not_applicable",
            "reason": f"intent_kind:{intent_kind or 'unknown'}",
            "local_context_transition_present": 1.0,
            "narrator_consequence_present": 1.0,
            "new_location_established": 1.0,
            "perception_result_present": 1.0,
            "action_consequence_contract_pass": 1.0,
            "npc_consequence_takeover_absent": 1.0,
        }
    local_context_transition_present = 1.0 if lct else 0.0
    narrator_consequence_present = 1.0 if (ncp and ncp.get("consequence_text")) else 0.0
    new_area_established = bool(lct and lct.get("new_area_established")) if lct else False
    movement_turn = bool(lct and str(lct.get("transition_type") or "").startswith("move")) if lct else False
    new_location_established = 1.0 if (new_area_established or not movement_turn) else 0.0
    perception_turn = bool(lct and str(lct.get("transition_type") or "") == "perception") if lct else False
    perception_result_present = 1.0 if (not perception_turn or (ncp and ncp.get("consequence_text"))) else 0.0
    consequence_contract_pass = bool(
        lct
        and ncp
        and (
            ncp.get("consequence_text")
            or ncp.get("consequence_type") not in {None, "generic"}
        )
    )
    action_consequence_contract_pass = 1.0 if consequence_contract_pass else 0.0
    # npc_consequence_takeover_absent: on action/perception turns, if responder set contains a
    # non-narrator actor and the visible bundle includes an NPC line that conveys the perception
    # result instead of the narrator, the score drops to 0. Heuristic: if visible NPC lines exist
    # on a perception or movement turn AND no narrator consequence_text was produced, NPC took over.
    npc_lines = int(path_summary.get("npc_visible_line_count") or 0)
    if npc_lines == 0:
        npc_takeover_absent = 1.0
    else:
        npc_takeover_absent = 0.0 if (movement_turn or perception_turn) and narrator_consequence_present == 0.0 else 1.0
    status = "evaluated"
    if not is_action_resolution:
        status = "evaluated_degraded"
    elif fallback_used:
        status = "evaluated_degraded"

    movement_return_intent = bool(path_summary.get("movement_return_intent"))
    aff_pol = str(path_summary.get("action_commit_policy") or "").strip().lower()
    aff_st = str(path_summary.get("affordance_status") or "").strip().lower()
    if movement_return_intent and aff_pol == "needs_clarification" and aff_st == "ambiguous":
        status = "needs_clarification"
        local_context_transition_present = 0.0
        narrator_consequence_present = 0.0
        new_location_established = 0.0
        action_consequence_contract_pass = 0.0

    tgt_src = path_summary.get("target_resolution_source")
    res_tgt = path_summary.get("resolved_target_id")
    if movement_return_intent and status == "needs_clarification" and not res_tgt:
        tgt_src = tgt_src or "missing_previous_location_id"

    out: dict[str, Any] = {
        "status": status,
        "local_context_transition_present": local_context_transition_present,
        "narrator_consequence_present": narrator_consequence_present,
        "new_location_established": new_location_established,
        "perception_result_present": perception_result_present,
        "action_consequence_contract_pass": action_consequence_contract_pass,
        "npc_consequence_takeover_absent": npc_takeover_absent,
    }
    if movement_return_intent:
        out["movement_return_intent"] = True
    if res_tgt:
        out["resolved_target_id"] = res_tgt
    if tgt_src:
        out["target_resolution_source"] = str(tgt_src)
    if "speech_projection_allowed" in path_summary:
        out["speech_projection_allowed"] = bool(path_summary.get("speech_projection_allowed"))
    return out

def _runtime_aspect_score_value(value: bool) -> float:
    return 1.0 if value else 0.0

def _runtime_aspect_score_metadata(
    *,
    ledger: dict[str, Any],
    aspect_name: str,
    score_name: str,
    value: float,
    path_summary: dict[str, Any],
) -> dict[str, Any]:
    meta = aspect_score_metadata(
        ledger=ledger,
        aspect_name=aspect_name,
        score_name=score_name,
    )
    meta.update(
        {
            "aspect_score": True,
            "score_value": value,
            "session_id": meta.get("session_id") or path_summary.get("session_id"),
            "turn_number": meta.get("turn_number") or path_summary.get("turn_number"),
            "canonical_turn_id": path_summary.get("canonical_turn_id")
            or (
                _canonical_turn_id(
                    str(path_summary.get("session_id") or ledger.get("session_id") or ""),
                    int(path_summary.get("turn_number") or ledger.get("turn_number") or 0),
                )
                if (path_summary.get("session_id") or ledger.get("session_id"))
                else None
            ),
            "raw_player_input": path_summary.get("raw_player_input"),
            "turn_kind": path_summary.get("turn_kind"),
            "module_id": path_summary.get("module_id") or ledger.get("module_id"),
            "runtime_profile_id": path_summary.get("runtime_profile_id") or ledger.get("runtime_profile_id"),
            "environment": path_summary.get("environment"),
        }
    )
    if value < 1.0 and not meta.get("failure_reason"):
        meta["failure_reason"] = "aspect_score_failed"
    return meta

def _build_canonical_degradation_signals(path_summary: dict[str, Any]) -> list[str]:
    """Filter ``path_summary['degradation_signals']`` to canonical values only.

    The canonical contract (``DEGRADATION_SIGNAL_VALUES``) is consumed by
    diagnostics / operator-history aggregation. Score metadata uses this filtered
    view so that the canonical surface stays stable regardless of what
    ``_ldss_opening_fallback_state`` or visibility-marker pipelines append.
    """
    raw = path_summary.get("degradation_signals") or []
    if not isinstance(raw, list):
        return []
    canonical: list[str] = []
    for entry in raw:
        token = str(entry).strip()
        if token and token in DEGRADATION_SIGNAL_VALUES and token not in canonical:
            canonical.append(token)
    return canonical

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
