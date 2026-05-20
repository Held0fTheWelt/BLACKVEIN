"""
Deterministic CharacterMind construction from canonical YAML (no LLM
fill).
"""

from __future__ import annotations

from typing import Any

from ai_stack.contracts.character_mind_contract import CharacterMindRecord, FieldProvenance
from ai_stack.god_of_carnage_scene_identity import guidance_phase_key_for_scene_id


def resolve_runtime_actor_id(
    character_key: str,
    *,
    yaml_characters: dict[str, Any] | None,
    module_id: str | None = None,
) -> str:
    """Resolve a character key to its canonical runtime actor id.

    Resolution precedence:

    1. Explicit ``actor_id`` / ``runtime_actor_id`` published on the YAML characters row for this
       key.
    2. The character key itself, used only as a last-resort degraded id.

    Modules own their actor ids in content; runtime code does not maintain
    module-specific key-to-actor-id maps.
    """
    k = (character_key or "").lower().strip()
    if not k:
        return character_key or ""
    if isinstance(yaml_characters, dict):
        row = yaml_characters.get(k)
        if isinstance(row, dict):
            rid = row.get("actor_id") or row.get("runtime_actor_id")
            if isinstance(rid, str) and rid.strip():
                return rid.strip()
    del module_id
    return k

_TACTICAL_FROM_FORMAL: dict[str, str] = {
    "host_moral_idealist": "defend_civility_principles",
    "pragmatist_host_spouse": "defuse_and_capital",
    "guest_cynic": "intellectual_pressure",
    "guest_mediator": "de_escalate_and_bridge",
}


def _derive_tactical_posture(formal_role: str) -> tuple[str, str]:
    """Describe what ``_derive_tactical_posture`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        formal_role: ``formal_role`` (str); meaning follows the type and call sites.
    
    Returns:
        tuple[str, str]:
            Returns a value of type ``tuple[str, str]``; see the function body for structure, error paths, and sentinels.
    """
    fr = formal_role.strip().lower() if formal_role else ""
    for key, tact in _TACTICAL_FROM_FORMAL.items():
        if key in fr.replace(",", " ").replace("'", " "):
            return tact, "map_formal_role_to_tactical"
    if "moral" in fr or "ideal" in fr:
        return "defend_civility_principles", "heuristic_moral_lexicon"
    if "pragmat" in fr or "spouse" in fr:
        return "defuse_and_capital", "heuristic_pragmatist_lexicon"
    if "cynic" in fr or "intellectual" in fr:
        return "intellectual_pressure", "heuristic_cynic_lexicon"
    if "mediat" in fr or "conflict" in fr:
        return "de_escalate_and_bridge", "heuristic_mediator_lexicon"
    return "balanced_reactive", "default_tactical"


def _bias_for_phase(phase_key: str) -> tuple[str, str]:
    """``_bias_for_phase`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        phase_key: ``phase_key`` (str); meaning follows the type and call sites.
    
    Returns:
        tuple[str, str]:
            Returns a value of type ``tuple[str, str]``; see the function body for structure, error paths, and sentinels.
    """
    if phase_key == "phase_1_polite_opening":
        return "civility_first", "guidance_phase_derived"
    if phase_key == "phase_3_faction_shifts":
        return "alliance_sensitive", "guidance_phase_derived"
    if "phase_4" in phase_key:
        return "high_arousal", "guidance_phase_derived"
    return "negotiation_default", "guidance_phase_derived"


def build_character_mind_records_for_goc(
    *,
    yaml_slice: dict[str, Any] | None,
    active_character_keys: list[str],
    current_scene_id: str,
    module_id: str | None = None,
) -> list[CharacterMindRecord]:
    """Build mind records for listed character keys (typically primary
    responder + scene anchors).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        yaml_slice: ``yaml_slice`` (dict[str, Any] |
            None); meaning follows the type and call sites.
        active_character_keys: ``active_character_keys`` (list[str]); meaning follows the type and call sites.
        current_scene_id: ``current_scene_id`` (str); meaning follows the type and call sites.
    
    Returns:
        list[CharacterMindRecord]:
            Returns a value of type ``list[CharacterMindRecord]``; see the function body for structure, error paths, and sentinels.
    """
    voice_root: dict[str, Any] = {}
    chars_root: dict[str, Any] = {}
    if yaml_slice:
        if isinstance(yaml_slice.get("character_voice"), dict):
            voice_root = yaml_slice["character_voice"]
        if isinstance(yaml_slice.get("characters"), dict):
            chars_root = yaml_slice["characters"]

    if not isinstance(voice_root, dict):
        voice_root = {}
    if not isinstance(chars_root, dict):
        chars_root = {}

    phase = guidance_phase_key_for_scene_id(current_scene_id or "living_room")
    phase_bias, phase_rule = _bias_for_phase(phase)

    out: list[CharacterMindRecord] = []
    for key in active_character_keys:
        k = key.lower().strip()
        rid = resolve_runtime_actor_id(
            k, yaml_characters=chars_root, module_id=module_id
        )
        vblock = voice_root.get(k) if isinstance(voice_root.get(k), dict) else {}
        cblock = chars_root.get(k) if isinstance(chars_root.get(k), dict) else {}

        formal = ""
        if isinstance(vblock.get("formal_role"), str):
            formal = vblock["formal_role"]
        prov: dict[str, FieldProvenance] = {}

        if formal:
            prov["formal_role_label"] = FieldProvenance(source="authored")
        else:
            formal = str(cblock.get("role") or "")
            if formal:
                prov["formal_role_label"] = FieldProvenance(source="authored_derived", derivation_key="characters_yaml_role")
            else:
                formal = "unknown_role"
                prov["formal_role_label"] = FieldProvenance(source="fallback_default")

        tact, tact_rule = _derive_tactical_posture(formal)
        prov["tactical_posture"] = FieldProvenance(
            source="authored_derived" if tact_rule.startswith("map") or tact_rule.startswith("heuristic") else "fallback_default",
            derivation_key=tact_rule,
        )

        pressure_bias = phase_bias
        prov["pressure_response_bias"] = FieldProvenance(
            source="authored_derived",
            derivation_key=phase_rule,
        )

        out.append(
            CharacterMindRecord(
                character_key=k,
                runtime_actor_id=rid,
                formal_role_label=formal[:512],
                tactical_posture=tact,
                pressure_response_bias=pressure_bias,
                provenance=prov,
            )
        )
    return out
