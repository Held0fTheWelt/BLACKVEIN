"""Deterministic CharacterMind construction from canonical YAML (no LLM fill)."""

from __future__ import annotations

from typing import Any

from ai_stack.character_mind_contract import CharacterMindRecord, FieldProvenance
from ai_stack.goc_yaml_authority import guidance_phase_key_for_scene_id

_RUNTIME_ACTOR_IDS: dict[str, str] = {
    "veronique": "veronique_vallon",
    "michel": "michel_longstreet",
    "annette": "annette_reille",
    "alain": "alain_reille",
}

_TACTICAL_FROM_FORMAL: dict[str, str] = {
    "host_moral_idealist": "defend_civility_principles",
    "pragmatist_host_spouse": "defuse_and_capital",
    "guest_cynic": "intellectual_pressure",
    "guest_mediator": "de_escalate_and_bridge",
}


def _derive_tactical_posture(formal_role: str) -> tuple[str, str]:
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
) -> list[CharacterMindRecord]:
    """Build mind records for listed character keys (typically primary responder + scene anchors)."""
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
        rid = _RUNTIME_ACTOR_IDS.get(k, k)
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
