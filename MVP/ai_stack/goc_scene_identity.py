"""
Single owned surface: GoC runtime scene_id → scene_guidance.yaml phase
keys.

See ADR-0003: the mapping here is the **source of truth**; tests verify
consistency against ``scene_guidance.yaml`` and ``scenes.yaml`` phase
ids. Do not duplicate this mapping elsewhere (CI enforces via
``tools/verify_goc_scene_identity_single_source.py``).
"""

from __future__ import annotations

# Default when scene_id is unknown or empty (director staging bias).
GOC_DEFAULT_GUIDANCE_PHASE_KEY: str = "phase_2_moral_negotiation"

# Runtime / slice scene identifiers → top-level keys in direction/scene_guidance.yaml
GOC_SCENE_ID_TO_GUIDANCE_PHASE: dict[str, str] = {
    "courtesy": "phase_1_polite_opening",
    "living_room": "phase_2_moral_negotiation",
    "phase_1": "phase_1_polite_opening",
    "phase_2": "phase_2_moral_negotiation",
    "phase_3": "phase_3_faction_shifts",
    "phase_4": "phase_4_emotional_derailment",
    "phase_5": "phase_5_loss_of_control_escalation_or_collapse",
}

# guidance phase key → escalation_arc sub-key in character_voice.yaml
GUIDANCE_PHASE_TO_ESCALATION_ARC_KEY: dict[str, str] = {
    "phase_1_polite_opening": "phase_1",
    "phase_2_moral_negotiation": "phase_2",
    "phase_3_faction_shifts": "phase_3",
    "phase_4_emotional_derailment": "phase_4",
    "phase_5_loss_of_control_escalation_or_collapse": "phase_5",
}


def guidance_phase_key_for_scene_id(scene_id: str) -> str:
    """Resolve a runtime scene id to a scene_guidance.yaml block key.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        scene_id: ``scene_id`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    return GOC_SCENE_ID_TO_GUIDANCE_PHASE.get(scene_id.strip(), GOC_DEFAULT_GUIDANCE_PHASE_KEY)


def all_expected_guidance_phase_keys() -> frozenset[str]:
    """Phase block keys that must exist in merged scene_guidance.yaml for
    GoC.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        frozenset[str]:
            Returns a value of type ``frozenset[str]``; see the function body for structure, error paths, and sentinels.
    """
    return frozenset(GOC_SCENE_ID_TO_GUIDANCE_PHASE.values())
