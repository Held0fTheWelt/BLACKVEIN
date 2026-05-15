from __future__ import annotations

import re

import pytest

from ai_stack.capability_selector import validate_semantic_capability_name
from ai_stack.capability_validator_registry import (
    CANONICAL_OBSERVER_DIAGNOSTIC_IDS,
    KNOWN_TURN_CLASSES,
    TURN_CLASS_DEGRADED_OR_FALLBACK_TURN,
    TURN_CLASS_ENFORCED_VALIDATORS,
    TURN_CLASS_NPC_CONFLICT_TURN,
    TURN_CLASS_NORMAL_PLAYER_TURN,
    TURN_CLASS_OPENING_SCENE,
    TURN_CLASS_RECOVERY_TURN,
    TURN_CLASS_SYSTEM_TRANSITION,
    TurnClassRegistryCoverage,
    assert_turn_class_registry_coverage,
    build_available_semantic_validator_registry,
    build_degraded_or_fallback_enforced_semantic_validator_registry,
    build_default_semantic_validator_registry,
    build_npc_conflict_enforced_semantic_validator_registry,
    build_opening_enforced_semantic_validator_registry,
    build_player_turn_enforced_semantic_validator_registry,
    build_recovery_turn_enforced_semantic_validator_registry,
    build_system_transition_enforced_semantic_validator_registry,
    get_registry_coverage_for_turn_class,
    get_turn_class_enforced_validators,
    get_typical_observer_diagnostic_ids_for_turn_class,
    normalize_turn_class_key,
)


_active_pi_key = re.compile(
    r"(?<![A-Za-z0-9])pi_\d+\b|(?<![A-Za-z0-9])pi\d+_[A-Za-z0-9_]+\b|Π\d+\b",
    re.IGNORECASE,
)


def test_turn_class_enforced_match_registry_map() -> None:
    for tc in KNOWN_TURN_CLASSES:
        assert get_turn_class_enforced_validators(tc) == TURN_CLASS_ENFORCED_VALIDATORS[tc]


def test_turn_class_coverage_map_matches_known_turn_classes() -> None:
    assert set(KNOWN_TURN_CLASSES) == set(TURN_CLASS_ENFORCED_VALIDATORS.keys())


def test_opening_registry_covers_all_opening_enforced_validators() -> None:
    cov = assert_turn_class_registry_coverage(
        TURN_CLASS_OPENING_SCENE,
        build_opening_enforced_semantic_validator_registry(),
    )
    assert cov.coverage_complete
    assert set(cov.validator_ids_registered) == set(cov.required_enforced_validator_ids)


def test_player_turn_registry_covers_all_player_turn_enforced_validators() -> None:
    cov = assert_turn_class_registry_coverage(
        TURN_CLASS_NORMAL_PLAYER_TURN,
        build_player_turn_enforced_semantic_validator_registry(),
    )
    assert cov.coverage_complete
    assert set(cov.validator_ids_registered) == set(cov.required_enforced_validator_ids)


def test_npc_conflict_registry_covers_all_npc_conflict_enforced_validators() -> None:
    cov = assert_turn_class_registry_coverage(
        TURN_CLASS_NPC_CONFLICT_TURN,
        build_npc_conflict_enforced_semantic_validator_registry(),
    )
    assert cov.coverage_complete
    assert set(cov.validator_ids_registered) == set(cov.required_enforced_validator_ids)


def test_recovery_turn_registry_covers_all_recovery_turn_enforced_validators() -> None:
    cov = assert_turn_class_registry_coverage(
        TURN_CLASS_RECOVERY_TURN,
        build_recovery_turn_enforced_semantic_validator_registry(),
    )
    assert cov.coverage_complete
    assert set(cov.validator_ids_registered) == set(cov.required_enforced_validator_ids)


def test_system_transition_registry_covers_all_system_transition_enforced_validators() -> None:
    cov = assert_turn_class_registry_coverage(
        TURN_CLASS_SYSTEM_TRANSITION,
        build_system_transition_enforced_semantic_validator_registry(),
    )
    assert cov.coverage_complete
    assert set(cov.validator_ids_registered) == set(cov.required_enforced_validator_ids)


def test_degraded_fallback_registry_covers_all_degraded_turn_enforced_validators() -> None:
    cov = assert_turn_class_registry_coverage(
        TURN_CLASS_DEGRADED_OR_FALLBACK_TURN,
        build_degraded_or_fallback_enforced_semantic_validator_registry(),
    )
    assert cov.coverage_complete
    assert set(cov.validator_ids_registered) == set(cov.required_enforced_validator_ids)


def test_default_registry_remains_empty() -> None:
    assert build_default_semantic_validator_registry() == {}


def test_turn_class_coverage_uses_semantic_ids_only() -> None:
    for turn_class in KNOWN_TURN_CLASSES:
        normalize_turn_class_key(turn_class)
        assert not _active_pi_key.search(turn_class)
        for vid in get_turn_class_enforced_validators(turn_class):
            validate_semantic_capability_name(vid)
            assert not _active_pi_key.search(vid)


def test_observer_diagnostics_are_not_required_blocking_validators() -> None:
    for turn_class in KNOWN_TURN_CLASSES:
        enforced = set(get_turn_class_enforced_validators(turn_class))
        assert enforced.isdisjoint(CANONICAL_OBSERVER_DIAGNOSTIC_IDS)
        for oid in get_typical_observer_diagnostic_ids_for_turn_class(turn_class):
            validate_semantic_capability_name(oid)
            assert oid.endswith("_diagnostic")


def test_missing_turn_class_fails_closed() -> None:
    with pytest.raises(ValueError):
        normalize_turn_class_key("")
    with pytest.raises(ValueError, match="Unknown ADR-0041 turn class"):
        get_turn_class_enforced_validators("not_a_known_turn_class")


def test_unavailable_validators_are_reported_not_passed() -> None:
    cov_empty = get_registry_coverage_for_turn_class(TURN_CLASS_OPENING_SCENE, {})
    assert cov_empty.coverage_complete is False
    assert cov_empty.validator_ids_missing == cov_empty.required_enforced_validator_ids
    assert cov_empty.validator_ids_registered == ()

    full = build_opening_enforced_semantic_validator_registry()
    assert get_registry_coverage_for_turn_class(TURN_CLASS_OPENING_SCENE, full).coverage_complete

    missing_one = {k: v for k, v in full.items() if k != "scene_energy_contract"}
    cov_partial = get_registry_coverage_for_turn_class(TURN_CLASS_OPENING_SCENE, missing_one)
    assert cov_partial.coverage_complete is False
    assert "scene_energy_contract" in cov_partial.validator_ids_missing

    assert_turn_class_registry_coverage(TURN_CLASS_OPENING_SCENE, {}, require_complete=False)
    with pytest.raises(AssertionError):
        assert_turn_class_registry_coverage(TURN_CLASS_OPENING_SCENE, {}, require_complete=True)
