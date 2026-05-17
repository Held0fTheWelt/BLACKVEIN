"""P0 regression: action resolution via ontology + entity registry (no phrase-specific engine branches)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from ai_stack.action_ontology import clear_action_ontology_cache
from ai_stack.player_action_resolution import resolve_player_action


@pytest.fixture(autouse=True)
def _clear_ontology_cache():
    clear_action_ontology_cache()
    yield
    clear_action_ontology_cache()


def _root() -> Path:
    return Path(__file__).resolve().parents[2] / "content" / "modules"


def _projection() -> dict:
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


def test_gehe_kueche_resolves_kitchen_offscreen() -> None:
    out = resolve_player_action(
        raw_text="Gehe in die Kueche",
        interpreted_input={
            "player_input_kind": "action",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "projection_captures": {"room": "die Kueche"},
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=_root(),
    )
    frame = out["player_action_frame"]
    assert frame["verb"] == "move_to"
    assert frame["resolved_target_id"] == "kitchen"
    assert frame["affordance_status"] == "allowed_offscreen"


def test_gehe_arbeitszimmer_resolves_study_offscreen() -> None:
    out = resolve_player_action(
        raw_text="Gehe ins Arbeitszimmer",
        interpreted_input={
            "player_input_kind": "action",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "projection_captures": {"room": "ins Arbeitszimmer"},
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=_root(),
    )
    frame = out["player_action_frame"]
    assert frame["verb"] == "move_to"
    assert frame["resolved_target_id"] == "study"
    assert frame["affordance_status"] == "allowed_offscreen"


def test_begruesse_accented_name_resolves_actor() -> None:
    out = resolve_player_action(
        raw_text="Begrüße Véronique",
        interpreted_input={
            "player_input_kind": "action",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=_root(),
    )
    frame = out["player_action_frame"]
    assert frame["verb"] == "greet"
    assert frame["resolved_target_type"] == "actor"
    assert frame["resolved_target_id"] == "veronique_vallon"


def _modules_root_with_scene_objects(tmp_path: Path, *, empty_objects: bool) -> Path:
    """Minimal ``content/modules`` tree for ``resolve_player_action`` tests."""
    repo_locale = _root() / "god_of_carnage" / "locale"
    dst_root = tmp_path / "modules"
    loc = dst_root / "god_of_carnage" / "locale"
    loc.mkdir(parents=True)
    shutil.copy2(repo_locale / "action_ontology.yaml", loc / "action_ontology.yaml")
    shutil.copy2(repo_locale / "module_strings.yaml", loc / "module_strings.yaml")
    if empty_objects:
        (loc / "scene_affordances.yaml").write_text(
            "scene_affordances:\n"
            "  current_area: test_area\n"
            "  inferred_area_policy: residential_apartment\n"
            "  locations: []\n"
            "  objects: []\n",
            encoding="utf-8",
        )
    else:
        shutil.copy2(repo_locale / "scene_affordances.yaml", loc / "scene_affordances.yaml")
    return dst_root


def _modules_root_with_beer_fridge(tmp_path: Path, *, available: bool) -> Path:
    repo_locale = _root() / "god_of_carnage" / "locale"
    dst_root = tmp_path / "modules"
    loc = dst_root / "god_of_carnage" / "locale"
    loc.mkdir(parents=True)
    shutil.copy2(repo_locale / "action_ontology.yaml", loc / "action_ontology.yaml")
    shutil.copy2(repo_locale / "module_strings.yaml", loc / "module_strings.yaml")
    objects = (
        '    - id: beer\n'
        '      aliases: ["Bier", "beer"]\n'
        '      affordances: ["take"]\n'
        '    - id: refrigerator\n'
        '      aliases: ["Kuehlschrank", "Kühlschrank", "fridge", "refrigerator"]\n'
        '      affordances: ["open", "take_from"]\n'
        if available
        else ""
    )
    (loc / "scene_affordances.yaml").write_text(
        "scene_affordances:\n"
        "  current_area: test_kitchen\n"
        "  inferred_area_policy: residential_apartment\n"
        "  locations: []\n"
        "  objects:\n"
        f"{objects}",
        encoding="utf-8",
    )
    return dst_root


def _modules_root_with_beer_without_fridge(tmp_path: Path) -> Path:
    repo_locale = _root() / "god_of_carnage" / "locale"
    dst_root = tmp_path / "modules"
    loc = dst_root / "god_of_carnage" / "locale"
    loc.mkdir(parents=True)
    shutil.copy2(repo_locale / "action_ontology.yaml", loc / "action_ontology.yaml")
    shutil.copy2(repo_locale / "module_strings.yaml", loc / "module_strings.yaml")
    (loc / "scene_affordances.yaml").write_text(
        "scene_affordances:\n"
        "  current_area: test_kitchen\n"
        "  inferred_area_policy: residential_apartment\n"
        "  locations: []\n"
        "  objects:\n"
        '    - id: beer\n'
        '      aliases: ["Bier", "beer"]\n'
        '      affordances: ["take"]\n',
        encoding="utf-8",
    )
    return dst_root


def test_take_beer_from_fridge_available_stays_object_action_with_source_query(tmp_path: Path) -> None:
    root = _modules_root_with_beer_fridge(tmp_path, available=True)
    out = resolve_player_action(
        raw_text="Ich nehme ein Bier aus dem Kuehlschrank",
        interpreted_input={
            "player_input_kind": "action",
            "lang": "de",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=root,
    )
    frame = out["player_action_frame"]
    aff = out["affordance_resolution"]
    assert frame["player_input_kind"] == "action"
    assert frame["action_kind"] == "object_interaction"
    assert frame["verb"] == "take"
    assert frame["target_query"] == "Bier aus dem Kuehlschrank"
    assert frame["source_query"] == "Kuehlschrank"
    assert frame["resolved_target_id"] == "beer"
    assert frame["resolved_source_id"] == "refrigerator"
    assert aff["affordance_status"] == "allowed"
    assert aff["action_commit_policy"] == "commit_action"
    assert frame["narrator_response_expected"] is True
    assert frame["npc_response_expected"] is False


def test_take_beer_from_unknown_source_is_clarification_not_speech(tmp_path: Path) -> None:
    root = _modules_root_with_beer_without_fridge(tmp_path)
    out = resolve_player_action(
        raw_text="Ich nehme ein Bier aus dem Kuehlschrank",
        interpreted_input={
            "player_input_kind": "action",
            "lang": "de",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=root,
    )
    frame = out["player_action_frame"]
    aff = out["affordance_resolution"]
    assert frame["player_input_kind"] == "action"
    assert frame["resolved_target_id"] == "beer"
    assert frame["source_query"] == "Kuehlschrank"
    assert frame["resolved_source_id"] is None
    assert aff["affordance_status"] == "unknown_target"
    assert aff["action_commit_policy"] == "needs_clarification"
    assert aff["reason"] == "source_query_unresolved"


def test_take_beer_from_fridge_unavailable_remains_action_unknown_target(tmp_path: Path) -> None:
    root = _modules_root_with_beer_fridge(tmp_path, available=False)
    out = resolve_player_action(
        raw_text="Ich nehme ein Bier aus dem Kuehlschrank",
        interpreted_input={
            "player_input_kind": "action",
            "lang": "de",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=root,
    )
    frame = out["player_action_frame"]
    aff = out["affordance_resolution"]
    assert frame["player_input_kind"] == "action"
    assert frame["action_kind"] == "object_interaction"
    assert frame["verb"] == "take"
    assert frame["source_query"] == "Kuehlschrank"
    assert frame["resolved_target_id"] is None
    assert frame["resolved_source_id"] is None
    assert aff["affordance_status"] == "unknown_target"
    assert aff["action_commit_policy"] == "needs_clarification"
    assert aff["commit_allowed"] is False


def test_schalte_fernseher_ein_when_upstream_labels_speech_still_object_interaction(tmp_path: Path) -> None:
    """Intent classifier may emit ``speech``; bounded device imperatives stay action + object path."""
    root = _modules_root_with_scene_objects(tmp_path, empty_objects=False)
    out = resolve_player_action(
        raw_text="Schalte den Fernseher ein",
        interpreted_input={
            "player_input_kind": "speech",
            "lang": "de",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=root,
    )
    frame = out["player_action_frame"]
    assert frame["input_kind"] == "action"
    assert frame["action_kind"] == "object_interaction"
    assert frame["verb"] == "activate"


def test_schalte_fernseher_ein_object_interaction_with_scene_object(tmp_path: Path) -> None:
    root = _modules_root_with_scene_objects(tmp_path, empty_objects=False)
    out = resolve_player_action(
        raw_text="Schalte den Fernseher ein",
        interpreted_input={
            "player_input_kind": "action",
            "lang": "de",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=root,
    )
    frame = out["player_action_frame"]
    aff = out["affordance_resolution"]
    assert frame["player_input_kind"] == "action"
    assert frame["action_kind"] == "object_interaction"
    assert frame["verb"] == "activate"
    assert frame["target_query"] == "Fernseher"
    assert frame["resolved_target_id"] == "television"
    assert frame["selected_actor_id"] == "annette_reille"
    assert frame["narrator_response_expected"] is True
    assert frame["npc_response_expected"] is False
    assert aff["affordance_status"] == "allowed"
    assert aff["action_commit_policy"] == "commit_action"


def test_schalte_fernseher_ein_unknown_target_stays_action_without_scene_object(tmp_path: Path) -> None:
    root = _modules_root_with_scene_objects(tmp_path, empty_objects=True)
    out = resolve_player_action(
        raw_text="Schalte den Fernseher ein",
        interpreted_input={
            "player_input_kind": "action",
            "lang": "de",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=root,
    )
    frame = out["player_action_frame"]
    aff = out["affordance_resolution"]
    assert frame["player_input_kind"] == "action"
    assert frame["action_kind"] == "object_interaction"
    assert frame["verb"] == "activate"
    assert frame["target_query"] == "Fernseher"
    assert aff["affordance_status"] == "unknown_target"
    assert aff["action_commit_policy"] == "needs_clarification"
    assert aff["commit_allowed"] is False


def test_mach_das_licht_aus_deactivate_extracts_object(tmp_path: Path) -> None:
    root = _modules_root_with_scene_objects(tmp_path, empty_objects=True)
    out = resolve_player_action(
        raw_text="Mach das Licht aus",
        interpreted_input={
            "player_input_kind": "action",
            "lang": "de",
            "narrator_response_expected": True,
            "npc_response_expected": False,
        },
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=root,
    )
    frame = out["player_action_frame"]
    assert frame["verb"] == "deactivate"
    assert frame["target_query"] == "Licht"
    assert frame["action_kind"] == "object_interaction"


def test_mixed_stand_and_say_carries_speech_text() -> None:
    out = resolve_player_action(
        raw_text="Ich stehe auf und sage: Das reicht.",
        interpreted_input={
            "player_input_kind": "mixed",
            "narrator_response_expected": True,
            "npc_response_expected": True,
            "projection_captures": {"speech": "Das reicht."},
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=_root(),
    )
    frame = out["player_action_frame"]
    assert frame["speech_text"] == "Das reicht."
    assert frame["verb"] == "stand_up"
