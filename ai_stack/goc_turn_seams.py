"""Proposal, validation, commit, visible seams helpers (CANONICAL_TURN_CONTRACT_GOC.md §2)."""

from __future__ import annotations

from typing import Any

from ai_stack.goc_dramatic_alignment import dramatic_alignment_violation, extract_proposed_narrative_text
from ai_stack.goc_frozen_vocab import DIRECTOR_IMMUTABLE_FIELDS, GOC_MODULE_ID, assert_transition_pattern
from ai_stack.goc_yaml_authority import thin_edge_staging_line_from_guidance


def strip_director_overwrites_from_structured_output(
    structured: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Remove immutable director fields from model structured output (§3.6)."""
    if not structured or not isinstance(structured, dict):
        return structured, []
    markers: list[dict[str, Any]] = []
    cleaned = dict(structured)
    for key in DIRECTOR_IMMUTABLE_FIELDS:
        if key in cleaned:
            del cleaned[key]
            markers.append(
                {
                    "marker": "stripped_model_overwrite_attempt",
                    "field": key,
                    "note": "CANONICAL_TURN_CONTRACT_GOC.md §3.6 — model cannot replace director fields.",
                }
            )
    return cleaned, markers


def structured_output_to_proposed_effects(structured: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Map structured output into proposed_state_effects list."""
    if not structured or not isinstance(structured, dict):
        return []
    raw = structured.get("proposed_state_effects")
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if structured.get("effect_type") or structured.get("description"):
        return [
            {
                "effect_type": structured.get("effect_type", "narrative_beat"),
                "description": str(structured.get("description", "")),
            }
        ]
    narr = structured.get("narrative_response")
    if isinstance(narr, str) and narr.strip():
        return [
            {
                "effect_type": "narrative_proposal",
                "description": narr.strip()[:4096],
            }
        ]
    return []


def run_validation_seam(
    *,
    module_id: str,
    proposed_state_effects: list[dict[str, Any]],
    generation: dict[str, Any],
    director_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit validation_outcome — no player text (CANONICAL_TURN_CONTRACT_GOC.md §2.1)."""
    if module_id != GOC_MODULE_ID:
        return {
            "status": "waived",
            "reason": "non_goc_vertical_slice",
        }
    success = generation.get("success")
    if success is False or generation.get("error"):
        return {
            "status": "rejected",
            "reason": "model_generation_failed",
        }
    for eff in proposed_state_effects:
        if not isinstance(eff, dict):
            return {"status": "rejected", "reason": "malformed_proposed_effect"}
        if "description" not in eff and "effect_type" not in eff:
            return {"status": "rejected", "reason": "incomplete_proposed_effect"}

    ctx = director_context if isinstance(director_context, dict) else {}
    narr = extract_proposed_narrative_text(proposed_state_effects)
    viol = dramatic_alignment_violation(
        selected_scene_function=str(ctx.get("selected_scene_function") or "establish_pressure"),
        pacing_mode=str(ctx.get("pacing_mode") or "standard"),
        silence_brevity_decision=ctx.get("silence_brevity_decision")
        if isinstance(ctx.get("silence_brevity_decision"), dict)
        else None,
        proposed_narrative=narr,
    )
    if viol:
        return {
            "status": "rejected",
            "reason": viol,
            "dramatic_quality_gate": "alignment_reject",
        }
    return {
        "status": "approved",
        "reason": "goc_default_validator_pass",
    }


def run_commit_seam(
    *,
    module_id: str,
    validation_outcome: dict[str, Any],
    proposed_state_effects: list[dict[str, Any]],
) -> dict[str, Any]:
    if validation_outcome.get("status") != "approved":
        return {"committed_effects": [], "commit_applied": False}
    if module_id != GOC_MODULE_ID:
        return {"committed_effects": [], "commit_applied": False}
    return {
        "committed_effects": list(proposed_state_effects),
        "commit_applied": bool(proposed_state_effects),
    }


def run_visible_render(
    *,
    module_id: str,
    committed_result: dict[str, Any],
    validation_outcome: dict[str, Any],
    generation: dict[str, Any],
    transition_pattern: str,
    render_context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Build visible_output_bundle aligned with committed truth (§2.2–§2.3)."""
    _ = transition_pattern  # reserved for future bundle tone selection
    content = str(generation.get("content") or generation.get("text") or "").strip()
    if not content and isinstance(generation.get("metadata"), dict):
        meta = generation["metadata"]
        if isinstance(meta.get("raw_content"), str):
            content = meta["raw_content"].strip()

    markers: list[str] = []
    approved = validation_outcome.get("status") == "approved"
    committed = committed_result.get("committed_effects") or []
    has_commit = bool(committed) and committed_result.get("commit_applied")
    rc = render_context if isinstance(render_context, dict) else {}
    pacing_mode = str(rc.get("pacing_mode") or "")
    silence_dec = rc.get("silence_brevity_decision") if isinstance(rc.get("silence_brevity_decision"), dict) else {}
    scene_id = str(rc.get("current_scene_id") or "")
    scene_guidance = rc.get("scene_guidance") if isinstance(rc.get("scene_guidance"), dict) else {}
    prop_excerpt = str(rc.get("proposed_narrative_excerpt") or "").strip()
    profile = rc.get("character_profile_snippet") if isinstance(rc.get("character_profile_snippet"), dict) else {}
    guidance_snips = rc.get("scene_guidance_snippets") if isinstance(rc.get("scene_guidance_snippets"), dict) else {}

    if module_id != GOC_MODULE_ID:
        bundle = {
            "gm_narration": [content] if content else [],
            "spoken_lines": [],
        }
        markers.append("non_factual_staging")
        return bundle, markers

    if has_commit and approved:
        supplement = ""
        if scene_guidance and scene_id and (
            pacing_mode == "thin_edge" or silence_dec.get("mode") == "withheld"
        ):
            supplement = thin_edge_staging_line_from_guidance(scene_guidance=scene_guidance, scene_id=scene_id)
        gm_lines: list[str] = []
        if content:
            gm_lines.append(content)
        narr_len = len(prop_excerpt) if prop_excerpt else len(content)
        if supplement and (narr_len < 50 or silence_dec.get("mode") == "withheld"):
            gm_lines.append(f"(Director staging — phase context) {supplement}")
        role = str(profile.get("formal_role") or profile.get("role") or "").strip()
        tone = str(profile.get("baseline_tone") or "").strip()
        phase_arc = str(profile.get("phase_arc_hint") or "").strip()
        ai_hint = str(guidance_snips.get("ai_guidance_hint") or "").strip()
        if role and (silence_dec.get("mode") == "withheld" or pacing_mode in ("compressed", "multi_pressure")):
            gm_lines.append(f"(Director register — responder role) {role}")
        if tone and pacing_mode in ("thin_edge", "multi_pressure"):
            gm_lines.append(f"(Director register — tonal pressure) {tone}")
        if phase_arc and narr_len < 90:
            gm_lines.append(f"(Director staging — character pressure arc) {phase_arc}")
        if ai_hint and (narr_len < 80 or pacing_mode == "multi_pressure"):
            gm_lines.append(f"(Director staging — phase pressure cue) {ai_hint}")
        if not gm_lines:
            gm_lines = ["(scene continues — committed effects applied.)"]
        bundle = {
            "gm_narration": gm_lines,
            "spoken_lines": [],
        }
        markers.append("truth_aligned")
        used_supplement = bool(
            supplement and (narr_len < 50 or silence_dec.get("mode") == "withheld")
        )
        if used_supplement:
            markers.append("bounded_ambiguity")
        return bundle, markers

    # No commit: truth-safe staging (GATE_SCORING_POLICY_GOC.md §6.3).
    safe = content if content else "(Preview staging — no committed world-state change.)"
    bundle = {
        "gm_narration": [safe],
        "spoken_lines": [],
    }
    markers.append("non_factual_staging")
    return bundle, markers


def build_diagnostics_refs(
    *,
    graph_diagnostics: dict[str, Any],
    experiment_preview: bool,
    transition_pattern: str,
    gate_hints: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Project operational diagnostics into canonical refs (CANONICAL_TURN_CONTRACT_GOC.md §5)."""
    tp = assert_transition_pattern(transition_pattern)
    refs: list[dict[str, Any]] = [
        {
            "ref_type": "graph_diagnostics_projection",
            "graph_name": graph_diagnostics.get("graph_name"),
            "graph_version": graph_diagnostics.get("graph_version"),
            "nodes_executed": graph_diagnostics.get("nodes_executed"),
            "node_outcomes": graph_diagnostics.get("node_outcomes"),
            "fallback_path_taken": graph_diagnostics.get("fallback_path_taken"),
            "execution_health": graph_diagnostics.get("execution_health"),
        },
        {
            "ref_type": "experiment_preview",
            "experiment_preview": experiment_preview,
        },
        {
            "ref_type": "transition_pattern",
            "transition_pattern": tp,
        },
    ]
    if gate_hints:
        refs.append({"ref_type": "gate_review_hints", **gate_hints})
    return refs


def repro_metadata_complete(repro: dict[str, Any]) -> bool:
    """GATE_SCORING_POLICY_GOC.md §5.2 — required fields for operator questions."""
    required = (
        "graph_name",
        "trace_id",
        "selected_model",
        "selected_provider",
        "retrieval_domain",
        "retrieval_profile",
        "model_attempted",
        "model_success",
        "adapter_invocation_mode",
        "graph_path_summary",
    )
    return all(repro.get(k) not in (None, "") for k in required)


_SCENE_FN_TO_CONTINUITY_PRIMARY: dict[str, str] = {
    "reveal_surface": "revealed_fact",
    "redirect_blame": "blame_pressure",
    "escalate_conflict": "situational_pressure",
    "repair_or_stabilize": "repair_attempt",
    "probe_motive": "situational_pressure",
    "establish_pressure": "situational_pressure",
    "withhold_or_evade": "silent_carry",
    "scene_pivot": "refused_cooperation",
}


def build_goc_continuity_impacts_on_commit(
    *,
    module_id: str,
    selected_scene_function: str,
    proposed_state_effects: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Emit one or more frozen continuity classes after a successful commit (bounded, YAML-vocabulary aligned)."""
    if module_id != GOC_MODULE_ID:
        return []
    primary = _SCENE_FN_TO_CONTINUITY_PRIMARY.get(selected_scene_function)
    if not primary:
        primary = "situational_pressure"
    impacts: list[dict[str, Any]] = [
        {"class": primary, "note": f"committed_scene_function:{selected_scene_function}"},
    ]
    blob = " ".join(
        str(e.get("description", "")) for e in proposed_state_effects if isinstance(e, dict)
    ).lower()
    if "blame" in blob and primary != "blame_pressure":
        impacts.append({"class": "blame_pressure", "note": "effect_text_blame_keyword"})
    if ("sorry" in blob or "apolog" in blob) and primary != "repair_attempt":
        impacts.append({"class": "repair_attempt", "note": "effect_text_repair_keyword"})
    return impacts[:2]
