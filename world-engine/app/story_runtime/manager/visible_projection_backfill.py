from __future__ import annotations

from ._deps import *

def _try_spoken_with_blocks(
    *,
    append_fn: Any,
    actor_label_fn: Any,
    runtime_projection: dict[str, Any] | None,
    human_actor_id: str,
    selected_player_role: str,
    structured_output: dict[str, Any],
) -> str | None:
    spoken = structured_output.get("spoken_lines")
    if not isinstance(spoken, list):
        return None
    for row in spoken:
        if not isinstance(row, dict):
            continue
        speaker_id = str(row.get("speaker_id") or "").strip()
        line = str(row.get("text") or row.get("line") or "").strip()
        if not line:
            continue
        if runtime_projection is not None:
            if not speaker_id:
                continue
            if _is_goc_human_lane_actor(
                speaker_id,
                human_actor_id=human_actor_id,
                selected_player_role=selected_player_role,
            ):
                continue
        append_fn(
            "actor_line",
            line,
            speaker_label=actor_label_fn(speaker_id),
            actor_id=speaker_id or None,
        )
        return "spoken_lines"
    return None

def _try_action_with_blocks(
    *,
    append_fn: Any,
    actor_label_fn: Any,
    runtime_projection: dict[str, Any] | None,
    human_actor_id: str,
    selected_player_role: str,
    structured_output: dict[str, Any],
    action_block_type: str = "actor_action",
) -> str | None:
    actions = structured_output.get("action_lines")
    if not isinstance(actions, list):
        return None
    for row in actions:
        if not isinstance(row, dict):
            continue
        aid = str(row.get("actor_id") or "").strip()
        line = str(row.get("text") or row.get("line") or "").strip()
        if not line:
            continue
        if runtime_projection is not None:
            if not aid:
                continue
            if _is_goc_human_lane_actor(
                aid,
                human_actor_id=human_actor_id,
                selected_player_role=selected_player_role,
            ):
                continue
        bt = str(action_block_type or "actor_action").strip().lower()
        if bt not in {"actor_action", "actor_line"}:
            bt = "actor_action"
        append_fn(
            bt,
            line,
            speaker_label=actor_label_fn(aid),
            actor_id=aid or None,
        )
        return "action_lines"
    return None

def _try_initiative_with_blocks(
    *,
    append_fn: Any,
    actor_label_fn: Any,
    runtime_projection: dict[str, Any] | None,
    human_actor_id: str,
    selected_player_role: str,
    structured_output: dict[str, Any],
) -> str | None:
    events = structured_output.get("initiative_events")
    if not isinstance(events, list):
        return None
    for ev in events:
        if not isinstance(ev, dict):
            continue
        aid = str(ev.get("actor_id") or "").strip()
        ev_type = str(ev.get("type") or "").strip().lower()
        if ev_type not in {"interrupt", "counter", "seize_initiative"}:
            continue
        line = str(ev.get("text") or ev.get("line") or ev.get("summary") or "").strip()
        if not line or not aid:
            continue
        if runtime_projection is not None and _is_goc_human_lane_actor(
            aid,
            human_actor_id=human_actor_id,
            selected_player_role=selected_player_role,
        ):
            continue
        append_fn(
            "actor_action",
            line,
            speaker_label=actor_label_fn(aid),
            actor_id=aid or None,
        )
        return "initiative_events"
    return None

def _append_canonical_signal(signals: list[str], signal: str) -> None:
    if signal not in DEGRADATION_SIGNAL_VALUES:
        return
    if signal not in signals:
        signals.append(signal)

def _canonical_quality_fields_from_surfaces(
    *,
    runtime_governance_surface: dict[str, Any],
    authority_summary: dict[str, Any],
) -> tuple[str, list[str], str]:
    quality = str(runtime_governance_surface.get("quality_class") or "").strip().lower()
    signals = runtime_governance_surface.get("degradation_signals")
    signal_list: list[str] = []
    if isinstance(signals, list):
        for signal in signals:
            _append_canonical_signal(signal_list, str(signal).strip())

    if not signal_list:
        validation_status = str(authority_summary.get("validation_status") or "").strip().lower()
        validation_reason = str(runtime_governance_surface.get("validation_reason") or "").strip().lower()
        fallback_stage = str(runtime_governance_surface.get("fallback_stage_reached") or "").strip().lower()
        transition_pattern = str(runtime_governance_surface.get("transition_pattern") or "").strip().lower()
        if fallback_stage and fallback_stage != "primary_only":
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_FALLBACK_USED)
        if bool(runtime_governance_surface.get("mock_output_flag")):
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_FALLBACK_USED)
        if transition_pattern == "diagnostics_only":
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_NON_FACTUAL_STAGING)
        if validation_reason == "degraded_commit_after_retries":
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_DEGRADED_COMMIT)
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_RETRY_EXHAUSTED)
        if validation_reason == "opening_leniency_approved":
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_PROSE_ONLY_RECOVERY)
        if runtime_governance_surface.get("dramatic_quality_gate") == "effect_gate_weak_signal":
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_WEAK_SIGNAL_ACCEPTED)
        rationale_codes = runtime_governance_surface.get("dramatic_effect_rationale_codes")
        if isinstance(rationale_codes, list) and "actor_lanes_thin_prose_override" in [str(x) for x in rationale_codes]:
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_THIN_PROSE_OVERRIDE)
        actor_lane_status = str(runtime_governance_surface.get("actor_lane_validation_status") or "").strip().lower()
        if actor_lane_status == "rejected":
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_ACTOR_LANES_VALIDATION_GATED)
        if validation_status and validation_status != "approved" and quality != QUALITY_CLASS_FAILED:
            quality = QUALITY_CLASS_FAILED

    if quality not in QUALITY_CLASS_VALUES:
        validation_status = str(authority_summary.get("validation_status") or "").strip().lower()
        quality = canonical_quality_class(
            validation_outcome={"status": validation_status},
            commit_applied=bool(authority_summary.get("commit_applied")),
            degradation_signals=signal_list,
        )

    summary = str(runtime_governance_surface.get("degradation_summary") or "").strip()
    if not summary:
        summary = ", ".join(signal_list) if signal_list else "none"
    return quality, signal_list, summary

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
