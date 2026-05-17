"""German player-input semantics are delegated to the AI adapter contract."""

from __future__ import annotations

import pytest

from story_runtime_core.language_adapter import (
    build_player_attributed_visible_line,
    prepare_player_input_semantic_resolution,
    clear_language_adapter_caches,
    resolve_content_modules_root,
)

MODULE = "god_of_carnage"
LANG = "de"
NAME = "Annette"


def setup_module(_m: object) -> None:
    clear_language_adapter_caches()


def _classify(text: str) -> dict:
    return prepare_player_input_semantic_resolution(
        text,
        module_id=MODULE,
        lang_hint=LANG,
        content_modules_root=resolve_content_modules_root(),
    )


@pytest.mark.parametrize(
    "text",
    [
        "Ich sage: Das reicht.",
        "Warum sind wir hier?",
        "Gehe ins Badezimmer.",
        "Ich gehe in die Küche.",
        "Schau aus dem Fenster.",
        "Nimm das Glas.",
        "Begrüße Véronique.",
    ],
)
def test_german_input_requests_semantic_ai_resolution(text: str) -> None:
    hit = _classify(text)
    assert hit["player_input_kind"] == "ambiguous"
    assert hit["semantic_resolution_required"] is True
    assert hit["projection_key"] is None
    assert hit["captures"] == {}
    assert hit["semantic_resolution_contract"]["input"]["session_input_language"] == LANG
    assert hit["semantic_resolution_contract"]["input"]["session_output_language"] == LANG
    assert hit["semantic_resolution_contract"]["input"]["internal_resolution_language"] == "en"
    assert hit["semantic_resolution_contract"]["policy"]["translate_input_to_internal_english_before_grounding"] is True


def test_german_projection_is_plain_attribution_until_semantics_exist() -> None:
    text = "Schau aus dem Fenster."
    hit = _classify(text)
    line = build_player_attributed_visible_line(
        name=NAME,
        raw=text,
        input_kind=hit["player_input_kind"],
        lang=LANG,
        module_id=MODULE,
        content_modules_root=resolve_content_modules_root(),
    )
    assert line == f"{NAME}: {text}"
