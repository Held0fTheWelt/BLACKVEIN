"""German return-movement locale contract tests (English test names only)."""

from __future__ import annotations

import pytest

from story_runtime_core.content_locale import (
    build_player_attributed_visible_line,
    classify_player_input_from_rules,
    clear_content_locale_caches,
    resolve_content_modules_root,
)

MODULE = "god_of_carnage"
_LANG = "de"
_NAME = "Annette"


def setup_module(_m: object) -> None:
    clear_content_locale_caches()


def _classify(text: str) -> dict:
    return classify_player_input_from_rules(
        text,
        module_id=MODULE,
        lang_hint=_LANG,
        content_modules_root=resolve_content_modules_root(),
    )


@pytest.mark.parametrize(
    "raw",
    [
        "Ich gehe zurück.",
        "Ich gehe wieder zurück.",
        "Ich gehe zurück ins Wohnzimmer.",
        "Ich gehe wieder ins Wohnzimmer.",
    ],
)
def test_german_return_movement_sets_return_intent(raw: str) -> None:
    hit = _classify(raw)
    assert hit.get("movement_return_intent") is True
    assert hit["player_input_kind"] == "action"


def test_german_return_movement_with_explicit_target_preserves_target_query() -> None:
    raw = "Ich gehe zurück ins Wohnzimmer."
    hit = _classify(raw)
    caps = hit.get("captures") or {}
    assert isinstance(caps, dict)
    assert str(caps.get("room") or "").strip(), "expected room capture for explicit destination"


@pytest.mark.parametrize(
    "raw",
    [
        "Ich gehe zurück.",
        "Ich gehe wieder zurück.",
        "Ich gehe zurück ins Wohnzimmer.",
    ],
)
def test_german_return_movement_is_not_classified_as_speech(raw: str) -> None:
    hit = _classify(raw)
    assert hit["speech_projection_allowed"] is False
    line = build_player_attributed_visible_line(
        name=_NAME,
        raw=raw,
        input_kind=hit["player_input_kind"],
        lang=_LANG,
        module_id=MODULE,
        content_modules_root=resolve_content_modules_root(),
        projection_key=hit.get("projection_key"),
        projection_captures=hit.get("captures") or {},
    )
    assert "sagt:" not in line
