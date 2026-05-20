from __future__ import annotations

from ._deps import *

def _recoverable_playable_turn_envelope(
    *,
    session: "StorySession",
    commit_turn_number: int,
    player_input: str,
    trace_id: str | None,
    turn_kind: str,
    interpreted_input: dict[str, Any],
    narrative_commit: dict[str, Any],
    validation_outcome: dict[str, Any],
    message: str,
    turn_aspect_ledger: dict[str, Any],
    reason: str,
    diagnostics_extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Shared transport envelope for recoverable / graph-rescue short paths (ADR-0038 Phase C)."""
    turn_aspect_ledger = _stamp_turn_aspect_ledger_identity(
        turn_aspect_ledger,
        session=session,
        commit_turn_number=commit_turn_number,
        turn_kind=turn_kind,
    ) or turn_aspect_ledger
    committed_result = {
        "commit_applied": False,
        "committed_effects": [],
        "reason": reason,
        "recoverable_rejection": True,
    }
    visible_output_bundle = _recoverable_narrator_visible_output_bundle(message=message)
    no_dead_end_recovery = build_no_dead_end_recovery_record(
        story_session_id=session.session_id,
        module_id=session.module_id,
        turn_number=commit_turn_number,
        turn_kind=turn_kind,
        player_input=player_input,
        reason=reason,
        validation_outcome=validation_outcome,
        narrative_commit=narrative_commit,
        committed_result=committed_result,
        visible_output_bundle=visible_output_bundle,
        recoverable_outcome=True,
    )
    turn_aspect_ledger = _record_no_dead_end_recovery_aspect(
        turn_aspect_ledger,
        no_dead_end_recovery,
    ) or turn_aspect_ledger
    playability = _recoverable_playability_metadata(
        player_input=player_input,
        reason=reason,
        turn_kind=turn_kind,
        no_dead_end_recovery=no_dead_end_recovery,
    )
    diag: dict[str, Any] = {
        "recoverable_rejection": True,
        "hard_boundary_failure": False,
        "turn_aspect_ledger": turn_aspect_ledger,
        "no_dead_end_recovery": no_dead_end_recovery,
    }
    if diagnostics_extras:
        diag.update(diagnostics_extras)
    diag["recoverable_playability"] = playability
    return {
        "turn_number": commit_turn_number,
        "canonical_turn_id": _canonical_turn_id(session.session_id, commit_turn_number),
        "turn_kind": turn_kind,
        "raw_input": player_input,
        "trace_id": trace_id,
        "turn_aspect_ledger": turn_aspect_ledger,
        "interpreted_input": interpreted_input,
        "narrative_commit": narrative_commit,
        "validation_outcome": validation_outcome,
        "committed_result": committed_result,
        "visible_output_bundle": visible_output_bundle,
        "no_dead_end_recovery": no_dead_end_recovery,
        "ok": False,
        "turn_status": "rejected_recoverable",
        "reason": reason,
        "recoverable_playability": playability,
        "player_visible_message": message,
        "diagnostics": diag,
    }

def _build_human_input_attribution_record(
    *,
    session: "StorySession",
    graph_state: dict[str, Any],
    interpreted_input: dict[str, Any],
    selected_responder_set: list[dict[str, Any]] | None,
    commit_turn_number: int,
    player_input: str,
) -> dict[str, Any]:
    vis_diag = (
        graph_state.get("_visible_narrative_contract")
        if isinstance(graph_state.get("_visible_narrative_contract"), dict)
        else {}
    )
    raw_bundle = graph_state.get("visible_output_bundle") if isinstance(graph_state.get("visible_output_bundle"), dict) else {}
    render_support = raw_bundle.get("render_support") if isinstance(raw_bundle.get("render_support"), dict) else {}
    human_filters = (
        render_support.get("human_lane_structured_filters")
        if isinstance(render_support.get("human_lane_structured_filters"), dict)
        else {}
    )
    generated_human_rows_dropped = int(human_filters.get("spoken_lines_dropped") or 0) + int(
        human_filters.get("action_lines_dropped") or 0
    )
    projection = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
    human_actor_id = str(projection.get("human_actor_id") or "").strip()
    selected_player_role = str(projection.get("selected_player_role") or "").strip()
    responders = selected_responder_set if isinstance(selected_responder_set, list) else []
    first_responder = responders[0] if responders and isinstance(responders[0], dict) else {}
    primary_responder_id = str(
        graph_state.get("primary_responder_id")
        or first_responder.get("actor_id")
        or first_responder.get("responder_id")
        or ""
    ).strip()
    player_input_kind = interpreted_input.get("player_input_kind")
    graph_input_kind = interpreted_input.get("input_kind") or interpreted_input.get("kind")
    if not player_input_kind:
        player_input_kind = graph_input_kind
    echo_count = int(vis_diag.get("player_input_echo_removed_from_npc_block") or 0)
    return {
        "player_input_actor_id": interpreted_input.get("actor_id"),
        "human_actor_id": human_actor_id or None,
        "selected_player_role": selected_player_role or None,
        "primary_responder_id": primary_responder_id or None,
        "player_input_kind": player_input_kind,
        "graph_input_kind": graph_input_kind,
        "player_action_committed": bool(interpreted_input.get("player_action_committed")),
        "player_speech_committed": bool(interpreted_input.get("player_speech_committed")),
        "narrator_response_expected": bool(interpreted_input.get("narrator_response_expected")),
        "npc_response_expected": bool(interpreted_input.get("npc_response_expected")),
        "player_input_visible_block_present": bool(
            str(player_input or "").strip() and (human_actor_id or selected_player_role) and commit_turn_number > 0
        ),
        "npc_echoed_player_input": echo_count > 0,
        "player_input_attribution_pass": bool(
            str(player_input or "").strip()
            and (human_actor_id or selected_player_role)
            and commit_turn_number > 0
            and echo_count == 0
        ),
        "generated_human_actor_output_filtered": generated_human_rows_dropped > 0,
        "generated_human_lane_rows_dropped": generated_human_rows_dropped,
    }

@dataclass
class StorySession:
    session_id: str
    module_id: str
    runtime_projection: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    turn_counter: int = 0
    current_scene_id: str = ""
    session_input_language: str = DEFAULT_SESSION_LANGUAGE
    session_output_language: str = DEFAULT_SESSION_LANGUAGE
    history: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    narrative_threads: StoryNarrativeThreadSet = field(default_factory=StoryNarrativeThreadSet)
    last_thread_update_trace: ThreadUpdateTrace | None = None
    # Bounded carry-forward of committed GoC continuity classes (not a second memory surface).
    prior_continuity_impacts: list[dict[str, Any]] = field(default_factory=list)
    # Bounded hierarchical memory derived only from canonical committed turns.
    hierarchical_memory: dict[str, Any] = field(default_factory=dict)
    # Durable Pi15 environment state derived from canonical content and committed turns.
    environment_state: dict[str, Any] = field(default_factory=dict)
    # Mechanical runtime world for the unified story session loop.
    runtime_world: dict[str, Any] = field(default_factory=dict)
    # Immutable-ish snapshot of published content identity at session birth (audit F-M3).
    content_provenance: dict[str, Any] = field(default_factory=dict)
    # Canonical path pointer (Phase 5). For modules with a canonical_path, holds the
    # id of the currently active step (e.g. "opening_004_den_arrival_positioning").
    canonical_step_id: str | None = None
    # ADR-0063: append-only W5 actor-situation snapshots. Phase 1 is shadow-only.
    w5_history: list[dict[str, Any]] = field(default_factory=list)
    w5_latest_snapshot: dict[str, Any] | None = None

def _parse_iso_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def story_session_to_payload(session: StorySession) -> dict[str, Any]:
    trace = session.last_thread_update_trace
    return {
        "format_version": 1,
        "session_id": session.session_id,
        "module_id": session.module_id,
        "runtime_projection": session.runtime_projection,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "turn_counter": session.turn_counter,
        "current_scene_id": session.current_scene_id,
        "session_input_language": session.session_input_language,
        "session_output_language": session.session_output_language,
        "history": session.history,
        "diagnostics": session.diagnostics,
        "narrative_threads": session.narrative_threads.model_dump(mode="json"),
        "last_thread_update_trace": trace.model_dump(mode="json") if trace is not None else None,
        "prior_continuity_impacts": session.prior_continuity_impacts,
        "hierarchical_memory": session.hierarchical_memory,
        "environment_state": session.environment_state,
        "runtime_world": session.runtime_world,
        "content_provenance": session.content_provenance,
        "canonical_step_id": session.canonical_step_id,
        # ADR-0063: append-only W5 actor-situation snapshots (shadow in Phase 1).
        "w5_history": list(session.w5_history),
        "w5_latest_snapshot": session.w5_latest_snapshot,
    }

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
