"""
Canonical YAML authority for God of Carnage
(VERTICAL_SLICE_CONTRACT_GOC.md §6.1).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from ai_stack.goc_frozen_vocab import GOC_MODULE_ID
from ai_stack.goc_scene_identity import (
    GOC_SCENE_ID_TO_GUIDANCE_PHASE,
    GUIDANCE_PHASE_TO_ESCALATION_ARC_KEY,
    guidance_phase_key_for_scene_id,
)

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


def _repo_root() -> Path:
    """Describe what ``_repo_root`` does in one line (verb-led summary for
    this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        Path:
            Returns a value of type ``Path``; see the function body for structure, error paths, and sentinels.
    """
    return Path(__file__).resolve().parent.parent


def goc_module_yaml_dir() -> Path:
    """``goc_module_yaml_dir`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        Path:
            Returns a value of type ``Path``; see the function body for structure, error paths, and sentinels.
    """
    return _repo_root() / "content" / "modules" / GOC_MODULE_ID


def load_goc_canonical_module_yaml() -> dict[str, Any]:
    """Load authoritative module.yaml for god_of_carnage from the
    repository tree.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    if yaml is None:
        raise RuntimeError("PyYAML is required to load canonical GoC module YAML.")
    path = goc_module_yaml_dir() / "module.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Canonical GoC module.yaml not found at {path}")
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError("module.yaml must parse to a mapping.")
    mid = data.get("module_id")
    if mid != GOC_MODULE_ID:
        raise ValueError(f"module.yaml module_id mismatch: expected {GOC_MODULE_ID!r}, got {mid!r}")
    return data


@lru_cache(maxsize=1)
def cached_goc_yaml_title() -> str:
    """``cached_goc_yaml_title`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    mod = load_goc_canonical_module_yaml()
    title = mod.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Canonical module.yaml must define a non-empty string title.")
    return title.strip()


def _safe_load_yaml_mapping(path: Path) -> dict[str, Any]:
    """``_safe_load_yaml_mapping`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        path: ``path`` (Path); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    if yaml is None:
        raise RuntimeError("PyYAML is required to load canonical GoC module YAML.")
    if not path.is_file():
        return {}
    raw = path.read_text(encoding="utf-8")
    merged: dict[str, Any] = {}
    for doc in yaml.safe_load_all(raw):
        if isinstance(doc, dict):
            merged.update(doc)
    return merged


def load_goc_characters_yaml() -> dict[str, Any]:
    """Load content/modules/god_of_carnage/characters.yaml (canonical
    slice).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    path = goc_module_yaml_dir() / "characters.yaml"
    data = _safe_load_yaml_mapping(path)
    ch = data.get("characters")
    return ch if isinstance(ch, dict) else {}


def load_goc_character_voice_yaml() -> dict[str, Any]:
    """Load direction/character_voice.yaml.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    path = goc_module_yaml_dir() / "direction" / "character_voice.yaml"
    data = _safe_load_yaml_mapping(path)
    ch = data.get("characters")
    return ch if isinstance(ch, dict) else {}


def load_goc_scene_guidance_yaml() -> dict[str, Any]:
    """Load direction/scene_guidance.yaml (multi-document YAML merged).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    path = goc_module_yaml_dir() / "direction" / "scene_guidance.yaml"
    return _safe_load_yaml_mapping(path)


def load_goc_opening_sequence_yaml() -> dict[str, Any]:
    """Load direction/opening_sequence.yaml (session opening handover, ADR-0035)."""
    path = goc_module_yaml_dir() / "direction" / "opening_sequence.yaml"
    return _safe_load_yaml_mapping(path)


def load_goc_scene_phases_yaml() -> dict[str, Any]:
    """Load scenes.yaml phase definitions as canonical runtime law."""
    path = goc_module_yaml_dir() / "scenes.yaml"
    data = _safe_load_yaml_mapping(path)
    phases = data.get("scene_phases")
    return phases if isinstance(phases, dict) else {}


def load_goc_relationships_yaml() -> dict[str, Any]:
    """Load relationships.yaml without dropping pairwise relationship data."""
    path = goc_module_yaml_dir() / "relationships.yaml"
    data = _safe_load_yaml_mapping(path)
    return {
        "relationship_axes": data.get("relationship_axes") if isinstance(data.get("relationship_axes"), dict) else {},
        "relationships": data.get("relationships") if isinstance(data.get("relationships"), dict) else {},
        "stability_constraints": data.get("stability_constraints")
        if isinstance(data.get("stability_constraints"), dict)
        else {},
    }


def load_goc_triggers_yaml() -> dict[str, Any]:
    """Load trigger definitions and recognition strategy."""
    path = goc_module_yaml_dir() / "triggers.yaml"
    data = _safe_load_yaml_mapping(path)
    return {
        "trigger_types": data.get("trigger_types") if isinstance(data.get("trigger_types"), dict) else {},
        "trigger_recognition": data.get("trigger_recognition")
        if isinstance(data.get("trigger_recognition"), dict)
        else {},
        "trigger_state": data.get("trigger_state") if isinstance(data.get("trigger_state"), dict) else {},
    }


def load_goc_transitions_yaml() -> dict[str, Any]:
    """Load phase transition rules and safeguards."""
    path = goc_module_yaml_dir() / "transitions.yaml"
    data = _safe_load_yaml_mapping(path)
    return {
        "phase_transitions": data.get("phase_transitions")
        if isinstance(data.get("phase_transitions"), dict)
        else {},
        "transition_mechanics": data.get("transition_mechanics")
        if isinstance(data.get("transition_mechanics"), dict)
        else {},
        "state_on_transition": data.get("state_on_transition")
        if isinstance(data.get("state_on_transition"), dict)
        else {},
        "transition_safeguards": data.get("transition_safeguards")
        if isinstance(data.get("transition_safeguards"), dict)
        else {},
    }


def load_goc_endings_yaml() -> dict[str, Any]:
    """Load ending definitions."""
    path = goc_module_yaml_dir() / "endings.yaml"
    data = _safe_load_yaml_mapping(path)
    endings = data.get("ending_types")
    return endings if isinstance(endings, dict) else {}


def load_goc_escalation_axes_yaml() -> dict[str, Any]:
    """Load escalation axes and interaction model."""
    path = goc_module_yaml_dir() / "escalation_axes.yaml"
    data = _safe_load_yaml_mapping(path)
    return {
        "escalation_axes": data.get("escalation_axes") if isinstance(data.get("escalation_axes"), dict) else {},
        "interaction_model": data.get("interaction_model") if isinstance(data.get("interaction_model"), dict) else {},
    }


def load_goc_system_prompt_text() -> str:
    """Load the authored GoC system prompt text for bounded excerpts."""
    path = goc_module_yaml_dir() / "direction" / "system_prompt.md"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_goc_yaml_slice_bundle() -> dict[str, Any]:
    """Bundle of YAML-backed slice surfaces used by the director
    (VERTICAL_SLICE_CONTRACT_GOC.md §6).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    relationships = load_goc_relationships_yaml()
    triggers = load_goc_triggers_yaml()
    transitions = load_goc_transitions_yaml()
    escalation = load_goc_escalation_axes_yaml()
    return {
        "characters": load_goc_characters_yaml(),
        "character_voice": load_goc_character_voice_yaml(),
        "scene_guidance": load_goc_scene_guidance_yaml(),
        "opening_sequence": load_goc_opening_sequence_yaml(),
        "scene_phases": load_goc_scene_phases_yaml(),
        "relationship_axes": relationships["relationship_axes"],
        "relationships": relationships["relationships"],
        "stability_constraints": relationships["stability_constraints"],
        "trigger_types": triggers["trigger_types"],
        "trigger_recognition": triggers["trigger_recognition"],
        "trigger_state": triggers["trigger_state"],
        "phase_transitions": transitions["phase_transitions"],
        "transition_mechanics": transitions["transition_mechanics"],
        "state_on_transition": transitions["state_on_transition"],
        "transition_safeguards": transitions["transition_safeguards"],
        "ending_types": load_goc_endings_yaml(),
        "escalation_axes": escalation["escalation_axes"],
        "escalation_interaction_model": escalation["interaction_model"],
        "system_prompt_excerpt": load_goc_system_prompt_text()[:2400],
    }


def clear_goc_yaml_slice_cache() -> None:
    """Describe what ``clear_goc_yaml_slice_cache`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    """
    load_goc_yaml_slice_bundle.cache_clear()


def thin_edge_staging_line_from_guidance(*, scene_guidance: dict[str, Any], scene_id: str) -> str:
    """First line from YAML narrative_context for bounded non-factual
    staging (truth-safe supplement).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        scene_guidance: ``scene_guidance`` (dict[str,
            Any]); meaning follows the type and call sites.
        scene_id: ``scene_id`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    if not scene_guidance:
        return ""
    phase = guidance_phase_key_for_scene_id(scene_id)
    block = scene_guidance.get(phase)
    if not isinstance(block, dict):
        return ""
    nc = block.get("narrative_context")
    if not isinstance(nc, str) or not nc.strip():
        return ""
    first_line = nc.strip().split("\n")[0].strip()
    return first_line[:280]


def scene_assessment_phase_hints(*, scene_guidance: dict[str, Any], scene_id: str) -> dict[str, Any]:
    """Read-only hints from YAML for scene_assessment (not a second truth
    surface).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        scene_guidance: ``scene_guidance`` (dict[str,
            Any]); meaning follows the type and call sites.
        scene_id: ``scene_id`` (str); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    if not scene_guidance:
        return {}
    phase = guidance_phase_key_for_scene_id(scene_id)
    block = scene_guidance.get(phase)
    if not isinstance(block, dict):
        return {"guidance_phase_key": phase}
    title = block.get("title")
    ce = block.get("constraint_enforcement")
    civ = None
    if isinstance(ce, dict):
        civ = ce.get("civility_required")
    return {
        "guidance_phase_key": phase,
        "guidance_phase_title": title if isinstance(title, str) else None,
        "guidance_civility_required": civ,
    }


def scene_guidance_snippets(*, scene_guidance: dict[str, Any], scene_id: str) -> dict[str, str]:
    """Read short operator/render snippets from scene_guidance without
    creating new truth.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        scene_guidance: ``scene_guidance`` (dict[str,
            Any]); meaning follows the type and call sites.
        scene_id: ``scene_id`` (str); meaning follows the type and call sites.
    
    Returns:
        dict[str, str]:
            Returns a value of type ``dict[str, str]``; see the function body for structure, error paths, and sentinels.
    """
    if not scene_guidance:
        return {}
    phase = guidance_phase_key_for_scene_id(scene_id)
    block = scene_guidance.get(phase)
    if not isinstance(block, dict):
        return {"guidance_phase_key": phase}
    out: dict[str, str] = {"guidance_phase_key": phase}
    exit_signal = block.get("exit_signal")
    if isinstance(exit_signal, str) and exit_signal.strip():
        out["exit_signal"] = exit_signal.strip()[:220]
    ai_guidance = block.get("ai_guidance")
    if isinstance(ai_guidance, list):
        for item in ai_guidance:
            if isinstance(item, str) and item.strip():
                out["ai_guidance_hint"] = item.strip()[:220]
                break
    return out


def goc_character_profile_snippet(
    *,
    actor_id: str,
    yaml_slice: dict[str, Any] | None,
    scene_id: str = "",
) -> dict[str, str]:
    """Return short YAML-backed role/voice snippets for responder-specific
    rendering.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        actor_id: ``actor_id`` (str); meaning follows the type and call sites.
        yaml_slice: ``yaml_slice`` (dict[str, Any] |
            None); meaning follows the type and call sites.
        scene_id: ``scene_id`` (str); meaning follows the type and call sites.
    
    Returns:
        dict[str, str]:
            Returns a value of type ``dict[str, str]``; see the function body for structure, error paths, and sentinels.
    """
    if not isinstance(yaml_slice, dict):
        return {}
    actor_key_map = {
        "veronique_vallon": "veronique",
        "michel_longstreet": "michel",
        "annette_reille": "annette",
        "alain_reille": "alain",
    }
    key = actor_key_map.get(actor_id)
    if not key:
        return {}
    chars = yaml_slice.get("characters") if isinstance(yaml_slice.get("characters"), dict) else {}
    voice = yaml_slice.get("character_voice") if isinstance(yaml_slice.get("character_voice"), dict) else {}
    cblock = chars.get(key) if isinstance(chars.get(key), dict) else {}
    vblock = voice.get(key) if isinstance(voice.get(key), dict) else {}
    out: dict[str, str] = {"character_key": key}
    role = cblock.get("role")
    if isinstance(role, str) and role.strip():
        out["role"] = role.strip()[:120]
    baseline = cblock.get("baseline_attitude")
    if isinstance(baseline, str) and baseline.strip():
        out["baseline_attitude"] = baseline.strip()[:180]
    formal_role = vblock.get("formal_role")
    if isinstance(formal_role, str) and formal_role.strip():
        out["formal_role"] = formal_role.strip()[:140]
    baseline_tone = vblock.get("baseline_tone")
    if isinstance(baseline_tone, str) and baseline_tone.strip():
        out["baseline_tone"] = baseline_tone.strip()[:140]
    if scene_id.strip():
        phase_key = guidance_phase_key_for_scene_id(scene_id)
        arc = vblock.get("escalation_arc")
        if isinstance(arc, dict):
            phase_arc_key = GUIDANCE_PHASE_TO_ESCALATION_ARC_KEY.get(phase_key)
            if phase_arc_key:
                arc_text = arc.get(phase_arc_key)
                if isinstance(arc_text, str) and arc_text.strip():
                    out["phase_arc_hint"] = arc_text.strip()[:180]
    return out


def detect_builtin_yaml_title_conflict(
    *,
    host_template_id: str | None,
    host_template_title: str | None,
) -> dict[str, Any] | None:
    """If a secondary builtin template contradicts YAML title, return a
    failure marker payload.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        host_template_id: ``host_template_id`` (str |
            None); meaning follows the type and call sites.
        host_template_title: ``host_template_title`` (str
            | None); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any] | None:
            Returns a value of type ``dict[str, Any] | None``; see the function body for structure, error paths, and sentinels.
    """
    if not host_template_id or host_template_id != "god_of_carnage_solo":
        return None
    if not host_template_title:
        return None
    canonical = cached_goc_yaml_title()
    if host_template_title.strip() == canonical:
        return None
    return {
        "failure_class": "scope_breach",
        "note": "builtins_yaml_title_mismatch",
        "canonical_yaml_title": canonical,
        "host_template_title": host_template_title.strip(),
    }
