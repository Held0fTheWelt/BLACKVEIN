from __future__ import annotations

import json

from ai_stack.contracts.dramatic_irony_contracts import (
    DRAMATIC_IRONY_SCHEMA_VERSION,
    DRAMATIC_IRONY_SOURCE_NPC_PRIVATE_PLAN_SELECTED,
    DRAMATIC_IRONY_SURFACE_MISREAD_REACTION,
)
from ai_stack.contracts.expectation_variation_contracts import (
    EXPECTATION_VARIATION_BOUNDED_REVEAL,
    EXPECTATION_VARIATION_SCHEMA_VERSION,
)
from ai_stack.contracts.genre_awareness_contracts import (
    GENRE_AWARENESS_FAILURE_FORBIDDEN_MARKER,
    GENRE_AWARENESS_SCHEMA_VERSION,
)
from ai_stack.contracts.improvisational_coherence_contracts import (
    IMPROV_FAILURE_SCENE_ANCHOR_MISSING,
    IMPROVISATIONAL_COHERENCE_SCHEMA_VERSION,
)
from ai_stack.contracts.narrative_momentum_contracts import NARRATIVE_MOMENTUM_SCHEMA_VERSION
from ai_stack.contracts.active_listening_contracts import (
    BROAD_NLU_LISTENING_SCHEMA_VERSION,
    CONVERSATIONAL_MEMORY_SCHEMA_VERSION,
    PROMPT_AUTHORITY_SCHEMA_VERSION,
    build_broad_nlu_listening_aspect_record,
    build_conversational_memory_aspect_record,
    build_prompt_authority_aspect_record,
)
from ai_stack.story_runtime.runtime_aspect_ledger import (
    ASPECT_ACTION_RESOLUTION,
    ASPECT_BROAD_NLU_LISTENING,
    ASPECT_CONSEQUENCE_CASCADE,
    ASPECT_CONVERSATIONAL_MEMORY,
    ASPECT_DRAMATIC_IRONY,
    ASPECT_EXPECTATION_VARIATION,
    ASPECT_GENRE_AWARENESS,
    ASPECT_IMPROVISATIONAL_COHERENCE,
    ASPECT_INPUT,
    ASPECT_KEYS,
    ASPECT_META_NARRATIVE_AWARENESS,
    ASPECT_NARRATIVE_MOMENTUM,
    ASPECT_NPC_AGENCY,
    ASPECT_PACING_RHYTHM,
    ASPECT_PROMPT_AUTHORITY,
    ASPECT_RELATIONSHIP_STATE,
    ASPECT_SCENE_ENERGY,
    ASPECT_SENSORY_CONTEXT,
    ASPECT_SOCIAL_PRESSURE,
    ASPECT_SYMBOLIC_OBJECT_RESONANCE,
    ASPECT_TEMPORAL_CONTROL,
    ASPECT_TONAL_CONSISTENCY,
    build_runtime_intelligence_projection,
    initialize_runtime_aspect_ledger,
    set_aspect_record,
    stable_ledger_json,
)
from ai_stack.contracts.scene_energy_contracts import SCENE_ENERGY_FAILURE_CODES
from ai_stack.contracts.pacing_rhythm_contracts import PACING_RHYTHM_FAILURE_CODES
from ai_stack.contracts.sensory_context_contracts import (
    SENSORY_CONTEXT_FAILURE_CODES,
    SENSORY_CONTEXT_SCHEMA_VERSION,
)
from ai_stack.contracts.symbolic_object_resonance_contracts import (
    SYMBOLIC_OBJECT_RESONANCE_SCHEMA_VERSION,
)
from ai_stack.contracts.temporal_control_contracts import TEMPORAL_CONTROL_SCHEMA_VERSION
from ai_stack.contracts.tonal_consistency_contracts import TONAL_CONSISTENCY_SCHEMA_VERSION


def _scene_energy_missing_pressure_code() -> str:
    for code in SCENE_ENERGY_FAILURE_CODES:
        if code.endswith("missing_required_pressure"):
            return code
    raise AssertionError("scene_energy_contract_missing_pressure_failure_code")


def _pacing_rhythm_density_code() -> str:
    for code in PACING_RHYTHM_FAILURE_CODES:
        if code.endswith("visible_density_exceeded"):
            return code
    raise AssertionError("pacing_rhythm_contract_missing_density_failure_code")


def _sensory_context_missing_layer_code() -> str:
    for code in SENSORY_CONTEXT_FAILURE_CODES:
        if code.endswith("missing_required_layer"):
            return code
    raise AssertionError("sensory_context_contract_missing_layer_failure_code")


def test_runtime_aspect_ledger_serializes_stably() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s1",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Ich nehme ein Bier aus dem Kuehlschrank",
        input_kind="action",
        turn_id="t1",
        trace_id="trace1",
    )

    first = stable_ledger_json(ledger)
    second = stable_ledger_json(json.loads(first))

    assert first == second
    parsed = json.loads(first)
    assert parsed["schema_version"] == "turn_aspect_ledger.v1"
    assert parsed["record_version"] == "runtime_aspect_ledger.v1"
    assert list(parsed["turn_aspect_ledger"].keys()) == sorted(ASPECT_KEYS)
    assert parsed["turn_aspect_ledger"][ASPECT_INPUT]["status"] == "passed"


def test_opening_marks_player_action_as_not_applicable() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s1",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )

    action = ledger["turn_aspect_ledger"][ASPECT_ACTION_RESOLUTION]
    assert action["applicable"] is False
    assert action["status"] == "not_applicable"
    assert action["reasons"] == ["opening_turn_not_player_action_evidence_lane"]


def test_runtime_projection_exposes_active_listening_authority_aspects() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s1",
        module_id="god_of_carnage",
        turn_number=2,
        turn_kind="player",
        raw_player_input="Ich frage Annette nach der Wahrheit.",
    )
    broad_nlu = {
        "schema_version": BROAD_NLU_LISTENING_SCHEMA_VERSION,
        "primary_discourse_act": "question",
        "player_input_kind": "question",
        "confidence": 0.88,
        "ambiguity_codes": [],
        "repair_prompt_recommended": False,
        "response_expectation": "npc_response",
        "target_actor_refs": ["annette_reille"],
        "object_refs": [],
        "source_refs": ["interpreted_input.kind", "semantic_move_record"],
        "raw_player_input_included": False,
    }
    memory = {
        "schema_version": CONVERSATIONAL_MEMORY_SCHEMA_VERSION,
        "memory_present": True,
        "bounded": True,
        "context_line_count": 1,
        "selected_tiers": ["session"],
        "selected_memory_ref_ids": ["memory:session:1"],
        "source_refs": ["hierarchical_memory_context"],
        "raw_player_input_included": False,
        "raw_prompt_included": False,
    }
    authority = {
        "schema_version": PROMPT_AUTHORITY_SCHEMA_VERSION,
        "authority_mode": "model_visible_generation_constraints",
        "authoritative_sections": [
            "player_intent_surface",
            "broad_nlu_listening",
            "conversational_memory",
        ],
        "source_refs": [
            "interpreted_input",
            "runtime_intelligence_projection.capability_selection",
        ],
        "selected_capabilities": ["player_intent_inference"],
        "selected_memory_ref_ids": ["memory:session:1"],
        "prompt_authority_applied_to_packet": True,
        "commit_gate_changed": False,
        "readiness_gate_changed": False,
        "validation_outcome_changed": False,
    }
    ledger = set_aspect_record(
        ledger,
        ASPECT_BROAD_NLU_LISTENING,
        build_broad_nlu_listening_aspect_record(broad_nlu),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_CONVERSATIONAL_MEMORY,
        build_conversational_memory_aspect_record(memory),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_PROMPT_AUTHORITY,
        build_prompt_authority_aspect_record(authority),
    )

    projection = build_runtime_intelligence_projection(ledger)

    assert projection[ASPECT_BROAD_NLU_LISTENING]["schema_version"] == (
        BROAD_NLU_LISTENING_SCHEMA_VERSION
    )
    assert projection[ASPECT_BROAD_NLU_LISTENING]["primary_discourse_act"] == "question"
    assert projection[ASPECT_BROAD_NLU_LISTENING]["raw_player_input_included"] is False
    assert projection[ASPECT_BROAD_NLU_LISTENING]["contract_pass"] is True
    assert projection[ASPECT_CONVERSATIONAL_MEMORY]["schema_version"] == (
        CONVERSATIONAL_MEMORY_SCHEMA_VERSION
    )
    assert projection[ASPECT_CONVERSATIONAL_MEMORY]["selected_memory_ref_ids"] == [
        "memory:session:1"
    ]
    assert projection[ASPECT_CONVERSATIONAL_MEMORY]["bounded"] is True
    assert projection[ASPECT_PROMPT_AUTHORITY]["schema_version"] == (
        PROMPT_AUTHORITY_SCHEMA_VERSION
    )
    assert "broad_nlu_listening" in projection[ASPECT_PROMPT_AUTHORITY][
        "authoritative_sections"
    ]
    assert projection[ASPECT_PROMPT_AUTHORITY]["commit_gate_changed"] is False
    assert projection[ASPECT_PROMPT_AUTHORITY]["validation_outcome_changed"] is False


def test_runtime_projection_exposes_npc_agency_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s1",
        module_id="god_of_carnage",
        turn_number=2,
        turn_kind="player",
        raw_player_input="Ich widerspreche.",
    )
    expected_actual = {
        "planned_actor_ids": ["npc_primary", "npc_secondary"],
        "realized_actor_ids": ["npc_primary"],
        "missing_required_actor_ids": ["npc_secondary"],
        "error_codes": ["npc_initiative_missing_required"],
        "multi_npc_initiative_realized": False,
        "not_full_multi_agent_simulation": True,
        "contract_status": "partial_runtime_projection",
        "long_horizon_state_present": True,
        "intention_threads_active": 2,
        "private_plan_resolution_present": True,
        "private_plan_visibility_respected": True,
        "selected_private_plan_ids": ["npc_primary:private_plan:2"],
    }
    ledger = set_aspect_record(
        ledger,
        ASPECT_NPC_AGENCY,
        {
            "applicable": True,
            "status": "failed",
            "expected": {
                "contract_status": expected_actual["contract_status"],
                "not_full_multi_agent_simulation": True,
            },
            "actual": expected_actual,
            "reasons": expected_actual["error_codes"],
            "failure_class": "recoverable_dramatic_failure",
            "failure_reason": expected_actual["error_codes"][0],
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    npc_agency = projection[ASPECT_NPC_AGENCY]
    assert npc_agency["contract_status"] == expected_actual["contract_status"]
    assert npc_agency["planned_actor_ids"] == expected_actual["planned_actor_ids"]
    assert npc_agency["realized_actor_ids"] == expected_actual["realized_actor_ids"]
    assert npc_agency["missing_required_actor_ids"] == expected_actual["missing_required_actor_ids"]
    assert npc_agency["error_codes"] == expected_actual["error_codes"]
    assert npc_agency["not_full_multi_agent_simulation"] is expected_actual["not_full_multi_agent_simulation"]
    assert npc_agency["long_horizon_state_present"] is True
    assert npc_agency["intention_threads_active"] == expected_actual["intention_threads_active"]
    assert npc_agency["private_plan_resolution_present"] is True
    assert npc_agency["private_plan_visibility_respected"] is True
    assert npc_agency["selected_private_plan_ids"] == expected_actual["selected_private_plan_ids"]


def test_runtime_projection_exposes_dramatic_irony_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s1",
        module_id="god_of_carnage",
        turn_number=2,
        turn_kind="player",
        raw_player_input="Ich widerspreche.",
    )
    selected = {
        "selected_opportunity_ids": ["fact:runtime:selected:unknown_to:actor_b"],
        "selected_fact_ids": ["fact:runtime:selected"],
    }
    actual = {
        "status": "selected",
        "fact_count": len(selected["selected_fact_ids"]),
        "opportunity_count": len(selected["selected_opportunity_ids"]),
        "selected_opportunity_count": len(selected["selected_opportunity_ids"]),
        "realization_status": "realized",
        "realized_opportunity_ids": selected["selected_opportunity_ids"],
        "leak_blocked": False,
        "violation_codes": [],
        "contract_pass": True,
    }
    ledger = set_aspect_record(
        ledger,
        ASPECT_DRAMATIC_IRONY,
        {
            "applicable": True,
            "status": "passed",
            "expected": {
                "schema_version": DRAMATIC_IRONY_SCHEMA_VERSION,
                "policy_present": True,
                "policy_enabled": True,
                "allowed_sources": [DRAMATIC_IRONY_SOURCE_NPC_PRIVATE_PLAN_SELECTED],
                "allowed_surface_modes": [DRAMATIC_IRONY_SURFACE_MISREAD_REACTION],
                "direct_reveal_allowed": False,
            },
            "selected": selected,
            "actual": actual,
            "source": "validator",
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    dramatic_irony = projection[ASPECT_DRAMATIC_IRONY]
    assert dramatic_irony["policy_present"] is True
    assert dramatic_irony["selected_opportunity_ids"] == selected["selected_opportunity_ids"]
    assert dramatic_irony["selected_fact_ids"] == selected["selected_fact_ids"]
    assert dramatic_irony["opportunity_count"] == actual["opportunity_count"]
    assert dramatic_irony["realization_status"] == actual["realization_status"]
    assert dramatic_irony["leak_blocked"] is False
    assert dramatic_irony["contract_pass"] is True


def test_runtime_projection_exposes_scene_energy_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s1",
        module_id="god_of_carnage",
        turn_number=2,
        turn_kind="player",
        raw_player_input="Ich bleibe am Tisch.",
    )
    target = {
        "schema_version": "scene_energy.v1",
        "energy_level": "rising",
        "pressure_vector": "social",
        "tempo": "accelerating",
        "density": "layered",
        "volatility": "unstable",
        "target_transition": "rise",
        "minimum_actor_response_count": 2,
        "maximum_visible_density_count": 8,
        "forbidden_transitions": [],
        "source_evidence": [],
        "rationale_codes": [],
    }
    missing_pressure_code = _scene_energy_missing_pressure_code()
    ledger = set_aspect_record(
        ledger,
        ASPECT_SCENE_ENERGY,
        {
            "applicable": True,
            "status": "failed",
            "expected": {
                "schema_version": target["schema_version"],
                "policy_present": True,
                "policy_enabled": True,
            },
            "selected": {
                "target": target,
                "transition": {
                    "schema_version": "scene_energy.v1",
                    "from_energy_level": None,
                    "to_energy_level": target["energy_level"],
                    "transition_intent": target["target_transition"],
                    "allowed": True,
                    "reason_codes": [],
                },
            },
            "actual": {
                "actual_actor_response_count": 1,
                "visible_density_count": 2,
                "transition_allowed": True,
                "contract_pass": False,
                "failure_codes": [missing_pressure_code],
            },
            "reasons": [missing_pressure_code],
            "failure_class": "recoverable_dramatic_failure",
            "failure_reason": missing_pressure_code,
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    scene_energy = projection[ASPECT_SCENE_ENERGY]
    assert scene_energy["schema_version"] == target["schema_version"]
    assert scene_energy["energy_level"] == target["energy_level"]
    assert scene_energy["pressure_vector"] == target["pressure_vector"]
    assert scene_energy["target_transition"] == target["target_transition"]
    assert scene_energy["minimum_actor_response_count"] == target["minimum_actor_response_count"]
    assert scene_energy["actual_actor_response_count"] == 1
    assert scene_energy["failure_codes"] == [missing_pressure_code]
    assert scene_energy["contract_pass"] is False


def test_runtime_projection_exposes_pacing_rhythm_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-rhythm",
        module_id="god_of_carnage",
        turn_number=2,
        turn_kind="player",
        raw_player_input="Ich bleibe am Tisch.",
    )
    target = {
        "schema_version": "pacing_rhythm.v1",
        "cadence": "press",
        "tempo_arc": "accelerating",
        "response_shape": "exchange",
        "turn_change_policy": "prefer_actor_turn_change",
        "min_visible_blocks": 1,
        "max_visible_blocks": 3,
        "min_actor_turns": 1,
        "max_actor_turns": 3,
        "requires_pause": False,
        "blocks_forced_speech": False,
        "source_evidence": [],
        "rationale_codes": [],
    }
    density_code = _pacing_rhythm_density_code()
    ledger = set_aspect_record(
        ledger,
        ASPECT_PACING_RHYTHM,
        {
            "applicable": True,
            "status": "failed",
            "expected": {
                "schema_version": target["schema_version"],
                "policy_present": True,
                "policy_enabled": True,
            },
            "selected": {"target": target},
            "actual": {
                "visible_block_count": 5,
                "actor_turn_count": 1,
                "contract_pass": False,
                "failure_codes": [density_code],
            },
            "reasons": [density_code],
            "failure_class": "recoverable_dramatic_failure",
            "failure_reason": density_code,
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    rhythm = projection[ASPECT_PACING_RHYTHM]
    assert rhythm["schema_version"] == target["schema_version"]
    assert rhythm["cadence"] == target["cadence"]
    assert rhythm["response_shape"] == target["response_shape"]
    assert rhythm["max_visible_blocks"] == target["max_visible_blocks"]
    assert rhythm["visible_block_count"] == 5
    assert rhythm["failure_codes"] == [density_code]
    assert rhythm["contract_pass"] is False


def test_runtime_projection_exposes_sensory_context_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-sensory",
        module_id="god_of_carnage",
        turn_number=2,
        turn_kind="player",
        raw_player_input="Ich sehe zum Fenster.",
    )
    layer = {
        "layer_id": "object:window:perception",
        "layer_kind": "object_perception",
        "source": "scene_affordances",
        "source_field": "objects.window.perception_detail.de",
        "source_ref": "scene_affordances.objects.window.perception_detail",
        "language": "de",
        "text": "canonical text loaded by sensory context target",
        "required": True,
    }
    target = {
        "schema_version": SENSORY_CONTEXT_SCHEMA_VERSION,
        "intensity": "medium",
        "location_id": "living_room",
        "object_id": "window",
        "mood_key": "mid_tension",
        "selected_layers": [layer],
        "required_layer_ids": [layer["layer_id"]],
        "min_layers_per_turn": 1,
        "max_layers_per_turn": 3,
        "require_structured_events": True,
        "source_evidence": [],
        "rationale_codes": [],
    }
    missing_code = _sensory_context_missing_layer_code()
    ledger = set_aspect_record(
        ledger,
        ASPECT_SENSORY_CONTEXT,
        {
            "applicable": True,
            "status": "failed",
            "expected": {
                "schema_version": SENSORY_CONTEXT_SCHEMA_VERSION,
                "policy_present": True,
                "policy_enabled": True,
            },
            "selected": {
                "target": target,
                "selected_layer_ids": [layer["layer_id"]],
                "required_layer_ids": [layer["layer_id"]],
                "intensity": target["intensity"],
                "location_id": target["location_id"],
                "object_id": target["object_id"],
            },
            "actual": {
                "event_count": 0,
                "realized_layer_ids": [],
                "required_layer_ids": [layer["layer_id"]],
                "contract_pass": False,
                "failure_codes": [missing_code],
            },
            "reasons": [missing_code],
            "failure_class": "recoverable_dramatic_failure",
            "failure_reason": missing_code,
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    sensory = projection[ASPECT_SENSORY_CONTEXT]
    assert sensory["schema_version"] == SENSORY_CONTEXT_SCHEMA_VERSION
    assert sensory["intensity"] == target["intensity"]
    assert sensory["location_id"] == target["location_id"]
    assert sensory["object_id"] == target["object_id"]
    assert sensory["selected_layer_ids"] == [layer["layer_id"]]
    assert sensory["event_count"] == 0
    assert sensory["failure_codes"] == [missing_code]
    assert sensory["contract_pass"] is False


def test_runtime_projection_exposes_tonal_consistency_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-tone",
        module_id="example_module",
        turn_number=2,
        turn_kind="player",
        raw_player_input="structured input",
    )
    failure_code = "tonal_consistency_required_dimension_missing"
    ledger = set_aspect_record(
        ledger,
        ASPECT_TONAL_CONSISTENCY,
        {
            "applicable": True,
            "status": "partial",
            "expected": {
                "schema_version": TONAL_CONSISTENCY_SCHEMA_VERSION,
                "policy_present": True,
                "policy_enabled": True,
                "require_structured_classification": True,
                "drift_behavior": "diagnostic",
            },
            "selected": {
                "profile_id": "profile_alpha",
                "target_dimension_ids": ["dimension_alpha", "dimension_beta"],
                "required_dimension_ids": ["dimension_alpha"],
                "allowed_registers": ["register_alpha"],
                "forbidden_marker_classes": ["marker_class_alpha"],
                "scene_function": "scene_function_alpha",
                "pressure_band": "high",
            },
            "actual": {
                "structured_classification_present": True,
                "realized_dimension_ids": [],
                "missing_required_dimension_ids": ["dimension_alpha"],
                "required_dimension_present_count": 0,
                "register_label": "register_alpha",
                "genre_label": "register_alpha",
                "forbidden_marker_hits": {"marker_class_alpha": 1},
                "marker_hit_count": 1,
                "contract_pass": False,
                "failure_codes": [failure_code],
            },
            "reasons": [failure_code],
            "failure_class": "degradation_only",
            "failure_reason": failure_code,
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    tonal = projection[ASPECT_TONAL_CONSISTENCY]
    assert tonal["schema_version"] == TONAL_CONSISTENCY_SCHEMA_VERSION
    assert tonal["policy_enabled"] is True
    assert tonal["profile_id"] == "profile_alpha"
    assert tonal["required_dimension_ids"] == ["dimension_alpha"]
    assert tonal["realized_dimension_ids"] == []
    assert tonal["forbidden_marker_classes"] == ["marker_class_alpha"]
    assert tonal["forbidden_marker_hits"] == {"marker_class_alpha": 1}
    assert tonal["marker_hit_count"] == 1
    assert tonal["contract_pass"] is False
    assert tonal["failure_codes"] == [failure_code]


def test_runtime_projection_exposes_genre_awareness_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-genre",
        module_id="example_module",
        turn_number=2,
        turn_kind="player",
        raw_player_input="structured input",
    )
    target = {
        "schema_version": GENRE_AWARENESS_SCHEMA_VERSION,
        "policy_version": "genre_awareness_policy.v1",
        "policy_enabled": True,
        "commit_impact": "recover",
        "genre_profile_id": "bourgeois_social_drama",
        "selected_registers": ["social_drama"],
        "required_conventions": ["civility_under_pressure"],
        "forbidden_marker_ids": ["fantasy_quest_frame"],
        "require_structured_events": True,
        "max_genre_signals_per_turn": 1,
    }
    ledger = set_aspect_record(
        ledger,
        ASPECT_GENRE_AWARENESS,
        {
            "applicable": True,
            "status": "failed",
            "expected": {
                "schema_version": GENRE_AWARENESS_SCHEMA_VERSION,
                "policy_present": True,
                "policy_enabled": True,
                "commit_impact": "recover",
                "require_structured_events": True,
                "max_genre_signals_per_turn": 1,
            },
            "selected": {
                "target": target,
                "genre_profile_id": target["genre_profile_id"],
                "selected_registers": target["selected_registers"],
                "required_conventions": target["required_conventions"],
            },
            "actual": {
                "structured_events_present": True,
                "event_count": 1,
                "realized_profile_ids": ["bourgeois_social_drama"],
                "realized_registers": ["social_drama"],
                "realized_conventions": [],
                "missing_required_conventions": ["civility_under_pressure"],
                "contract_pass": False,
                "failure_codes": [GENRE_AWARENESS_FAILURE_FORBIDDEN_MARKER],
            },
            "reasons": [GENRE_AWARENESS_FAILURE_FORBIDDEN_MARKER],
            "failure_class": "recoverable_dramatic_failure",
            "failure_reason": GENRE_AWARENESS_FAILURE_FORBIDDEN_MARKER,
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    genre = projection[ASPECT_GENRE_AWARENESS]
    assert genre["schema_version"] == GENRE_AWARENESS_SCHEMA_VERSION
    assert genre["policy_present"] is True
    assert genre["policy_enabled"] is True
    assert genre["genre_profile_id"] == "bourgeois_social_drama"
    assert genre["selected_registers"] == ["social_drama"]
    assert genre["required_conventions"] == ["civility_under_pressure"]
    assert genre["event_count"] == 1
    assert genre["missing_required_conventions"] == ["civility_under_pressure"]
    assert genre["failure_codes"] == [GENRE_AWARENESS_FAILURE_FORBIDDEN_MARKER]
    assert genre["contract_pass"] is False


def test_runtime_projection_exposes_improvisational_coherence_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-improv",
        module_id="god_of_carnage",
        turn_number=2,
        turn_kind="player",
        raw_player_input="Ich will die Szene in einen Streit ueber Schuld drehen.",
    )
    anchor_ref = {
        "source": "scene_plan_record",
        "field": "selected_scene_function",
        "value": "domestic_pressure",
    }
    ledger = set_aspect_record(
        ledger,
        ASPECT_IMPROVISATIONAL_COHERENCE,
        {
            "applicable": True,
            "status": "failed",
            "expected": {
                "schema_version": IMPROVISATIONAL_COHERENCE_SCHEMA_VERSION,
                "policy_present": True,
                "policy_enabled": True,
                "commit_impact": "recover",
                "require_structured_events": True,
                "min_anchor_refs": 1,
            },
            "selected": {
                "contribution_id": "turn_contribution:alpha",
                "contribution_kind": "speech",
                "acceptance_mode": "accept",
                "min_anchor_refs": 1,
                "selected_scene_function": "domestic_pressure",
                "required_anchor_refs": [anchor_ref],
            },
            "actual": {
                "contribution_acknowledged": True,
                "acceptance_mode": "accept",
                "advance_class": "pressure_raise",
                "anchor_refs": [],
                "anchor_sources": [],
                "contract_pass": False,
                "failure_codes": [IMPROV_FAILURE_SCENE_ANCHOR_MISSING],
            },
            "reasons": [IMPROV_FAILURE_SCENE_ANCHOR_MISSING],
            "failure_class": "recoverable_dramatic_failure",
            "failure_reason": IMPROV_FAILURE_SCENE_ANCHOR_MISSING,
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    improv = projection[ASPECT_IMPROVISATIONAL_COHERENCE]
    assert improv["schema_version"] == IMPROVISATIONAL_COHERENCE_SCHEMA_VERSION
    assert improv["policy_enabled"] is True
    assert improv["contribution_id"] == "turn_contribution:alpha"
    assert improv["acceptance_mode"] == "accept"
    assert improv["advance_class"] == "pressure_raise"
    assert improv["min_anchor_refs"] == 1
    assert improv["required_anchor_refs"] == [anchor_ref]
    assert improv["contribution_acknowledged"] is True
    assert improv["contract_pass"] is False
    assert improv["failure_codes"] == [IMPROV_FAILURE_SCENE_ANCHOR_MISSING]


def test_runtime_projection_exposes_expectation_variation_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-expectation",
        module_id="example_module",
        turn_number=2,
        turn_kind="player",
        raw_player_input="structured input",
    )
    setup_ref = {
        "source": "information_disclosure_target",
        "field": "selected_unit_ids",
        "value": "unit_alpha",
    }
    ledger = set_aspect_record(
        ledger,
        ASPECT_EXPECTATION_VARIATION,
        {
            "applicable": True,
            "status": "passed",
            "expected": {
                "schema_version": EXPECTATION_VARIATION_SCHEMA_VERSION,
                "policy_present": True,
                "policy_enabled": True,
                "commit_impact": "recover",
                "require_structured_events": True,
                "max_variation_units_per_turn": 1,
                "cooldown_turns": 1,
                "allowed_variation_types": [EXPECTATION_VARIATION_BOUNDED_REVEAL],
            },
            "selected": {
                "selected_variation_ids": ["expectation_variation:bounded_reveal:unit_alpha"],
                "selected_variation_types": [EXPECTATION_VARIATION_BOUNDED_REVEAL],
                "withheld_variation_ids": [],
                "required_setup_refs": [setup_ref],
                "budget_remaining": 0,
            },
            "actual": {
                "structured_events_present": True,
                "event_count": 1,
                "realized_variation_ids": ["expectation_variation:bounded_reveal:unit_alpha"],
                "realized_variation_types": [EXPECTATION_VARIATION_BOUNDED_REVEAL],
                "budget_used": 1,
                "contract_pass": True,
                "failure_codes": [],
            },
            "source": "validator",
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    variation = projection[ASPECT_EXPECTATION_VARIATION]
    assert variation["schema_version"] == EXPECTATION_VARIATION_SCHEMA_VERSION
    assert variation["policy_present"] is True
    assert variation["selected_variation_types"] == [EXPECTATION_VARIATION_BOUNDED_REVEAL]
    assert variation["required_setup_refs"] == [setup_ref]
    assert variation["realized_variation_ids"] == ["expectation_variation:bounded_reveal:unit_alpha"]
    assert variation["budget_used"] == 1
    assert variation["contract_pass"] is True
    assert variation["failure_codes"] == []


def test_runtime_projection_exposes_narrative_momentum_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-momentum",
        module_id="example_module",
        turn_number=2,
        turn_kind="player",
        raw_player_input="structured input",
    )
    driver_ref = {
        "source": "scene_energy_transition",
        "field": "target_transition",
        "value": "rise",
    }
    ledger = set_aspect_record(
        ledger,
        ASPECT_NARRATIVE_MOMENTUM,
        {
            "applicable": True,
            "status": "passed",
            "expected": {
                "schema_version": NARRATIVE_MOMENTUM_SCHEMA_VERSION,
                "policy_present": True,
                "policy_enabled": True,
                "commit_impact": "recover",
                "require_structured_events": True,
            },
            "selected": {
                "target_state": "building",
                "target_score": 0.6,
                "allowed_next_states": ["building", "driving"],
                "requires_forward_motion": True,
                "release_allowed": False,
                "min_progress_event_count": 1,
                "selected_driver_refs": [driver_ref],
            },
            "actual": {
                "current_state": "building",
                "current_score": 0.6,
                "trend": "rising",
                "velocity": 0.2,
                "transition_allowed": True,
                "structured_events_present": True,
                "event_count": 1,
                "progress_event_count": 1,
                "stall_turn_count": 0,
                "stall_budget_respected": True,
                "source_refs_valid": True,
                "contract_pass": True,
                "failure_codes": [],
            },
            "source": "validator",
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    momentum = projection[ASPECT_NARRATIVE_MOMENTUM]
    assert momentum["schema_version"] == NARRATIVE_MOMENTUM_SCHEMA_VERSION
    assert momentum["policy_present"] is True
    assert momentum["target_state"] == "building"
    assert momentum["current_state"] == "building"
    assert momentum["trend"] == "rising"
    assert momentum["transition_allowed"] is True
    assert momentum["progress_event_count"] == 1
    assert momentum["stall_budget_respected"] is True
    assert momentum["contract_pass"] is True
    assert momentum["failure_codes"] == []


def test_runtime_projection_exposes_symbolic_object_resonance_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-symbolic-object",
        module_id="example_module",
        turn_number=2,
        turn_kind="player",
        raw_player_input="structured input",
    )
    source_ref = {
        "source": "environment_state",
        "field": "salient_object_ids",
        "value": "object_alpha",
    }
    ledger = set_aspect_record(
        ledger,
        ASPECT_SYMBOLIC_OBJECT_RESONANCE,
        {
            "applicable": True,
            "status": "passed",
            "expected": {
                "schema_version": SYMBOLIC_OBJECT_RESONANCE_SCHEMA_VERSION,
                "policy_present": True,
                "policy_enabled": True,
                "commit_impact": "recover",
                "require_structured_events": True,
                "max_symbols_per_turn": 1,
                "allowed_resonance_roles": ["territorial_anchor"],
            },
            "selected": {
                "selected_symbol_ids": ["symbolic_object_resonance:alpha"],
                "selected_object_ids": ["object_alpha"],
                "selected_resonance_roles": ["territorial_anchor"],
                "required_source_refs": [source_ref],
            },
            "actual": {
                "structured_events_present": True,
                "event_count": 1,
                "realized_object_ids": ["object_alpha"],
                "realized_symbol_ids": ["symbolic_object_resonance:alpha"],
                "realized_resonance_roles": ["territorial_anchor"],
                "contract_pass": True,
                "failure_codes": [],
            },
            "source": "validator",
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    symbolic = projection[ASPECT_SYMBOLIC_OBJECT_RESONANCE]
    assert symbolic["schema_version"] == SYMBOLIC_OBJECT_RESONANCE_SCHEMA_VERSION
    assert symbolic["policy_present"] is True
    assert symbolic["policy_enabled"] is True
    assert symbolic["selected_object_ids"] == ["object_alpha"]
    assert symbolic["selected_symbol_ids"] == ["symbolic_object_resonance:alpha"]
    assert symbolic["selected_resonance_roles"] == ["territorial_anchor"]
    assert symbolic["required_source_refs"] == [source_ref]
    assert symbolic["structured_events_present"] is True
    assert symbolic["realized_object_ids"] == ["object_alpha"]
    assert symbolic["realized_symbol_ids"] == ["symbolic_object_resonance:alpha"]
    assert symbolic["contract_pass"] is True
    assert symbolic["failure_codes"] == []


def test_runtime_projection_exposes_temporal_control_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-temporal",
        module_id="example_module",
        turn_number=3,
        turn_kind="player",
        raw_player_input="structured input",
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_TEMPORAL_CONTROL,
        {
            "applicable": True,
            "status": "passed",
            "expected": {
                "schema_version": TEMPORAL_CONTROL_SCHEMA_VERSION,
                "policy_present": True,
                "policy_enabled": True,
                "commit_impact": "recover",
                "require_structured_events": True,
                "allowed_operations": ["recall_committed_past", "resume_present"],
                "max_recalled_turns": 2,
                "max_elapsed_turns": 4,
            },
            "selected": {
                "operation": "recall_committed_past",
                "anchor_turn_id": "turn-current",
                "anchor_turn_number": 3,
                "recalled_turn_ids": ["turn-alpha"],
                "recalled_consequence_ids": ["cons-alpha"],
                "elapsed_turns": 0,
            },
            "actual": {
                "structured_events_present": True,
                "event_count": 1,
                "operation": "recall_committed_past",
                "realized_operations": ["recall_committed_past"],
                "realized_turn_ids": ["turn-alpha"],
                "realized_consequence_ids": ["cons-alpha"],
                "elapsed_turns": 0,
                "contract_pass": True,
                "failure_codes": [],
            },
            "source": "validator",
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    temporal = projection[ASPECT_TEMPORAL_CONTROL]
    assert temporal["schema_version"] == TEMPORAL_CONTROL_SCHEMA_VERSION
    assert temporal["policy_present"] is True
    assert temporal["operation"] == "recall_committed_past"
    assert temporal["recalled_turn_ids"] == ["turn-alpha"]
    assert temporal["recalled_consequence_ids"] == ["cons-alpha"]
    assert temporal["realized_operations"] == ["recall_committed_past"]
    assert temporal["contract_pass"] is True
    assert temporal["failure_codes"] == []


def test_runtime_projection_exposes_social_pressure_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-pressure",
        module_id="god_of_carnage",
        turn_number=2,
        turn_kind="player",
        raw_player_input="Ich bleibe am Tisch.",
    )
    target = {
        "schema_version": "social_pressure.v1",
        "target_score": 0.74,
        "target_band": "high",
        "trend": "rising",
        "pressure_floor": 0.67,
        "requires_visible_pressure": True,
        "release_allowed": False,
        "source_evidence": [],
        "rationale_codes": [],
    }
    ledger = set_aspect_record(
        ledger,
        ASPECT_SOCIAL_PRESSURE,
        {
            "applicable": True,
            "status": "passed",
            "expected": {
                "schema_version": target["schema_version"],
                "policy_present": True,
                "policy_enabled": True,
            },
            "selected": {"target": target},
            "actual": {
                "current_score": 0.74,
                "current_band": "high",
                "trend": "rising",
                "velocity": 0.22,
                "contract_pass": True,
                "failure_codes": [],
            },
            "source": "validator",
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    pressure = projection[ASPECT_SOCIAL_PRESSURE]
    assert pressure["schema_version"] == target["schema_version"]
    assert pressure["target_score"] == target["target_score"]
    assert pressure["target_band"] == target["target_band"]
    assert pressure["current_score"] == 0.74
    assert pressure["current_band"] == "high"
    assert pressure["trend"] == "rising"
    assert pressure["requires_visible_pressure"] is True
    assert pressure["contract_pass"] is True


def test_runtime_projection_exposes_relationship_state_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-relationship",
        module_id="example_module",
        turn_number=2,
        turn_kind="player",
        raw_player_input="structured input",
    )
    target = {
        "schema_version": "relationship_state_machine.v1",
        "target_axis_ids": ["axis_alpha"],
        "target_relationship_ids": ["rel_alpha"],
        "required_transition_codes": ["blame_pressure"],
        "pressure_band": "strained",
        "requires_visible_relationship_beat": True,
        "source_evidence": [],
        "rationale_codes": ["relationship_state_target_from_durable_state"],
    }
    ledger = set_aspect_record(
        ledger,
        ASPECT_RELATIONSHIP_STATE,
        {
            "applicable": True,
            "status": "passed",
            "expected": {
                "schema_version": target["schema_version"],
                "policy_present": True,
                "policy_enabled": True,
            },
            "selected": {"target": target},
            "actual": {
                "pair_count": 1,
                "axis_count": 1,
                "transition_event_count": 1,
                "contract_pass": True,
                "failure_codes": [],
            },
            "source": "validator",
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    relationship = projection[ASPECT_RELATIONSHIP_STATE]
    assert relationship["schema_version"] == target["schema_version"]
    assert relationship["target_axis_ids"] == target["target_axis_ids"]
    assert relationship["target_relationship_ids"] == target["target_relationship_ids"]
    assert relationship["pressure_band"] == "strained"
    assert relationship["requires_visible_relationship_beat"] is True
    assert relationship["pair_count"] == 1
    assert relationship["contract_pass"] is True


def test_runtime_projection_exposes_meta_narrative_awareness_v2_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-meta-v2",
        module_id="example_module",
        turn_number=4,
        turn_kind="player",
        raw_player_input="structured input",
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_META_NARRATIVE_AWARENESS,
        {
            "applicable": True,
            "status": "passed",
            "expected": {
                "schema_version": "meta_narrative_awareness.v2",
                "policy_present": True,
                "policy_enabled": True,
                "opt_in_required": True,
                "allowed_awareness_modes": ["direct_player_address"],
                "allowed_fourth_wall_levels": ["full_fourth_wall"],
            },
            "selected": {
                "active": True,
                "opt_in_enabled": True,
                "awareness_tier": "full",
                "intensity": "full_fourth_wall",
                "trigger_frequency": "frequent",
                "selected_actor_ids": ["veronique"],
                "max_events_per_turn": 2,
                "max_direct_addresses_per_turn": 1,
                "direct_player_address_allowed": True,
                "cross_session_memory_allowed": True,
                "selected_memory_ref_ids": ["mem_return_1"],
                "adaptive_signal_codes": ["meta_narrative_adaptive_memory_context"],
            },
            "actual": {
                "structured_events_present": True,
                "event_count": 1,
                "direct_address_count": 1,
                "realized_actor_ids": ["veronique"],
                "awareness_modes": ["direct_player_address"],
                "fourth_wall_levels": ["full_fourth_wall"],
                "realized_memory_ref_ids": ["mem_return_1"],
                "cross_session_memory_ref_count": 1,
                "contract_pass": True,
                "failure_codes": [],
            },
            "source": "validator",
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    meta = projection[ASPECT_META_NARRATIVE_AWARENESS]
    assert meta["schema_version"] == "meta_narrative_awareness.v2"
    assert meta["awareness_tier"] == "full"
    assert meta["direct_player_address_allowed"] is True
    assert meta["selected_memory_ref_ids"] == ["mem_return_1"]
    assert meta["direct_address_count"] == 1
    assert meta["realized_memory_ref_ids"] == ["mem_return_1"]
    assert meta["contract_pass"] is True


def test_runtime_projection_exposes_consequence_cascade_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-cascade",
        module_id="god_of_carnage",
        turn_number=3,
        turn_kind="player",
        raw_player_input="Ich widerspreche.",
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_CONSEQUENCE_CASCADE,
        {
            "applicable": True,
            "status": "passed",
            "expected": {
                "policy_present": True,
                "policy_enabled": True,
                "max_atoms": 8,
                "max_edges": 8,
                "derived_from_committed_truth": True,
                "mutates_canonical_state": False,
            },
            "selected": {
                "selected_consequence_ids": ["cons_alpha"],
                "selected_edge_ids": ["cascade_edge_alpha"],
                "selected_continuity_classes": ["pressure_alpha"],
                "selected_statuses": ["active"],
            },
            "actual": {
                "cascade_id": "consequence_cascade_alpha",
                "atom_count": 2,
                "edge_count": 1,
                "active_atom_count": 2,
                "graph_item_count": 1,
                "status_counts": {"active": 2},
                "edge_kind_counts": {"carry_forward": 1},
                "continuity_classes": ["pressure_alpha"],
                "contract_pass": True,
                "failure_codes": [],
            },
            "source": "commit",
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    cascade = projection[ASPECT_CONSEQUENCE_CASCADE]
    assert cascade["policy_present"] is True
    assert cascade["cascade_id"] == "consequence_cascade_alpha"
    assert cascade["selected_consequence_ids"] == ["cons_alpha"]
    assert cascade["selected_edge_ids"] == ["cascade_edge_alpha"]
    assert cascade["selected_continuity_classes"] == ["pressure_alpha"]
    assert cascade["atom_count"] == 2
    assert cascade["edge_count"] == 1
    assert cascade["contract_pass"] is True
