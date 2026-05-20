"""Authored hints/ YAML loads and selects into director_surface_hints shape."""

from __future__ import annotations

from pathlib import Path

from ai_stack.story_runtime.turn.god_of_carnage_turn_seams import run_visible_render
from ai_stack.story_runtime.god_of_carnage.god_of_carnage_yaml_authority import (
    clear_goc_yaml_slice_cache,
    load_goc_director_surface_hints_yaml,
    select_goc_director_surface_hints_for_turn,
)
from story_runtime_core.director_surface_hints import load_module_director_surface_hints


def test_load_goc_director_surface_hints_catalog() -> None:
    clear_goc_yaml_slice_cache()
    hints = load_goc_director_surface_hints_yaml()
    assert len(hints) >= 3
    ids = {str(item.get("hint_id") or "") for item in hints}
    assert "goc_hint_violence_vs_civilization_master" in ids


def test_select_hints_for_living_room_phase_two() -> None:
    clear_goc_yaml_slice_cache()
    selected = select_goc_director_surface_hints_for_turn(
        scene_id="living_room",
        pacing_mode="compressed",
    )
    types = {str(item.get("hint_type") or "") for item in selected}
    assert "phase_context" in types
    assert "staging_symbol" in types


def test_run_visible_render_merges_authored_hints() -> None:
    clear_goc_yaml_slice_cache()
    bundle, markers = run_visible_render(
        module_id="god_of_carnage",
        committed_result={"committed_effects": ["test"], "commit_applied": True},
        validation_outcome={"status": "approved"},
        generation={
            "content": "Short exchange at the table.",
            "metadata": {"structured_output": {"spoken_lines": [], "action_lines": []}},
        },
        transition_pattern="hard",
        render_context={
            "current_scene_id": "living_room",
            "pacing_mode": "compressed",
            "scene_guidance": {},
            "character_profile_snippet": {},
            "scene_guidance_snippets": {},
        },
    )
    assert "truth_aligned" in markers
    support = bundle.get("render_support") or {}
    hints = support.get("director_surface_hints") or []
    assert support.get("player_visible") is False
    sources = {str(item.get("source") or "") for item in hints if isinstance(item, dict)}
    assert any("hints/" in source for source in sources)


def test_template_hints_load_without_error() -> None:
    module_dir = Path(__file__).resolve().parents[2] / "content" / "modules" / "_template"
    hints = load_module_director_surface_hints(module_dir)
    assert len(hints) == 1
    assert hints[0].get("hint_id") == "template_hint_example_phase_context"
