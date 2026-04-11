"""Roadmap §4.2 semantic registry integrity (gate G1)."""

from __future__ import annotations

import pytest

from ai_stack.goc_roadmap_semantic_surface import ROADMAP_SEMANTIC_REGISTRY


def test_roadmap_registry_has_all_mandatory_families() -> None:
    expected = {
        "task_types",
        "model_roles",
        "fallback_classes",
        "decision_classes",
        "routing_labels",
        "scene_direction_subdecision_labels",
        "runtime_profile_labels",
        "controlled_reason_codes",
    }
    assert set(ROADMAP_SEMANTIC_REGISTRY.keys()) == expected


@pytest.mark.parametrize(
    "name,minimum",
    [
        ("task_types", 10),
        ("routing_labels", 8),
        ("scene_direction_subdecision_labels", 20),
    ],
)
def test_registry_sets_are_substantive(name: str, minimum: int) -> None:
    assert len(ROADMAP_SEMANTIC_REGISTRY[name]) >= minimum


def test_controlled_reason_codes_matches_routing_labels() -> None:
    assert ROADMAP_SEMANTIC_REGISTRY["controlled_reason_codes"] == ROADMAP_SEMANTIC_REGISTRY["routing_labels"]
