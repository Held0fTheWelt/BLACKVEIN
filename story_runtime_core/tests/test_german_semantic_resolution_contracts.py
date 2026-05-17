"""German movement wording stays semantic, not rule-mapped."""

from __future__ import annotations

import pytest

from story_runtime_core.language_adapter import prepare_player_input_semantic_resolution, resolve_content_modules_root

MODULE = "god_of_carnage"
LANG = "de"


@pytest.mark.parametrize(
    "raw",
    [
        "Ich gehe zurück.",
        "Ich gehe wieder zurück.",
        "Ich gehe zurück ins Wohnzimmer.",
        "Ich gehe wieder ins Wohnzimmer.",
    ],
)
def test_german_return_movement_is_not_rule_mapped(raw: str) -> None:
    hit = prepare_player_input_semantic_resolution(
        raw,
        module_id=MODULE,
        lang_hint=LANG,
        content_modules_root=resolve_content_modules_root(),
    )
    assert hit["semantic_resolution_required"] is True
    assert hit["deterministic_intent_rule"] is None
    assert "movement_return_intent" not in hit
