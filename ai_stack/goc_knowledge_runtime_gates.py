"""Runtime gates for GoC opening-sequence and hard-forbidden knowledge."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from ai_stack.goc_frozen_vocab import canonicalize_goc_actor_id, expand_goc_actor_id_aliases
from ai_stack.opening_shape_normalizer import narration_summary_to_plain_str

KNOWLEDGE_RUNTIME_GATES_CONTRACT = "goc_knowledge_runtime_gates.v1"

_ACTOR_DISPLAY_NAMES: dict[str, tuple[str, ...]] = {
    "annette": ("Annette", "Annette Reille"),
    "annette_reille": ("Annette", "Annette Reille"),
    "alain": ("Alain", "Alain Reille"),
    "alain_reille": ("Alain", "Alain Reille"),
    "veronique": ("Veronique", "Veronique Vallon", "Véronique", "Véronique Vallon"),
    "veronique_vallon": ("Veronique", "Veronique Vallon", "Véronique", "Véronique Vallon"),
    "michel": ("Michel", "Michel Vallon"),
    "michel_longstreet": ("Michel", "Michel Vallon"),
}

_EVENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "event_01_triggering_incident": (
        "schoolyard",
        "school yard",
        "playground",
        "child",
        "children",
        "boy",
        "boys",
        "tooth",
        "teeth",
        "stick",
        "injury",
        "injured",
        "incident",
        "schulhof",
        "spielplatz",
        "kind",
        "kinder",
        "junge",
        "jungen",
        "zahn",
        "stock",
        "verletz",
        "vorfall",
    ),
    "event_02_adult_consequence": (
        "parents",
        "adults",
        "meeting",
        "meet",
        "civilized",
        "polite",
        "consequence",
        "eltern",
        "erwachsene",
        "treffen",
        "besprechen",
        "hoeflich",
        "zivilisiert",
        "folge",
    ),
    "event_03_arrival_threshold": (
        "door",
        "doorway",
        "threshold",
        "arrival",
        "arrive",
        "guests",
        "host",
        "hosts",
        "apartment",
        "salon",
        "tuer",
        "tur",
        "schwelle",
        "ankommen",
        "eintreten",
        "gaeste",
        "gaste",
        "gastgeber",
        "wohnung",
        "wohnzimmer",
    ),
    "event_04_apartment_as_stage": (
        "apartment",
        "living room",
        "salon",
        "room",
        "chairs",
        "table",
        "coffee table",
        "tulips",
        "sofa",
        "host",
        "guest",
        "wohnung",
        "wohnzimmer",
        "zimmer",
        "stuehle",
        "stuhle",
        "tisch",
        "couchtisch",
        "tulpen",
        "sofa",
        "gastgeber",
        "gast",
    ),
    "event_06_first_playable_moment": (
        "now",
        "moment",
        "waiting",
        "waits",
        "room to",
        "free to",
        "choose",
        "speak",
        "act",
        "jetzt",
        "moment",
        "wartet",
        "raum",
        "frei",
        "waehlen",
        "wahlen",
        "sprechen",
        "handeln",
    ),
}


def _fold_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    asciiish = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return asciiish.casefold()


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
        role_variant = pkt.get("selected_role_variant")
        if isinstance(role_variant, dict) and role_variant:
            lines.append(f"- selected_role_variant: {role_variant}")
    lines.append("Hard Forbidden Runtime Rules:")
    lines.append(f"- detection_policy: {pkt.get('hard_forbidden_detection_policy') or {}}")
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


def _actor_names(actor_lane_context: dict[str, Any] | None) -> list[str]:
    ctx = _as_dict(actor_lane_context)
    raw_ids = [
        str(ctx.get("human_actor_id") or "").strip(),
        str(ctx.get("selected_player_role") or "").strip(),
    ]
    out: list[str] = []
    for raw in raw_ids:
        if not raw:
            continue
        canon = canonicalize_goc_actor_id(raw) or raw
        for key in {raw, canon}:
            for name in _ACTOR_DISPLAY_NAMES.get(key, (key,)):
                if name and name not in out:
                    out.append(name)
    return out


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


def _detect_forced_player_speech(
    *,
    structured_output: dict[str, Any],
    text: str,
    actor_lane_context: dict[str, Any] | None,
) -> bool:
    forbidden_ids = _forbidden_actor_ids(actor_lane_context)
    for row in _as_list(_as_dict(structured_output).get("spoken_lines")):
        if not isinstance(row, dict):
            continue
        if _speaker_is_forbidden(str(row.get("speaker_id") or ""), forbidden_ids):
            return True
    for name in _actor_names(actor_lane_context):
        folded = re.escape(_fold_text(name))
        if re.search(rf"(^|\n)\s*{folded}\s*[:\-]", _fold_text(text)):
            return True
    return False


def _detect_player_agency_violation(text: str, actor_lane_context: dict[str, Any] | None) -> bool:
    low = _fold_text(text)
    names = [_fold_text(name) for name in _actor_names(actor_lane_context)]
    if re.search(r"\byou\s+(decide|feel|know|realize|believe|want|intend)\b", low):
        return True
    if re.search(r"\bdu\s+(entscheidest|fuhlst|weisst|weißt|willst|glaubst)\b", low):
        return True
    for name in names:
        if not name:
            continue
        if re.search(rf"\b{re.escape(name)}\s+(decides|feels|knows|realizes|believes|wants|intends)\b", low):
            return True
        if re.search(rf"\b{re.escape(name)}\s+(entscheidet|fuhlt|weiss|weiß|will|glaubt)\b", low):
            return True
    return False


def _detect_npc_world_explanation(structured_output: dict[str, Any]) -> bool:
    rows = _as_list(_as_dict(structured_output).get("spoken_lines"))
    if not rows:
        return False
    env_words = (
        "apartment",
        "living room",
        "salon",
        "room",
        "table",
        "door",
        "tulips",
        "schoolyard",
        "incident",
        "wohnung",
        "wohnzimmer",
        "zimmer",
        "tisch",
        "tuer",
        "tur",
        "tulpen",
        "schulhof",
        "vorfall",
    )
    explain_words = (
        "you can see",
        "you see",
        "the room is",
        "the apartment is",
        "this is where",
        "let me explain",
        "as you know",
        "du siehst",
        "man sieht",
        "der raum ist",
        "die wohnung ist",
        "ich erklaere",
        "ich erklare",
        "wie du weisst",
        "wie du weißt",
    )
    for row in rows:
        if not isinstance(row, dict):
            continue
        line = _fold_text(str(row.get("text") or row.get("line") or ""))
        if not line:
            continue
        if any(word in line for word in explain_words):
            return True
        if sum(1 for word in env_words if word in line) >= 2 and len(line) > 80:
            return True
    return False


def _detect_meta_runtime_language(text: str) -> bool:
    low = _fold_text(text)
    return any(
        marker in low
        for marker in (
            "prompt",
            "module",
            "runtime",
            "player role",
            "scene phase",
            "evaluator",
            "narrative system",
            "validator",
            "langfuse",
        )
    )


def _detect_stage_direction_labels(text: str) -> bool:
    return bool(
        re.search(
            r"(?im)^\s*(narrator_intro|role_anchor|scene_setup|beat_\d+|camera(?:\s+direction)?)\s*:",
            text,
        )
    )


def _detect_abstract_theme_dump(text: str) -> bool:
    low = _fold_text(text)
    theme_words = ("civility", "violence", "morality", "bourgeois", "hypocrisy", "zivilisiertheit", "moral", "gewalt")
    concrete_words = ("room", "table", "door", "child", "schoolyard", "wohnung", "tisch", "tuer", "tur", "kind", "schulhof")
    return sum(1 for word in theme_words if word in low) >= 2 and not any(word in low for word in concrete_words)


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


def _detect_summary_only_opening(
    *,
    text: str,
    structured_output: dict[str, Any],
    opening_scene_sequence: dict[str, Any] | None,
    visible_blocks: list[dict[str, Any]] | None = None,
) -> bool:
    opening = _as_dict(opening_scene_sequence)
    render_policy = _as_dict(opening.get("narration_mode"))
    summary_allowed = bool(render_policy.get("summary_allowed"))
    if summary_allowed:
        return False
    block_count = _visible_block_count(structured_output, visible_blocks=visible_blocks)
    actor_rows = len(_as_list(structured_output.get("spoken_lines"))) + len(_as_list(structured_output.get("action_lines")))
    if visible_blocks:
        actor_rows += len(
            [
                row
                for row in visible_blocks
                if str(row.get("block_type") or row.get("type") or "").strip().lower()
                in {"actor_line", "actor_action"}
            ]
        )
    low = _fold_text(text)
    summary_markers = (
        "in short",
        "summary",
        "backstory",
        "the story begins",
        "after the incident",
        "kurz gesagt",
        "zusammenfassung",
        "vorgeschichte",
        "nach dem vorfall",
    )
    eventish = sum(
        1
        for words in _EVENT_KEYWORDS.values()
        if any(word in low for word in words)
    )
    if block_count <= 2 and actor_rows == 0 and (len(text.strip()) < 900 or any(m in low for m in summary_markers)):
        return True
    return actor_rows == 0 and block_count <= 1 and eventish < 3


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
    """Detect authored hard-forbidden conditions in generated runtime output."""
    hard = _as_dict(hard_forbidden_rules)
    policy = _as_dict(hard.get("hard_forbidden_detection"))
    reject_policy = set(_unique_strs(policy.get("reject_on")))
    recover_policy = set(_unique_strs(policy.get("recover_on")))
    structured = _as_dict(structured_output)
    detected: list[dict[str, Any]] = []

    def add(key: str, rule_id: str, *, action: str) -> None:
        detected.append({"detection_key": key, "rule_id": rule_id, "action": action})

    if _detect_forced_player_speech(structured_output=structured, text=text, actor_lane_context=actor_lane_context):
        add("forced_player_speech", "no_forced_player_speech", action="reject")
    if _detect_player_agency_violation(text, actor_lane_context):
        add("player_agency_violation", "no_forced_player_decision", action="reject")
    if _detect_npc_world_explanation(structured):
        add("npc_world_explanation", "no_npc_world_explanation", action="reject")
    if _detect_meta_runtime_language(text):
        add("meta_runtime_language", "no_meta_runtime_language", action="reject")
    if _detect_stage_direction_labels(text):
        add("stage_direction_labels", "no_stage_direction_labels", action="recover")
    if _detect_abstract_theme_dump(text):
        add("abstract_theme_dump", "no_abstract_theme_dump", action="recover")
    if str(turn_input_class or "").strip().lower() == "opening" and _detect_summary_only_opening(
        text=text,
        structured_output=structured,
        opening_scene_sequence=opening_scene_sequence,
        visible_blocks=visible_blocks,
    ):
        add("summary_only_opening", "summarize_the_backstory_in_two_sentences", action="recover")

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
    key = "forced_player_speech" if reason == "ai_controlled_human_actor" else "player_agency_violation"
    rule_id = "no_forced_player_speech" if key == "forced_player_speech" else "no_forced_player_decision"
    policy = _as_dict(_as_dict(hard_forbidden_rules).get("hard_forbidden_detection"))
    return {
        "contract": KNOWLEDGE_RUNTIME_GATES_CONTRACT,
        "status": "rejected",
        "action": "reject",
        "reason": key,
        "detected": [{"detection_key": key, "rule_id": rule_id, "action": "reject"}],
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


def evaluate_opening_event_coverage(
    *,
    opening_scene_sequence: dict[str, Any] | None,
    text: str,
    actor_lane_context: dict[str, Any] | None = None,
    scene_plan_record: dict[str, Any] | None = None,
    current_scene_id: str | None = None,
    visible_blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate opening narrative event and handover coverage."""
    opening = _as_dict(opening_scene_sequence)
    if not opening:
        return {
            "contract": KNOWLEDGE_RUNTIME_GATES_CONTRACT,
            "opening_event_coverage_pass": True,
            "applicable": False,
        }
    low = _fold_text(text)
    expected_events = [str(event.get("id") or "").strip() for event in _event_rows(opening) if event.get("id")]
    covered_events: list[str] = []
    for event_id in expected_events:
        if event_id == "event_05_role_anchor":
            if any(_fold_text(name) in low for name in _actor_names(actor_lane_context)):
                covered_events.append(event_id)
            elif visible_blocks and len(visible_blocks) >= 2:
                covered_events.append(event_id)
            continue
        words = _EVENT_KEYWORDS.get(event_id, ())
        if any(word in low for word in words):
            covered_events.append(event_id)
    opening_contract = _as_dict(opening.get("opening_contract"))
    must_establish = _unique_strs(opening_contract.get("must_establish"))
    must_coverage = {
        "triggering_incident": "event_01_triggering_incident" in covered_events,
        "adult_consequence": "event_02_adult_consequence" in covered_events,
        "reason_for_meeting": "event_02_adult_consequence" in covered_events,
        "apartment_as_social_stage": "event_04_apartment_as_stage" in covered_events,
        "selected_player_role_presence": "event_05_role_anchor" in covered_events,
        "first_playable_moment": "event_06_first_playable_moment" in covered_events,
    }
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
