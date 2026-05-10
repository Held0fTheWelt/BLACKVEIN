"""Tests for content-backed locale resolution (no prose literals in assertions)."""

from __future__ import annotations

from pathlib import Path

import yaml

from story_runtime_core.content_locale import (
    build_player_attributed_visible_line,
    clear_content_locale_caches,
    greeting_imperative_addressee_fragment,
    load_session_language_model_directive,
    resolve_content_modules_root,
    resolve_string,
)


def _load_module_strings(root: Path) -> dict:
    p = root / "god_of_carnage" / "locale" / "module_strings.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_resolve_string_matches_module_yaml() -> None:
    clear_content_locale_caches()
    root = resolve_content_modules_root()
    bundle = _load_module_strings(root)
    strings = bundle["strings"]
    for key in ("player_shell.second_person", "player_shell.npc_responder_label"):
        for lang in ("de", "en"):
            expected = strings[key][lang]
            got = resolve_string("god_of_carnage", key, lang, content_modules_root=root)
            assert got == expected


def test_player_outcome_templates_round_trip() -> None:
    clear_content_locale_caches()
    root = resolve_content_modules_root()
    bundle = _load_module_strings(root)
    for lang in ("de", "en"):
        exp = bundle["strings"]["player_outcome.speech_statement"][lang]
        got = build_player_attributed_visible_line(
            name="N",
            raw="Hi",
            input_kind="speech",
            lang=lang,
            module_id="god_of_carnage",
            content_modules_root=root,
        )
        assert got == exp.format(name="N", raw="Hi")


def test_greeting_imperative_addressee_en() -> None:
    clear_content_locale_caches()
    root = resolve_content_modules_root()
    frag = greeting_imperative_addressee_fragment(
        "greet Veronique",
        lang="en",
        module_id="god_of_carnage",
        content_modules_root=root,
    )
    assert frag == "Veronique"


def test_session_language_directive_loads_markdown() -> None:
    clear_content_locale_caches()
    root = resolve_content_modules_root()
    text = load_session_language_model_directive(
        module_id="god_of_carnage",
        lang="en",
        content_modules_root=root,
    )
    assert "session_output_language=en" in text
    assert "ASCII double quotes" in text


def test_resolve_string_falls_back_when_module_has_no_locale() -> None:
    clear_content_locale_caches()
    root = resolve_content_modules_root()
    got = resolve_string(
        "totally_missing_module_xyz",
        "player_shell.second_person",
        "en",
        content_modules_root=root,
    )
    assert got == "You"
