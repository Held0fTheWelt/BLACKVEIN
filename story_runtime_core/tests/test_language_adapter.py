"""Tests for the universal semantic language adapter."""

from __future__ import annotations

from story_runtime_core.language_adapter import (
    build_interaction_surface,
    build_player_attributed_visible_line,
    clear_language_adapter_caches,
    greeting_imperative_addressee_fragment,
    load_session_language_model_directive,
    resolve_content_modules_root,
    resolve_string,
)


def test_interaction_surface_is_content_derived_and_map_free() -> None:
    clear_language_adapter_caches()
    root = resolve_content_modules_root()
    surface = build_interaction_surface("god_of_carnage", content_modules_root=root)

    assert surface["authority"] == "derived_from_content_files"
    assert surface["adapter_policy"]["engine_maps_allowed"] is False
    assert surface["semantic_resolution_contract"]["policy"]["no_hardcoded_language_maps"] is True
    assert {row.get("id") for row in surface["locations"]}.issuperset({"living_room", "kitchen"})
    assert {row.get("id") for row in surface["objects"]}.issuperset({"coffee_table", "elevator"})


def test_visible_line_is_neutral_attribution_not_locale_template() -> None:
    clear_language_adapter_caches()
    root = resolve_content_modules_root()
    got = build_player_attributed_visible_line(
        name="Annette",
        raw="Gehe in die Küche",
        input_kind="ambiguous",
        lang="de",
        module_id="god_of_carnage",
        content_modules_root=root,
    )
    assert got == "Annette: Gehe in die Küche"


def test_resolve_string_has_only_technical_fallbacks() -> None:
    clear_language_adapter_caches()
    root = resolve_content_modules_root()
    assert resolve_string("god_of_carnage", "any.key", "de", content_modules_root=root) == ""
    assert (
        resolve_string("god_of_carnage", "any.key", "de", content_modules_root=root, name="Annette", raw="Hallo")
        == "Annette: Hallo"
    )


def test_greeting_imperative_is_not_phrase_mapped() -> None:
    clear_language_adapter_caches()
    root = resolve_content_modules_root()
    assert (
        greeting_imperative_addressee_fragment(
            "Begrüße Véronique",
            lang="de",
            module_id="god_of_carnage",
            content_modules_root=root,
        )
        is None
    )


def test_session_language_directive_requires_semantic_ai_resolution() -> None:
    clear_language_adapter_caches()
    root = resolve_content_modules_root()
    text = load_session_language_model_directive(
        module_id="god_of_carnage",
        lang="en",
        content_modules_root=root,
    )
    assert "session_output_language=en" in text
    assert "lookup maps" in text
    assert "grounded content catalog" in text
