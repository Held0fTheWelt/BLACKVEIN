"""LDSS narrative queue helpers.

Queues and drains narrative events for lightweight downstream session-state synchronization.
"""
from __future__ import annotations

from ._deps import *

def _build_ldss_scene_envelope(
    *,
    session: "StorySession",
    graph_state: dict[str, Any],
    player_input: str,
    turn_number: int,
) -> dict[str, Any] | None:
    """Build SceneTurnEnvelope.v2 for God of Carnage solo sessions via LDSS.

    Called from _finalize_committed_turn after actor-lane validation and commit
    have already completed. Returns None for non-solo sessions.
    """
    proj = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
    human_actor_id = str(proj.get("human_actor_id") or "").strip()
    if not human_actor_id:
        return None

    npc_ids = proj.get("npc_actor_ids")
    npc_actor_ids = sorted(
        str(a) for a in (npc_ids or []) if isinstance(a, str) and a.strip()
    )
    selected_player_role = str(proj.get("selected_player_role") or "").strip()

    canonical_path = _resolve_canonical_path_for_session(session)
    if canonical_path is not None and not session.canonical_step_id:
        session.canonical_step_id = canonical_path.first_step_id()

    ldss_input = build_ldss_input_from_session(
        session_id=session.session_id,
        module_id=session.module_id,
        turn_number=turn_number,
        selected_player_role=selected_player_role or human_actor_id,
        human_actor_id=human_actor_id,
        npc_actor_ids=npc_actor_ids,
        player_input=player_input,
        current_scene_id=session.current_scene_id,
        runtime_profile_id=str(_runtime_profile_id_from_projection(proj) or session.module_id),
        content_module_id=session.module_id,
        # STAGING-OPENING-LANGUAGE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P1: pass session output
        # language so the deterministic fallback renders language-correct opening text.
        session_output_language=getattr(session, "session_output_language", DEFAULT_SESSION_LANGUAGE) or DEFAULT_SESSION_LANGUAGE,
        canonical_step_id=session.canonical_step_id,
        canonical_path=canonical_path,
    )

    ldss_output = run_ldss(ldss_input)

    # Advance the canonical step pointer when the canonical-step path produced
    # visible output. The full unlock-gate logic (theme realization, forces
    # response chain completion) is a Phase 6 deliverable; here we advance on
    # successful turn completion only.
    if (
        canonical_path is not None
        and session.canonical_step_id
        and ldss_output.status == "approved"
        and ldss_output.visible_actor_response_present
        and not _turn_holds_canonical_path_for_free_player_action(graph_state)
    ):
        nxt = canonical_path.next_step_id_after(session.canonical_step_id)
        if nxt:
            session.canonical_step_id = nxt

    envelope = build_scene_turn_envelope_v2(
        ldss_input=ldss_input,
        ldss_output=ldss_output,
        story_session_id=session.session_id,
        turn_number=turn_number,
        runtime_module_id=str(proj.get("runtime_module_id") or "solo_story_runtime"),
    )
    graph_state.setdefault("phase_costs", {})["ldss"] = dict(ldss_output.phase_cost)
    return envelope.to_dict()

def _orchestrate_narrative_agent(
    manager: "StoryRuntimeManager",
    session_id: str,
    ldss_output: dict[str, Any] | None,
    runtime_state: dict[str, Any],
    dramatic_signature: dict[str, Any],
    narrative_threads: list[dict[str, Any]],
    turn_number: int,
    trace_id: str | None = None,
    narrator_packet: dict[str, Any] | None = None,
) -> bool:
    """
    Start NarrativeRuntimeAgent streaming narrator blocks (Phase 3).

    Called after LDSS execution. Creates agent, marks streaming as active.
    Returns True if orchestration started, False if LDSS output not available.
    """
    if not ldss_output or not ldss_output.get("npc_agency_plan"):
        return False

    npc_agency_plan = ldss_output.get("npc_agency_plan", {})

    # Create agent input from committed state
    agent_input = NarrativeRuntimeAgentInput(
        runtime_state=runtime_state,
        npc_agency_plan=npc_agency_plan,
        dramatic_signature=dramatic_signature,
        narrative_threads=narrative_threads or [],
        session_id=session_id,
        turn_number=turn_number,
        trace_id=trace_id,
        enable_langfuse_tracing=manager._get_tracing_config(session_id),
        narrator_packet=dict(narrator_packet) if isinstance(narrator_packet, dict) else {},
    )

    # Create and store agent with input for streaming endpoint to access
    agent = NarrativeRuntimeAgent()
    agent.current_input = agent_input  # Store for streaming endpoint
    manager.narrative_agents[session_id] = agent
    manager.input_queues[session_id] = []
    manager._narrative_streaming_active[session_id] = True

    return True

def _check_ruhepunkt_signal(
    manager: "StoryRuntimeManager",
    session_id: str,
    agent: NarrativeRuntimeAgent | None = None,
) -> bool:
    """
    Check if NarrativeRuntimeAgent has signaled ruhepunkt (rest point).

    Ruhepunkt = remaining NPC initiatives = 0, input can be processed.
    Returns True if ruhepunkt reached, False otherwise.
    """
    if not agent:
        agent = manager.narrative_agents.get(session_id)

    if not agent:
        return False

    # In MVP3, ruhepunkt is signaled when motivation analysis shows 0 remaining initiatives
    # This is a simplified check - full implementation in Phase 4-5 involves
    # streaming state from the agent
    return manager._narrative_streaming_active.get(session_id, False) is False

def _process_input_queue(
    manager: "StoryRuntimeManager",
    session_id: str,
) -> list[str]:
    """
    Process queued player inputs after ruhepunkt signal.

    Returns list of queued inputs that should be processed next.
    Clears queue after returning.
    """
    queue = manager.input_queues.get(session_id, [])
    if queue:
        manager.input_queues[session_id] = []
    return queue

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
