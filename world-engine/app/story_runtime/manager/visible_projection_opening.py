from __future__ import annotations

from ._deps import *

def _record_callback_web_aspect(
    *,
    session: StorySession,
    graph_state: dict[str, Any],
    event: dict[str, Any],
    record: dict[str, Any] | None,
    graph_export: dict[str, Any] | None,
    validation: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    runtime_profile_id = _runtime_profile_id_from_projection(
        session.runtime_projection if isinstance(session.runtime_projection, dict) else None
    )
    blocks = callback_web_aspect_blocks(
        record=record,
        graph_export=graph_export,
        validation=validation,
        policy=policy,
    )
    status = str(validation.get("status") or "missing")
    failure_codes = [
        str(code)
        for code in (validation.get("failure_codes") or [])
        if str(code).strip()
    ]
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
    ledger = set_aspect_record(
        ledger,
        ASPECT_CALLBACK_WEB,
        make_aspect_record(
            applicable=bool(policy.get("enabled")),
            status=status,
            expected=blocks.get("expected") if isinstance(blocks.get("expected"), dict) else {},
            selected=blocks.get("selected") if isinstance(blocks.get("selected"), dict) else {},
            actual=blocks.get("actual") if isinstance(blocks.get("actual"), dict) else {},
            reasons=failure_codes,
            source="commit",
            failure_class="observability_gap" if failure_codes else None,
            failure_reason=failure_codes[0] if failure_codes else None,
        ),
    )
    event["turn_aspect_ledger"] = ledger
    graph_state["turn_aspect_ledger"] = ledger

def _record_consequence_cascade_aspect(
    *,
    session: StorySession,
    graph_state: dict[str, Any],
    event: dict[str, Any],
    record: dict[str, Any] | None,
    graph_export: dict[str, Any] | None,
    validation: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    runtime_profile_id = _runtime_profile_id_from_projection(
        session.runtime_projection if isinstance(session.runtime_projection, dict) else None
    )
    blocks = consequence_cascade_aspect_blocks(
        record=record,
        graph_export=graph_export,
        validation=validation,
        policy=policy,
    )
    status = str(validation.get("status") or "missing")
    failure_codes = [
        str(code)
        for code in (validation.get("failure_codes") or [])
        if str(code).strip()
    ]
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
    ledger = set_aspect_record(
        ledger,
        ASPECT_CONSEQUENCE_CASCADE,
        make_aspect_record(
            applicable=bool(policy.get("enabled")),
            status=status,
            expected=blocks.get("expected") if isinstance(blocks.get("expected"), dict) else {},
            selected=blocks.get("selected") if isinstance(blocks.get("selected"), dict) else {},
            actual=blocks.get("actual") if isinstance(blocks.get("actual"), dict) else {},
            reasons=failure_codes,
            source="commit",
            failure_class="observability_gap" if failure_codes else None,
            failure_reason=failure_codes[0] if failure_codes else None,
        ),
    )
    event["turn_aspect_ledger"] = ledger
    graph_state["turn_aspect_ledger"] = ledger

def _module_scope_truth(module_id: str | None = None) -> dict[str, Any]:
    requested = str(module_id or "").strip() or None
    supported = (
        requested in SUPPORTED_LIVE_STORY_MODULE_IDS
        if requested is not None
        else None
    )
    return {
        "contract": "story_runtime_module_scope.v1",
        "runtime_scope": "module_specific",
        "supported_live_module_ids": list(SUPPORTED_LIVE_STORY_MODULE_IDS),
        "requested_module_id": requested,
        "requested_module_supported": supported,
        "module_specific_hooks": [
            "goc_host_experience_template",
            "goc_prior_continuity_for_graph",
            "goc_append_continuity_impacts",
            "callback_web",
            "consequence_cascade",
        ],
        "unsupported_module_policy": (
            "non_goc_modules_are_not_advertised_as_full_live_story_support"
        ),
        "support_note": (
            "God of Carnage is the only fully wired live story module in this "
            "runtime lane; other module ids must be reported honestly until "
            "module-general support is implemented."
        ),
    }

def _coerce_visible_text_lines(value: Any) -> list[str]:
    if isinstance(value, str):
        line = value.strip()
        return [line] if line else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []

def _ensure_gm_narration_from_narrator_scene_blocks(bundle: dict[str, Any]) -> dict[str, Any]:
    """When gm_narration is absent but scene_blocks include narrator lanes, mirror text for MVP4 contracts."""
    out = dict(bundle)
    if _coerce_visible_text_lines(out.get("gm_narration")):
        return out
    blocks = out.get("scene_blocks")
    if not isinstance(blocks, list):
        return out
    lines: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if str(block.get("block_type") or "").strip() != "narrator":
            continue
        t = str(block.get("text") or "").strip()
        if t:
            lines.append(t)
    if lines:
        out["gm_narration"] = lines
    return out

def _finalize_visible_bundle_opening_gm_narration(
    *,
    session: StorySession,
    graph_state: dict[str, Any],
    packaged_bundle: Any,
    commit_turn_number: int,
) -> Any:
    """After experience packaging, restore model-authored GM opening beats for GoC turn 0 when needed."""
    graph_state.pop("_opening_narration_normalization", None)
    if commit_turn_number != 0 or session.module_id != GOD_OF_CARNAGE_MODULE_ID:
        return packaged_bundle
    if not isinstance(packaged_bundle, dict):
        return packaged_bundle
    if str(graph_state.get("director_path_mode") or "").strip() == "narrator_path":
        return packaged_bundle
    gen = graph_state.get("generation") if isinstance(graph_state.get("generation"), dict) else {}
    meta = gen.get("metadata") if isinstance(gen.get("metadata"), dict) else {}
    structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), dict) else None
    if structured is None and isinstance(gen.get("structured_output"), dict):
        structured = gen["structured_output"]
    if not isinstance(structured, dict):
        return packaged_bundle
    narration = structured.get("narration_summary")
    proj = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
    selected = proj.get("selected_player_role")
    human = proj.get("human_actor_id")
    spoken = structured.get("spoken_lines")
    beats, norm_meta = normalize_opening_narration_beats(
        narration,
        selected_player_role=str(selected).strip() if selected else None,
        human_actor_id=str(human).strip() if human else None,
        module_id=session.module_id,
        turn_number=commit_turn_number,
        output_language=getattr(session, "session_output_language", None),
        existing_actor_lines=spoken if isinstance(spoken, list) else None,
    )
    if isinstance(norm_meta, dict):
        graph_state["_opening_narration_normalization"] = norm_meta
    if beats is None or len(beats) < 3:
        return packaged_bundle
    out = dict(packaged_bundle)
    out["gm_narration"] = beats[:12]
    return out

def _maybe_split_goc_opening_into_two_movements(
    blocks: list[dict[str, Any]],
    *,
    commit_turn_number: int,
) -> list[dict[str, Any]]:
    """ADR-0035: Prefer two visible narrator blocks for opening (premise → salon) when prose uses paragraph breaks."""
    if commit_turn_number != 0 or len(blocks) != 1:
        return blocks
    b0 = blocks[0]
    if str(b0.get("block_type") or "").strip() != "narrator":
        return blocks
    text = str(b0.get("text") or "").strip()
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(parts) < 2:
        return blocks
    out: list[dict[str, Any]] = []
    for i, p in enumerate(parts):
        nb = dict(b0)
        nb["text"] = p
        nb["id"] = f"turn-{commit_turn_number}-live-block-{i + 1}"
        out.append(nb)
    return out

def _dedupe_goc_speaker_colon_stutter(text: str) -> str:
    """Delegate to shared visible-text helper (also applied inside ``sanitize_visible_block_text``)."""
    return dedupe_goc_speaker_colon_stutter_visible(text)

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
