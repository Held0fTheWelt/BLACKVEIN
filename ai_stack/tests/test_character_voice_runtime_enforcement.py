"""Runtime voice consistency enforcement from canonical content.

These tests derive enforcement markers from ``character_voice.yaml`` and assert
runtime invariants rather than pinning narrative example prose, per ADR-0039.
"""

from __future__ import annotations

import re

from ai_stack.character_voice_semantic_classifier import SEMANTIC_DIMENSIONS, STOPWORDS
from ai_stack.character_voice_goc import build_character_voice_profiles_for_goc
from ai_stack.character_voice_validation import validate_voice_consistency
from ai_stack.goc_yaml_authority import load_goc_yaml_slice_bundle
from ai_stack.langgraph_runtime_executor import RuntimeTurnGraphExecutor, _build_runtime_aspect_validation
from ai_stack.runtime_aspect_ledger import (
    ASPECT_VALIDATION,
    ASPECT_VOICE_CONSISTENCY,
    initialize_runtime_aspect_ledger,
)

_TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)


def _profiles():
    bundle = load_goc_yaml_slice_bundle()
    profiles = build_character_voice_profiles_for_goc(
        yaml_slice=bundle,
        active_character_keys=["veronique", "michel", "annette", "alain"],
        current_scene_id="living_room",
        module_id="god_of_carnage",
    )
    return bundle, [profile.to_runtime_dict() for profile in profiles]


def _first_forbidden_marker(bundle):
    marker_root = bundle["voice_consistency"]["forbidden_language_markers"]
    assert marker_root, "canonical GoC voice YAML must publish forbidden language markers"
    for category, marker_block in marker_root.items():
        markers = marker_block.get("markers") if isinstance(marker_block, dict) else marker_block
        if markers:
            return str(category), str(markers[0])
    raise AssertionError("canonical GoC voice YAML must publish at least one marker")


def _forbidden_marker_case():
    bundle, profiles = _profiles()
    _category, marker = _first_forbidden_marker(bundle)
    return {
        "schema_version": "runtime_actor_turn_v1",
        "narration_summary": "fixture",
        "spoken_lines": [
            {
                "speaker_id": "annette_reille",
                "text": f"This response uses {marker} as a policy marker.",
            }
        ],
        "action_lines": [],
        "initiative_events": [],
        "state_effects": [],
    }, profiles, bundle


def _semantic_tokens(text):
    return {
        token
        for token in _TOKEN_RE.findall(str(text or "").casefold())
        if len(token) >= 4 and token not in STOPWORDS
    }


def _semantic_profile_fixture_text(profiles, *, source_actor_id, target_actor_id=None):
    source = next(profile for profile in profiles if profile["runtime_actor_id"] == source_actor_id)
    non_source_terms = set()
    for profile in profiles:
        if profile["runtime_actor_id"] == source_actor_id:
            continue
        for text in profile["semantic_profile"].values():
            non_source_terms.update(_semantic_tokens(text))
    selected_terms = []
    for dimension, text in source["semantic_profile"].items():
        terms = sorted(_semantic_tokens(text) - non_source_terms)
        selected_terms.extend(terms[:4])
    assert len(selected_terms) >= 8
    if target_actor_id is not None:
        assert target_actor_id != source_actor_id
    return " ".join(selected_terms)


def _semantic_cross_actor_case():
    bundle, profiles = _profiles()
    source_actor_id = "veronique_vallon"
    target_actor_id = "annette_reille"
    text = _semantic_profile_fixture_text(
        profiles,
        source_actor_id=source_actor_id,
        target_actor_id=target_actor_id,
    )
    return {
        "schema_version": "runtime_actor_turn_v1",
        "narration_summary": "fixture",
        "spoken_lines": [
            {
                "speaker_id": target_actor_id,
                "text": text,
            }
        ],
        "action_lines": [],
        "initiative_events": [],
        "state_effects": [],
    }, profiles, bundle, source_actor_id, target_actor_id


def test_voice_policy_loads_global_consistency_rules_from_canonical_yaml() -> None:
    bundle, profiles = _profiles()

    assert bundle["voice_consistency"]["maintain_consistency"]
    assert bundle["voice_consistency"]["pitfalls_to_avoid"]
    assert bundle["voice_consistency"]["forbidden_language_markers"]
    assert bundle["voice_consistency"]["semantic_classification"]["enabled"] is True
    assert any(profile["pitfalls_to_avoid"] for profile in profiles)
    assert all(set(SEMANTIC_DIMENSIONS).issubset(profile["semantic_profile"]) for profile in profiles)
    assert all(profile["semantic_policy"] for profile in profiles)
    assert all("dialogue_examples" not in profile for profile in profiles)


def test_voice_validator_rejects_policy_declared_forbidden_language_marker() -> None:
    structured, profiles, _bundle = _forbidden_marker_case()

    result = validate_voice_consistency(
        structured_output=structured,
        voice_profiles=profiles,
        validation_mode="schema_plus_semantic",
    ).to_runtime_dict()

    assert result["status"] == "rejected"
    assert result["reason"] == "voice_consistency_drift"
    assert result["blocking_findings"][0]["drift_class"] == "forbidden_language_marker"
    assert result["blocking_findings"][0]["policy_source"] == (
        "character_voice.voice_consistency.forbidden_language_markers"
    )
    assert result["blocking_findings"][0]["expected_profile_actor_id"] == "annette_reille"


def test_voice_validator_schema_only_records_no_runtime_block() -> None:
    structured, profiles, _bundle = _forbidden_marker_case()

    result = validate_voice_consistency(
        structured_output=structured,
        voice_profiles=profiles,
        validation_mode="schema_only",
    ).to_runtime_dict()

    assert result["status"] == "approved"
    assert result["reason"] == "schema_only_voice_validation_skipped"


def test_semantic_voice_classifier_warns_without_blocking_in_schema_plus_semantic() -> None:
    (
        structured,
        profiles,
        _bundle,
        source_actor_id,
        target_actor_id,
    ) = _semantic_cross_actor_case()

    result = validate_voice_consistency(
        structured_output=structured,
        voice_profiles=profiles,
        validation_mode="schema_plus_semantic",
    ).to_runtime_dict()

    assert result["status"] == "approved"
    assert result["semantic_classifications"][0]["best_matching_actor_id"] == source_actor_id
    assert result["semantic_classifications"][0]["expected_profile_actor_id"] == target_actor_id
    assert result["findings"][0]["drift_class"] == "cross_actor_voice_confusion"
    assert result["findings"][0]["severity"] == "warning"
    assert result["blocking_findings"] == []


def test_semantic_voice_classifier_rejects_in_strict_rule_engine() -> None:
    (
        structured,
        profiles,
        _bundle,
        source_actor_id,
        target_actor_id,
    ) = _semantic_cross_actor_case()

    result = validate_voice_consistency(
        structured_output=structured,
        voice_profiles=profiles,
        validation_mode="strict_rule_engine",
    ).to_runtime_dict()

    assert result["status"] == "rejected"
    assert result["blocking_findings"][0]["drift_class"] == "cross_actor_voice_confusion"
    assert result["blocking_findings"][0]["expected_profile_actor_id"] == target_actor_id
    assert result["blocking_findings"][0]["actual_source_actor_id"] == source_actor_id
    assert result["blocking_findings"][0]["policy_source"] == (
        "character_voice.voice_consistency.semantic_classification"
    )


def test_semantic_voice_classifier_accepts_all_canonical_actor_profiles() -> None:
    _bundle, profiles = _profiles()

    for profile in profiles:
        actor_id = profile["runtime_actor_id"]
        structured = {
            "schema_version": "runtime_actor_turn_v1",
            "narration_summary": "fixture",
            "spoken_lines": [
                {
                    "speaker_id": actor_id,
                    "text": _semantic_profile_fixture_text(
                        profiles,
                        source_actor_id=actor_id,
                    ),
                }
            ],
            "action_lines": [],
            "initiative_events": [],
            "state_effects": [],
        }
        result = validate_voice_consistency(
            structured_output=structured,
            voice_profiles=profiles,
            validation_mode="strict_rule_engine",
        ).to_runtime_dict()

        assert result["status"] == "approved"
        assert result["semantic_classifications"][0]["best_matching_actor_id"] == actor_id
        assert result["semantic_classifications"][0]["classification_status"] == "pass"
        assert result["findings"] == []


def test_semantic_voice_classifier_rejects_all_cross_actor_profile_swaps() -> None:
    _bundle, profiles = _profiles()

    for source in profiles:
        for target in profiles:
            source_actor_id = source["runtime_actor_id"]
            target_actor_id = target["runtime_actor_id"]
            if source_actor_id == target_actor_id:
                continue
            structured = {
                "schema_version": "runtime_actor_turn_v1",
                "narration_summary": "fixture",
                "spoken_lines": [
                    {
                        "speaker_id": target_actor_id,
                        "text": _semantic_profile_fixture_text(
                            profiles,
                            source_actor_id=source_actor_id,
                            target_actor_id=target_actor_id,
                        ),
                    }
                ],
                "action_lines": [],
                "initiative_events": [],
                "state_effects": [],
            }
            result = validate_voice_consistency(
                structured_output=structured,
                voice_profiles=profiles,
                validation_mode="strict_rule_engine",
            ).to_runtime_dict()

            assert result["status"] == "rejected", (source_actor_id, target_actor_id, result)
            assert result["semantic_classifications"][0]["best_matching_actor_id"] == source_actor_id
            assert result["blocking_findings"][0]["actual_source_actor_id"] == source_actor_id
            assert result["blocking_findings"][0]["expected_profile_actor_id"] == target_actor_id


def test_voice_drift_is_runtime_validation_failure_before_commit() -> None:
    structured, profiles, bundle = _forbidden_marker_case()
    state = {
        "session_id": "voice-runtime",
        "module_id": "god_of_carnage",
        "current_scene_id": "living_room",
        "turn_number": 1,
        "validation_execution_mode": "schema_plus_semantic",
        "goc_yaml_slice": bundle,
        "character_voice_profiles": profiles,
        "selected_responder_set": [{"actor_id": "annette_reille"}],
        "selected_scene_function": "probe_motive",
        "interpreted_input": {"player_input_kind": "speech", "npc_response_expected": True},
        "turn_aspect_ledger": initialize_runtime_aspect_ledger(
            session_id="voice-runtime",
            module_id="god_of_carnage",
            turn_number=1,
            turn_kind="player",
            raw_player_input="Sag etwas.",
        ),
    }
    generation = {
        "success": True,
        "content": "structured",
        "metadata": {"structured_output": structured},
    }

    result = _build_runtime_aspect_validation(
        state=state,
        generation=generation,
        proposed_state_effects=[
            {
                "effect_type": "narrative_projection",
                "description": "fixture",
            }
        ],
        outcome={"status": "approved", "reason": "goc_default_validator_pass"},
    )

    assert result["outcome"]["status"] == "rejected"
    assert result["outcome"]["reason"] == "voice_consistency_drift"
    aspect = result["turn_aspect_ledger"]["turn_aspect_ledger"][ASPECT_VOICE_CONSISTENCY]
    assert aspect["status"] == "failed"
    assert aspect["failure_reason"] == "voice_consistency_drift"
    validation = result["turn_aspect_ledger"]["turn_aspect_ledger"][ASPECT_VALIDATION]
    assert validation["status"] == "failed"
    assert validation["actual"]["voice_consistency_status"] == "rejected"


def test_semantic_voice_drift_is_runtime_validation_failure_before_commit() -> None:
    (
        structured,
        profiles,
        bundle,
        source_actor_id,
        target_actor_id,
    ) = _semantic_cross_actor_case()
    state = {
        "session_id": "voice-runtime-semantic",
        "module_id": "god_of_carnage",
        "current_scene_id": "living_room",
        "turn_number": 1,
        "validation_execution_mode": "strict_rule_engine",
        "goc_yaml_slice": bundle,
        "character_voice_profiles": profiles,
        "selected_responder_set": [{"actor_id": target_actor_id}],
        "selected_scene_function": "probe_motive",
        "interpreted_input": {"player_input_kind": "speech", "npc_response_expected": True},
        "turn_aspect_ledger": initialize_runtime_aspect_ledger(
            session_id="voice-runtime-semantic",
            module_id="god_of_carnage",
            turn_number=1,
            turn_kind="player",
            raw_player_input="Sag etwas.",
        ),
    }
    generation = {
        "success": True,
        "content": "structured",
        "metadata": {"structured_output": structured},
    }

    result = _build_runtime_aspect_validation(
        state=state,
        generation=generation,
        proposed_state_effects=[
            {
                "effect_type": "narrative_projection",
                "description": "fixture",
            }
        ],
        outcome={"status": "approved", "reason": "goc_default_validator_pass"},
    )

    assert result["outcome"]["status"] == "rejected"
    assert result["outcome"]["validator_lane"] == "runtime_voice_consistency_v2"
    assert result["outcome"]["voice_consistency_validation"]["blocking_findings"][0][
        "actual_source_actor_id"
    ] == source_actor_id
    aspect = result["turn_aspect_ledger"]["turn_aspect_ledger"][ASPECT_VOICE_CONSISTENCY]
    assert aspect["status"] == "failed"
    assert aspect["expected"]["semantic_classification_enabled"] is True
    assert aspect["actual"]["semantic_classification_count"] > 0
    validation = result["turn_aspect_ledger"]["turn_aspect_ledger"][ASPECT_VALIDATION]
    assert validation["status"] == "failed"
    assert validation["actual"]["voice_consistency_status"] == "rejected"


def test_semantic_voice_drift_self_correction_revalidates_rewritten_voice() -> None:
    (
        structured,
        profiles,
        bundle,
        _source_actor_id,
        target_actor_id,
    ) = _semantic_cross_actor_case()
    executor = object.__new__(RuntimeTurnGraphExecutor)
    executor.max_self_correction_attempts = 1
    executor.allow_degraded_commit_after_retries = False
    state = {
        "session_id": "voice-runtime-retry",
        "module_id": "god_of_carnage",
        "current_scene_id": "living_room",
        "player_input": "Sag etwas.",
        "turn_number": 1,
        "validation_execution_mode": "strict_rule_engine",
        "goc_yaml_slice": bundle,
        "character_voice_profiles": profiles,
        "selected_responder_set": [{"actor_id": target_actor_id}],
        "selected_scene_function": "probe_motive",
        "interpreted_input": {
            "player_input_kind": "speech",
            "narrator_response_expected": False,
            "npc_response_expected": True,
        },
        "actor_lane_context": {
            "human_actor_id": "veronique_vallon",
            "selected_player_role": "veronique_vallon",
            "npc_actor_ids": ["michel_longstreet", "annette_reille", "alain_reille"],
            "actor_lanes": {
                "veronique_vallon": "human",
                "michel_longstreet": "npc",
                "annette_reille": "npc",
                "alain_reille": "npc",
            },
        },
        "generation": {
            "success": True,
            "content": "structured",
            "metadata": {"structured_output": structured},
        },
        "proposed_state_effects": [
            {"effect_type": "narrative_projection", "description": "voice fixture"}
        ],
        "turn_aspect_ledger": initialize_runtime_aspect_ledger(
            session_id="voice-runtime-retry",
            module_id="god_of_carnage",
            turn_number=1,
            turn_kind="player",
            raw_player_input="Sag etwas.",
        ),
    }

    def _fake_self_correct(
        _current_state,
        _current_generation,
        _current_proposed,
        feedback_codes,
        attempt_index,
        preserve_actor_lanes=False,
        **_retry_context_kwargs,
    ):
        repaired = {
            "schema_version": "runtime_actor_turn_v1",
            "narration_summary": "fixture",
            "spoken_lines": [
                {
                    "speaker_id": target_actor_id,
                    "text": _semantic_profile_fixture_text(
                        profiles,
                        source_actor_id=target_actor_id,
                    ),
                }
            ],
            "action_lines": [],
            "initiative_events": [],
            "state_effects": [],
        }
        return (
            {
                "success": True,
                "content": "structured",
                "metadata": {"structured_output": repaired},
            },
            [{"effect_type": "narrative_projection", "description": "voice repaired"}],
            {
                "attempt_index": attempt_index,
                "candidate_model": "test-model",
                "feedback_codes": list(feedback_codes),
                "success": True,
                "parser_error": None,
                "preserve_actor_lanes": preserve_actor_lanes,
            },
        )

    executor._self_correct_generation = _fake_self_correct

    update = executor._validate_seam(state)

    assert update["validation_outcome"]["status"] == "approved"
    assert update["self_correction"]["attempt_count"] == 1
    attempt = update["self_correction"]["attempts"][0]
    assert attempt["trigger_source"] == "validation"
    assert "voice_drift:cross_actor_voice_confusion" in attempt["feedback_codes"]
    assert "voice_best_match:veronique_vallon" in attempt["feedback_codes"]
    assert update["voice_consistency_validation"]["status"] == "approved"
    final_classification = update["voice_consistency_validation"]["semantic_classifications"][0]
    assert final_classification["best_matching_actor_id"] == target_actor_id
    assert final_classification["classification_status"] == "pass"
