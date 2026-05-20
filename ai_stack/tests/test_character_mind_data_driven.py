"""Tests for data-driven character-mind selection.

These pin the runtime's ability to build character-mind records from actor ids
published by content modules. Runtime code must not maintain a module-specific
fallback map from character keys to actor ids.
"""

from __future__ import annotations

from ai_stack.story_runtime.npc_agency.character.character_mind_goc import (
    build_character_mind_records_for_goc,
    resolve_runtime_actor_id,
)


def test_resolve_actor_id_prefers_explicit_yaml_actor_id() -> None:
    chars = {"hero": {"actor_id": "hero_001", "role": "Protagonist"}}
    assert resolve_runtime_actor_id("hero", yaml_characters=chars) == "hero_001"


def test_resolve_actor_id_does_not_use_goc_fallback_for_short_keys() -> None:
    assert resolve_runtime_actor_id(
        "annette", yaml_characters={}, module_id="god_of_carnage"
    ) == "annette"


def test_resolve_actor_id_returns_key_for_unknown_modules() -> None:
    # No YAML mapping and no known module → the character key is the id.
    assert resolve_runtime_actor_id(
        "phoenix", yaml_characters={}, module_id="unknown_module"
    ) == "phoenix"


def test_resolve_actor_id_uses_explicit_yaml_for_goc_short_key() -> None:
    chars = {"annette": {"actor_id": "annette_override"}}
    assert (
        resolve_runtime_actor_id(
            "annette", yaml_characters=chars, module_id="god_of_carnage"
        )
        == "annette_override"
    )


def test_build_character_mind_records_uses_yaml_actor_ids() -> None:
    yaml_slice = {
        "characters": {
            "hero": {
                "actor_id": "hero_001",
                "role": "Protagonist",
            },
            "rival": {
                "actor_id": "rival_001",
                "role": "Antagonist",
            },
        }
    }
    records = build_character_mind_records_for_goc(
        yaml_slice=yaml_slice,
        active_character_keys=["hero", "rival"],
        current_scene_id="act_one",
        module_id="custom_module",
    )
    ids = [r.runtime_actor_id for r in records]
    assert ids == ["hero_001", "rival_001"]


def test_build_character_mind_records_goc_short_keys_require_content_actor_ids() -> None:
    records = build_character_mind_records_for_goc(
        yaml_slice={
            "characters": {
                "annette": {"actor_id": "annette_reille", "role": "Guest"},
                "alain": {"actor_id": "alain_reille", "role": "Guest"},
            }
        },
        active_character_keys=["annette", "alain"],
        current_scene_id="living_room",
        module_id="god_of_carnage",
    )
    ids = [r.runtime_actor_id for r in records]
    assert ids == ["annette_reille", "alain_reille"]
