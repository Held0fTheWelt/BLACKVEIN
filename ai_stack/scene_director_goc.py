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


def build_responder_and_function(
    *,
    player_input: str,
    interpreted_move: dict[str, Any],
    pacing_mode: str,
    prior_continuity_impacts: list[dict[str, Any]] | None = None,
    yaml_slice: dict[str, Any] | None = None,
    current_scene_id: str = "",
) -> tuple[list[dict[str, Any]], str, dict[str, str], dict[str, Any]]:
    """Choose responder set, scene function, implied continuity map, and multi-pressure resolution record."""
    text = f"{player_input} {interpreted_move.get('player_intent', '')}".lower()
    prior_classes = prior_continuity_classes(prior_continuity_impacts)
    implied: dict[str, str] = {}
    candidates: list[str] = []

    if pacing_mode == "containment":
        candidates.append("scene_pivot")
        implied["scene_pivot"] = "refused_cooperation"
    elif pacing_mode == "thin_edge":
        if "silent" in text or "say nothing" in text or "nothing" in text:
            candidates.append("withhold_or_evade")
            implied["withhold_or_evade"] = "silent_carry"
        else:
            candidates.append("establish_pressure")
            implied["establish_pressure"] = "situational_pressure"
    else:
        if "silent" in text or "say nothing" in text:
            candidates.append("withhold_or_evade")
            implied["withhold_or_evade"] = "silent_carry"
        if (
            "humiliat" in text
            or "embarrass" in text
            or "ashamed" in text
            or "ridicule" in text
            or "mock" in text
        ):
            candidates.append("redirect_blame")
            implied["redirect_blame"] = "dignity_injury"
        if (
            "evade" in text
            or "deflect" in text
            or "avoid answering" in text
            or "change subject" in text
        ):
            candidates.append("withhold_or_evade")
            implied["withhold_or_evade"] = "silent_carry"
        if "sorry" in text or "apolog" in text or "repair" in text:
            candidates.append("repair_or_stabilize")
            implied["repair_or_stabilize"] = "repair_attempt"
        if "reveal" in text or "secret" in text or "truth" in text or "admit" in text:
            candidates.append("reveal_surface")
            implied["reveal_surface"] = "revealed_fact"
        if "blame" in text or "fault" in text:
            candidates.append("redirect_blame")
            implied["redirect_blame"] = "blame_pressure"
        if "why" in text or "motive" in text or "reason" in text:
            candidates.append("probe_motive")
            implied["probe_motive"] = "situational_pressure"
        if "escalat" in text or "fight" in text or "angry" in text or "furious" in text or "attack" in text:
            candidates.append("escalate_conflict")
            implied["escalate_conflict"] = "situational_pressure"
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

        if "blame_pressure" in prior_classes and not candidates:
            candidates.append("redirect_blame")
            implied["redirect_blame"] = "blame_pressure"
        if "dignity_injury" in prior_classes and not candidates:
            candidates.append("redirect_blame")
            implied["redirect_blame"] = "dignity_injury"
        if "alliance_shift" in prior_classes and "probe_motive" not in candidates and "why" in text:
            candidates.append("probe_motive")
            implied["probe_motive"] = "alliance_shift"
        if "blame_pressure" in prior_classes and "redirect_blame" not in candidates and "watch" in text:
            candidates.append("redirect_blame")
            implied["redirect_blame"] = "blame_pressure"

        if not candidates:
            candidates.append("establish_pressure")
            implied["establish_pressure"] = "situational_pressure"

    scene_fn = select_single_scene_function(candidates, implied_continuity_by_function=implied)

    resolution: dict[str, Any] = {
        "candidates": list(candidates),
        "implied_continuity_by_function": dict(implied),
        "chosen_scene_function": scene_fn,
        "rationale": (
            "CANONICAL_TURN_CONTRACT_GOC.md section 3.5 — ranked implied continuity obligation "
            f"(carry_forward_classes={prior_classes}); tie-break lexicographic smallest label."
        ),
    }

    if "annette" in text:
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
        # Pressure-specific default nudges preserve character identity under repeated pressure.
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
    if module_id != GOC_MODULE_ID:
        return assert_pacing_mode("standard"), {
            "mode": assert_silence_brevity_mode("normal"),
            "reason": "non_goc_slice_default",
        }
    off_scope = ("mars" in text or "spaceship" in text or "lighthouse" in text or "dragon" in text) and "carnage" not in text
    if off_scope:
        return assert_pacing_mode("containment"), {
            "mode": assert_silence_brevity_mode("normal"),
            "reason": "slice_boundary_containment_move",
        }
    trimmed = player_input.strip()
    words = [w for w in trimmed.replace(".", " ").split() if w]
    thin_fragment = len(trimmed) <= 10 and len(words) <= 2 and "?" not in trimmed
    if "thin edge" in text or "one beat" in text or thin_fragment:
        if "silent" in text or "say nothing" in text:
            return assert_pacing_mode("thin_edge"), {
                "mode": assert_silence_brevity_mode("withheld"),
                "reason": "thin_edge_plus_withheld",
            }
        return assert_pacing_mode("thin_edge"), {
            "mode": assert_silence_brevity_mode("brief"),
            "reason": "thin_edge_brevity_pressure",
        }
    if "brief" in text or "short" in text:
        pacing = assert_pacing_mode("compressed")
        silence = {"mode": assert_silence_brevity_mode("brief"), "reason": "player_requested_brevity"}
    elif "silent" in text or "say nothing" in text:
        pacing = assert_pacing_mode("standard")
        silence = {"mode": assert_silence_brevity_mode("withheld"), "reason": "dramatic_silence_move"}
    elif "multi" in text and "pressure" in text:
        pacing = assert_pacing_mode("multi_pressure")
        silence = {"mode": assert_silence_brevity_mode("normal"), "reason": "default_verbal_density"}
    elif "repair_attempt" in text and "why" in text:
        pacing = assert_pacing_mode("compressed")
        silence = {"mode": assert_silence_brevity_mode("brief"), "reason": "continuity_compact_probe_after_repair"}
    elif "repair" in text and ("truth" in text or "reveal" in text or "secret" in text):
        pacing = assert_pacing_mode("multi_pressure")
        silence = {"mode": assert_silence_brevity_mode("normal"), "reason": "repair_and_exposure_compete"}
    else:
        pacing = assert_pacing_mode("standard")
        silence = {"mode": assert_silence_brevity_mode("normal"), "reason": "default_verbal_density"}
    return pacing, silence
