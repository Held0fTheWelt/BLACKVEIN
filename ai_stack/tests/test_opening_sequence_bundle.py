"""Canonical GoC opening_sequence.yaml is bundled for runtime and narrative hints."""
from __future__ import annotations

from ai_stack.goc_yaml_authority import clear_goc_yaml_slice_cache, load_goc_opening_sequence_yaml, load_goc_yaml_slice_bundle


def test_load_goc_opening_sequence_yaml_structure() -> None:
    data = load_goc_opening_sequence_yaml()
    assert data.get("module_id") == "god_of_carnage"
    parts = data.get("parts")
    assert isinstance(parts, dict)
    assert "part_1_background_and_premise" in parts
    assert "part_2_into_the_scene" in parts
    p1 = parts["part_1_background_and_premise"]
    assert isinstance(p1.get("narrator_bar"), dict)
    seeds = data.get("premise_fact_seeds")
    assert isinstance(seeds, list) and len(seeds) >= 1


def test_yaml_slice_bundle_includes_opening_sequence() -> None:
    clear_goc_yaml_slice_cache()
    bundle = load_goc_yaml_slice_bundle()
    osq = bundle.get("opening_sequence")
    assert isinstance(osq, dict)
    assert osq.get("handover_to_scene_phase") == "phase_1"
