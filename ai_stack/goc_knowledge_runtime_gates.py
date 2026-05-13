"""Runtime gates for GoC opening-sequence and hard-forbidden knowledge."""

from __future__ import annotations

from typing import Any

from ai_stack.goc_frozen_vocab import canonicalize_goc_actor_id, expand_goc_actor_id_aliases
from ai_stack.opening_shape_normalizer import narration_summary_to_plain_str

KNOWLEDGE_RUNTIME_GATES_CONTRACT = "goc_knowledge_runtime_gates.v1"


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _unique_strs(values: Any) -> list[str]:
    out: list[str] = []
    for value in _as_list(values):
        text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _event_rows(opening_scene_sequence: dict[str, Any] | None) -> list[dict[str, Any]]:
    opening = _as_dict(opening_scene_sequence)
    return [dict(row) for row in _as_list(opening.get("narrative_events")) if isinstance(row, dict)]


def _opening_handover_phase(opening_scene_sequence: dict[str, Any] | None) -> str | None:
    for event in _event_rows(opening_scene_sequence):
        phase = str(event.get("handover_to_scene_phase") or "").strip()
        if phase:
            return phase
    return None


def _flatten_hard_rules(hard_forbidden_rules: dict[str, Any] | None) -> list[dict[str, Any]]:
    root = _as_dict(_as_dict(hard_forbidden_rules).get("hard_forbidden"))
    rows: list[dict[str, Any]] = []
    for group_id, group_rows in root.items():
        if not isinstance(group_rows, list):
            continue
        for row in group_rows:
            if not isinstance(row, dict):
                continue
            rows.append(
                {
                    "group_id": str(group_id),
                    "id": str(row.get("id") or "").strip(),
                    "rule": str(row.get("rule") or "").strip(),
                    "applies_to": _unique_strs(row.get("applies_to")),
                }
            )
    return [row for row in rows if row.get("id")]


def _role_variant(opening_scene_sequence: dict[str, Any] | None, actor_lane_context: dict[str, Any] | None) -> dict[str, Any]:
    ctx = _as_dict(actor_lane_context)
    role_raw = str(ctx.get("selected_player_role") or ctx.get("human_actor_id") or "").strip()
    role_ids = [role_raw]
    canon = canonicalize_goc_actor_id(role_raw) if role_raw else None
    if canon:
        role_ids.append(canon)
    for event in _event_rows(opening_scene_sequence):
        variants = _as_dict(event.get("role_variants"))
        for role_id in role_ids:
            if role_id in variants and isinstance(variants[role_id], dict):
                return {
                    "event_id": event.get("id"),
                    "role_id": role_id,
                    **dict(variants[role_id]),
                }
    return {}


def build_runtime_knowledge_contract(
    *,
    opening_scene_sequence: dict[str, Any] | None,
    hard_forbidden_rules: dict[str, Any] | None,
    actor_lane_context: dict[str, Any] | None = None,
    session_output_language: str | None = None,
    story_runtime_experience: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the compact model/runtime packet from authored GoC knowledge."""
    opening = _as_dict(opening_scene_sequence)
    hard = _as_dict(hard_forbidden_rules)
    opening_contract = _as_dict(opening.get("opening_contract"))
    narration_mode = _as_dict(opening.get("narration_mode"))
    detection = _as_dict(hard.get("hard_forbidden_detection"))
    rules = _flatten_hard_rules(hard)
    events: list[dict[str, Any]] = []
    for event in _event_rows(opening):
        row = {
            "id": event.get("id"),
            "title": event.get("title"),
            "narrative_function": event.get("narrative_function"),
            "narrator_task": event.get("narrator_task"),
            "establishes": _unique_strs(event.get("establishes")),
            "must_show": _unique_strs(event.get("must_show")),
            "must_not": _unique_strs(event.get("must_not")),
        }
        if event.get("handover_to_scene_phase"):
            row["handover_to_scene_phase"] = event.get("handover_to_scene_phase")
        if isinstance(event.get("role_variants"), dict):
            row["role_variants"] = event["role_variants"]
        events.append(row)
    negative_constraints = [
        {"id": row["id"], "group_id": row["group_id"], "rule": row["rule"]}
        for row in rules
    ]
    return {
        "contract": KNOWLEDGE_RUNTIME_GATES_CONTRACT,
        "opening_scene_sequence_id": opening.get("id"),
        "opening_authority": opening.get("authority"),
        "opening_references": _unique_strs(opening.get("references")),
        "opening_must_establish": _unique_strs(opening_contract.get("must_establish")),
        "opening_must_not": _unique_strs(opening_contract.get("must_not")),
        "opening_event_tasks": events,
        "opening_event_ids": [str(event.get("id") or "").strip() for event in events if event.get("id")],
        "opening_handover_to_scene_phase": _opening_handover_phase(opening),
        "opening_render_policy": {
            "summary_allowed": bool(narration_mode.get("summary_allowed")),
            "min_visible_blocks": narration_mode.get("min_visible_blocks"),
            "preferred_visible_blocks": narration_mode.get("preferred_visible_blocks"),
            "max_visible_blocks": narration_mode.get("max_visible_blocks"),
            "narration_mode_type": narration_mode.get("type"),
        },
        "selected_role_variant": _role_variant(opening, actor_lane_context),
        "hard_forbidden_detection_policy": {
            "reject_on": _unique_strs(detection.get("reject_on")),
            "recover_on": _unique_strs(detection.get("recover_on")),
            "structured_detection_fields": _unique_strs(detection.get("structured_detection_fields")),
            "marker_map": dict(_as_dict(detection.get("marker_map"))),
            "structural_checks": [
                dict(row) for row in _as_list(detection.get("structural_checks")) if isinstance(row, dict)
            ],
        },
        "hard_forbidden_rule_ids": [row["id"] for row in rules],
        "hard_forbidden_negative_constraints": negative_constraints,
        "session_output_language": (session_output_language or "").strip().lower()[:2] or None,
        "story_runtime_experience": dict(story_runtime_experience)
        if isinstance(story_runtime_experience, dict)
        else None,
    }


def build_opening_scene_plan_metadata(
    *,
    opening_scene_sequence: dict[str, Any] | None,
    hard_forbidden_rules: dict[str, Any] | None,
    actor_lane_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = build_runtime_knowledge_contract(
        opening_scene_sequence=opening_scene_sequence,
        hard_forbidden_rules=hard_forbidden_rules,
        actor_lane_context=actor_lane_context,
    )
    return {
        "opening_scene_sequence_id": contract.get("opening_scene_sequence_id"),
        "opening_event_ids": list(contract.get("opening_event_ids") or []),
        "opening_must_establish": list(contract.get("opening_must_establish") or []),
        "opening_handover_to_scene_phase": contract.get("opening_handover_to_scene_phase"),
        "opening_render_policy": dict(contract.get("opening_render_policy") or {}),
        "hard_forbidden_detection_policy": dict(contract.get("hard_forbidden_detection_policy") or {}),
        "hard_forbidden_rule_ids": list(contract.get("hard_forbidden_rule_ids") or []),
        "planner_rationale_code": "opening_scene_sequence_runtime_contract",
    }


def build_narrator_packet(
    *,
    opening_scene_sequence: dict[str, Any] | None,
    hard_forbidden_rules: dict[str, Any] | None,
    actor_lane_context: dict[str, Any] | None = None,
    session_output_language: str | None = None,
    story_runtime_experience: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project the knowledge contract into the narrator phase input."""
    contract = build_runtime_knowledge_contract(
        opening_scene_sequence=opening_scene_sequence,
        hard_forbidden_rules=hard_forbidden_rules,
        actor_lane_context=actor_lane_context,
        session_output_language=session_output_language,
        story_runtime_experience=story_runtime_experience,
    )
    return {
        "contract": "goc_narrator_knowledge_packet.v1",
        "event_tasks": list(contract.get("opening_event_tasks") or []),
        "forbidden_rules": list(contract.get("hard_forbidden_negative_constraints") or []),
        "hard_forbidden_detection_policy": dict(contract.get("hard_forbidden_detection_policy") or {}),
        "role_variant": dict(contract.get("selected_role_variant") or {}),
        "render_policy": dict(contract.get("opening_render_policy") or {}),
        "session_output_language": contract.get("session_output_language"),
    }


def knowledge_contract_prompt_lines(contract: dict[str, Any] | None, *, opening_turn: bool) -> list[str]:
    """Return concise model-visible prompt lines for the active knowledge gates."""
    pkt = _as_dict(contract)
    if not pkt:
        return []
    lines: list[str] = []
    if opening_turn:
        lines.append("Opening Scene Sequence Contract:")
        lines.append(f"- id: {pkt.get('opening_scene_sequence_id')}")
        lines.append(f"- must_establish: {pkt.get('opening_must_establish') or []}")
        lines.append(f"- event_order: {pkt.get('opening_event_ids') or []}")
        lines.append(f"- handover_to_scene_phase: {pkt.get('opening_handover_to_scene_phase')}")
        lines.append(f"- render_policy: {pkt.get('opening_render_policy') or {}}")
        lines.append("- runtime_evidence: structured_output.opening_event_ids must list covered event ids")
        role_variant = pkt.get("selected_role_variant")
        if isinstance(role_variant, dict) and role_variant:
            lines.append(f"- selected_role_variant: {role_variant}")
    lines.append("Hard Forbidden Runtime Rules:")
    lines.append(f"- detection_policy: {pkt.get('hard_forbidden_detection_policy') or {}}")
    lines.append("- runtime_evidence: semantic rule hits must use structured runtime_gate_detections ids")
    constraints = pkt.get("hard_forbidden_negative_constraints")
    if isinstance(constraints, list) and constraints:
        compact = [
            {"id": row.get("id"), "group_id": row.get("group_id"), "rule": row.get("rule")}
            for row in constraints[:18]
            if isinstance(row, dict)
        ]
        lines.append(f"- negative_constraints: {compact}")
    return lines


def _structured_from_generation(generation: dict[str, Any] | None) -> dict[str, Any]:
    gen = _as_dict(generation)
    meta = _as_dict(gen.get("metadata"))
    structured = meta.get("structured_output")
    if isinstance(structured, dict):
        return structured
    structured = gen.get("structured_output")
    return structured if isinstance(structured, dict) else {}


def text_from_structured_output(structured: dict[str, Any] | None) -> str:
    structured = _as_dict(structured)
    parts: list[str] = []
    for key in ("narration_summary", "narrative_response"):
        text = narration_summary_to_plain_str(structured.get(key))
        if text.strip():
            parts.append(text.strip())
    for lane_key in ("spoken_lines", "action_lines", "initiative_events"):
        for row in _as_list(structured.get(lane_key)):
            if isinstance(row, dict):
                text = str(row.get("text") or row.get("line") or row.get("summary") or "").strip()
            else:
                text = str(row or "").strip()
            if text:
                parts.append(text)
    return "\n".join(parts)


def text_from_generation_and_effects(
    *,
    generation: dict[str, Any] | None,
    proposed_state_effects: list[dict[str, Any]] | None = None,
) -> str:
    structured = _structured_from_generation(generation)
    parts = [text_from_structured_output(structured)]
    gen = _as_dict(generation)
    for key in ("content", "model_raw_text"):
        text = str(gen.get(key) or "").strip()
        if text:
            parts.append(text)
    for eff in proposed_state_effects or []:
        if isinstance(eff, dict):
            text = str(eff.get("description") or eff.get("summary") or eff.get("text") or "").strip()
            if text:
                parts.append(text)
    return "\n".join(part for part in parts if part.strip())


def text_from_visible_event(event: dict[str, Any] | None) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    event = _as_dict(event)
    bundle = _as_dict(event.get("visible_output_bundle"))
    blocks = [dict(row) for row in _as_list(bundle.get("scene_blocks")) if isinstance(row, dict)]
    parts: list[str] = []
    for row in blocks:
        text = str(row.get("text") or "").strip()
        label = str(row.get("speaker_label") or "").strip()
        if text:
            parts.append(f"{label}: {text}" if label else text)
    for item in _as_list(bundle.get("gm_narration")):
        text = str(item or "").strip()
        if text:
            parts.append(text)
    gen = _as_dict(_as_dict(event.get("model_route")).get("generation"))
    structured = _as_dict(_as_dict(gen.get("metadata")).get("structured_output"))
    if not structured and isinstance(gen.get("structured_output"), dict):
        structured = gen["structured_output"]
    structured_text = text_from_structured_output(structured)
    if structured_text:
        parts.append(structured_text)
    return "\n".join(parts), blocks, structured


def _forbidden_actor_ids(actor_lane_context: dict[str, Any] | None) -> set[str]:
    ctx = _as_dict(actor_lane_context)
    ids: set[str] = set()
    for raw in _as_list(ctx.get("ai_forbidden_actor_ids")) + [
        ctx.get("human_actor_id"),
        ctx.get("selected_player_role"),
    ]:
        text = str(raw or "").strip()
        if not text:
            continue
        ids.update(expand_goc_actor_id_aliases(text))
        canon = canonicalize_goc_actor_id(text)
        if canon:
            ids.update(expand_goc_actor_id_aliases(canon))
    return ids


def _speaker_is_forbidden(speaker_id: str, forbidden_ids: set[str]) -> bool:
    speaker = str(speaker_id or "").strip()
    if not speaker:
        return False
    canon = canonicalize_goc_actor_id(speaker) or speaker
    return speaker in forbidden_ids or canon in forbidden_ids


def _visible_block_count(structured_output: dict[str, Any], visible_blocks: list[dict[str, Any]] | None = None) -> int:
    if visible_blocks:
        return len([row for row in visible_blocks if isinstance(row, dict) and str(row.get("text") or "").strip()])
    count = 0
    ns = _as_dict(structured_output).get("narration_summary")
    if isinstance(ns, list):
        count += len([item for item in ns if str(item or "").strip()])
    elif isinstance(ns, str) and ns.strip():
        count += 1
    if not count and str(_as_dict(structured_output).get("narrative_response") or "").strip():
        count += 1
    count += len([row for row in _as_list(_as_dict(structured_output).get("spoken_lines")) if isinstance(row, dict)])
    count += len([row for row in _as_list(_as_dict(structured_output).get("action_lines")) if isinstance(row, dict)])
    return count


def _detection_policy(hard_forbidden_rules: dict[str, Any] | None) -> dict[str, Any]:
    return _as_dict(_as_dict(hard_forbidden_rules).get("hard_forbidden_detection"))


def _configured_detection_fields(policy: dict[str, Any]) -> list[str]:
    return _unique_strs(policy.get("structured_detection_fields"))


def _rule_id_for_detection(policy: dict[str, Any], detection_key: str, explicit_rule_id: str | None = None) -> str:
    rule_id = str(explicit_rule_id or "").strip()
    if rule_id:
        return rule_id
    marker_map = _as_dict(policy.get("marker_map"))
    mapped = str(marker_map.get(detection_key) or "").strip()
    return mapped or detection_key


def _action_for_detection(policy: dict[str, Any], detection_key: str, explicit_action: str | None = None) -> str:
    action = str(explicit_action or "").strip().lower()
    if action in {"reject", "recover"}:
        return action
    if detection_key in set(_unique_strs(policy.get("recover_on"))):
        return "recover"
    return "reject"


def _iter_detection_markers(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    if isinstance(value, str):
        return [value]
    return []


def _markers_from_detection_field(value: Any) -> list[Any]:
    if isinstance(value, dict) and not any(
        key in value for key in ("detection_key", "key", "reason", "rule_key", "rule_id", "id")
    ):
        return [{"detection_key": key} for key, detected in value.items() if detected and str(key or "").strip()]
    return _iter_detection_markers(value)


def _coerce_detection_marker(marker: Any, policy: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(marker, str):
        detection_key = marker.strip()
        if not detection_key:
            return None
        return {
            "detection_key": detection_key,
            "rule_id": _rule_id_for_detection(policy, detection_key),
            "action": _action_for_detection(policy, detection_key),
            "source": "structured_detection_marker",
        }
    if not isinstance(marker, dict):
        return None
    detection_key = str(
        marker.get("detection_key")
        or marker.get("key")
        or marker.get("reason")
        or marker.get("rule_key")
        or ""
    ).strip()
    rule_id_raw = str(marker.get("rule_id") or marker.get("id") or "").strip()
    if not detection_key:
        marker_map = _as_dict(policy.get("marker_map"))
        for key, mapped_rule_id in marker_map.items():
            if rule_id_raw and str(mapped_rule_id or "").strip() == rule_id_raw:
                detection_key = str(key or "").strip()
                break
    if not detection_key:
        return None
    return {
        "detection_key": detection_key,
        "rule_id": _rule_id_for_detection(policy, detection_key, rule_id_raw),
        "action": _action_for_detection(policy, detection_key, str(marker.get("action") or "")),
        "source": str(marker.get("source") or "structured_detection_marker"),
    }


def _collect_structured_detection_markers(
    *, structured_output: dict[str, Any], visible_blocks: list[dict[str, Any]] | None, policy: dict[str, Any]
) -> list[dict[str, Any]]:
    fields = _configured_detection_fields(policy)
    markers: list[dict[str, Any]] = []
    for field in fields:
        for raw in _markers_from_detection_field(_as_dict(structured_output).get(field)):
            marker = _coerce_detection_marker(raw, policy)
            if marker:
                markers.append(marker)
    for block in visible_blocks or []:
        if not isinstance(block, dict):
            continue
        metadata = _as_dict(block.get("metadata"))
        for field in fields:
            for raw in _markers_from_detection_field(block.get(field)) + _markers_from_detection_field(metadata.get(field)):
                marker = _coerce_detection_marker(raw, policy)
                if marker:
                    marker["source"] = marker.get("source") or "visible_block_detection_marker"
                    markers.append(marker)
    return markers


def _structural_checks(policy: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in _as_list(policy.get("structural_checks"))
        if isinstance(row, dict) and str(row.get("kind") or "").strip() == kind
    ]


def _actor_lane_rows(
    *, structured_output: dict[str, Any], visible_blocks: list[dict[str, Any]] | None, lanes: list[str]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lane in lanes:
        for row in _as_list(_as_dict(structured_output).get(lane)):
            if isinstance(row, dict):
                rows.append(row)
    for block in visible_blocks or []:
        if not isinstance(block, dict):
            continue
        block_type = str(block.get("block_type") or block.get("type") or "").strip()
        if block_type in lanes:
            rows.append(block)
    return rows


def _detect_forbidden_actor_lane_markers(
    *,
    structured_output: dict[str, Any],
    visible_blocks: list[dict[str, Any]] | None,
    actor_lane_context: dict[str, Any] | None,
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    forbidden_ids = _forbidden_actor_ids(actor_lane_context)
    if not forbidden_ids:
        return []
    markers: list[dict[str, Any]] = []
    for check in _structural_checks(policy, "forbidden_actor_lane"):
        detection_key = str(check.get("detection_key") or "").strip()
        if not detection_key:
            continue
        lanes = _unique_strs(check.get("lanes"))
        actor_fields = _unique_strs(check.get("actor_fields"))
        for row in _actor_lane_rows(
            structured_output=structured_output,
            visible_blocks=visible_blocks,
            lanes=lanes,
        ):
            for field in actor_fields:
                if _speaker_is_forbidden(str(row.get(field) or ""), forbidden_ids):
                    markers.append(
                        {
                            "detection_key": detection_key,
                            "rule_id": _rule_id_for_detection(
                                policy, detection_key, str(check.get("rule_id") or "")
                            ),
                            "action": _action_for_detection(policy, detection_key, str(check.get("action") or "")),
                            "source": "forbidden_actor_lane",
                        }
                    )
                    break
    return markers


def _actor_lane_count(structured_output: dict[str, Any], visible_blocks: list[dict[str, Any]] | None = None) -> int:
    count = len(_as_list(_as_dict(structured_output).get("spoken_lines")))
    count += len(_as_list(_as_dict(structured_output).get("action_lines")))
    for block in visible_blocks or []:
        if not isinstance(block, dict):
            continue
        block_type = str(block.get("block_type") or block.get("type") or "").strip()
        if block_type in {"spoken_lines", "action_lines", "actor_line", "actor_action"}:
            count += 1
    return count


def _narrator_block_count(
    structured_output: dict[str, Any],
    visible_blocks: list[dict[str, Any]] | None = None,
) -> int:
    count = 0
    if visible_blocks:
        for block in visible_blocks:
            if isinstance(block, dict):
                block_type = str(block.get("block_type") or block.get("type") or "").strip().lower()
                if block_type in {"narrator", "gm_narration"} and str(block.get("text") or "").strip():
                    count += 1
        if count:
            return count
    ns = _as_dict(structured_output).get("narration_summary")
    if isinstance(ns, list):
        count += len([item for item in ns if str(item or "").strip()])
    elif isinstance(ns, str) and ns.strip():
        count += 1
    if not count and str(_as_dict(structured_output).get("narrative_response") or "").strip():
        count += 1
    return count


def _opening_scenic_event_realization(
    *,
    structured_output: dict[str, Any],
    opening_scene_sequence: dict[str, Any] | None,
    visible_blocks: list[dict[str, Any]] | None = None,
) -> tuple[int, int, list[str]]:
    """Return (covered_event_count, expected_event_count, missing_event_ids).

    Coverage evidence comes from both structured_output (opening_event_ids field) and
    visible_blocks (per-block opening_event_id metadata). Either surface satisfies the
    realization requirement.
    """
    expected_ids = [
        str(event.get("id") or "").strip()
        for event in _event_rows(opening_scene_sequence)
        if isinstance(event, dict) and event.get("id")
    ]
    expected_ids = [eid for eid in expected_ids if eid]
    covered = set(_collect_opening_event_ids(structured_output=structured_output, visible_blocks=visible_blocks))
    missing = [eid for eid in expected_ids if eid not in covered]
    return len(expected_ids) - len(missing), len(expected_ids), missing


def _detect_opening_render_policy_markers(
    *,
    structured_output: dict[str, Any],
    opening_scene_sequence: dict[str, Any] | None,
    visible_blocks: list[dict[str, Any]] | None,
    turn_input_class: str | None,
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    if str(turn_input_class or "").strip().lower() != "opening":
        return []
    opening = _as_dict(opening_scene_sequence)
    if not opening:
        return []
    markers: list[dict[str, Any]] = []
    for check in _structural_checks(policy, "opening_render_policy"):
        detection_key = str(check.get("detection_key") or "").strip()
        if not detection_key:
            continue
        render_policy = _as_dict(opening.get("narration_mode"))
        if bool(render_policy.get("summary_allowed")):
            continue
        explicit = _as_dict(structured_output).get("opening_render_policy_evidence")
        reasons: list[str] = []
        if isinstance(explicit, dict) and explicit.get("summary_only") is True:
            summary_only = True
            reasons.append("explicit_opening_render_policy_evidence")
        else:
            min_visible_blocks = render_policy.get("min_visible_blocks")
            try:
                min_blocks = int(min_visible_blocks)
            except (TypeError, ValueError):
                min_blocks = 0
            block_count = _visible_block_count(structured_output, visible_blocks=visible_blocks)
            narrator_count = _narrator_block_count(structured_output, visible_blocks=visible_blocks)
            actor_count = _actor_lane_count(structured_output, visible_blocks)
            # STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P3: semantic
            # summary-only detection. The previous rule required actor_lane_count == 0,
            # which let summary-like openings escape whenever any NPC line was emitted.
            # The new rule judges narrator realization quality independently of NPC presence.
            required_narrator = max(3, min_blocks - 1) if min_blocks else 3
            if min_blocks and block_count < min_blocks:
                reasons.append("too_few_visible_blocks_for_opening_policy")
            if narrator_count < required_narrator:
                reasons.append("too_few_narrator_blocks_for_opening_policy")
            covered_events, expected_events, missing_events = _opening_scenic_event_realization(
                structured_output=structured_output,
                opening_scene_sequence=opening,
                visible_blocks=visible_blocks,
            )
            if expected_events and covered_events == 0:
                reasons.append("missing_scenic_event_realization")
            elif expected_events and len(missing_events) > expected_events // 2:
                reasons.append("missing_scenic_event_realization")
            # If the only visible-block mass comes from actor lanes and narrator is sparse, the
            # narrator did not satisfy the opening scenic contract — even if actor lanes exist.
            if actor_count > 0 and narrator_count <= 1:
                reasons.append("actor_lane_does_not_satisfy_opening_scenic_requirement")
            # Pure abstract-summary fallback: small-block narrator-only without event coverage.
            if narrator_count > 0 and narrator_count <= 3 and not covered_events and expected_events:
                reasons.append("narrator_blocks_are_abstract_summary")
            summary_only = bool(reasons)
        if summary_only:
            markers.append(
                {
                    "detection_key": detection_key,
                    "rule_id": _rule_id_for_detection(policy, detection_key, str(check.get("rule_id") or "")),
                    "action": _action_for_detection(policy, detection_key, str(check.get("action") or "")),
                    "source": "opening_render_policy",
                    "summary_only_reasons": reasons,
                }
            )
    return markers


_PHASE_ONE_PREMATURE_NPC_MARKERS: tuple[tuple[str, ...], ...] = (
    # English markers — bourgeois prosecutorial frame, accusation, escalation.
    ("legal question",),
    ("you keep",),
    ("a question of law",),
    ("we agreed",),
    ("i refuse",),
    ("how dare you",),
    ("ridiculous",),
    ("monstrous",),
    # German markers — same dramatic functions in runtime locale.
    ("rechtlich",),
    ("juristisch",),
    ("rechtsfrage",),
    ("ich weigere mich",),
    ("wie könnt ihr",),
    ("wie konnt ihr",),
    ("eine frechheit",),
    ("unverschämt",),
    ("unverschaemt",),
    # Multi-token escalation patterns (all must appear).
    ("schuld", "ihr"),
    ("blame", "your"),
)


def _phase_one_npc_line_violates(text: str) -> bool:
    if not text:
        return False
    low = text.lower()
    for pattern in _PHASE_ONE_PREMATURE_NPC_MARKERS:
        if all(token in low for token in pattern):
            return True
    return False


def _detect_phase_one_premature_npc_escalation_markers(
    *,
    structured_output: dict[str, Any],
    visible_blocks: list[dict[str, Any]] | None,
    turn_input_class: str | None,
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    """STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P2: Turn-0 NPC lines that
    skip directly into mid-conflict / prosecutorial framing violate phase-1 polite-opening
    policy. Detection is heuristic on visible actor lines + spoken_lines structured output.
    """
    if str(turn_input_class or "").strip().lower() != "opening":
        return []
    detection_key = "npc_phase_one_premature_escalation"
    rule_id = _rule_id_for_detection(policy, detection_key, "no_immediate_full_escalation")
    action = _action_for_detection(policy, detection_key, "recover")
    markers: list[dict[str, Any]] = []
    candidates: list[str] = []
    for row in _as_list(_as_dict(structured_output).get("spoken_lines")):
        if isinstance(row, dict):
            candidates.append(str(row.get("text") or row.get("line") or ""))
        else:
            candidates.append(str(row or ""))
    for block in visible_blocks or []:
        if not isinstance(block, dict):
            continue
        block_type = str(block.get("block_type") or block.get("type") or "").strip().lower()
        if block_type in {"actor_line", "spoken_line"}:
            candidates.append(str(block.get("text") or ""))
    for text in candidates:
        if _phase_one_npc_line_violates(text):
            markers.append(
                {
                    "detection_key": detection_key,
                    "rule_id": rule_id,
                    "action": action,
                    "source": "phase_one_premature_npc_escalation",
                }
            )
            break  # single hit suffices to gate the turn
    return markers


def detect_hard_forbidden_runtime(
    *,
    hard_forbidden_rules: dict[str, Any] | None,
    opening_scene_sequence: dict[str, Any] | None = None,
    text: str,
    structured_output: dict[str, Any] | None = None,
    actor_lane_context: dict[str, Any] | None = None,
    turn_input_class: str | None = None,
    visible_blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Detect authored hard-forbidden conditions from structured runtime evidence."""
    policy = _detection_policy(hard_forbidden_rules)
    reject_policy = set(_unique_strs(policy.get("reject_on")))
    recover_policy = set(_unique_strs(policy.get("recover_on")))
    structured = _as_dict(structured_output)
    detected = _collect_structured_detection_markers(
        structured_output=structured,
        visible_blocks=visible_blocks,
        policy=policy,
    )
    detected.extend(
        _detect_forbidden_actor_lane_markers(
            structured_output=structured,
            visible_blocks=visible_blocks,
            actor_lane_context=actor_lane_context,
            policy=policy,
        )
    )
    detected.extend(
        _detect_opening_render_policy_markers(
            structured_output=structured,
            opening_scene_sequence=opening_scene_sequence,
            visible_blocks=visible_blocks,
            turn_input_class=turn_input_class,
            policy=policy,
        )
    )
    detected.extend(
        _detect_phase_one_premature_npc_escalation_markers(
            structured_output=structured,
            visible_blocks=visible_blocks,
            turn_input_class=turn_input_class,
            policy=policy,
        )
    )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for hit in detected:
        key = str(hit.get("detection_key") or "").strip()
        rule_id = str(hit.get("rule_id") or "").strip()
        action_hint = str(hit.get("action") or "").strip()
        if not key:
            continue
        normalized = {
            "detection_key": key,
            "rule_id": _rule_id_for_detection(policy, key, rule_id),
            "action": _action_for_detection(policy, key, action_hint),
            "source": str(hit.get("source") or "").strip() or "runtime_evidence",
        }
        # P3: preserve diagnostic reasons (e.g. summary_only_reasons) for dashboards.
        reasons = hit.get("summary_only_reasons")
        if isinstance(reasons, list) and reasons:
            normalized["summary_only_reasons"] = list(reasons)
        marker_id = (
            normalized["detection_key"],
            normalized["rule_id"],
            normalized["source"],
        )
        if marker_id in seen:
            continue
        seen.add(marker_id)
        deduped.append(normalized)
    detected = deduped

    reject_hits: list[dict[str, Any]] = []
    recover_hits: list[dict[str, Any]] = []
    for hit in detected:
        key = str(hit.get("detection_key") or "")
        action = str(hit.get("action") or "")
        if key in reject_policy or action == "reject":
            reject_hits.append(hit)
        elif key in recover_policy or action == "recover":
            recover_hits.append(hit)
        else:
            reject_hits.append(hit)
    status = "passed"
    action = "pass"
    if reject_hits:
        status = "rejected"
        action = "reject"
    elif recover_hits:
        status = "recoverable_rejection"
        action = "recover"
    first = (reject_hits or recover_hits or [{}])[0]
    return {
        "contract": KNOWLEDGE_RUNTIME_GATES_CONTRACT,
        "status": status,
        "action": action,
        "reason": first.get("detection_key") if first else None,
        "detected": detected,
        "reject_on_detected": [hit["detection_key"] for hit in reject_hits],
        "recover_on_detected": [hit["detection_key"] for hit in recover_hits],
        "rule_ids": [hit["rule_id"] for hit in detected if hit.get("rule_id")],
        "hard_forbidden_absent": not bool(detected),
        "opening_summary_only_absent": not any(
            hit.get("detection_key") == "summary_only_opening" for hit in detected
        ),
        "detection_policy": {
            "reject_on": sorted(reject_policy),
            "recover_on": sorted(recover_policy),
        },
    }


def hard_forbidden_detection_for_actor_lane_violation(
    *, reason: str, hard_forbidden_rules: dict[str, Any] | None = None
) -> dict[str, Any]:
    policy = _detection_policy(hard_forbidden_rules)
    violation_map = _as_dict(policy.get("actor_lane_violation_map"))
    mapped = _as_dict(violation_map.get(str(reason or "").strip()))
    key = str(mapped.get("detection_key") or reason or "actor_lane_violation").strip()
    rule_id = _rule_id_for_detection(policy, key, str(mapped.get("rule_id") or ""))
    action = _action_for_detection(policy, key, str(mapped.get("action") or "reject"))
    return {
        "contract": KNOWLEDGE_RUNTIME_GATES_CONTRACT,
        "status": "rejected",
        "action": action,
        "reason": key,
        "detected": [
            {
                "detection_key": key,
                "rule_id": rule_id,
                "action": action,
                "source": "actor_lane_validation",
            }
        ],
        "reject_on_detected": [key],
        "recover_on_detected": [],
        "rule_ids": [rule_id],
        "hard_forbidden_absent": False,
        "opening_summary_only_absent": True,
        "detection_policy": {
            "reject_on": _unique_strs(policy.get("reject_on")),
            "recover_on": _unique_strs(policy.get("recover_on")),
        },
    }


def _ids_from_value(value: Any) -> list[str]:
    ids: list[str] = []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, dict) and not any(key in value for key in ("id", "event_id", "opening_event_id")):
        iterable: list[Any] = [
            {"id": key}
            for key, covered in value.items()
            if covered and str(key or "").strip()
        ]
    else:
        iterable = _as_list(value)
        if isinstance(value, dict):
            iterable = [value]
    for item in iterable:
        if isinstance(item, dict):
            raw = item.get("id") or item.get("event_id") or item.get("opening_event_id")
        else:
            raw = item
        text = str(raw or "").strip()
        if text and text not in ids:
            ids.append(text)
    return ids


def _collect_opening_event_ids(
    *, structured_output: dict[str, Any] | None, visible_blocks: list[dict[str, Any]] | None
) -> list[str]:
    structured = _as_dict(structured_output)
    found: list[str] = []
    for key in ("opening_event_ids", "opening_events_covered", "covered_event_ids"):
        for event_id in _ids_from_value(structured.get(key)):
            if event_id not in found:
                found.append(event_id)
    for nested_key in ("opening_event_coverage", "event_coverage"):
        nested = _as_dict(structured.get(nested_key))
        for key in ("covered_event_ids", "opening_event_ids", "events"):
            for event_id in _ids_from_value(nested.get(key)):
                if event_id not in found:
                    found.append(event_id)
    for block in visible_blocks or []:
        if not isinstance(block, dict):
            continue
        metadata = _as_dict(block.get("metadata"))
        for source in (block, metadata):
            for key in ("opening_event_id", "event_id"):
                event_id = str(source.get(key) or "").strip()
                if event_id and event_id not in found:
                    found.append(event_id)
            for key in ("opening_event_ids", "event_ids"):
                for event_id in _ids_from_value(source.get(key)):
                    if event_id not in found:
                        found.append(event_id)
    return found


def _event_establishes_map(opening_scene_sequence: dict[str, Any] | None) -> dict[str, list[str]]:
    return {
        str(event.get("id") or "").strip(): _unique_strs(event.get("establishes"))
        for event in _event_rows(opening_scene_sequence)
        if event.get("id")
    }


def _collect_must_establish_coverage(structured_output: dict[str, Any] | None) -> set[str]:
    structured = _as_dict(structured_output)
    found: set[str] = set()
    for key in ("opening_must_establish_coverage", "must_establish_coverage"):
        value = structured.get(key)
        if isinstance(value, dict):
            found.update(str(item).strip() for item, covered in value.items() if covered and str(item).strip())
        else:
            found.update(_ids_from_value(value))
    for nested_key in ("opening_event_coverage", "event_coverage"):
        nested = _as_dict(structured.get(nested_key))
        value = nested.get("must_establish_coverage")
        if isinstance(value, dict):
            found.update(str(item).strip() for item, covered in value.items() if covered and str(item).strip())
        else:
            found.update(_ids_from_value(value))
    return found


def evaluate_opening_event_coverage(
    *,
    opening_scene_sequence: dict[str, Any] | None,
    text: str,
    structured_output: dict[str, Any] | None = None,
    actor_lane_context: dict[str, Any] | None = None,
    scene_plan_record: dict[str, Any] | None = None,
    current_scene_id: str | None = None,
    visible_blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate opening event and handover coverage from structured semantic evidence."""
    opening = _as_dict(opening_scene_sequence)
    if not opening:
        return {
            "contract": KNOWLEDGE_RUNTIME_GATES_CONTRACT,
            "opening_event_coverage_pass": True,
            "applicable": False,
        }
    expected_events = [str(event.get("id") or "").strip() for event in _event_rows(opening) if event.get("id")]
    evidence_events = _collect_opening_event_ids(
        structured_output=structured_output,
        visible_blocks=visible_blocks,
    )
    covered_events = [event_id for event_id in expected_events if event_id in set(evidence_events)]
    opening_contract = _as_dict(opening.get("opening_contract"))
    must_establish = _unique_strs(opening_contract.get("must_establish"))
    establishes_by_event = _event_establishes_map(opening)
    covered_must = _collect_must_establish_coverage(structured_output)
    for event_id in covered_events:
        covered_must.update(establishes_by_event.get(event_id, []))
    must_coverage = {item: item in covered_must for item in must_establish}
    missing_must = [key for key in must_establish if not must_coverage.get(key, False)]
    scene_plan = _as_dict(scene_plan_record)
    expected_handover = _opening_handover_phase(opening)
    actual_handover = str(
        scene_plan.get("opening_handover_to_scene_phase")
        or scene_plan.get("handover_to_scene_phase")
        or scene_plan.get("phase_id")
        or ""
    ).strip()
    if not actual_handover and current_scene_id:
        actual_handover = "phase_1" if "opening" in str(current_scene_id).lower() else ""
    handover_pass = not expected_handover or actual_handover == expected_handover
    missing_events = [event_id for event_id in expected_events if event_id not in covered_events]
    pass_value = not missing_must and handover_pass and not missing_events
    return {
        "contract": KNOWLEDGE_RUNTIME_GATES_CONTRACT,
        "applicable": True,
        "opening_scene_sequence_id": opening.get("id"),
        "expected_event_ids": expected_events,
        "covered_event_ids": covered_events,
        "missing_event_ids": missing_events,
        "must_establish": must_establish,
        "must_establish_coverage": must_coverage,
        "missing_must_establish": missing_must,
        "handover_to_scene_phase_expected": expected_handover,
        "handover_to_scene_phase_actual": actual_handover or None,
        "handover_to_scene_phase_pass": handover_pass,
        "opening_event_coverage_pass": pass_value,
    }


def build_knowledge_path_summary(
    *,
    graph_state: dict[str, Any],
    event: dict[str, Any],
    actor_lane_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    opening = _as_dict(graph_state.get("opening_scene_sequence"))
    hard = _as_dict(graph_state.get("hard_forbidden_rules"))
    text, visible_blocks, structured = text_from_visible_event(event)
    if not structured:
        structured = _structured_from_generation(graph_state.get("generation") if isinstance(graph_state.get("generation"), dict) else {})
    if not text.strip():
        text = text_from_generation_and_effects(
            generation=graph_state.get("generation") if isinstance(graph_state.get("generation"), dict) else {},
            proposed_state_effects=graph_state.get("proposed_state_effects")
            if isinstance(graph_state.get("proposed_state_effects"), list)
            else [],
        )
    validation = _as_dict(graph_state.get("validation_outcome"))
    scene_plan = _as_dict(graph_state.get("scene_plan_record"))
    turn_input_class = str(graph_state.get("turn_input_class") or event.get("turn_kind") or "").strip().lower()
    detection = detect_hard_forbidden_runtime(
        hard_forbidden_rules=hard,
        opening_scene_sequence=opening,
        text=text,
        structured_output=structured,
        actor_lane_context=actor_lane_context,
        turn_input_class=turn_input_class,
        visible_blocks=visible_blocks,
    )
    prior_detection = validation.get("hard_forbidden_detection")
    coverage = evaluate_opening_event_coverage(
        opening_scene_sequence=opening,
        text=text,
        structured_output=structured,
        actor_lane_context=actor_lane_context,
        scene_plan_record=scene_plan,
        current_scene_id=str(graph_state.get("current_scene_id") or ""),
        visible_blocks=visible_blocks,
    ) if turn_input_class == "opening" or int(event.get("turn_number") or 0) == 0 else {
        "opening_event_coverage_pass": True,
        "applicable": False,
    }
    return {
        "knowledge_runtime_gates_contract": KNOWLEDGE_RUNTIME_GATES_CONTRACT,
        "opening_scene_sequence_id": opening.get("id"),
        "opening_event_ids_expected": coverage.get("expected_event_ids") or [],
        "opening_event_ids_covered": coverage.get("covered_event_ids") or [],
        "opening_missing_event_ids": coverage.get("missing_event_ids") or [],
        "opening_missing_must_establish": coverage.get("missing_must_establish") or [],
        "opening_handover_to_scene_phase_expected": coverage.get("handover_to_scene_phase_expected"),
        "opening_handover_to_scene_phase_actual": coverage.get("handover_to_scene_phase_actual"),
        "opening_event_coverage_pass": bool(coverage.get("opening_event_coverage_pass", True)),
        "hard_forbidden_detection": detection,
        "prior_validation_hard_forbidden_detection": prior_detection if isinstance(prior_detection, dict) else None,
        "hard_forbidden_rule_ids": [row["id"] for row in _flatten_hard_rules(hard)],
        "hard_forbidden_absent": bool(detection.get("hard_forbidden_absent", True)),
        "opening_summary_only_absent": bool(detection.get("opening_summary_only_absent", True)),
    }
