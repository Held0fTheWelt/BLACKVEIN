from __future__ import annotations

from ._deps import *

def story_session_from_payload(data: dict[str, Any]) -> StorySession:
    fv = data.get("format_version", 1)
    if fv != 1:
        raise ValueError(f"Unsupported story session snapshot format_version: {fv!r}")

    raw_trace = data.get("last_thread_update_trace")
    trace: ThreadUpdateTrace | None = None
    if isinstance(raw_trace, dict):
        trace = ThreadUpdateTrace.model_validate(raw_trace)

    threads_raw = data.get("narrative_threads") or {}
    threads = StoryNarrativeThreadSet.model_validate(threads_raw)

    created_at = _parse_iso_datetime(str(data["created_at"]))
    updated_at = _parse_iso_datetime(str(data["updated_at"]))

    provenance = data.get("content_provenance")
    if not isinstance(provenance, dict):
        provenance = {}

    return StorySession(
        session_id=str(data["session_id"]),
        module_id=str(data["module_id"]),
        runtime_projection=dict(data["runtime_projection"]),
        created_at=created_at,
        updated_at=updated_at,
        turn_counter=int(data.get("turn_counter", 0)),
        current_scene_id=str(data.get("current_scene_id") or ""),
        session_input_language=str(data.get("session_input_language") or data.get("session_output_language") or DEFAULT_SESSION_LANGUAGE),
        session_output_language=str(data.get("session_output_language") or DEFAULT_SESSION_LANGUAGE),
        history=list(data.get("history") or []),
        diagnostics=list(data.get("diagnostics") or []),
        narrative_threads=threads,
        last_thread_update_trace=trace,
        prior_continuity_impacts=list(data.get("prior_continuity_impacts") or []),
        hierarchical_memory=dict(data.get("hierarchical_memory") or {}),
        environment_state=dict(data.get("environment_state") or {}),
        runtime_world=dict(data.get("runtime_world") or {}),
        content_provenance=provenance,
        canonical_step_id=(str(data["canonical_step_id"]) if data.get("canonical_step_id") else None),
        # ADR-0063: legacy payloads without W5 fields default to [] / None.
        w5_history=[
            dict(snap) for snap in (data.get("w5_history") or []) if isinstance(snap, dict)
        ],
        w5_latest_snapshot=(
            dict(data["w5_latest_snapshot"])
            if isinstance(data.get("w5_latest_snapshot"), dict)
            else None
        ),
    )

def _load_module_memory_policy(
    *,
    module_id: str,
    runtime_profile_id: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        runtime_policy = load_module_runtime_policy(
            module_id=module_id,
            runtime_profile_id=runtime_profile_id,
        ).to_dict()
    except Exception:
        return {}, {}
    memory_policy = (
        runtime_policy.get("memory_policy")
        if isinstance(runtime_policy.get("memory_policy"), dict)
        else {}
    )
    return runtime_policy, memory_policy

def _load_module_callback_web_policy(
    *,
    module_id: str,
    runtime_profile_id: str | None,
) -> dict[str, Any]:
    try:
        runtime_policy = load_module_runtime_policy(
            module_id=module_id,
            runtime_profile_id=runtime_profile_id,
        ).to_dict()
    except Exception:
        return normalize_callback_web_policy(None)
    return callback_web_policy_from_module_runtime(runtime_policy)

def _load_module_consequence_cascade_policy(
    *,
    module_id: str,
    runtime_profile_id: str | None,
) -> dict[str, Any]:
    try:
        runtime_policy = load_module_runtime_policy(
            module_id=module_id,
            runtime_profile_id=runtime_profile_id,
        ).to_dict()
    except Exception:
        return normalize_consequence_cascade_policy(None)
    return consequence_cascade_policy_from_module_runtime(runtime_policy)

def _record_hierarchical_memory_aspect(
    *,
    session: StorySession,
    graph_state: dict[str, Any],
    event: dict[str, Any],
    committed_turn: dict[str, Any],
    allow_write: bool,
) -> dict[str, Any]:
    """Record policy-driven memory evidence and optionally update session memory."""
    runtime_profile_id = _runtime_profile_id_from_projection(
        session.runtime_projection if isinstance(session.runtime_projection, dict) else None
    )
    runtime_policy, memory_policy = _load_module_memory_policy(
        module_id=session.module_id,
        runtime_profile_id=runtime_profile_id,
    )
    prior_snapshot = (
        session.hierarchical_memory
        if isinstance(session.hierarchical_memory, dict)
        else empty_hierarchical_memory_snapshot(
            module_id=session.module_id,
            runtime_profile_id=runtime_profile_id,
        )
    )
    memory_turn = dict(committed_turn)
    memory_turn.setdefault("module_id", session.module_id)
    memory_turn.setdefault("runtime_profile_id", runtime_profile_id)
    if not allow_write:
        memory_turn["recoverable_outcome"] = True
    write_result = build_hierarchical_memory_write(
        memory_policy=memory_policy,
        committed_turn=memory_turn,
        runtime_policy=runtime_policy,
    )
    if allow_write and write_result.get("write_allowed") and not write_result.get("uncommitted_write_detected"):
        snapshot_after = merge_hierarchical_memory_snapshot(
            prior_snapshot=prior_snapshot,
            write_result=write_result,
            memory_policy=memory_policy,
            module_id=session.module_id,
            runtime_profile_id=runtime_profile_id,
        )
        session.hierarchical_memory = snapshot_after
    else:
        snapshot_after = normalize_hierarchical_memory_snapshot(
            prior_snapshot,
            module_id=session.module_id,
            runtime_profile_id=runtime_profile_id,
        )
        session.hierarchical_memory = snapshot_after
    context = project_hierarchical_memory_context(
        snapshot=snapshot_after,
        memory_policy=memory_policy,
    )
    memory_surface = {
        "contract": "hierarchical_memory_runtime_surface.v1",
        "write_result": write_result,
        "context": context,
    }
    event["hierarchical_memory"] = memory_surface
    graph_state["hierarchical_memory_context"] = context
    selected_tiers = [
        str(item).strip()
        for item in (write_result.get("selected_tiers") or [])
        if str(item).strip()
    ]
    written_items = [
        item
        for item in (write_result.get("written_items") or [])
        if isinstance(item, dict)
    ]
    tiers_written: list[str] = []
    for item in written_items:
        tier_id = str(item.get("tier") or "").strip()
        if tier_id and tier_id not in tiers_written:
            tiers_written.append(tier_id)
    ledger = (
        event.get("turn_aspect_ledger")
        if isinstance(event.get("turn_aspect_ledger"), dict)
        else graph_state.get("turn_aspect_ledger")
        if isinstance(graph_state.get("turn_aspect_ledger"), dict)
        else None
    )
    ledger = ensure_runtime_aspect_ledger(
        ledger,
        session_id=session.session_id,
        module_id=session.module_id,
        turn_number=event.get("turn_number"),
        turn_kind=str(event.get("turn_kind") or "player"),
        raw_player_input=event.get("raw_input"),
        trace_id=event.get("trace_id"),
        runtime_profile_id=runtime_profile_id,
    )
    policy_present = bool(write_result.get("policy_present"))
    status = str(write_result.get("status") or "not_applicable")
    failure_reason = write_result.get("failure_reason")
    ledger = set_aspect_record(
        ledger,
        ASPECT_HIERARCHICAL_MEMORY,
        make_aspect_record(
            applicable=policy_present,
            status=status,
            expected={
                "policy_present": policy_present,
                "policy_enabled": bool(write_result.get("policy_enabled")),
                "committed_turn_required": True,
                "allow_uncommitted_writes": bool(memory_policy.get("allow_uncommitted_writes")),
                "context_projection_bounded": True,
            },
            selected={
                "selected_tiers": selected_tiers,
                "source_canonical_turn_id": write_result.get("source_canonical_turn_id"),
            },
            actual={
                "write_allowed": bool(write_result.get("write_allowed")),
                "written_item_count": len(written_items),
                "tiers_written": tiers_written,
                "memory_present": bool(context.get("memory_present")),
                "context_item_count": int(context.get("item_count") or 0),
                "context_bounded": bool(context.get("bounded")),
                "uncommitted_write_detected": bool(write_result.get("uncommitted_write_detected")),
                "snapshot_item_count": int(snapshot_after.get("item_count") or 0),
            },
            reasons=[str(failure_reason)] if failure_reason else [],
            source="commit" if allow_write else "commit_guard",
            failure_class="hard_contract_failure" if write_result.get("uncommitted_write_detected") else None,
            failure_reason=str(failure_reason) if failure_reason else None,
            missing_field="canonical_turn_id" if failure_reason == "canonical_turn_id_missing" else None,
        ),
    )
    event["turn_aspect_ledger"] = ledger
    graph_state["turn_aspect_ledger"] = ledger
    return memory_surface

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
