"""Model cost and path-core helpers.

Tracks model invocation cost metadata and canonical path fields that must survive turn commits.
"""
from __future__ import annotations

from ._deps import *

def _build_p0_action_resolution_evidence(
    *,
    event: dict[str, Any],
    graph_state: dict[str, Any],
    interpreted_input: dict[str, Any],
    validation: dict[str, Any],
    committed_result: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic P0 player-action audit fields for real player turns only.

    Opening traces (``turn_number == 0``) set ``p0_player_action_evidence_applicable`` false
    and omit player-action payload so Langfuse scores/metadata are not misread as P0 proof.
    """
    turn_number = int(event.get("turn_number") or 0)
    p0_applicable = turn_number > 0
    intent_surface_diag = (
        validation.get("intent_surface_diagnostics")
        if isinstance(validation.get("intent_surface_diagnostics"), dict)
        else {}
    )
    npc_narrated_violation = bool(
        validation.get("npc_narrated_player_action_violation")
        or intent_surface_diag.get("npc_narrated_player_action_violation")
    )
    if not p0_applicable:
        return {
            "contract": "p0_action_resolution_evidence.v1",
            "p0_player_action_evidence_applicable": False,
            "p0_excluded_reason": "opening_turn_not_player_action_evidence_lane",
            "raw_player_input": None,
            "player_action_frame": None,
            "resolved_target_status": None,
            "affordance_status": None,
            "action_commit_policy": None,
            "action_commit_status": None,
            "player_speech_committed": None,
            "player_action_committed": None,
            "narrator_response_expected": None,
            "npc_response_expected": None,
            "npc_committed_player_action": None,
            "turn_status": event.get("turn_status"),
            "http_status": event.get("http_status"),
        }

    paf = graph_state.get("player_action_frame") if isinstance(graph_state.get("player_action_frame"), dict) else {}
    inner_aff = paf.get("affordance_resolution") if isinstance(paf.get("affordance_resolution"), dict) else {}
    top_aff = (
        graph_state.get("affordance_resolution") if isinstance(graph_state.get("affordance_resolution"), dict) else {}
    )
    aff_src = inner_aff or top_aff
    aff_st = str(aff_src.get("affordance_status") or paf.get("affordance_status") or "").strip() or None
    pol = str(aff_src.get("action_commit_policy") or "").strip() or None
    paa = (
        committed_result.get("player_action_authority")
        if isinstance(committed_result.get("player_action_authority"), dict)
        else {}
    )
    action_commit_status = str(paa.get("action_commit_status") or "").strip() or None

    p_frame = {
        "raw_text": paf.get("raw_text"),
        "input_kind": paf.get("input_kind") or paf.get("player_input_kind"),
        "action_kind": paf.get("action_kind"),
        "verb": paf.get("verb"),
        "target_query": paf.get("target_query"),
    }

    return {
        "contract": "p0_action_resolution_evidence.v1",
        "p0_player_action_evidence_applicable": True,
        "p0_excluded_reason": None,
        "raw_player_input": str(event.get("raw_input") or graph_state.get("player_input") or "").strip() or None,
        "player_action_frame": p_frame,
        "resolved_target_status": _compose_resolved_target_status(paf, aff_st),
        "affordance_status": aff_st,
        "action_commit_policy": pol,
        "action_commit_status": action_commit_status,
        "player_speech_committed": interpreted_input.get("player_speech_committed"),
        "player_action_committed": interpreted_input.get("player_action_committed"),
        "narrator_response_expected": interpreted_input.get("narrator_response_expected"),
        "npc_response_expected": interpreted_input.get("npc_response_expected"),
        "npc_committed_player_action": npc_narrated_violation,
        "turn_status": event.get("turn_status"),
        "http_status": event.get("http_status"),
    }

def _coerce_non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0

def _build_model_generation_phase_cost(graph_state: dict[str, Any]) -> dict[str, Any] | None:
    """Build truthful phase cost for the final model invocation, when present."""
    if not isinstance(graph_state, dict):
        return None
    generation = graph_state.get("generation") if isinstance(graph_state.get("generation"), dict) else {}
    routing = graph_state.get("routing") if isinstance(graph_state.get("routing"), dict) else {}
    gen_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}

    adapter = str(
        gen_meta.get("final_adapter")
        or gen_meta.get("adapter")
        or gen_meta.get("provider_used")
        or ""
    ).strip()
    provider = str(
        gen_meta.get("provider")
        or gen_meta.get("provider_used")
        or routing.get("selected_provider")
        or adapter
        or ""
    ).strip()
    model = str(
        gen_meta.get("model")
        or gen_meta.get("model_name")
        or routing.get("selected_model")
        or ""
    ).strip()
    attempted = bool(generation.get("attempted") or adapter or provider or model)
    if not attempted:
        return None

    usage_details = gen_meta.get("usage_details") if isinstance(gen_meta.get("usage_details"), dict) else {}
    input_tokens = _coerce_non_negative_int(usage_details.get("input") or gen_meta.get("tokens_prompt"))
    output_tokens = _coerce_non_negative_int(usage_details.get("output") or gen_meta.get("tokens_completion"))
    total_tokens = _coerce_non_negative_int(usage_details.get("total") or gen_meta.get("tokens_total"))
    if total_tokens <= 0 and (input_tokens > 0 or output_tokens > 0):
        total_tokens = input_tokens + output_tokens

    latency_ms_raw = gen_meta.get("generation_latency_ms") or gen_meta.get("latency_ms")
    latency_ms = _coerce_non_negative_int(latency_ms_raw) if latency_ms_raw is not None else None
    phase_extra = {
        "adapter": adapter or None,
        "usage_source": gen_meta.get("usage_source"),
        "usage_available": bool(gen_meta.get("usage_available")) or total_tokens > 0,
        "fallback_used": bool(generation.get("fallback_used")),
        "response_id": gen_meta.get("response_id"),
        "adapter_invocation_mode": gen_meta.get("adapter_invocation_mode"),
    }

    adapter_key = adapter.lower()
    provider_key = provider.lower()
    model_key = model.lower()
    deterministic_adapters = {"ldss_fallback", "ldss_deterministic", "world_engine"}
    mockish = (
        adapter_key == "mock"
        or provider_key == "mock"
        or model_key == "mock"
        or model_key == "mock-model"
    )
    deterministic = adapter_key in deterministic_adapters or provider_key in {"world_engine", "deterministic"}

    if total_tokens > 0 and not mockish and not deterministic:
        return build_provider_usage_phase_cost(
            phase="model_generation",
            provider=provider or adapter or "unknown",
            model=model or "unknown",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            **phase_extra,
        )
    if mockish:
        return build_mock_phase_cost(
            phase="model_generation",
            provider=provider or "mock",
            model=model or "mock",
            latency_ms=latency_ms,
            **phase_extra,
        )
    if deterministic:
        return build_deterministic_phase_cost(
            phase="model_generation",
            provider=provider or "world_engine",
            model=model or adapter or "world_engine_deterministic",
            latency_ms=latency_ms,
            **phase_extra,
        )
    return build_unavailable_phase_cost(
        phase="model_generation",
        provider=provider or adapter or "unknown",
        model=model or "unknown",
        reason="provider_usage_unavailable",
        latency_ms=latency_ms,
        **phase_extra,
    )

def _ensure_model_generation_phase_cost(graph_state: dict[str, Any]) -> None:
    phase_cost = _build_model_generation_phase_cost(graph_state)
    if not phase_cost:
        return
    graph_state.setdefault("phase_costs", {})["model_generation"] = phase_cost

def _langfuse_level_for_output(output: dict[str, Any]) -> str:
    error = str(output.get("error") or output.get("generation_error") or "").strip()
    if error:
        return "ERROR"
    if output.get("fallback_used") or output.get("quality_class") == "degraded":
        return "WARNING"
    if output.get("parser_error_present"):
        return "WARNING"
    return "DEFAULT"

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
