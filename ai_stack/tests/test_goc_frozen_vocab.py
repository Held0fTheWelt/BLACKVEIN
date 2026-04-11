"""Frozen vocabulary parity with VERTICAL_SLICE_CONTRACT_GOC.md §5."""

from __future__ import annotations

import pytest

from ai_stack.goc_frozen_vocab import (
    CONTINUITY_CLASSES,
    FAILURE_CLASSES,
    GATE_FAMILIES,
    PACING_MODES,
    SCENE_FUNCTIONS,
    SILENCE_BREVITY_MODES,
    TRANSITION_PATTERNS,
    VISIBILITY_CLASSES,
    assert_pacing_mode,
    assert_scene_function,
    assert_transition_pattern,
)
from ai_stack.scene_director_goc import select_single_scene_function as sd_select


def test_scene_function_count_matches_freeze() -> None:
    assert len(SCENE_FUNCTIONS) == 8


def test_pacing_and_silence_sets_closed() -> None:
    assert PACING_MODES == frozenset(
        {"standard", "compressed", "thin_edge", "containment", "multi_pressure"}
    )
    assert SILENCE_BREVITY_MODES == frozenset({"normal", "brief", "withheld", "expanded"})


def test_gate_families_match_gate_policy_doc() -> None:
    assert GATE_FAMILIES == frozenset(
        {"slice_boundary", "turn_integrity", "dramatic_quality", "diagnostic_sufficiency"}
    )


def test_transition_patterns_disjoint_from_scene_functions() -> None:
    assert not SCENE_FUNCTIONS & TRANSITION_PATTERNS


def test_assert_scene_function_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        assert_scene_function("not_a_scene_function")


def test_assert_pacing_and_transition_helpers() -> None:
    assert assert_pacing_mode("standard") == "standard"
    with pytest.raises(ValueError):
        assert_pacing_mode("fast")
    assert assert_transition_pattern("hard") == "hard"


def test_section_3_5_priority_revealed_over_repair() -> None:
    implied = {
        "repair_or_stabilize": "repair_attempt",
        "reveal_surface": "revealed_fact",
    }
    chosen = sd_select(["repair_or_stabilize", "reveal_surface"], implied_continuity_by_function=implied)
    assert chosen == "reveal_surface"


def test_section_3_5_lexicographic_tiebreak() -> None:
    implied = {"escalate_conflict": "situational_pressure", "probe_motive": "situational_pressure"}
    chosen = sd_select(["probe_motive", "escalate_conflict"], implied_continuity_by_function=implied)
    assert chosen == "escalate_conflict"


def test_continuity_and_failure_classes_non_empty() -> None:
    assert CONTINUITY_CLASSES
    assert FAILURE_CLASSES
    assert VISIBILITY_CLASSES
