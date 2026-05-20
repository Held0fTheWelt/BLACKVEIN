"""
Deterministic scene director for God of Carnage
(CANONICAL_TURN_CONTRACT_GOC.md §3).
"""

from __future__ import annotations

from typing import Any

from ai_stack.goc_frozen_vocab import (
    CONTINUITY_CLASSES,
    CONTINUITY_CLASS_SEVERITY_ORDER,
    GOC_MODULE_ID,
    SCENE_FUNCTIONS,
    assert_pacing_mode,
    assert_scene_function,
    assert_silence_brevity_mode,
)
from ai_stack.goc_scene_identity import GOC_DEFAULT_GUIDANCE_PHASE_KEY, guidance_phase_key_for_scene_id
from ai_stack.goc_yaml_authority import (
    goc_actor_ids_from_content,
    goc_actor_identity_index,
    scene_assessment_phase_hints,
    scene_guidance_snippets,
)
from ai_stack.director.scene_direction_subdecision_matrix import assert_subdecision_label_in_matrix
from ai_stack.semantic_planner.semantic_move_contract import SEMANTIC_MOVE_TYPES
from ai_stack.silence_negative_space_contract import (
    build_silence_negative_space_decision,
    coerce_silence_negative_space_decision,
)
from story_runtime_core.player_input_intent_contract import (
    is_narrator_only_player_input_kind,
    is_question_punctuation_probe_guarded,
)


def _finalize_pacing_silence(pacing: str, silence: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Describe what ``_finalize_pacing_silence`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        pacing: ``pacing`` (str); meaning follows the type and call sites.
        silence: ``silence`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        tuple[str, dict[str, Any]]:
            Returns a value of type ``tuple[str, dict[str, Any]]``; see the function body for structure, error paths, and sentinels.
    """
    assert_subdecision_label_in_matrix("pacing_mode", pacing)
    normalized_silence = coerce_silence_negative_space_decision(silence)
    assert_subdecision_label_in_matrix("silence_brevity_mode", normalized_silence["mode"])
    return pacing, normalized_silence

# CANONICAL_TURN_CONTRACT_GOC.md §5.1 — minimal keys for GoC scene_assessment (when slice active).
GOC_SCENE_ASSESSMENT_MINIMAL_KEYS: frozenset[str] = frozenset({"scene_core", "pressure_state", "module_slice"})


def goc_scene_assessment_has_minimal_fields(assessment: dict[str, Any] | None) -> bool:
    """Return True if assessment dict carries required minimal schema for
    GoC operator/gate checks.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        assessment: ``assessment`` (dict[str, Any] |
            None); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    if not assessment or not isinstance(assessment, dict):
        return False
    for key in GOC_SCENE_ASSESSMENT_MINIMAL_KEYS:
        val = assessment.get(key)
        if val is None or val == "":
            return False
    return True


def _severity_index(continuity_class: str) -> int:
    """``_severity_index`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        continuity_class: ``continuity_class`` (str); meaning follows the type and call sites.
    
    Returns:
        int:
            Returns a value of type ``int``; see the function body for structure, error paths, and sentinels.
    """
    try:
        return CONTINUITY_CLASS_SEVERITY_ORDER.index(continuity_class)
    except ValueError:
        return len(CONTINUITY_CLASS_SEVERITY_ORDER)


def prior_continuity_classes(prior_continuity_impacts: list[dict[str, Any]] | None) -> list[str]:
    """Extract frozen continuity class labels from carry-forward impacts
    (bounded, not a memory system).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        prior_continuity_impacts: ``prior_continuity_impacts`` (list[dict[str, Any]] | None); meaning follows the type and call sites.
    
    Returns:
        list[str]:
            Returns a value of type ``list[str]``; see the function body for structure, error paths, and sentinels.
    """
    if not prior_continuity_impacts:
        return []
    out: list[str] = []
    for item in prior_continuity_impacts:
        if not isinstance(item, dict):
            continue
        c = item.get("class")
        if isinstance(c, str) and c in CONTINUITY_CLASSES and c not in out:
            out.append(c)
    return out


def select_single_scene_function(
    candidates: list[str],
    *,
    implied_continuity_by_function: dict[str, str],
) -> str:
    """CANONICAL_TURN_CONTRACT_GOC.md §3.5 — single function from competing
    candidates.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        candidates: ``candidates`` (list[str]); meaning follows the type and call sites.
        implied_continuity_by_function: ``implied_continuity_by_function`` (dict[str, str]); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    valid = [c for c in candidates if c in SCENE_FUNCTIONS]
    if not valid:
        return "establish_pressure"
    if len(valid) == 1:
        return assert_scene_function(valid[0])

    def rank(fn: str) -> tuple[int, str]:
        implied = implied_continuity_by_function.get(fn, "silent_carry")
        return (_severity_index(implied), fn)

    best_rank = min(rank(f) for f in valid)
    tied = [f for f in valid if rank(f) == best_rank]
    tied.sort()
    return assert_scene_function(tied[0])


def build_scene_assessment(
    *,
    module_id: str,
    current_scene_id: str,
    canonical_yaml: dict[str, Any] | None,
    prior_continuity_impacts: list[dict[str, Any]] | None = None,
    yaml_slice: dict[str, Any] | None = None,
    prior_narrative_thread_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """``build_scene_assessment`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        module_id: ``module_id`` (str); meaning follows the type and call sites.
        current_scene_id: ``current_scene_id`` (str); meaning follows the type and call sites.
        canonical_yaml: ``canonical_yaml`` (dict[str,
            Any] | None); meaning follows the type and call sites.
        prior_continuity_impacts: ``prior_continuity_impacts`` (list[dict[str, Any]] | None); meaning follows the type and call sites.
        yaml_slice: ``yaml_slice`` (dict[str, Any] |
            None); meaning follows the type and call sites.
        prior_narrative_thread_state: bounded committed thread continuity from
            the story session, if any.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    setting = "unknown"
    narrative_scope = "unknown"
    if canonical_yaml:
        content = canonical_yaml.get("content")
        if isinstance(content, dict):
            setting = str(content.get("setting") or setting)
            narrative_scope = str(content.get("narrative_scope") or narrative_scope)

    prior_classes = prior_continuity_classes(prior_continuity_impacts)
    pressure_state = "moderate_tension"
    if "blame_pressure" in prior_classes:
        pressure_state = "high_blame"
    elif "revealed_fact" in prior_classes:
        pressure_state = "post_revelation_tension"
    elif "repair_attempt" in prior_classes:
        pressure_state = "stabilization_attempt"

    thread_state = (
        prior_narrative_thread_state
        if isinstance(prior_narrative_thread_state, dict)
        else {}
    )
    try:
        thread_pressure_level = int(thread_state.get("thread_pressure_level") or 0)
    except (TypeError, ValueError):
        thread_pressure_level = 0
    dominant_thread_kind = (
        str(thread_state.get("dominant_thread_kind") or "").strip() or None
    )
    if thread_pressure_level >= 3 and not prior_classes:
        pressure_state = "thread_pressure_high"

    assessment: dict[str, Any] = {
        "scene_core": f"goc_scene:{current_scene_id}",
        "pressure_state": pressure_state,
        "module_slice": module_id,
        "canonical_setting": setting,
        "narrative_scope": narrative_scope,
        "active_continuity_classes": prior_classes,
        "continuity_carry_forward_note": (
            "prior_turn_committed_classes:" + ",".join(prior_classes) if prior_classes else "no_prior_continuity"
        ),
    }
    if thread_state:
        assessment["narrative_thread_feedback"] = {
            "feedback_contract": thread_state.get("feedback_contract")
            or "narrative_thread_feedback.v1",
            "thread_count": thread_state.get("thread_count", 0),
            "dominant_thread_kind": dominant_thread_kind,
            "thread_pressure_level": thread_pressure_level,
            "thread_pressure_summary_present": bool(
                str(thread_state.get("thread_pressure_summary") or "").strip()
            ),
        }
        assessment["thread_pressure_state"] = (
            "high_unresolved_thread_pressure"
            if thread_pressure_level >= 3
            else "active_thread_pressure"
            if thread_pressure_level > 0
            else "no_active_thread_pressure"
        )

    sg: dict[str, Any] = {}
    if yaml_slice and isinstance(yaml_slice.get("scene_guidance"), dict):
        sg = yaml_slice["scene_guidance"]
    hints = scene_assessment_phase_hints(scene_guidance=sg, scene_id=current_scene_id)
    if hints:
        assessment["guidance_phase_key"] = hints.get("guidance_phase_key")
        if hints.get("guidance_phase_title"):
            assessment["guidance_phase_title"] = hints.get("guidance_phase_title")
        if hints.get("guidance_civility_required") is not None:
            assessment["guidance_civility_required"] = hints.get("guidance_civility_required")
    snippets = scene_guidance_snippets(scene_guidance=sg, scene_id=current_scene_id)
    if snippets.get("exit_signal"):
        assessment["guidance_exit_signal_hint"] = snippets.get("exit_signal")
    if snippets.get("ai_guidance_hint"):
        assessment["guidance_ai_hint"] = snippets.get("ai_guidance_hint")

    return assessment


def _content_actor_rows(yaml_slice: dict[str, Any] | None) -> list[dict[str, str]]:
    rows = [dict(row) for row in goc_actor_identity_index(yaml_slice).values()]
    voice = (
        yaml_slice.get("character_voice")
        if isinstance(yaml_slice, dict) and isinstance(yaml_slice.get("character_voice"), dict)
        else {}
    )
    for row in rows:
        character_key = str(row.get("character_key") or "").strip()
        vrow = voice.get(character_key) if isinstance(voice.get(character_key), dict) else {}
        formal_role = vrow.get("formal_role") if isinstance(vrow.get("formal_role"), str) else ""
        if formal_role:
            row["formal_role"] = formal_role
    return rows


def _actor_row_blob(row: dict[str, str]) -> str:
    return " ".join(
        str(row.get(key) or "")
        for key in (
            "actor_id",
            "character_key",
            "name",
            "role",
            "formal_role",
            "playable_status",
            "household_side",
        )
    ).lower()


def _select_actor_row(
    rows: list[dict[str, str]],
    *,
    require: tuple[str, ...] = (),
    prefer: tuple[str, ...] = (),
) -> dict[str, str]:
    if not rows:
        return {}
    candidates = [
        row for row in rows
        if all(term.lower() in _actor_row_blob(row) for term in require)
    ]
    if not candidates:
        candidates = list(rows)

    def rank(row: dict[str, str]) -> tuple[int, str]:
        blob = _actor_row_blob(row)
        score = sum(1 for term in prefer if term.lower() in blob)
        return (-score, str(row.get("character_key") or row.get("actor_id") or ""))

    return sorted(candidates, key=rank)[0]


def _actor_reason(row: dict[str, str], prefix: str) -> str:
    role = str(row.get("formal_role") or row.get("role") or row.get("character_key") or "").strip()
    return f"{prefix}:{role}" if role else prefix


def _content_actor_id_from_ref(ref: str | None, yaml_slice: dict[str, Any] | None) -> str:
    raw = str(ref or "").strip()
    if not raw:
        return ""
    raw_low = raw.lower()
    for row in _content_actor_rows(yaml_slice):
        aliases = {
            str(row.get("actor_id") or "").strip(),
            str(row.get("character_key") or "").strip(),
            str(row.get("name") or "").strip(),
            str(row.get("first_name") or "").strip(),
        }
        if raw in aliases or raw_low in {alias.lower() for alias in aliases if alias}:
            return str(row.get("actor_id") or "").strip()
    return ""


def _yaml_default_responder(
    *,
    yaml_slice: dict[str, Any] | None,
    prior_classes: list[str],
    scene_id: str = "",
    selected_scene_function: str = "",
) -> tuple[str, str]:
    """Asymmetry: unnamed moves route pressure to different actors under
    comparable carry-forward.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        yaml_slice: ``yaml_slice`` (dict[str, Any] |
            None); meaning follows the type and call sites.
        prior_classes: ``prior_classes`` (list[str]); meaning follows the type and call sites.
        scene_id: ``scene_id`` (str); meaning follows the type and call sites.
        selected_scene_function: ``selected_scene_function`` (str); meaning follows the type and call sites.
    
    Returns:
        tuple[str, str]:
            Returns a value of type ``tuple[str, str]``; see the function body for structure, error paths, and sentinels.
    """
    rows = _content_actor_rows(yaml_slice)
    phase_key = guidance_phase_key_for_scene_id(scene_id) if scene_id.strip() else GOC_DEFAULT_GUIDANCE_PHASE_KEY

    def choose(
        *,
        require: tuple[str, ...] = (),
        prefer: tuple[str, ...] = (),
        reason_prefix: str = "yaml_voice_bias",
    ) -> tuple[str, str]:
        row = _select_actor_row(rows, require=require, prefer=prefer)
        return str(row.get("actor_id") or "").strip(), _actor_reason(row, reason_prefix)

    if "repair_attempt" in prior_classes:
        return choose(require=("guest",), prefer=("lawyer", "pragmatist", "procedure", "mediation"))
    if "blame_pressure" in prior_classes:
        return choose(require=("host",), prefer=("practical", "conflict-containment", "spouse", "pragmatist"))
    if "revealed_fact" in prior_classes:
        return choose(require=("guest",), prefer=("injured", "mother", "pressure holder", "controlled observer"))
    if selected_scene_function == "repair_or_stabilize":
        return choose(require=("guest",), prefer=("lawyer", "pragmatist", "procedure", "mediation"))
    if selected_scene_function == "probe_motive":
        return choose(require=("guest",), prefer=("injured", "mother", "pressure holder", "controlled observer"))
    if phase_key == "phase_1_polite_opening":
        return choose(require=("host",), prefer=("moral", "ideal", "civilized", "welcome"))
    if phase_key == "phase_3_faction_shifts":
        return choose(require=("host",), prefer=("spouse", "practical", "containment", "pragmatist"))
    row = _select_actor_row(
        rows,
        require=("guest",),
        prefer=("pressure holder", "controlled", "human_playable", "injured"),
    )
    return str(row.get("actor_id") or "").strip(), "default_pressure_bearer"


def semantic_move_to_scene_candidates(
    *,
    move_type: str,
    pacing_mode: str,
    prior_classes: list[str],
    player_input: str,
    interpreted_move: dict[str, Any],
    prior_planner_truth: dict[str, Any] | None = None,
) -> tuple[list[str], dict[str, str], list[str]]:
    """Map semantic move_type to scene-function candidates —
    planner-primary, grounded in the bounded semantic move contract.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        move_type: ``move_type`` (str); meaning follows the type and call sites.
        pacing_mode: ``pacing_mode`` (str); meaning follows the type and call sites.
        prior_classes: ``prior_classes`` (list[str]); meaning follows the type and call sites.
        player_input: ``player_input`` (str); meaning follows the type and call sites.
        interpreted_move: ``interpreted_move`` (dict[str,
            Any]); meaning follows the type and call sites.
    
    Returns:
        tuple[list[str], dict[str, str], list[str]]:
            Returns a value of type ``tuple[list[str], dict[str, str],
            list[str]]``; see the function body for structure, error paths, and sentinels.
    """
    del player_input, interpreted_move
    implied: dict[str, str] = {}
    candidates: list[str] = []
    heuristic_trace: list[str] = []

    if pacing_mode == "containment":
        candidates.append("scene_pivot")
        implied["scene_pivot"] = "refused_cooperation"
        heuristic_trace.append("semantic:pacing_containment->scene_pivot")
        return candidates, implied, heuristic_trace

    if move_type == "competing_repair_and_reveal":
        candidates.append("repair_or_stabilize")
        implied["repair_or_stabilize"] = "repair_attempt"
        candidates.append("reveal_surface")
        implied["reveal_surface"] = "revealed_fact"
        heuristic_trace.append("semantic:competing_repair_and_reveal->repair_plus_reveal_candidates")
        return candidates, implied, heuristic_trace

    if pacing_mode == "thin_edge":
        if move_type == "silence_withdrawal":
            # Wave 3: when prior tension exists, upgrade silence_withdrawal to probe_motive
            if _has_unresolved_carry_forward_tension(prior_planner_truth):
                candidates.append("probe_motive")
                implied["probe_motive"] = "tension_carry_forward_probe"
                heuristic_trace.append("semantic:thin_edge+silence_withdrawal+prior_tension->probe_motive_upgrade")
            else:
                candidates.append("withhold_or_evade")
                implied["withhold_or_evade"] = "silent_carry"
                heuristic_trace.append("semantic:thin_edge+silence_withdrawal->withhold_or_evade")
        else:
            candidates.append("establish_pressure")
            implied["establish_pressure"] = "situational_pressure"
            heuristic_trace.append("semantic:thin_edge_default->establish_pressure")
        return candidates, implied, heuristic_trace

    primary_map: dict[str, tuple[str, str]] = {
        "off_scope_containment": ("scene_pivot", "refused_cooperation"),
        "silence_withdrawal": ("withhold_or_evade", "silent_carry"),
        "repair_attempt": ("repair_or_stabilize", "repair_attempt"),
        "direct_accusation": ("redirect_blame", "blame_pressure"),
        "indirect_provocation": ("escalate_conflict", "situational_pressure"),
        "evasive_deflection": ("withhold_or_evade", "silent_carry"),
        "humiliating_exposure": ("redirect_blame", "dignity_injury"),
        "alliance_reposition": ("scene_pivot", "alliance_shift"),
        "probe_inquiry": ("probe_motive", "situational_pressure"),
        "escalation_threat": ("escalate_conflict", "situational_pressure"),
        "reveal_surface": ("reveal_surface", "revealed_fact"),
        "establish_situational_pressure": ("establish_pressure", "situational_pressure"),
    }
    fn, cont = primary_map.get(move_type, ("establish_pressure", "situational_pressure"))
    candidates.append(fn)
    implied[fn] = cont
    heuristic_trace.append(f"semantic:move_type={move_type}->{fn}")

    if not candidates:
        candidates.append("establish_pressure")
        implied["establish_pressure"] = "situational_pressure"
        heuristic_trace.append("semantic:fallback_empty->establish_pressure")

    return candidates, implied, heuristic_trace


def _narrative_thread_feedback_signal(
    prior_narrative_thread_state: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(prior_narrative_thread_state, dict):
        return {}
    try:
        pressure = int(prior_narrative_thread_state.get("thread_pressure_level") or 0)
    except (TypeError, ValueError):
        pressure = 0
    active = prior_narrative_thread_state.get("active_threads")
    if not isinstance(active, list):
        active = []
    dominant_kind = str(
        prior_narrative_thread_state.get("dominant_thread_kind") or ""
    ).strip()
    related_entities: list[str] = []
    dominant_status = ""
    for row in active:
        if not isinstance(row, dict):
            continue
        if not dominant_status and str(row.get("thread_kind") or "") == dominant_kind:
            dominant_status = str(row.get("status") or "").strip()
        ents = row.get("related_entities")
        if isinstance(ents, list):
            for ent in ents:
                s = str(ent).strip()
                if s and s not in related_entities:
                    related_entities.append(s)
    return {
        "dominant_thread_kind": dominant_kind or None,
        "dominant_thread_status": dominant_status or None,
        "thread_pressure_level": pressure,
        "related_entities": related_entities[:4],
        "thread_count": prior_narrative_thread_state.get("thread_count", len(active)),
    }


def _actor_from_thread_entities(
    entities: list[str],
    *,
    yaml_slice: dict[str, Any] | None,
) -> str | None:
    for raw in entities:
        actor_id = _content_actor_id_from_ref(str(raw or "").strip(), yaml_slice)
        if actor_id:
            return actor_id
    return None


def _goc_primary_responder_from_context(
    *,
    text: str,
    hint: str | None,
    yaml_slice: dict[str, Any] | None,
    prior_classes: list[str],
    current_scene_id: str,
    scene_fn: str,
    implied: dict[str, str],
    thread_feedback: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Describe what ``_goc_primary_responder_from_context`` does in one
    line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        text: ``text`` (str); meaning follows the type and call sites.
        hint: ``hint`` (str | None); meaning follows the type and call sites.
        yaml_slice: ``yaml_slice`` (dict[str, Any] |
            None); meaning follows the type and call sites.
        prior_classes: ``prior_classes`` (list[str]); meaning follows the type and call sites.
        current_scene_id: ``current_scene_id`` (str); meaning follows the type and call sites.
        scene_fn: ``scene_fn`` (str); meaning follows the type and call sites.
        implied: ``implied`` (dict[str, str]); meaning follows the type and call sites.
    
    Returns:
        tuple[str, str]:
            Returns a value of type ``tuple[str, str]``; see the function body for structure, error paths, and sentinels.
    """
    hinted_actor_id = _content_actor_id_from_ref(hint, yaml_slice)
    if hinted_actor_id:
        return hinted_actor_id, "semantic_target_actor_hint"
    tf = thread_feedback if isinstance(thread_feedback, dict) else {}
    actor_from_thread = _actor_from_thread_entities(
        tf.get("related_entities") if isinstance(tf.get("related_entities"), list) else [],
        yaml_slice=yaml_slice,
    )
    if actor_from_thread:
        return actor_from_thread, "narrative_thread_related_entity_focus"
    if (
        scene_fn == "scene_pivot"
        and tf.get("dominant_thread_kind") == "progression_blocked"
    ):
        row = _select_actor_row(
            _content_actor_rows(yaml_slice),
            require=("guest",),
            prefer=("lawyer", "pragmatist", "procedure", "mediation"),
        )
        return str(row.get("actor_id") or "").strip(), _actor_reason(
            row, "narrative_thread_bias:progression_blocked_mediation"
        )

    actor, reason = _yaml_default_responder(
        yaml_slice=yaml_slice,
        prior_classes=prior_classes,
        scene_id=current_scene_id,
        selected_scene_function=scene_fn,
    )
    if scene_fn == "redirect_blame" and "dignity_injury" in prior_classes:
        row = _select_actor_row(
            _content_actor_rows(yaml_slice),
            require=("host",),
            prefer=("moral", "ideal", "civilized", "responsibility"),
        )
        return str(row.get("actor_id") or "").strip(), _actor_reason(
            row, "pressure_identity_bias:dignity_injury_host_reaction"
        )
    if scene_fn == "scene_pivot" and "alliance_shift" in implied.values():
        row = _select_actor_row(
            _content_actor_rows(yaml_slice),
            require=("host",),
            prefer=("spouse", "practical", "containment", "pragmatist"),
        )
        return str(row.get("actor_id") or "").strip(), _actor_reason(
            row, "pressure_identity_bias:alliance_shift_reposition"
        )
    return actor, reason


def _append_responder(
    responders: list[dict[str, Any]],
    *,
    actor_id: str,
    reason: str,
    role: str,
    sequence: int = 0,
) -> None:
    actor = str(actor_id or "").strip()
    if not actor:
        return
    for row in responders:
        if str(row.get("actor_id") or "").strip() == actor:
            return
    responders.append({
        "actor_id": actor,
        "reason": reason,
        "role": role,
        "preferred_reaction_order": sequence,
    })


def _content_actor_ids(yaml_slice: dict[str, Any] | None) -> list[str]:
    return goc_actor_ids_from_content(yaml_slice)


def _first_available_actor_id(actor_ids: list[str], *, excluded: set[str]) -> str:
    for actor_id in actor_ids:
        if actor_id and actor_id not in excluded:
            return actor_id
    return ""


def _build_responder_set(
    *,
    primary_actor: str,
    primary_reason: str,
    yaml_slice: dict[str, Any] | None,
    scene_fn: str,
    pacing_mode: str,
    prior_classes: list[str],
    interpreted_move: dict[str, Any],
    text: str,
    social_state_record: dict[str, Any] | None,
    thread_feedback: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build primary + optional secondary + optional interrupter responder set."""
    responders: list[dict[str, Any]] = []
    _append_responder(
        responders,
        actor_id=primary_actor,
        reason=primary_reason,
        role="primary_responder",
        sequence=0,
    )

    tf = thread_feedback if isinstance(thread_feedback, dict) else {}
    thread_pressure = 0
    try:
        thread_pressure = int(tf.get("thread_pressure_level") or 0)
    except (TypeError, ValueError):
        thread_pressure = 0
    social = social_state_record if isinstance(social_state_record, dict) else {}
    social_risk_band = str(social.get("social_risk_band") or "").strip().lower()
    move_type = str(interpreted_move.get("move_type") or "").strip().lower()
    is_high_pressure = (
        scene_fn in {"escalate_conflict", "redirect_blame", "scene_pivot"}
        or pacing_mode in {"multi_pressure", "compressed"}
        or thread_pressure >= 3
        or "blame_pressure" in prior_classes
        or "dignity_injury" in prior_classes
        or social_risk_band == "high"
        or move_type in {"direct_accusation", "escalation_threat"}
    )

    ordering_rules: list[str] = [
        "primary_responder_selected_from_context",
        "secondary_reactor_enabled_on_high_pressure",
        "interruption_candidate_enabled_on_thread_or_escalation_pressure",
        "secondary_must_react_when_nominated_and_high_pressure",
    ]

    if is_high_pressure:
        secondary = _first_available_actor_id(
            _content_actor_ids(yaml_slice),
            excluded={str(row.get("actor_id") or "").strip() for row in responders if isinstance(row, dict)},
        )
        if secondary:
            _append_responder(
                responders,
                actor_id=secondary,
                reason="secondary_reactor:high_pressure_cross_couple",
                role="secondary_reactor",
                sequence=1,
            )

    interruption_trigger = (
        thread_pressure >= 3
        or scene_fn in {"escalate_conflict", "scene_pivot"}
        or move_type in {"direct_accusation", "escalation_threat"}
    )
    if interruption_trigger:
        interrupter = _first_available_actor_id(
            _content_actor_ids(yaml_slice),
            excluded={str(row.get("actor_id") or "").strip() for row in responders if isinstance(row, dict)},
        )
        if interrupter:
            _append_responder(
                responders,
                actor_id=interrupter,
                reason="interruption_candidate:pressure_interrupt_window",
                role="interruption_candidate",
                sequence=2,
            )

    return responders, {
        "responder_ordering_rules": ordering_rules,
        "secondary_reactor_enabled": is_high_pressure,
        "interruption_candidate_enabled": interruption_trigger,
    }


def build_responder_and_function(
    *,
    player_input: str,
    interpreted_move: dict[str, Any],
    interpreted_input: dict[str, Any] | None = None,
    pacing_mode: str,
    prior_continuity_impacts: list[dict[str, Any]] | None = None,
    yaml_slice: dict[str, Any] | None = None,
    current_scene_id: str = "",
    semantic_move_record: dict[str, Any] | None = None,
    social_state_record: dict[str, Any] | None = None,
    prior_narrative_thread_state: dict[str, Any] | None = None,
    prior_planner_truth: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str, dict[str, str], dict[str, Any]]:
    """Choose responder set, scene function, implied continuity map, and
    multi-pressure resolution record.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        player_input: ``player_input`` (str); meaning follows the type and call sites.
        interpreted_move: ``interpreted_move`` (dict[str,
            Any]); meaning follows the type and call sites.
        pacing_mode: ``pacing_mode`` (str); meaning follows the type and call sites.
        prior_continuity_impacts: ``prior_continuity_impacts`` (list[dict[str, Any]] | None); meaning follows the type and call sites.
        yaml_slice: ``yaml_slice`` (dict[str, Any] |
            None); meaning follows the type and call sites.
        current_scene_id: ``current_scene_id`` (str); meaning follows the type and call sites.
        semantic_move_record: ``semantic_move_record`` (dict[str, Any] | None); meaning follows the type and call sites.
        social_state_record: ``social_state_record`` (dict[str, Any] | None); meaning follows the type and call sites.
        prior_narrative_thread_state: bounded committed thread continuity from
            the story session, if any.
    
    Returns:
        tuple[list[dict[str, Any]], str, dict[str, str], dict[str, A...:
            Returns a value of type ``tuple[list[dict[str, Any]], str, dict[str,
            str], dict[str, Any]]``; see the function body for structure, error paths, and sentinels.
    """
    text = f"{player_input} {interpreted_move.get('player_intent', '')}".lower()
    interp = interpreted_input if isinstance(interpreted_input, dict) else {}
    player_input_kind = str(interp.get("player_input_kind") or "").strip().lower()
    narrator_expected = bool(interp.get("narrator_response_expected"))
    npc_expected = bool(interp.get("npc_response_expected"))
    prior_classes = prior_continuity_classes(prior_continuity_impacts)
    selection_source = "semantic_pipeline_v1"
    if semantic_move_record and isinstance(semantic_move_record, dict) and semantic_move_record.get("move_type"):
        move_type = str(semantic_move_record["move_type"])
        if move_type not in SEMANTIC_MOVE_TYPES:
            selection_source = "invalid_semantic_move"
            candidates = ["establish_pressure"]
            implied = {"establish_pressure": "situational_pressure"}
            heuristic_trace = [f"semantic:invalid_move_type={move_type[:80]}->establish_pressure"]
        else:
            candidates, implied, heuristic_trace = semantic_move_to_scene_candidates(
                move_type=move_type,
                pacing_mode=pacing_mode,
                prior_classes=prior_classes,
                player_input=player_input,
                interpreted_move=interpreted_move,
                prior_planner_truth=prior_planner_truth,
            )
    else:
        selection_source = "semantic_move_required"
        candidates = ["scene_pivot"] if pacing_mode == "containment" else ["establish_pressure"]
        implied = {
            candidates[0]: "refused_cooperation" if pacing_mode == "containment" else "situational_pressure"
        }
        heuristic_trace = [
            "semantic:missing_semantic_move_record->neutral_scene_candidate"
        ]

    thread_feedback = _narrative_thread_feedback_signal(prior_narrative_thread_state)
    if (
        thread_feedback.get("dominant_thread_kind") == "progression_blocked"
        and thread_feedback.get("thread_pressure_level", 0) >= 2
    ):
        if "scene_pivot" not in candidates:
            candidates.append("scene_pivot")
        implied["scene_pivot"] = "refused_cooperation"
        heuristic_trace.append("thread:progression_blocked->scene_pivot")

    scene_fn = select_single_scene_function(candidates, implied_continuity_by_function=implied)
    if (
        thread_feedback.get("dominant_thread_kind") == "progression_blocked"
        and thread_feedback.get("thread_pressure_level", 0) >= 2
    ):
        scene_fn = "scene_pivot"
        heuristic_trace.append("thread:progression_blocked_override->scene_pivot")
    if (
        is_question_punctuation_probe_guarded(player_input_kind)
        and narrator_expected
        and not npc_expected
        and scene_fn == "probe_motive"
    ):
        # Keep action/perception turns out of NPC-answer-first scene modes.
        scene_fn = "establish_pressure"
        heuristic_trace.append("intent_surface:action_or_perception_override->establish_pressure")
    assert_subdecision_label_in_matrix("scene_function", scene_fn)

    semantic_trace_ref = ""
    if semantic_move_record and isinstance(semantic_move_record.get("interpretation_trace"), list):
        tr = semantic_move_record["interpretation_trace"]
        if tr and isinstance(tr[0], dict) and tr[0].get("detail_code"):
            semantic_trace_ref = str(tr[0].get("detail_code"))[:120]
    subtext_record = (
        semantic_move_record.get("subtext")
        if isinstance(semantic_move_record, dict)
        and isinstance(semantic_move_record.get("subtext"), dict)
        else {}
    )

    resolution: dict[str, Any] = {
        "candidates": list(candidates),
        "implied_continuity_by_function": dict(implied),
        "chosen_scene_function": scene_fn,
        "rationale": (
            "CANONICAL_TURN_CONTRACT_GOC.md section 3.5 — ranked implied continuity obligation "
            f"(carry_forward_classes={prior_classes}); tie-break lexicographic smallest label."
        ),
        "heuristic_trace": heuristic_trace[:16],
        "selection_source": selection_source,
        "legacy_keyword_scene_candidates_used": False,
        "semantic_move_required": selection_source == "semantic_move_required",
        "semantic_move_contract_valid": selection_source != "invalid_semantic_move",
        "player_input_kind": player_input_kind or None,
        "narrator_response_expected": narrator_expected,
        "npc_response_expected": npc_expected,
        "semantic_move_trace_ref": semantic_trace_ref,
        "subtext_surface_mode": subtext_record.get("surface_mode"),
        "subtext_hidden_intent_hypothesis": subtext_record.get("hidden_intent_hypothesis"),
        "subtext_function": subtext_record.get("subtext_function"),
        "subtext_policy_rule_id": subtext_record.get("policy_rule_id"),
        "semantic_secondary_move_type": (
            str(semantic_move_record.get("secondary_move_type") or "").strip()
            if isinstance(semantic_move_record, dict)
            else None
        ),
        "semantic_secondary_features": (
            [
                str(x).strip()
                for x in (semantic_move_record.get("secondary_dramatic_features") or [])
                if str(x).strip()
            ][:6]
            if isinstance(semantic_move_record, dict)
            else []
        ),
        "social_state_asymmetry": (social_state_record or {}).get("responder_asymmetry_code")
        if isinstance(social_state_record, dict)
        else None,
        "narrative_thread_feedback": thread_feedback or None,
    }

    hint = None
    if semantic_move_record and isinstance(semantic_move_record.get("target_actor_hint"), str):
        hint = semantic_move_record["target_actor_hint"]

    actor, reason = _goc_primary_responder_from_context(
        text=text,
        hint=hint,
        yaml_slice=yaml_slice,
        prior_classes=prior_classes,
        current_scene_id=current_scene_id,
        scene_fn=scene_fn,
        implied=implied,
        thread_feedback=thread_feedback,
    )

    responders, responder_set_resolution = _build_responder_set(
        primary_actor=actor,
        primary_reason=reason,
        yaml_slice=yaml_slice,
        scene_fn=scene_fn,
        pacing_mode=pacing_mode,
        prior_classes=prior_classes,
        interpreted_move=interpreted_move,
        text=text,
        social_state_record=social_state_record if isinstance(social_state_record, dict) else None,
        thread_feedback=thread_feedback,
    )
    resolution["responder_set_resolution"] = responder_set_resolution
    if is_narrator_only_player_input_kind(player_input_kind) and narrator_expected and not npc_expected:
        resolution["selection_source"] = "advisory_npc_reaction_after_player_action"
        resolution["npc_response_policy"] = "optional_social_only"
        if responders and isinstance(responders[0], dict):
            responders[0] = {
                **responders[0],
                "reason": "advisory_npc_reaction_after_player_action",
                "role": "advisory_reaction",
            }
    resolution["selected_responder_roles"] = [
        {
            "actor_id": str(row.get("actor_id") or "").strip(),
            "role": str(row.get("role") or "").strip() or "responder",
            "reason": str(row.get("reason") or "").strip(),
        }
        for row in responders
        if isinstance(row, dict)
    ]

    return responders, scene_fn, implied, resolution


def _has_unresolved_carry_forward_tension(
    prior_planner_truth: dict[str, Any] | None,
) -> bool:
    """Return True when prior committed planner truth records unresolved tension."""
    if not isinstance(prior_planner_truth, dict):
        return False
    notes = prior_planner_truth.get("carry_forward_tension_notes")
    if isinstance(notes, str) and notes.strip():  # whitespace-only does not count
        return True
    if prior_planner_truth.get("social_pressure_shift") == "escalated":
        return True
    if prior_planner_truth.get("initiative_pressure_label") in ("contested", "floor_claimed"):
        return True
    return False


def _no_lexical_player_input(trimmed: str) -> bool:
    if not trimmed:
        return True
    return not any(ch.isalnum() for ch in trimmed)


def _semantic_silence_signal(
    *,
    player_input: str,
    interpreted_move: dict[str, Any],
    semantic_move_record: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return structured silence-negative-space signal metadata when silence is the social move."""

    sem = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    sem_move_type = str(sem.get("move_type") or "").strip()
    intent = str(interpreted_move.get("player_intent") or "").strip().lower()
    move_class = str(interpreted_move.get("move_class") or "").strip().lower()
    player_input_kind = str(interpreted_move.get("player_input_kind") or "").strip().lower()
    trimmed = player_input.strip()
    no_lexical = _no_lexical_player_input(trimmed)

    if sem_move_type == "silence_withdrawal":
        if not trimmed:
            silence_kind = "empty_input"
            interpreter_signal = "semantic_move:silence_withdrawal+empty_input"
        elif no_lexical:
            silence_kind = "non_lexical_input"
            interpreter_signal = "semantic_move:silence_withdrawal+non_lexical_input"
        else:
            silence_kind = str(sem.get("silence_kind") or "").strip() or "explicit_silence"
            interpreter_signal = "semantic_move:silence_withdrawal"
        return {
            "source": "semantic_move",
            "silence_kind": silence_kind,
            "semantic_move_type": sem_move_type,
            "interpreter_signal": interpreter_signal,
        }

    if (
        "withheld_response_or_silence" in intent
        or "silence" in intent
        or player_input_kind == "wait_or_observe"
        or (move_class in {"ambiguous", "intent_only"} and no_lexical)
        or (not move_class and no_lexical)
    ):
        silence_kind = "empty_input" if not trimmed else "non_lexical_input" if no_lexical else "withheld_answer"
        return {
            "source": "interpreted_input",
            "silence_kind": silence_kind,
            "semantic_move_type": sem_move_type or None,
            "interpreter_signal": f"interpreted:{move_class or player_input_kind or 'silence'}",
        }

    return None


def build_pacing_and_silence(
    *,
    player_input: str,
    interpreted_move: dict[str, Any],
    module_id: str,
    prior_narrative_thread_state: dict[str, Any] | None = None,
    semantic_move_record: dict[str, Any] | None = None,
    prior_planner_truth: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Describe what ``build_pacing_and_silence`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        player_input: ``player_input`` (str); meaning follows the type and call sites.
        interpreted_move: ``interpreted_move`` (dict[str,
            Any]); meaning follows the type and call sites.
        module_id: ``module_id`` (str); meaning follows the type and call sites.
        prior_narrative_thread_state: bounded committed thread continuity from
            the story session, if any.
    
    Returns:
        tuple[str, dict[str, Any]]:
            Returns a value of type ``tuple[str, dict[str, Any]]``; see the function body for structure, error paths, and sentinels.
    """
    if module_id != GOC_MODULE_ID:
        return _finalize_pacing_silence(
            assert_pacing_mode("standard"),
            {
                "mode": assert_silence_brevity_mode("normal"),
                "reason": "non_goc_slice_default",
                "source": "non_goc_slice",
                "silence_kind": "none",
                "dramatic_function": "not_applicable",
            },
        )

    sem = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    sem_move_type = str(sem.get("move_type") or "").strip()
    subtext = sem.get("subtext") if isinstance(sem.get("subtext"), dict) else {}
    subtext_function = str(subtext.get("subtext_function") or "").strip()
    trimmed = player_input.strip()
    words = [w for w in trimmed.replace(".", " ").split() if w]
    thin_fragment = len(trimmed) <= 10 and len(words) <= 2 and "?" not in trimmed

    if sem_move_type == "off_scope_containment":
        return _finalize_pacing_silence(
            assert_pacing_mode("containment"),
            {
                "mode": assert_silence_brevity_mode("normal"),
                "reason": "slice_boundary_containment_move",
                "source": "slice_boundary",
                "silence_kind": "boundary_containment",
                "dramatic_function": "contain_boundary",
            },
        )

    if sem_move_type == "escalation_threat":
        return _finalize_pacing_silence(
            assert_pacing_mode("standard"),
            {
                "mode": assert_silence_brevity_mode("normal"),
                "reason": "semantic_escalation_threat",
            },
        )

    semantic_silence = _semantic_silence_signal(
        player_input=player_input,
        interpreted_move=interpreted_move,
        semantic_move_record=semantic_move_record,
    )
    if semantic_silence:
        prior_tension = _has_unresolved_carry_forward_tension(prior_planner_truth)
        if prior_tension:
            return _finalize_pacing_silence(
                assert_pacing_mode("compressed"),
                build_silence_negative_space_decision(
                    mode=assert_silence_brevity_mode("brief"),
                    reason="silence_withdrawal_upgraded_by_prior_tension",
                    source=str(semantic_silence["source"]),
                    silence_kind="charged_after_tension",
                    dramatic_function="carry_tension",
                    pressure_basis="prior_planner_truth",
                    semantic_move_type=str(semantic_silence.get("semantic_move_type") or "silence_withdrawal"),
                    interpreter_signal=str(semantic_silence.get("interpreter_signal") or ""),
                ),
            )
        return _finalize_pacing_silence(
            assert_pacing_mode("thin_edge"),
            build_silence_negative_space_decision(
                mode=assert_silence_brevity_mode("withheld"),
                reason="silence_withdrawal",
                source=str(semantic_silence["source"]),
                silence_kind=str(semantic_silence["silence_kind"]),
                dramatic_function="withhold_response",
                pressure_basis="semantic_move",
                semantic_move_type=str(semantic_silence.get("semantic_move_type") or "silence_withdrawal"),
                interpreter_signal=str(semantic_silence.get("interpreter_signal") or ""),
            ),
        )

    if sem_move_type in {
        "competing_repair_and_reveal",
        "direct_accusation",
        "indirect_provocation",
    } and thin_fragment:
        return _finalize_pacing_silence(
            assert_pacing_mode("multi_pressure"),
            {
                "mode": assert_silence_brevity_mode("normal"),
                "reason": "semantic_sparse_pressure_move",
            },
        )
    if subtext_function in {"force_accountability", "raise_pressure", "reveal_under_repair"}:
        return _finalize_pacing_silence(
            assert_pacing_mode("multi_pressure"),
            {
                "mode": assert_silence_brevity_mode("normal"),
                "reason": "subtext_pressure_function",
            },
        )
    if subtext_function in {"probe_motive", "test_boundary"} and thin_fragment:
        return _finalize_pacing_silence(
            assert_pacing_mode("thin_edge"),
            {
                "mode": assert_silence_brevity_mode("brief"),
                "reason": "subtext_thin_edge_probe_or_boundary",
            },
        )
    if thin_fragment:
        return _finalize_pacing_silence(
            assert_pacing_mode("thin_edge"),
            {
                "mode": assert_silence_brevity_mode("brief"),
                "reason": "thin_edge_brevity_pressure",
            },
        )

    if sem_move_type == "competing_repair_and_reveal":
        pacing = assert_pacing_mode("multi_pressure")
        silence = {"mode": assert_silence_brevity_mode("normal"), "reason": "semantic_repair_and_reveal_compete"}
    elif sem_move_type == "probe_inquiry" and "repair_attempt" in (prior_planner_truth or {}).get(
        "carry_forward_classes", []
    ):
        pacing = assert_pacing_mode("compressed")
        silence = {"mode": assert_silence_brevity_mode("brief"), "reason": "semantic_probe_after_repair"}
    else:
        thread_feedback = _narrative_thread_feedback_signal(prior_narrative_thread_state)
        thread_pressure = int(thread_feedback.get("thread_pressure_level") or 0)
        dominant_thread_kind = thread_feedback.get("dominant_thread_kind")
        if thread_pressure >= 3:
            pacing = assert_pacing_mode("multi_pressure")
            silence = {
                "mode": assert_silence_brevity_mode("normal"),
                "reason": "narrative_thread_pressure_multi_pressure",
            }
        elif dominant_thread_kind == "interpretation_pressure":
            pacing = assert_pacing_mode("compressed")
            silence = {
                "mode": assert_silence_brevity_mode("brief"),
                "reason": "narrative_thread_interpretation_pressure",
            }
        else:
            pacing = assert_pacing_mode("standard")
            silence = {"mode": assert_silence_brevity_mode("normal"), "reason": "default_verbal_density"}
    return _finalize_pacing_silence(pacing, silence)
