"""God of Carnage structured setting YAML — bundle exposure and cross-layer consistency."""

from __future__ import annotations

from ai_stack.goc_yaml_authority import (
    clear_goc_yaml_slice_cache,
    load_goc_apartment_layout_yaml,
    load_goc_scene_affordances_block,
    load_goc_scene_affordances_yaml_inner,
    load_goc_yaml_slice_bundle,
)


def setup_module(_m: object) -> None:
    clear_goc_yaml_slice_cache()


def test_yaml_slice_bundle_exposes_structured_setting_keys() -> None:
    clear_goc_yaml_slice_cache()
    bundle = load_goc_yaml_slice_bundle()
    for key in (
        "scene_affordances",
        "apartment_layout",
        "apartment_objects",
        "premise_and_backstory",
        "actor_pressure_profiles",
        "phase_beat_policy",
        "narrator_sensory_palette",
        "opening_scene_sequence",
        "hard_forbidden_rules",
    ):
        assert key in bundle
    assert bundle["opening_scene_sequence"].get("id") == "goc_opening_sequence_v1"
    assert "hard_forbidden" in (bundle.get("hard_forbidden_rules") or {})
    assert bundle["apartment_layout"].get("setting_id") == "vallon_paris_evening_apartment"
    assert "phase_1" in (bundle.get("phase_beat_policy") or {}).get("phases", {})


def test_scene_affordances_aligns_layout_room_ids() -> None:
    inner = load_goc_scene_affordances_yaml_inner()
    layout = load_goc_apartment_layout_yaml()
    loc_ids = {str(x.get("id")) for x in (inner.get("locations") or []) if isinstance(x, dict)}
    layout_room_ids = {r.get("id") for r in (layout.get("rooms") or []) if isinstance(r, dict)}
    assert {"bathroom", "kitchen", "hallway"}.issubset(loc_ids)
    assert layout_room_ids.issuperset({"bathroom", "kitchen", "hallway", "vallon_living_room"})


def test_narrator_fixture_surface_has_german_runtime_cues_for_bathroom_kitchen_window() -> None:
    block = load_goc_scene_affordances_block()
    sa = block.get("scene_affordances") or {}
    locs = {str(x.get("id")): x for x in (sa.get("locations") or []) if isinstance(x, dict)}
    objs = {str(x.get("id")): x for x in (sa.get("objects") or []) if isinstance(x, dict)}
    assert "Küche" in (locs.get("kitchen") or {}).get("aliases", [])
    assert "Bad" in (locs.get("bathroom") or {}).get("aliases", [])
    de_bath = ((locs.get("bathroom") or {}).get("entry_sensory_detail") or {}).get("de", "")
    assert "Stille" in de_bath or "Abstand" in de_bath
    win = objs.get("window") or {}
    assert "Fenster" in win.get("aliases", [])
    de_win = (win.get("perception_detail") or {}).get("de", "")
    assert "Fenster" in de_win or "Straße" in de_win
