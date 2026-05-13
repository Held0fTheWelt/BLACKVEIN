"""PLAYER-INPUT-ACTION-SEMANTICS-ALGORITHM-01: German-language regression corpus.

Covers all required semantic categories with German inputs, including imperatives.
All test inputs are in German (lang_hint="de").
Tests verify:
  - correct player_input_kind / semantic_category
  - speech_projection_allowed gate
  - visible projection does not render raw action input as quoted speech
"""

from __future__ import annotations

import pytest

from story_runtime_core.content_locale import (
    build_player_attributed_visible_line,
    classify_player_input_from_rules,
    clear_content_locale_caches,
    resolve_content_modules_root,
)

MODULE = "god_of_carnage"
LANG = "de"
NAME = "Annette"

# German quoted-speech markers used in module_strings.yaml templates
_DE_SPEECH_OPEN = "„"  # „


def setup_module(_m: object) -> None:
    clear_content_locale_caches()


def _root():
    return resolve_content_modules_root()


def _classify(text: str):
    return classify_player_input_from_rules(
        text,
        module_id=MODULE,
        lang_hint=LANG,
        content_modules_root=_root(),
    )


def _project(text: str, hit: dict) -> str:
    return build_player_attributed_visible_line(
        name=NAME,
        raw=text,
        input_kind=hit["player_input_kind"],
        lang=LANG,
        module_id=MODULE,
        content_modules_root=_root(),
        projection_key=hit.get("projection_key"),
        projection_captures=hit.get("captures"),
    )


def _assert_no_speech_wrapping(line: str, raw: str) -> None:
    """Asserts raw action input is not rendered as quoted dialogue (German or English markers)."""
    assert f"sagt: {_DE_SPEECH_OPEN}" not in line, f"Action rendered as speech (sagt): {line!r}"
    assert f"fragt: {_DE_SPEECH_OPEN}" not in line, f"Action rendered as speech (fragt): {line!r}"
    assert 'says: "' not in line, f"Action rendered as speech (says): {line!r}"
    assert 'asks: "' not in line, f"Action rendered as speech (asks): {line!r}"


# ---------------------------------------------------------------------------
# Speech / question — speech projection IS allowed
# ---------------------------------------------------------------------------


def test_speech_ich_sage_is_speech():
    hit = _classify("Ich sage: Das reicht.")
    assert hit["player_input_kind"] == "speech"
    assert hit["speech_projection_allowed"] is True
    assert hit["player_speech_committed"] is True
    assert hit["player_action_committed"] is False


def test_speech_question_warum_sind_wir_hier():
    hit = _classify("Warum sind wir hier?")
    assert hit["player_input_kind"] == "speech"
    assert hit["speech_projection_allowed"] is True
    line = _project("Warum sind wir hier?", hit)
    assert "fragt" in line.lower()
    assert "Warum sind wir hier?" in line


def test_speech_direct_quoted_statement():
    hit = _classify('"Das reicht."')
    assert hit["speech_projection_allowed"] is True
    assert hit["player_input_kind"] == "speech"


# ---------------------------------------------------------------------------
# Movement — imperatives and first-person, speech projection NOT allowed
# ---------------------------------------------------------------------------


def test_movement_gehe_ins_badezimmer():
    hit = _classify("Gehe ins Badezimmer.")
    assert hit["player_input_kind"] == "action"
    assert hit["speech_projection_allowed"] is False
    assert hit["player_action_committed"] is True
    line = _project("Gehe ins Badezimmer.", hit)
    _assert_no_speech_wrapping(line, "Gehe ins Badezimmer.")
    assert NAME in line


def test_movement_ich_gehe_in_die_kueche():
    hit = _classify("Ich gehe in die Küche.")
    assert hit["player_input_kind"] == "action"
    assert hit["speech_projection_allowed"] is False
    line = _project("Ich gehe in die Küche.", hit)
    _assert_no_speech_wrapping(line, "Ich gehe in die Küche.")


def test_movement_setz_dich_imperative():
    hit = _classify("Setz dich.")
    assert hit["player_input_kind"] == "action"
    assert hit["speech_projection_allowed"] is False
    line = _project("Setz dich.", hit)
    _assert_no_speech_wrapping(line, "Setz dich.")
    assert NAME in line


def test_movement_ich_setze_mich():
    hit = _classify("Ich setze mich.")
    assert hit["player_input_kind"] == "action"
    assert hit["speech_projection_allowed"] is False


def test_movement_steh_auf_imperative():
    hit = _classify("Steh auf.")
    assert hit["player_input_kind"] == "action"
    assert hit["speech_projection_allowed"] is False
    line = _project("Steh auf.", hit)
    _assert_no_speech_wrapping(line, "Steh auf.")
    assert NAME in line


def test_movement_ich_stehe_auf():
    hit = _classify("Ich stehe auf.")
    assert hit["player_input_kind"] == "action"
    assert hit["speech_projection_allowed"] is False


def test_movement_gehe_zur_tuer():
    hit = _classify("Gehe zur Tür.")
    assert hit["player_input_kind"] == "action"
    assert hit["speech_projection_allowed"] is False


# ---------------------------------------------------------------------------
# Perception — imperatives and first-person, speech projection NOT allowed
# ---------------------------------------------------------------------------


def test_perception_schau_aus_dem_fenster_imperative():
    hit = _classify("Schau aus dem Fenster.")
    assert hit["player_input_kind"] == "perception"
    assert hit["speech_projection_allowed"] is False
    assert hit["narrator_response_expected"] is True
    line = _project("Schau aus dem Fenster.", hit)
    _assert_no_speech_wrapping(line, "Schau aus dem Fenster.")


def test_perception_schau_dich_um_imperative():
    hit = _classify("Schau dich im Zimmer um.")
    assert hit["player_input_kind"] == "perception"
    assert hit["speech_projection_allowed"] is False
    line = _project("Schau dich im Zimmer um.", hit)
    _assert_no_speech_wrapping(line, "Schau dich im Zimmer um.")


def test_perception_lausche_an_der_tuer_imperative():
    hit = _classify("Lausche an der Tür.")
    assert hit["player_input_kind"] == "perception"
    assert hit["speech_projection_allowed"] is False
    line = _project("Lausche an der Tür.", hit)
    _assert_no_speech_wrapping(line, "Lausche an der Tür.")


def test_perception_betrachte_den_tisch_imperative():
    hit = _classify("Betrachte den Tisch.")
    assert hit["player_input_kind"] == "perception"
    assert hit["speech_projection_allowed"] is False


def test_perception_was_sehe_ich_durch_das_fenster():
    hit = _classify("Was sehe ich durch das Fenster?")
    assert hit["player_input_kind"] == "perception"
    assert hit["speech_projection_allowed"] is False
    line = _project("Was sehe ich durch das Fenster?", hit)
    assert "fragt" not in line.lower()
    assert "sagt" not in line.lower()


# ---------------------------------------------------------------------------
# Object interaction — imperatives, speech projection NOT allowed
# ---------------------------------------------------------------------------


def test_object_nimm_das_glas_imperative():
    hit = _classify("Nimm das Glas.")
    assert hit["player_input_kind"] == "object_interaction"
    assert hit["speech_projection_allowed"] is False
    assert hit["player_action_committed"] is True
    line = _project("Nimm das Glas.", hit)
    _assert_no_speech_wrapping(line, "Nimm das Glas.")


def test_object_oeffne_die_tuer_imperative():
    hit = _classify("Öffne die Tür.")
    assert hit["player_input_kind"] == "object_interaction"
    assert hit["speech_projection_allowed"] is False
    line = _project("Öffne die Tür.", hit)
    _assert_no_speech_wrapping(line, "Öffne die Tür.")


def test_object_stell_das_glas_ab_imperative():
    hit = _classify("Stell das Glas ab.")
    assert hit["player_input_kind"] == "object_interaction"
    assert hit["speech_projection_allowed"] is False
    line = _project("Stell das Glas ab.", hit)
    _assert_no_speech_wrapping(line, "Stell das Glas ab.")


def test_object_leg_das_handy_auf_den_tisch_imperative():
    hit = _classify("Leg das Handy auf den Tisch.")
    assert hit["player_input_kind"] == "object_interaction"
    assert hit["speech_projection_allowed"] is False


# ---------------------------------------------------------------------------
# Social gesture — imperatives, speech projection NOT allowed
# ---------------------------------------------------------------------------


def test_social_begrüsse_imperative():
    hit = _classify("Begrüße Véronique.")
    assert hit["player_input_kind"] == "social_nonverbal_action"
    assert hit["speech_projection_allowed"] is False
    assert hit["npc_response_expected"] is True
    line = _project("Begrüße Véronique.", hit)
    _assert_no_speech_wrapping(line, "Begrüße Véronique.")


def test_social_grüsse_short_form_imperative():
    hit = _classify("Grüße Véronique.")
    assert hit["player_input_kind"] == "social_nonverbal_action"
    assert hit["speech_projection_allowed"] is False


def test_social_entschuldige_dich_imperative():
    hit = _classify("Entschuldige dich bei Michel.")
    assert hit["player_input_kind"] == "social_nonverbal_action"
    assert hit["speech_projection_allowed"] is False
    line = _project("Entschuldige dich bei Michel.", hit)
    _assert_no_speech_wrapping(line, "Entschuldige dich bei Michel.")


def test_social_bedanke_dich_imperative():
    hit = _classify("Bedanke dich für die Einladung.")
    assert hit["player_input_kind"] == "social_nonverbal_action"
    assert hit["speech_projection_allowed"] is False
    line = _project("Bedanke dich für die Einladung.", hit)
    _assert_no_speech_wrapping(line, "Bedanke dich für die Einladung.")


# ---------------------------------------------------------------------------
# Physical action — imperatives, speech projection NOT allowed
# ---------------------------------------------------------------------------


def test_physical_schubs_michel_imperative():
    hit = _classify("Schubs Michel.")
    assert hit["player_input_kind"] == "physical_action"
    assert hit["speech_projection_allowed"] is False
    assert hit["player_action_committed"] is True
    line = _project("Schubs Michel.", hit)
    _assert_no_speech_wrapping(line, "Schubs Michel.")


def test_physical_schlag_alain_imperative():
    hit = _classify("Schlag Alain.")
    assert hit["player_input_kind"] == "physical_action"
    assert hit["speech_projection_allowed"] is False
    line = _project("Schlag Alain.", hit)
    _assert_no_speech_wrapping(line, "Schlag Alain.")


def test_physical_wirf_das_glas_imperative():
    hit = _classify("Wirf das Glas.")
    assert hit["player_input_kind"] == "physical_action"
    assert hit["speech_projection_allowed"] is False
    line = _project("Wirf das Glas.", hit)
    _assert_no_speech_wrapping(line, "Wirf das Glas.")


# ---------------------------------------------------------------------------
# Mixed action + speech — action frame and speech component both present
# ---------------------------------------------------------------------------


def test_mixed_stehe_auf_und_sage():
    hit = _classify("Ich stehe auf und sage: Das reicht.")
    assert hit["player_input_kind"] == "mixed"
    assert hit["speech_projection_allowed"] is False
    assert hit["player_action_committed"] is True
    assert hit["player_speech_committed"] is True
    line = _project("Ich stehe auf und sage: Das reicht.", hit)
    assert "Das reicht" in line
    assert hit.get("captures", {}).get("speech") == "Das reicht."


def test_mixed_gehe_zur_tuer_und_frage():
    hit = _classify("Ich gehe zur Tür und frage, ob jemand kommt.")
    assert hit["player_input_kind"] == "mixed"
    assert hit["speech_projection_allowed"] is False
    assert hit["player_action_committed"] is True
    assert hit["player_speech_committed"] is True
    line = _project("Ich gehe zur Tür und frage, ob jemand kommt.", hit)
    _assert_no_speech_wrapping(line, "Ich gehe zur Tür und frage, ob jemand kommt.")


# ---------------------------------------------------------------------------
# Wait / observe
# ---------------------------------------------------------------------------


def test_wait_or_observe_ich_warte():
    hit = _classify("Ich warte.")
    assert hit["player_input_kind"] == "wait_or_observe"
    assert hit["speech_projection_allowed"] is False
    line = _project("Ich warte.", hit)
    _assert_no_speech_wrapping(line, "Ich warte.")


# ---------------------------------------------------------------------------
# No-rule-match: unclear / speech_projection_allowed=False
# ---------------------------------------------------------------------------


def test_no_rule_match_unrecognized_german():
    hit = _classify("Tue das seltsame Ding dort drüben.")
    assert hit["deterministic_intent_rule"] == "no_rule_match"
    assert hit["speech_projection_allowed"] is False


# ---------------------------------------------------------------------------
# STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P5:
# German look-around and return-movement idiom support.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "Ich sehe mich um.",
        "Ich schaue mich um.",
        "Ich blicke mich um.",
        "Ich sehe mich im Raum um.",
        "Ich schaue mich im Salon um.",
    ],
)
def test_german_look_around_idiom_classifies_as_perception_action(raw: str) -> None:
    """P5: 'sich umsehen' / 'sich umschauen' / 'sich umblicken' must be perception,
    not speech. The audit found 'Ich sehe mich um.' classified as speech which is a bug."""
    hit = _classify(raw)
    assert hit["player_input_kind"] == "perception", f"{raw!r} -> {hit['player_input_kind']!r}"
    assert hit["speech_projection_allowed"] is False
    assert hit["deterministic_intent_rule"] == "de_perception_look_around"
    # Visible projection must not wrap as quoted speech.
    line = _project(raw, hit)
    _assert_no_speech_wrapping(line, raw)


@pytest.mark.parametrize(
    "raw",
    [
        "Ich gehe zurück.",
        "Ich gehe zurück ins Wohnzimmer.",
        "Ich gehe zurueck ins Wohnzimmer.",
        "Ich gehe wieder ins Wohnzimmer.",
        "Ich gehe wieder in den Salon.",
    ],
)
def test_german_return_movement_idiom_classifies_as_action(raw: str) -> None:
    """P5: 'gehe zurück' / 'gehe wieder' must be action with movement_return_intent so
    downstream affordance resolution can use previous_location_id when target is implicit
    or use the captured destination noun when present."""
    hit = _classify(raw)
    assert hit["player_input_kind"] == "action", f"{raw!r} -> {hit['player_input_kind']!r}"
    assert hit["deterministic_intent_rule"] == "de_movement_gehe_zurueck"
    assert hit["speech_projection_allowed"] is False
    # The rule should be marked as a return-movement so affordance resolution can fall
    # back to previous_location_id when the captured room is missing.
    assert hit.get("movement_return_intent") is True


def test_german_plain_gehe_still_matches_after_return_idiom_rule() -> None:
    """P5: precedence — 'Ich gehe ins Badezimmer.' must still match the plain de_movement_gehe
    rule (not de_movement_gehe_zurueck) so existing movement flows are not regressed."""
    hit = _classify("Ich gehe ins Badezimmer.")
    assert hit["deterministic_intent_rule"] == "de_movement_gehe"
    assert hit["player_input_kind"] == "action"
    assert hit.get("movement_return_intent") in (None, False)


# ---------------------------------------------------------------------------
# speech_projection_allowed gate: non-speech inputs never produce sagt/fragt
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected_kind",
    [
        ("Gehe ins Badezimmer.", "action"),
        ("Schau aus dem Fenster.", "perception"),
        ("Nimm das Glas.", "object_interaction"),
        ("Öffne die Tür.", "object_interaction"),
        ("Schubs Michel.", "physical_action"),
        ("Wirf das Glas.", "physical_action"),
        ("Setz dich.", "action"),
        ("Steh auf.", "action"),
        ("Begrüße Véronique.", "social_nonverbal_action"),
        ("Entschuldige dich bei Michel.", "social_nonverbal_action"),
    ],
)
def test_non_speech_inputs_gate_de(raw: str, expected_kind: str) -> None:
    hit = _classify(raw)
    assert hit["player_input_kind"] == expected_kind, (
        f"{raw!r}: expected {expected_kind!r}, got {hit['player_input_kind']!r}"
    )
    assert hit["speech_projection_allowed"] is False, (
        f"{raw!r}: speech_projection_allowed should be False for {expected_kind}"
    )
    line = _project(raw, hit)
    assert f"sagt: {_DE_SPEECH_OPEN}" not in line, (
        f"Non-speech rendered as dialogue: {line!r} for {raw!r}"
    )
    assert f"fragt: {_DE_SPEECH_OPEN}" not in line, (
        f"Non-speech rendered as question-dialogue: {line!r} for {raw!r}"
    )
