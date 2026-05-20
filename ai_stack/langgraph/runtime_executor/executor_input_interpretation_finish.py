"""Input interpretation completion.

Finishes input interpretation with normalized runtime-state updates and route decisions for subsequent graph nodes.
"""
SOURCE_LINES = [
    '                reasons=[] if raw_pi or turn_number <= 0 else ["raw_player_input_missing"],\n',
    '                source="runtime",\n',
    '                failure_class=None if raw_pi or turn_number <= 0 else "observability_gap",\n',
    '                failure_reason=None if raw_pi or turn_number <= 0 else "raw_player_input_missing",\n',
    '                missing_field=None if raw_pi or turn_number <= 0 else "raw_player_input",\n',
    '            ),\n',
    '        )\n',
    '        update["turn_aspect_ledger"] = set_aspect_record(\n',
    '            update["turn_aspect_ledger"],\n',
    '            ASPECT_BROAD_NLU_LISTENING,\n',
    '            build_broad_nlu_listening_aspect_record(broad_nlu_listening),\n',
    '        )\n',
    '        if "turn_input_class" not in state or not state.get("turn_input_class"):\n',
    '            update["turn_input_class"] = move_class\n',
    '        return update\n',
]
