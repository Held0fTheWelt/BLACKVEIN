from __future__ import annotations

from ai_stack.active_listening_contracts import (
    BROAD_NLU_LISTENING_SCHEMA_VERSION,
    CONVERSATIONAL_MEMORY_SCHEMA_VERSION,
    PROMPT_AUTHORITY_SCHEMA_VERSION,
    build_broad_nlu_listening_aspect_record,
    build_conversational_memory_aspect_record,
    build_prompt_authority_aspect_record,
    build_prompt_authority_packet,
    derive_broad_nlu_listening,
    derive_conversational_memory_context,
)


def test_broad_nlu_listening_derives_structured_evidence_without_raw_input() -> None:
    evidence = derive_broad_nlu_listening(
        interpreted_input={
            "kind": "speech",
            "player_input_kind": "question",
            "intent": "question_utterance",
            "confidence": 0.91,
            "narrator_response_expected": False,
            "npc_response_expected": True,
            "entities": {
                "target_actor_id": "annette_reille",
                "object_id": "tulips",
            },
        },
        semantic_move_record={
            "move_type": "direct_question",
            "target_actor_hint": "annette_reille",
            "ranked_move_candidates": [{"move_type": "direct_question"}],
        },
    )

    assert evidence["schema_version"] == BROAD_NLU_LISTENING_SCHEMA_VERSION
    assert evidence["primary_discourse_act"] == "question"
    assert evidence["player_input_kind"] == "question"
    assert evidence["response_expectation"] == "npc_response"
    assert evidence["target_actor_refs"] == ["annette_reille"]
    assert evidence["object_refs"] == ["tulips"]
    assert evidence["raw_player_input_included"] is False
    assert evidence["live_or_staging_evidence"] is False

    record = build_broad_nlu_listening_aspect_record(evidence)
    assert record["status"] == "passed"
    assert record["actual"]["contract_pass"] is True


def test_conversational_memory_projects_committed_bounded_refs_only() -> None:
    evidence = derive_conversational_memory_context(
        hierarchical_memory_context={
            "memory_present": True,
            "bounded": True,
            "item_count": 3,
            "available_item_count": 3,
            "omitted_item_count": 0,
            "context_lines": ["Annette remembers the earlier accusation."],
            "projected_tiers": {
                "session": [
                    {"item_id": "memory:session:1"},
                    {"source_canonical_turn_id": "turn:0003"},
                ],
                "cross_session": [{"item_id": "memory:cross:2"}],
            },
        }
    )

    assert evidence["schema_version"] == CONVERSATIONAL_MEMORY_SCHEMA_VERSION
    assert evidence["memory_present"] is True
    assert evidence["bounded"] is True
    assert evidence["selected_tiers"] == ["session", "cross_session"]
    assert evidence["selected_memory_ref_ids"] == [
        "memory:session:1",
        "turn:0003",
        "memory:cross:2",
    ]
    assert evidence["committed_turn_refs_only"] is True
    assert evidence["raw_player_input_included"] is False
    assert evidence["raw_prompt_included"] is False

    record = build_conversational_memory_aspect_record(evidence)
    assert record["status"] == "passed"
    assert record["actual"]["contract_pass"] is True


def test_prompt_authority_declares_sources_without_mutating_gates() -> None:
    broad = derive_broad_nlu_listening(
        interpreted_input={
            "kind": "action",
            "player_input_kind": "action",
            "confidence": 0.84,
            "narrator_response_expected": True,
            "npc_response_expected": False,
        }
    )
    memory = derive_conversational_memory_context(
        hierarchical_memory_context={
            "memory_present": True,
            "bounded": True,
            "projected_tiers": {"session": [{"item_id": "memory:session:1"}]},
        }
    )

    authority = build_prompt_authority_packet(
        capability_selection={
            "selected": ["player_intent_inference", "action_resolution"],
            "observed_only": ["broad_nlu_listening", "conversational_memory"],
        },
        broad_nlu_listening=broad,
        conversational_memory=memory,
        dramatic_generation_packet={"npc_agency_plan": {"selected": []}},
    )

    assert authority["schema_version"] == PROMPT_AUTHORITY_SCHEMA_VERSION
    assert "broad_nlu_listening" in authority["authoritative_sections"]
    assert "conversational_memory" in authority["authoritative_sections"]
    assert "hierarchical_memory_context" in authority["source_refs"]
    assert authority["selected_memory_ref_ids"] == ["memory:session:1"]
    assert "generated_prose_as_validator_oracle" in authority["forbidden_inferences"]
    assert authority["commit_gate_changed"] is False
    assert authority["readiness_gate_changed"] is False
    assert authority["validation_outcome_changed"] is False
    assert authority["live_or_staging_evidence"] is False

    record = build_prompt_authority_aspect_record(authority)
    assert record["status"] == "passed"
    assert record["actual"]["contract_pass"] is True
