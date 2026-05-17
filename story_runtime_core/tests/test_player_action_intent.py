"""Player intent adapter tests: no deterministic phrase rules."""

from __future__ import annotations

import pytest

from story_runtime_core.language_adapter import (
    build_player_attributed_visible_line,
    prepare_player_input_semantic_resolution,
    clear_language_adapter_caches,
    infer_verb_and_action_kind,
    resolve_content_modules_root,
)


def _root() -> object:
    clear_language_adapter_caches()
    return resolve_content_modules_root()


@pytest.mark.parametrize(
    "raw,lang",
    [
        ("Gehe in die Küche", "de"),
        ("Schau aus dem Fenster", "de"),
        ("Gibt es hier ein Bad?", "de"),
        ("I go to the kitchen", "en"),
    ],
)
def test_player_language_requires_ai_semantic_resolution(raw: str, lang: str) -> None:
    root = _root()
    hit = prepare_player_input_semantic_resolution(
        raw,
        module_id="god_of_carnage",
        lang_hint=lang,
        content_modules_root=root,
    )
    assert hit["player_input_kind"] == "ambiguous"
    assert hit["semantic_category"] == "semantic_resolution_required"
    assert hit["semantic_resolution_required"] is True
    assert hit["deterministic_intent_rule"] is None
    assert hit["semantic_resolution_contract"]["policy"]["infer_meaning_from_player_utterance_and_content_catalog"] is True


def test_neutral_visible_line_does_not_restate_action_as_language_template() -> None:
    root = _root()
    raw = "Ich stehe auf und sage: Das reicht."
    hit = prepare_player_input_semantic_resolution(
        raw,
        module_id="god_of_carnage",
        lang_hint="de",
        content_modules_root=root,
    )
    line = build_player_attributed_visible_line(
        name="Annette",
        raw=raw,
        input_kind=hit["player_input_kind"],
        lang="de",
        module_id="god_of_carnage",
        content_modules_root=root,
    )
    assert line == f"Annette: {raw}"


def test_verb_inference_returns_semantic_sentinel_until_ai_resolves() -> None:
    verb, action_kind = infer_verb_and_action_kind(
        "Gehe in die Küche",
        module_id="god_of_carnage",
        player_input_kind="action",
        content_modules_root=_root(),
    )
    assert (verb, action_kind) == ("semantic_resolution_required", "semantic_action")

    speech_verb, speech_kind = infer_verb_and_action_kind(
        "Ich sage: Hallo",
        module_id="god_of_carnage",
        player_input_kind="speech",
        content_modules_root=_root(),
    )
    assert (speech_verb, speech_kind) == ("utterance", "speech")
