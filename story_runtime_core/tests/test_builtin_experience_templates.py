"""SSOT builtins: stable template ids and parity with app re-exports (DS-003)."""

from __future__ import annotations

from story_runtime_core.builtin_experience_templates import load_builtin_templates


def test_load_builtin_templates_three_known_ids():
    templates = load_builtin_templates()
    assert set(templates) == {
        "god_of_carnage_solo",
        "apartment_confrontation_group",
        "better_tomorrow_district_alpha",
    }
    assert templates["god_of_carnage_solo"].title == "God of Carnage"
