"""Deterministic scene director for God of Carnage (CANONICAL_TURN_CONTRACT_GOC.md §3)."""

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
from ai_stack.goc_yaml_authority import (
    guidance_phase_key_for_scene_id,
    scene_assessment_phase_hints,
    scene_guidance_snippets,
)
from ai_stack.scene_direction_subdecision_matrix import assert_subdecision_label_in_matrix


def _finalize_pacing_silence(pacing: str, silence: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    assert_subdecision_label_in_matrix("pacing_mode", pacing)
    assert_subdecision_label_in_matrix("silence_brevity_mode", silence["mode"])
    return pacing, silence

# CANONICAL_TURN_CONTRACT_GOC.md §5.1 — minimal keys for GoC scene_assessment (when slice active).
GOC_SCENE_ASSESSMENT_MINIMAL_KEYS: frozenset[str] = frozenset({"scene_core", "pressure_state", "module_slice"})


def goc_scene_assessment_has_minimal_fields(assessment: dict[str, Any] | None) -> bool:
    """Return True if assessment dict carries required minimal schema for GoC operator/gate checks."""
    if not assessment or not isinstance(assessment, dict):
        return False
    for key in GOC_SCENE_ASSESSMENT_MINIMAL_KEYS:
        val = assessment.get(key)
        if val is None or val == "":
            return False
    return True


def _severity_index(continuity_class: str) -> int:
    try:
        return CONTINUITY_CLASS_SEVERITY_ORDER.index(continuity_class)
    except ValueError:
        return len(CONTINUITY_CLASS_SEVERITY_ORDER)


def prior_continuity_classes(prior_continuity_impacts: list[dict[str, Any]] | None) -> list[str]:
    """Extract frozen continuity class labels from carry-forward impacts (bounded, not a memory system)."""
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
    """CANONICAL_TURN_CONTRACT_GOC.md §3.5 — single function from competing candidates."""
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
) -> dict[str, Any]:
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


def _yaml_default_responder(
    *,
    yaml_slice: dict[str, Any] | None,
    prior_classes: list[str],
    scene_id: str = "",
    selected_scene_function: str = "",
) -> tuple[str, str]:
    """Asymmetry: unnamed moves route pressure to different actors under comparable carry-forward."""
    voice = {}
    chars = {}
    if yaml_slice and isinstance(yaml_slice.get("character_voice"), dict):
        voice = yaml_slice["character_voice"]
    if yaml_slice and isinstance(yaml_slice.get("characters"), dict):
        chars = yaml_slice["characters"]
    veronique = voice.get("veronique") if isinstance(voice.get("veronique"), dict) else {}
    michel = voice.get("michel") if isinstance(voice.get("michel"), dict) else {}
    annette = voice.get("annette") if isinstance(voice.get("annette"), dict) else {}
    alain = voice.get("alain") if isinstance(voice.get("alain"), dict) else {}
    veronique_role = (
        veronique.get("formal_role") if isinstance(veronique.get("formal_role"), str) else "host_moral_idealist"
    )
    michel_role = michel.get("formal_role") if isinstance(michel.get("formal_role"), str) else "pragmatist_host_spouse"
    annette_role = annette.get("formal_role") if isinstance(annette.get("formal_role"), str) else "guest_cynic"
    alain_role = alain.get("formal_role") if isinstance(alain.get("formal_role"), str) else "guest_mediator"
    phase_key = guidance_phase_key_for_scene_id(scene_id) if scene_id.strip() else "phase_2_moral_negotiation"

    if "repair_attempt" in prior_classes:
        return "alain_reille", f"yaml_voice_bias:{alain_role}"
    if "blame_pressure" in prior_classes:
        return "michel_longstreet", f"yaml_voice_bias:{michel_role}"
    if "revealed_fact" in prior_classes:
        return "annette_reille", f"yaml_voice_bias:{annette_role}"
    if selected_scene_function == "repair_or_stabilize":
        return "alain_reille", f"yaml_voice_bias:{alain_role}"
    if selected_scene_function == "probe_motive":
        return "annette_reille", f"yaml_voice_bias:{annette_role}"
    if phase_key == "phase_1_polite_opening":
        return "veronique_vallon", f"yaml_voice_bias:{veronique_role}"
    if phase_key == "phase_3_faction_shifts":
        return "michel_longstreet", f"yaml_voice_bias:{michel_role}"
    _ = chars  # kept to show characters.yaml is loaded for future tie-break extension.
    return "annette_reille", "default_pressure_bearer"


def semantic_move_to_scene_candidates(
    *,
    move_type: str,
    pacing_mode: str,
    prior_classes: list[str],
    player_input: str,
    interpreted_move: dict[str, Any],
) -> tuple[list[str], dict[str, str], list[str]]:
    """Map semantic move_type to scene-function candidates — planner-primary (not keyword surface)."""
    text = f"{player_input} {interpreted_move.get('player_intent', '')}".lower()
    move_class = str(interpreted_move.get("move_class") or "").lower()
    intent = str(interpreted_move.get("player_intent") or "").lower()
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
        _merge_continuity_supplements(
            candidates,
            implied,
            heuristic_trace,
            prior_classes,
            text,
            move_class,
            intent,
            player_input,
            pacing_mode,
        )
        return candidates, implied, heuristic_trace

    if pacing_mode == "thin_edge":
        if move_type == "silence_withdrawal":
            candidates.append("withhold_or_evade")
            implied["withhold_or_evade"] = "silent_carry"
            heuristic_trace.append("semantic:thin_edge+silence_withdrawal->withhold_or_evade")
        elif "silent" in text or "say nothing" in text:
            candidates.append("withhold_or_evade")
            implied["withhold_or_evade"] = "silent_carry"
            heuristic_trace.append("semantic:thin_edge_silence_compat->withhold_or_evade")
        else:
            candidates.append("establish_pressure")
            implied["establish_pressure"] = "situational_pressure"
            heuristic_trace.append("semantic:thin_edge_default->establish_pressure")
        _merge_continuity_supplements(
            candidates,
            implied,
            heuristic_trace,
            prior_classes,
            text,
            move_class,
            intent,
            player_input,
            pacing_mode,
        )
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

    _merge_continuity_supplements(
        candidates,
        implied,
        heuristic_trace,
        prior_classes,
        text,
        move_class,
        intent,
        player_input,
        pacing_mode,
    )

    if not candidates:
        candidates.append("establish_pressure")
        implied["establish_pressure"] = "situational_pressure"
        heuristic_trace.append("semantic:fallback_empty->establish_pressure")

    return candidates, implied, heuristic_trace


def _merge_continuity_supplements(
    candidates: list[str],
    implied: dict[str, str],
    heuristic_trace: list[str],
    prior_classes: list[str],
    text: str,
    move_class: str,
    intent: str,
    player_input: str,
    pacing_mode: str,
) -> None:
    """Add carry-forward and structural nudges (bounded compatibility layer)."""
    if (
        ("question" in move_class or "question" in intent or player_input.strip().endswith("?"))
        and "probe_motive" not in candidates
        and pacing_mode != "containment"
    ):
        candidates.append("probe_motive")
        implied["probe_motive"] = "situational_pressure"
        heuristic_trace.append("compat:question_shape->probe_motive")

    if "blame_pressure" in prior_classes and not candidates:
        candidates.append("redirect_blame")
        implied["redirect_blame"] = "blame_pressure"
        heuristic_trace.append("continuity:blame_pressure_fallback->redirect_blame")
    if "dignity_injury" in prior_classes and not candidates:
        candidates.append("redirect_blame")
        implied["redirect_blame"] = "dignity_injury"
        heuristic_trace.append("continuity:dignity_injury_fallback->redirect_blame")
    if "alliance_shift" in prior_classes and "probe_motive" not in candidates and "why" in text:
        candidates.append("probe_motive")
        implied["probe_motive"] = "alliance_shift"
        heuristic_trace.append("continuity:alliance_shift_nudge->probe_motive")
    if "blame_pressure" in prior_classes and "redirect_blame" not in candidates and "watch" in text:
        candidates.append("redirect_blame")
        implied["redirect_blame"] = "blame_pressure"
        heuristic_trace.append("continuity:watch_under_blame->redirect_blame")


def _legacy_keyword_scene_candidates(
    *,
    pacing_mode: str,
    player_input: str,
    interpreted_move: dict[str, Any],
    prior_classes: list[str],
) -> tuple[list[str], dict[str, str], list[str]]:
    """Pre-semantic keyword/tie-break heuristic — bounded fallback only when semantic record absent."""
    text = f"{player_input} {interpreted_move.get('player_intent', '')}".lower()
    move_class = str(interpreted_move.get("move_class") or "").lower()
    intent = str(interpreted_move.get("player_intent") or "").lower()
    implied: dict[str, str] = {}
    candidates: list[str] = []
    heuristic_trace: list[str] = []

    if pacing_mode == "containment":
        candidates.append("scene_pivot")
        implied["scene_pivot"] = "refused_cooperation"
        heuristic_trace.append("pacing_mode:containment->scene_pivot")
    elif pacing_mode == "thin_edge":
        if "silent" in text or "say nothing" in text or "nothing" in text:
            candidates.append("withhold_or_evade")
            implied["withhold_or_evade"] = "silent_carry"
            heuristic_trace.append("thin_edge:silence_keyword->withhold_or_evade")
        else:
            candidates.append("establish_pressure")
            implied["establish_pressure"] = "situational_pressure"
            heuristic_trace.append("thin_edge:default->establish_pressure")
    else:
        if (
            "silent" in text
            or "say nothing" in text
            or "awkward pause" in text
            or "long pause" in text
            or "do not answer" in text
            or "won't answer" in text
        ):
            candidates.append("withhold_or_evade")
            implied["withhold_or_evade"] = "silent_carry"
            heuristic_trace.append("keyword:silence_pause->withhold_or_evade")
        if (
            "humiliat" in text
            or "embarrass" in text
            or "ashamed" in text
            or "ridicule" in text
            or "mock" in text
        ):
            candidates.append("redirect_blame")
            implied["redirect_blame"] = "dignity_injury"
            heuristic_trace.append("keyword:humiliation->redirect_blame")
        if (
            "evade" in text
            or "deflect" in text
            or "avoid answering" in text
            or "change subject" in text
        ):
            candidates.append("withhold_or_evade")
            implied["withhold_or_evade"] = "silent_carry"
            heuristic_trace.append("keyword:evasion->withhold_or_evade")
        if "sorry" in text or "apolog" in text or "repair" in text:
            candidates.append("repair_or_stabilize")
            implied["repair_or_stabilize"] = "repair_attempt"
            heuristic_trace.append("keyword:repair->repair_or_stabilize")
        if "reveal" in text or "secret" in text or "truth" in text or "admit" in text:
            candidates.append("reveal_surface")
            implied["reveal_surface"] = "revealed_fact"
            heuristic_trace.append("keyword:reveal->reveal_surface")
        if "blame" in text or "fault" in text:
            candidates.append("redirect_blame")
            implied["redirect_blame"] = "blame_pressure"
            heuristic_trace.append("keyword:blame->redirect_blame")
        if "why" in text or "motive" in text or "reason" in text:
            candidates.append("probe_motive")
            implied["probe_motive"] = "situational_pressure"
            heuristic_trace.append("keyword:probe->probe_motive")
        if "escalat" in text or "fight" in text or "angry" in text or "furious" in text or "attack" in text:
            candidates.append("escalate_conflict")
            implied["escalate_conflict"] = "situational_pressure"
            heuristic_trace.append("keyword:escalation->escalate_conflict")
        if (
            "side with" in text
            or "siding with" in text
            or "ally with" in text
            or "stand with" in text
            or "against your wife" in text
            or "against your husband" in text
        ):
            candidates.append("scene_pivot")
            implied["scene_pivot"] = "alliance_shift"
            heuristic_trace.append("keyword:alliance_reposition->scene_pivot")

        if (
            ("question" in move_class or "question" in intent or player_input.strip().endswith("?"))
            and "probe_motive" not in candidates
            and "containment" not in pacing_mode
        ):
            candidates.append("probe_motive")
            implied["probe_motive"] = "situational_pressure"
            heuristic_trace.append("interpreted_move:question_nudge->probe_motive")

        if "blame_pressure" in prior_classes and not candidates:
            candidates.append("redirect_blame")
            implied["redirect_blame"] = "blame_pressure"
            heuristic_trace.append("continuity:blame_pressure_fallback->redirect_blame")
        if "dignity_injury" in prior_classes and not candidates:
            candidates.append("redirect_blame")
            implied["redirect_blame"] = "dignity_injury"
            heuristic_trace.append("continuity:dignity_injury_fallback->redirect_blame")
        if "alliance_shift" in prior_classes and "probe_motive" not in candidates and "why" in text:
            candidates.append("probe_motive")
            implied["probe_motive"] = "alliance_shift"
            heuristic_trace.append("continuity:alliance_shift_nudge->probe_motive")
        if "blame_pressure" in prior_classes and "redirect_blame" not in candidates and "watch" in text:
            candidates.append("redirect_blame")
            implied["redirect_blame"] = "blame_pressure"
            heuristic_trace.append("continuity:watch_under_blame->redirect_blame")

        if not candidates:
            candidates.append("establish_pressure")
            implied["establish_pressure"] = "situational_pressure"
            heuristic_trace.append("default->establish_pressure")

    return candidates, implied, heuristic_trace


def build_responder_and_function(
    *,
    player_input: str,
    interpreted_move: dict[str, Any],
    pacing_mode: str,
    prior_continuity_impacts: list[dict[str, Any]] | None = None,
    yaml_slice: dict[str, Any] | None = None,
    current_scene_id: str = "",
    semantic_move_record: dict[str, Any] | None = None,
    social_state_record: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str, dict[str, str], dict[str, Any]]:
    """Choose responder set, scene function, implied continuity map, and multi-pressure resolution record."""
    text = f"{player_input} {interpreted_move.get('player_intent', '')}".lower()
    prior_classes = prior_continuity_classes(prior_continuity_impacts)
    selection_source = "semantic_pipeline_v1"
    if semantic_move_record and isinstance(semantic_move_record, dict) and semantic_move_record.get("move_type"):
        move_type = str(semantic_move_record["move_type"])
        candidates, implied, heuristic_trace = semantic_move_to_scene_candidates(
            move_type=move_type,
            pacing_mode=pacing_mode,
            prior_classes=prior_classes,
            player_input=player_input,
            interpreted_move=interpreted_move,
        )
    else:
        selection_source = "legacy_fallback"
        candidates, implied, heuristic_trace = _legacy_keyword_scene_candidates(
            pacing_mode=pacing_mode,
            player_input=player_input,
            interpreted_move=interpreted_move,
            prior_classes=prior_classes,
        )

    scene_fn = select_single_scene_function(candidates, implied_continuity_by_function=implied)
    assert_subdecision_label_in_matrix("scene_function", scene_fn)

    semantic_trace_ref = ""
    if semantic_move_record and isinstance(semantic_move_record.get("interpretation_trace"), list):
        tr = semantic_move_record["interpretation_trace"]
        if tr and isinstance(tr[0], dict) and tr[0].get("detail_code"):
            semantic_trace_ref = str(tr[0].get("detail_code"))[:120]

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
        "semantic_move_trace_ref": semantic_trace_ref,
        "social_state_asymmetry": (social_state_record or {}).get("responder_asymmetry_code")
        if isinstance(social_state_record, dict)
        else None,
    }

    hint = None
    if semantic_move_record and isinstance(semantic_move_record.get("target_actor_hint"), str):
        hint = semantic_move_record["target_actor_hint"]

    if hint and (
        hint.endswith("_reille") or hint.endswith("longstreet") or hint.endswith("vallon")
    ):
        actor = hint
        reason = "semantic_target_actor_hint"
    elif "annette" in text:
        actor = "annette_reille"
        reason = "named_in_player_move"
    elif "alain" in text:
        actor = "alain_reille"
        reason = "named_in_player_move"
    elif "michel" in text or "michael" in text:
        actor = "michel_longstreet"
        reason = "named_in_player_move"
    elif "veronique" in text or "penelope" in text:
        actor = "veronique_vallon"
        reason = "named_in_player_move"
    else:
        actor, reason = _yaml_default_responder(
            yaml_slice=yaml_slice,
            prior_classes=prior_classes,
            scene_id=current_scene_id,
            selected_scene_function=scene_fn,
        )
        if scene_fn == "redirect_blame" and "dignity_injury" in prior_classes:
            actor = "veronique_vallon"
            reason = "pressure_identity_bias:dignity_injury_host_reaction"
        elif scene_fn == "scene_pivot" and "alliance_shift" in implied.values():
            actor = "michel_longstreet"
            reason = "pressure_identity_bias:alliance_shift_reposition"

    responders = [{"actor_id": actor, "reason": reason}]

    return responders, scene_fn, implied, resolution


def build_pacing_and_silence(
    *,
    player_input: str,
    interpreted_move: dict[str, Any],
    module_id: str,
) -> tuple[str, dict[str, Any]]:
    text = f"{player_input} {interpreted_move.get('move_class', '')}".lower()
    intent = str(interpreted_move.get("player_intent") or "").lower()
    if module_id != GOC_MODULE_ID:
        return _finalize_pacing_silence(
            assert_pacing_mode("standard"),
            {
                "mode": assert_silence_brevity_mode("normal"),
                "reason": "non_goc_slice_default",
            },
        )
    off_scope_keywords = (
        "mars",
        "spaceship",
        "lighthouse",
        "dragon",
        "bitcoin",
        "stock market",
        "weather forecast",
        "football match",
        "tax return",
        "election campaign",
        "recipe blog",
    )
    off_scope = any(k in text for k in off_scope_keywords) and "carnage" not in text
    if off_scope:
        return _finalize_pacing_silence(
            assert_pacing_mode("containment"),
            {
                "mode": assert_silence_brevity_mode("normal"),
                "reason": "slice_boundary_containment_move",
            },
        )
    trimmed = player_input.strip()
    words = [w for w in trimmed.replace(".", " ").split() if w]
    thin_fragment = len(trimmed) <= 10 and len(words) <= 2 and "?" not in trimmed
    awkward_pause = (
        "awkward pause" in text
        or "long pause" in text
        or "won't answer" in text
        or "do not answer" in text
    )
    if "thin edge" in text or "one beat" in text or thin_fragment or awkward_pause:
        if "silent" in text or "say nothing" in text or awkward_pause:
            return _finalize_pacing_silence(
                assert_pacing_mode("thin_edge"),
                {
                    "mode": assert_silence_brevity_mode("withheld"),
                    "reason": "thin_edge_plus_withheld",
                },
            )
        return _finalize_pacing_silence(
            assert_pacing_mode("thin_edge"),
            {
                "mode": assert_silence_brevity_mode("brief"),
                "reason": "thin_edge_brevity_pressure",
            },
        )
    if "brief" in text or "short" in text:
        pacing = assert_pacing_mode("compressed")
        silence = {"mode": assert_silence_brevity_mode("brief"), "reason": "player_requested_brevity"}
    elif "silent" in text or "say nothing" in text:
        pacing = assert_pacing_mode("standard")
        silence = {"mode": assert_silence_brevity_mode("withheld"), "reason": "dramatic_silence_move"}
    elif "multi" in text and "pressure" in text:
        pacing = assert_pacing_mode("multi_pressure")
        silence = {"mode": assert_silence_brevity_mode("normal"), "reason": "default_verbal_density"}
    elif ("repair_attempt" in text or "repair" in intent) and "why" in text:
        pacing = assert_pacing_mode("compressed")
        silence = {"mode": assert_silence_brevity_mode("brief"), "reason": "continuity_compact_probe_after_repair"}
    elif "repair" in text and ("truth" in text or "reveal" in text or "secret" in text):
        pacing = assert_pacing_mode("multi_pressure")
        silence = {"mode": assert_silence_brevity_mode("normal"), "reason": "repair_and_exposure_compete"}
    else:
        pacing = assert_pacing_mode("standard")
        silence = {"mode": assert_silence_brevity_mode("normal"), "reason": "default_verbal_density"}
    return _finalize_pacing_silence(pacing, silence)
