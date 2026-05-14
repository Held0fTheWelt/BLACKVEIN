from __future__ import annotations

from pathlib import Path

from ai_stack.beat_lifecycle_contracts import phase_beat_candidates, select_beat_candidate
from ai_stack.module_runtime_policy import load_module_runtime_policy
from ai_stack.runtime_aspect_ledger import initialize_runtime_aspect_ledger


MODULE_ID = "god_of_carnage"


def test_module_runtime_policy_loads_goc_without_runtime_hardcoding() -> None:
    policy = load_module_runtime_policy(MODULE_ID, "solo_test").to_dict()

    assert policy["module_id"] == MODULE_ID
    assert policy["runtime_profile_id"] == "solo_test"
    assert policy["actor_roster"]
    assert policy["playable_roles"]
    assert policy["location_model"]["locations"]
    assert policy["phase_policy"]["phases"]
    assert "actor_pressure_profiles" in policy["content_sources"]


def test_runtime_aspect_ledger_schema_is_module_neutral() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="story-1",
        module_id="example_module",
        runtime_profile_id="example_profile",
        turn_number=3,
        turn_kind="player",
        raw_player_input="Look around.",
        turn_id="story-1:turn:3",
    )

    assert ledger["schema_version"] == "turn_aspect_ledger.v1"
    assert ledger["module_id"] == "example_module"
    assert ledger["runtime_profile_id"] == "example_profile"
    assert ledger["canonical_turn_id"] == "story-1:turn:3"
    assert "god_of_carnage" not in str(ledger)


def test_authority_and_capability_policy_come_from_module_policy() -> None:
    policy = load_module_runtime_policy(MODULE_ID, "solo_test").to_dict()

    forbidden = policy["capability_policy"]["forbidden"]
    assert "npc.execute_player_action.forbidden" in forbidden
    assert "npc.narrate_player_perception.forbidden" in forbidden
    assert policy["authority_policy"]["hard_forbidden_policy"]


def test_beat_candidates_come_from_phase_policy_data() -> None:
    policy = load_module_runtime_policy(MODULE_ID, "solo_test").to_dict()
    phase_id = next(iter(policy["phase_policy"]["phases"].keys()))

    candidates = phase_beat_candidates(
        module_policy=policy,
        phase_id=phase_id,
        expected_visible_functions=["narrator.scene_context.establish"],
    )
    selection = select_beat_candidate(candidates, selection_source="module_policy")

    assert candidates
    assert selection.selected_beat_id
    assert selection.selection_source == "module_policy"
    assert "narrator.scene_context.establish" in selection.expected_visible_functions


def test_generic_runtime_intelligence_modules_do_not_embed_goc_literals() -> None:
    repo = Path(__file__).resolve().parents[2]
    generic_files = [
        repo / "ai_stack" / "beat_lifecycle_contracts.py",
        repo / "ai_stack" / "authority_contracts.py",
        repo / "ai_stack" / "dramatic_capability_contracts.py",
        repo / "ai_stack" / "visible_origin_contracts.py",
        repo / "ai_stack" / "module_runtime_policy.py",
        repo / "ai_stack" / "runtime_aspect_ledger.py",
        repo / "ai_stack" / "runtime_dramatic_capabilities.py",
    ]
    forbidden = (
        "Annette",
        "Alain",
        "Veronique",
        "Véronique",
        "Michel",
        "bathroom",
        "living_room",
        "vallon_living_room",
        "phase_1",
        "ritual_civility",
    )
    for path in generic_files:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{token!r} leaked into {path}"
