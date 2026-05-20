from __future__ import annotations

from pathlib import Path

import pytest

from ai_stack.story_runtime.turn.god_of_carnage_turn_seams import run_validation_seam
from ai_stack.player_action_resolution import resolve_player_action
from ai_stack.language_io.language_adapter import clear_language_adapter_caches
from story_runtime_core.player_input_intent_contract import default_commit_flags_for_player_input_kind


@pytest.fixture(autouse=True)
def _clear_language_adapter_caches() -> None:
    clear_language_adapter_caches()
    yield
    clear_language_adapter_caches()


def _runtime_projection() -> dict:
    return {
        "human_actor_id": "annette_reille",
        "selected_player_role": "annette_reille",
        "npc_actor_ids": ["alain_reille", "veronique_vallon", "michel_longstreet"],
        "actor_lanes": {
            "annette_reille": "human",
            "alain_reille": "npc",
            "veronique_vallon": "npc",
            "michel_longstreet": "npc",
        },
    }


def _content_root() -> Path:
    return Path(__file__).resolve().parents[2] / "content" / "modules"


def _semantic_interpreted(
    *,
    target_id: str | None,
    target_type: str | None,
    target_query: str | None,
    verb: str,
    action_kind: str,
    actor_id: str = "annette_reille",
    commit_policy: str = "commit_action",
    extra_semantic: dict | None = None,
) -> dict:
    semantic = {
        "player_input_kind": "action",
        "verb": verb,
        "action_kind": action_kind,
        "target_query": target_query,
        "resolved_target_id": target_id,
        "resolved_target_type": target_type,
        "commit_policy": commit_policy,
        "confidence": "high" if target_id else "low",
    }
    if isinstance(extra_semantic, dict):
        semantic.update(extra_semantic)
    return {
        "player_input_kind": "action",
        "narrator_response_expected": True,
        "npc_response_expected": False,
        "actor_id": actor_id,
        "semantic_action": semantic,
    }


def test_action_without_ai_semantics_requests_clarification() -> None:
    out = resolve_player_action(
        raw_text="Gehe ins Bad",
        interpreted_input={
            "player_input_kind": "action",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=_content_root(),
    )
    aff = out["affordance_resolution"]
    assert aff["affordance_status"] == "ambiguous"
    assert aff["action_commit_policy"] == "needs_clarification"
    assert aff["target_resolution_source"] == "semantic_ai_resolution_required"


def test_ai_semantic_movement_resolves_content_location() -> None:
    out = resolve_player_action(
        raw_text="Gehe in die Küche",
        interpreted_input=_semantic_interpreted(
            verb="move_to",
            action_kind="movement",
            target_query="Küche",
            target_id="kitchen",
            target_type="location",
        ),
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=_content_root(),
    )
    frame = out["player_action_frame"]
    assert frame["verb"] == "move_to"
    assert frame["resolved_target_type"] == "location"
    assert frame["resolved_target_id"] == "kitchen"
    assert frame["affordance_status"] == "allowed"
    assert frame["validation_surface"] == "ai_semantic_resolution"


def test_grounded_location_action_normalizes_to_spatial_role_without_verb_map() -> None:
    out = resolve_player_action(
        raw_text="Gehe in die Küche",
        interpreted_input=_semantic_interpreted(
            verb="go_to",
            action_kind="go_to",
            target_query="the kitchen",
            target_id="kitchen",
            target_type="location",
            extra_semantic={
                "player_input_kind": "physical_action",
                "normalized_english_text": "Go to the kitchen",
                "target_query_english": "the kitchen",
            },
        ),
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=_content_root(),
    )

    frame = out["player_action_frame"]
    assert frame["player_input_kind"] == "physical_action"
    assert frame["resolved_target_id"] == "kitchen"
    assert frame["resolved_target_type"] == "location"
    assert frame["action_kind"] == "movement"
    assert frame["verb"] == "move_to"
    assert frame["target_resolution_source"] == "ai_semantic_resolution.content_id"


def test_ai_semantic_resolution_preserves_internal_english_normalization() -> None:
    interpreted = _semantic_interpreted(
        verb="move_to",
        action_kind="movement",
        target_query="kitchen",
        target_id="kitchen",
        target_type="location",
    )
    interpreted["semantic_resolution_contract"] = {
        "input": {
            "session_input_language": "de",
            "session_output_language": "de",
            "internal_resolution_language": "en",
        }
    }
    interpreted["semantic_action"]["normalized_english_text"] = "Go to the kitchen"
    interpreted["semantic_action"]["target_query_english"] = "kitchen"

    out = resolve_player_action(
        raw_text="Gehe in die Küche",
        interpreted_input=interpreted,
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=_content_root(),
    )

    frame = out["player_action_frame"]
    assert frame["normalized_english_text"] == "Go to the kitchen"
    assert frame["internal_resolution_language"] == "en"
    assert frame["session_input_language"] == "de"
    assert frame["session_output_language"] == "de"
    assert frame["target_query"] == "kitchen"


def test_ai_semantic_stairwell_resolution_is_prevented_not_forbidden() -> None:
    out = resolve_player_action(
        raw_text="Gehe ins Treppenhaus",
        interpreted_input=_semantic_interpreted(
            verb="move_to",
            action_kind="movement",
            target_query="Treppenhaus",
            target_id="building_stairwell",
            target_type="location",
            actor_id="alain_reille",
            commit_policy="no_commit",
        ),
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=_content_root(),
    )
    aff = out["affordance_resolution"]
    assert aff["affordance_status"] == "prevented"
    assert aff["action_commit_policy"] == "no_commit"
    assert aff["requires_narrator"] is True


def test_ai_semantic_object_resolution_uses_content_access() -> None:
    out = resolve_player_action(
        raw_text="Öffne den Fahrstuhl",
        interpreted_input=_semantic_interpreted(
            verb="open",
            action_kind="object_interaction",
            target_query="Fahrstuhl",
            target_id="elevator",
            target_type="object",
            actor_id="alain_reille",
            commit_policy="no_commit",
        ),
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=_content_root(),
    )
    frame = out["player_action_frame"]
    assert frame["verb"] == "open"
    assert frame["resolved_target_id"] == "elevator"
    assert frame["affordance_status"] == "prevented"


def test_speech_without_semantic_action_stays_speech_path() -> None:
    out = resolve_player_action(
        raw_text="Gibt es hier ein Bad?",
        interpreted_input={
            "player_input_kind": "speech",
            "narrator_response_expected": False,
            "npc_response_expected": True,
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=_content_root(),
    )
    frame = out["player_action_frame"]
    assert frame["player_input_kind"] == "speech"
    assert frame["verb"] == "utterance"
    assert frame["affordance_status"] == "allowed"
    assert frame["npc_response_expected"] is True


def test_semantic_unknown_target_returns_clarification_status() -> None:
    out = resolve_player_action(
        raw_text="Gehe nach Mordor",
        interpreted_input=_semantic_interpreted(
            verb="move_to",
            action_kind="movement",
            target_query="Mordor",
            target_id=None,
            target_type=None,
        ),
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=_content_root(),
    )
    aff = out["affordance_resolution"]
    assert aff["affordance_status"] == "unknown_target"
    assert aff["action_commit_policy"] == "needs_clarification"


def test_ai_semantic_canon_safe_plausible_object_gap_commits_without_content_map() -> None:
    out = resolve_player_action(
        raw_text="Öffne den unbenannten Behälter",
        interpreted_input=_semantic_interpreted(
            verb="open",
            action_kind="object_interaction",
            target_query="unlisted household container",
            target_id=None,
            target_type="object",
            extra_semantic={
                "normalized_english_text": "Open the unlisted household container",
                "inference_mode": "canon_safe_plausible_affordance",
                "inferred_target_id": "inferred_local_household_container",
                "canon_safety": "content_silent_mundane",
                "canonical_risk": "low",
                "inferred_affordance_summary": "A mundane household container implied by apartment use.",
                "confidence": "medium",
            },
        ),
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=_content_root(),
    )
    frame = out["player_action_frame"]
    aff = out["affordance_resolution"]
    assert frame["resolved_target_id"] == "inferred_local_household_container"
    assert frame["resolved_target_type"] == "object"
    assert frame["target_resolution_source"] == "ai_semantic_resolution.plausible_inference"
    assert frame["access_status"] == "inferred_plausible"
    assert frame["semantic_inference"]["canonical_risk"] == "low"
    assert frame["canonical_path_effect"] == "hold_current_step"
    assert aff["affordance_status"] == "allowed"
    assert aff["action_commit_policy"] == "commit_action"


def test_ai_semantic_canon_risky_unknown_target_stays_clarification() -> None:
    out = resolve_player_action(
        raw_text="Suche den verborgenen Beweis",
        interpreted_input=_semantic_interpreted(
            verb="look_at",
            action_kind="perception",
            target_query="hidden decisive evidence",
            target_id=None,
            target_type="object",
            extra_semantic={
                "normalized_english_text": "Look for hidden decisive evidence",
                "inference_mode": "canon_safe_plausible_affordance",
                "canon_safety": "hidden_or_load_bearing_fact",
                "canonical_risk": "high",
                "confidence": "low",
            },
        ),
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=_content_root(),
    )
    aff = out["affordance_resolution"]
    assert aff["affordance_status"] == "unknown_target"
    assert aff["action_commit_policy"] == "needs_clarification"


def test_meta_input_resolution_is_non_story_control() -> None:
    flags = default_commit_flags_for_player_input_kind("meta")
    out = resolve_player_action(
        raw_text="ooc: pause",
        interpreted_input={
            "player_input_kind": "meta",
            **flags,
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=_content_root(),
    )
    frame = out["player_action_frame"]
    aff = out["affordance_resolution"]
    assert frame["player_input_kind"] == "meta"
    assert frame["action_kind"] == "control"
    assert frame["verb"] == "meta"
    assert frame["speech_text"] is None
    assert frame["narrator_response_expected"] is False
    assert frame["npc_response_expected"] is False
    assert aff["action_commit_policy"] == "no_commit"
    assert aff["commit_allowed"] is False
    assert aff["allows_npc_reaction"] is False


def test_continuity_pressure_reject_overridden_by_allowed_resolution(monkeypatch) -> None:
    class _FakeGateResult:
        value = "rejected_continuity_pressure"

    class _FakeGateOut:
        gate_result = _FakeGateResult()
        structural_fallback_used = False
        rejection_reasons: list[str] = []

        @staticmethod
        def to_runtime_dict() -> dict:
            return {"gate_result": "rejected_continuity_pressure"}

    monkeypatch.setattr(
        "ai_stack.story_runtime.turn.god_of_carnage_turn_seams_validation.evaluate_dramatic_effect_gate",
        lambda _ctx: _FakeGateOut(),
    )

    result = run_validation_seam(
        module_id="god_of_carnage",
        proposed_state_effects=[{"effect_type": "narrative_projection", "description": "x"}],
        generation={"success": True, "metadata": {"structured_output": {}}},
        affordance_resolution={
            "affordance_status": "allowed",
            "action_commit_policy": "commit_action",
        },
        player_action_frame={
            "player_input_kind": "action",
            "verb": "move_to",
            "resolved_target_id": "bathroom",
        },
    )
    assert result["status"] == "approved"
    assert result["reason"] == "action_resolution_continuity_supported"
    assert result["continuity_pressure_resolution"]["override_applied"] is True
