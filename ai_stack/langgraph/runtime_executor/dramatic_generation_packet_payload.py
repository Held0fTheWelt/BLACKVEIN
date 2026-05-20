"""Dramatic packet final payload.

Finishes the dramatic generation packet by assembling final packet fields, diagnostics, and routing metadata.
"""
SOURCE_LINES = [
    '            packet["opening_scene_sequence"] = {\n',
    '                "id": knowledge_contract.get("opening_scene_sequence_id"),\n',
    '                "must_establish": knowledge_contract.get("opening_must_establish") or [],\n',
    '                "event_tasks": knowledge_contract.get("opening_event_tasks") or [],\n',
    '                "first_playable_scene_phase": knowledge_contract.get("opening_first_playable_scene_phase"),\n',
    '                "role_variant": knowledge_contract.get("selected_role_variant") or {},\n',
    '            }\n',
    '            packet["opening_render_policy"] = knowledge_contract.get("opening_render_policy") or {}\n',
    '    # Add prior_initiative_truth if any initiative fields are present\n',
    '    prior_planner = state.get("prior_planner_truth") if isinstance(state.get("prior_planner_truth"), dict) else {}\n',
    '    _pit = {\n',
    '        "initiative_seizer_id": prior_planner.get("initiative_seizer_id"),\n',
    '        "initiative_loser_id": prior_planner.get("initiative_loser_id"),\n',
    '        "initiative_pressure_label": prior_planner.get("initiative_pressure_label"),\n',
    '        "carry_forward_tension_notes": prior_planner.get("carry_forward_tension_notes"),\n',
    '    }\n',
    '    # Collapse to None when all values are empty/None (avoid prompt noise)\n',
    '    if any(v for v in _pit.values() if v):\n',
    '        packet["prior_initiative_truth"] = _pit\n',
    '    if w5_npc_projection_diagnostics:\n',
    '        packet["w5_npc_projection_diagnostics"] = w5_npc_projection_diagnostics\n',
    '    return packet\n',
]
