"""No-dead-end recovery helpers.

Builds playable recovery output when validation or graph execution rejects a turn without ending the session.
"""
from __future__ import annotations

from ._deps import *

def _recoverable_playability_metadata(
    *,
    player_input: str,
    reason: str,
    turn_kind: str,
    no_dead_end_recovery: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recovery = no_dead_end_recovery if isinstance(no_dead_end_recovery, dict) else {}
    recovery_obstacle_kind = str(recovery.get("obstacle_kind") or "").strip()
    if recovery_obstacle_kind == "validation_or_scene_constraint":
        obstacle_kind = "validation_rejection"
    else:
        obstacle_kind = recovery_obstacle_kind or (
            "runtime_graph_exception" if reason == "graph_execution_exception" else "validation_rejection"
        )
    next_steps = recovery.get("next_step_options") if isinstance(recovery.get("next_step_options"), list) else []
    out = {
        "contract": "recoverable_outcome_playability.v1",
        "recovery_mode": "retry_affordance" if obstacle_kind == "runtime_graph_exception" else "scene_constraint_redirect",
        "obstacle_kind": obstacle_kind,
        "attempted_action_present": bool(str(player_input or "").strip()),
        "next_step_affordance_present": True,
        "technical_leak_absent": True,
        "commits_story_truth": False,
        "turn_kind": turn_kind,
    }
    if recovery:
        playability = recovery.get("playability") if isinstance(recovery.get("playability"), dict) else {}
        commit_policy = recovery.get("commit_policy") if isinstance(recovery.get("commit_policy"), dict) else {}
        out.update(
            {
                "no_dead_end_recovery_schema": recovery.get("schema_version"),
                "recovery_class": recovery.get("recovery_class"),
                "next_step_count": len(next_steps),
                "next_step_affordance_present": bool(playability.get("next_step_affordance_present")),
                "technical_leak_absent": bool(playability.get("technical_leak_absent")),
                "commits_story_truth": bool(commit_policy.get("commits_story_truth")),
            }
        )
    return out

def _no_dead_end_recovery_aspect_record(recovery: dict[str, Any]) -> dict[str, Any]:
    validation = recovery.get("validation") if isinstance(recovery.get("validation"), dict) else {}
    failure_codes = validation.get("failure_codes") if isinstance(validation.get("failure_codes"), list) else []
    approved = str(validation.get("status") or "") == "approved"
    reason = str(recovery.get("obstacle_reason") or "").strip()
    playability = recovery.get("playability") if isinstance(recovery.get("playability"), dict) else {}
    commit_policy = recovery.get("commit_policy") if isinstance(recovery.get("commit_policy"), dict) else {}
    return make_aspect_record(
        applicable=True,
        status="passed" if approved else "failed",
        expected={
            "schema_version": NO_DEAD_END_RECOVERY_SCHEMA_VERSION,
            "playable_recovery_required": True,
            "next_step_required": True,
            "technical_leak_absent_required": True,
        },
        selected={
            "recovery_class": recovery.get("recovery_class"),
            "obstacle_kind": recovery.get("obstacle_kind"),
            "next_step_option_count": len(recovery.get("next_step_options") or []),
        },
        actual={
            "validation_status": validation.get("status"),
            "failure_codes": failure_codes,
            "next_step_affordance_present": bool(playability.get("next_step_affordance_present")),
            "technical_leak_absent": bool(playability.get("technical_leak_absent")),
            "commits_story_truth": bool(commit_policy.get("commits_story_truth")),
            "committed_truth_scope": commit_policy.get("committed_truth_scope"),
            "false_truth_feedback_allowed": bool(commit_policy.get("false_truth_feedback_allowed")),
        },
        reasons=[str(code) for code in failure_codes] or ([reason] if reason else []),
        source="runtime",
        failure_class=None if approved else "recoverable_dramatic_failure",
        failure_reason=None if approved else (str(failure_codes[0]) if failure_codes else reason or "no_dead_end_recovery_failed"),
    )

def _record_no_dead_end_recovery_aspect(
    ledger: dict[str, Any] | None,
    recovery: dict[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(ledger, dict):
        return None
    return set_aspect_record(
        ledger,
        ASPECT_NO_DEAD_END_RECOVERY,
        _no_dead_end_recovery_aspect_record(recovery),
    )

def _event_reason_for_no_dead_end(event: dict[str, Any], turn_outcome: str | None = None) -> str:
    validation = event.get("validation_outcome") if isinstance(event.get("validation_outcome"), dict) else {}
    commit = event.get("narrative_commit") if isinstance(event.get("narrative_commit"), dict) else {}
    for value in (
        validation.get("reason"),
        commit.get("commit_reason_code"),
        turn_outcome,
        event.get("reason"),
    ):
        text = str(value or "").strip()
        if text:
            return text
    return "continue"

def _attach_no_dead_end_recovery_to_event(
    *,
    session: "StorySession",
    graph_state: dict[str, Any],
    event: dict[str, Any],
    player_input: str,
    turn_number: int,
    turn_kind: str,
    turn_outcome: str,
    recoverable_outcome: bool = False,
) -> dict[str, Any] | None:
    if str(turn_kind or "").strip().lower() in {"opening", "engine_opening"} and not str(player_input or "").strip():
        return None
    visible_output_bundle = (
        event.get("visible_output_bundle")
        if isinstance(event.get("visible_output_bundle"), dict)
        else graph_state.get("visible_output_bundle")
        if isinstance(graph_state.get("visible_output_bundle"), dict)
        else {}
    )
    committed_result = (
        event.get("committed_result")
        if isinstance(event.get("committed_result"), dict)
        else graph_state.get("committed_result")
        if isinstance(graph_state.get("committed_result"), dict)
        else {}
    )
    recovery = build_no_dead_end_recovery_record(
        story_session_id=session.session_id,
        module_id=session.module_id,
        turn_number=turn_number,
        turn_kind=turn_kind,
        player_input=player_input,
        reason=_event_reason_for_no_dead_end(event, turn_outcome),
        validation_outcome=event.get("validation_outcome") if isinstance(event.get("validation_outcome"), dict) else {},
        narrative_commit=event.get("narrative_commit") if isinstance(event.get("narrative_commit"), dict) else {},
        committed_result=committed_result,
        visible_output_bundle=visible_output_bundle,
        recoverable_outcome=recoverable_outcome,
    )
    event["no_dead_end_recovery"] = recovery
    graph_state["no_dead_end_recovery"] = recovery
    ledger = event.get("turn_aspect_ledger") if isinstance(event.get("turn_aspect_ledger"), dict) else None
    if ledger is not None:
        ledger = _record_no_dead_end_recovery_aspect(ledger, recovery) or ledger
        event["turn_aspect_ledger"] = ledger
        graph_state["turn_aspect_ledger"] = ledger
    diagnostics = event.get("diagnostics") if isinstance(event.get("diagnostics"), dict) else None
    if diagnostics is not None:
        diagnostics["no_dead_end_recovery"] = recovery
        diagnostics["turn_aspect_ledger"] = event.get("turn_aspect_ledger")
    return recovery

def _recoverable_narrator_visible_output_bundle(*, message: str) -> dict[str, Any]:
    """Single writer for narrator-led recoverable player surface (ADR-0038 Phase C)."""
    block: dict[str, Any] = {
        "block_type": "narrator",
        "text": message,
        "player_display_text": message,
        "origin_aspect": "validation",
        "origin_beat_id": None,
        "origin_capability": "narrator.recoverable_failure",
        "authority_owner": "narrator",
    }
    return {
        "gm_narration": [message],
        "spoken_lines": [],
        "action_lines": [],
        "scene_blocks": [block],
    }

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
