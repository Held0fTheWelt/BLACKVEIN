"""
Single owned runtime mapping: GoC runtime scene_id → phase_beat_policy-derived
guidance keys.

See ADR-0003: the mapping here is the **source of truth**; tests verify
consistency against phase_beat_policy-derived phase blocks. Do not duplicate
this mapping elsewhere (CI enforces via
``tools/verify_goc_scene_identity_single_source.py``).
"""

from __future__ import annotations

# Default when scene_id is unknown or empty (director staging bias).
GOC_DEFAULT_GUIDANCE_PHASE_KEY: str = "phase_2_moral_negotiation"

# Runtime / slice scene identifiers → legacy-compatible phase guidance keys.
GOC_SCENE_ID_TO_GUIDANCE_PHASE: dict[str, str] = {
    "courtesy": "phase_1_polite_opening",
    "living_room": "phase_2_moral_negotiation",
    "phase_1": "phase_1_polite_opening",
    "phase_2": "phase_2_moral_negotiation",
    "phase_3": "phase_3_faction_shifts",
    "phase_4": "phase_4_emotional_derailment",
    "phase_5": "phase_5_loss_of_control_escalation_or_collapse",
    "prologue_park_edge": "phase_1_polite_opening",
    "basketball_court_cluster": "phase_1_polite_opening",
    "boys_argument": "phase_1_polite_opening",
    "stick_and_turn": "phase_1_polite_opening",
    "strike_and_aftermath": "phase_1_polite_opening",
    "apartment_threshold": "phase_1_polite_opening",
    "living_room_arrival": "phase_1_polite_opening",
    "selected_role_anchor": "phase_1_polite_opening",
    "first_playable_courtesy_gap": "phase_1_polite_opening",
    "written_statement_negotiation": "phase_1_polite_opening",
    "coffee_and_courtesy": "phase_1_polite_opening",
    "parenting_principles": "phase_2_moral_negotiation",
    "blame_pressure": "phase_2_moral_negotiation",
    "phone_intrusion": "phase_2_moral_negotiation",
    "spouse_alignment_cracks": "phase_3_faction_shifts",
    "hospitality_breakdown": "phase_4_emotional_derailment",
    "exit_attempt": "phase_5_loss_of_control_escalation_or_collapse",
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
    """Resolve a runtime scene id to a phase-policy-derived guidance block key.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        scene_id: ``scene_id`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    return GOC_SCENE_ID_TO_GUIDANCE_PHASE.get(scene_id.strip(), GOC_DEFAULT_GUIDANCE_PHASE_KEY)


def all_expected_guidance_phase_keys() -> frozenset[str]:
    """Phase guidance keys that must be derivable from phase_beat_policy for
    GoC.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        frozenset[str]:
            Returns a value of type ``frozenset[str]``; see the function body for structure, error paths, and sentinels.
    """
    return frozenset(GOC_SCENE_ID_TO_GUIDANCE_PHASE.values())
