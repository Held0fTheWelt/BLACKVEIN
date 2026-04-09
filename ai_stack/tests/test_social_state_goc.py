"""Social state projection from continuity and threads."""

from __future__ import annotations

from ai_stack.scene_director_goc import build_scene_assessment
from ai_stack.social_state_goc import build_social_state_record, social_state_fingerprint


def test_social_state_fingerprint_stable() -> None:
    sa = build_scene_assessment(
        module_id="god_of_carnage",
        current_scene_id="living_room",
        canonical_yaml={"content": {"setting": "Paris", "narrative_scope": "domestic"}},
        prior_continuity_impacts=[{"class": "blame_pressure"}],
        yaml_slice=None,
    )
    s1 = build_social_state_record(
        prior_continuity_impacts=[{"class": "blame_pressure"}],
        active_narrative_threads=[{"thread_id": "t1", "thread_kind": "x", "status": "open", "intensity": 2, "related_entities": []}],
        thread_pressure_summary="heat",
        scene_assessment=sa,
    )
    s2 = build_social_state_record(
        prior_continuity_impacts=[{"class": "blame_pressure"}],
        active_narrative_threads=[{"thread_id": "t1", "thread_kind": "x", "status": "open", "intensity": 2, "related_entities": []}],
        thread_pressure_summary="heat",
        scene_assessment=sa,
    )
    assert social_state_fingerprint(s1) == social_state_fingerprint(s2)
