"""Live-scene turn envelope helpers.

Builds the live-scene envelope that carries committed turn text, actor lines, diagnostics, and player-visible metadata.
"""
from __future__ import annotations

from ._deps import *

def _build_live_scene_turn_envelope(
    *,
    session: StorySession,
    graph_state: dict[str, Any],
    scene_blocks: list[dict[str, Any]],
    turn_number: int,
) -> dict[str, Any]:
    proj = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
    selected_player_role = str(proj.get("selected_player_role") or "").strip()
    human_actor_id = str(proj.get("human_actor_id") or "").strip()
    npc_actor_ids = [
        str(actor_id)
        for actor_id in (proj.get("npc_actor_ids") or [])
        if str(actor_id).strip()
    ]
    ai_allowed_actor_ids: set[str] = set()
    for actor_id in npc_actor_ids:
        ai_allowed_actor_ids.update(expand_goc_actor_id_aliases(actor_id))
    ai_forbidden_actor_ids = sorted(expand_goc_actor_id_aliases(human_actor_id))
    responders = graph_state.get("selected_responder_set")
    responder_ids = [
        str(row.get("actor_id") or row.get("responder_id") or "").strip()
        for row in (responders if isinstance(responders, list) else [])
        if isinstance(row, dict) and str(row.get("actor_id") or row.get("responder_id") or "").strip()
    ]
    embedded_speech_actor_ids: list[str] = []
    for block in scene_blocks:
        if not isinstance(block, dict):
            continue
        spans = block.get("embedded_speech_spans")
        if not isinstance(spans, list):
            continue
        for span in spans:
            if not isinstance(span, dict):
                continue
            actor_id = str(span.get("actor_id") or "").strip()
            speech_text = str(span.get("speech_text") or "").strip()
            if actor_id and speech_text and actor_id not in embedded_speech_actor_ids:
                embedded_speech_actor_ids.append(actor_id)
    if not responder_ids and embedded_speech_actor_ids:
        responder_ids = embedded_speech_actor_ids
    primary_responder_id = responder_ids[0] if responder_ids else ""
    secondary_responder_ids = responder_ids[1:]
    visible_actor_response_present = any(
        str(block.get("block_type") or "") in {"actor_line", "actor_action"}
        for block in scene_blocks
        if isinstance(block, dict)
    ) or bool(embedded_speech_actor_ids) or bool(primary_responder_id)
    narrator_path_no_npc = (
        str(graph_state.get("director_path_mode") or "").strip() == "narrator_path"
        and not visible_actor_response_present
        and not primary_responder_id
    )

    initiatives = []
    if primary_responder_id and not narrator_path_no_npc:
        initiatives.append(
            {
                "actor_id": primary_responder_id,
                "intent": "live_runtime_generated_response",
                "allowed_block_types": ["actor_line", "actor_action"],
                "target_actor_id": human_actor_id or None,
                "passivity_risk": "low",
            }
        )
    for actor_id in secondary_responder_ids:
        if not narrator_path_no_npc:
            initiatives.append(
                {
                    "actor_id": actor_id,
                    "intent": "live_runtime_secondary_response",
                    "allowed_block_types": ["actor_line", "actor_action"],
                    "target_actor_id": human_actor_id or None,
                    "passivity_risk": "low",
                }
            )
    npc_agency_plan = None if narrator_path_no_npc else {
        "contract": "npc_agency_plan.v1",
        "turn_number": turn_number,
        "primary_responder_id": primary_responder_id,
        "secondary_responder_ids": secondary_responder_ids,
        "npc_initiatives": initiatives,
    }
    npc_agency_diag = {
        "primary_responder_id": primary_responder_id,
        "secondary_responder_ids": secondary_responder_ids,
        "visible_actor_response_present": visible_actor_response_present,
        "npc_agency_plan_count": len(initiatives),
    }
    if narrator_path_no_npc:
        npc_agency_diag.update(
            {
                "status": "not_applicable",
                "reason": "narrator_path_speech_free_phase",
                "npc_agency_plan_built": False,
            }
        )

    return {
        "contract": "scene_turn_envelope.v2",
        "content_module_id": session.module_id,
        "runtime_profile_id": str(_runtime_profile_id_from_projection(proj) or session.module_id),
        "runtime_module_id": str(proj.get("runtime_module_id") or "solo_story_runtime"),
        "session_output_language": session.session_output_language,
        "player_role_display_name": _role_display_name(
            human_actor_id=human_actor_id or None,
            selected_player_role=selected_player_role or None,
        ),
        "selected_player_role": selected_player_role,
        "human_actor_id": human_actor_id,
        "npc_actor_ids": sorted(npc_actor_ids),
        "npc_agency_plan": npc_agency_plan,
        "visible_scene_output": {
            "contract": "visible_scene_output.blocks.v1",
            "blocks": [dict(block) for block in scene_blocks],
        },
        "diagnostics": {
            "live_dramatic_scene_simulator": {
                "status": "not_invoked_live_graph_primary",
                "invoked": False,
                "entrypoint": "story.turn.execute",
                "decision_count": 0,
                "output_contract": "visible_scene_output.blocks.v1",
                "scene_block_count": len(scene_blocks),
                "visible_actor_response_present": visible_actor_response_present,
                "legacy_blob_used": False,
                "story_session_id": session.session_id,
                "turn_number": turn_number,
                "input_hash": "",
                "output_hash": "",
            },
            "npc_agency": npc_agency_diag,
            "actor_lane_enforcement": {
                "human_actor_id": human_actor_id,
                "ai_allowed_actor_ids": sorted(ai_allowed_actor_ids),
                "ai_forbidden_actor_ids": ai_forbidden_actor_ids,
                "validation_ran_before_commit": True,
            },
            "phase_cost": {
                "phase": "live_runtime_graph_projection",
                "billing_mode": "included_in_model_invoke",
                "token_source": "model_generation",
                "billable": False,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "provider": "world_engine",
                "model": "live_runtime_graph_projection",
                "currency": "USD",
                "pricing_source": "included_in_model_invoke",
                "latency_ms": None,
                "decision_count": 0,
                "scene_block_count": len(scene_blocks),
                "visible_actor_response_present": visible_actor_response_present,
            },
        },
    }

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
