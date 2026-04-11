"""Scene-direction matrix contract vs roadmap registry (gate G4)."""

from __future__ import annotations

from ai_stack.scene_direction_subdecision_matrix import (
    MATRIX_CONTRACT_VERSION,
    SCENE_DIRECTION_SUBDECISION_ROWS,
    assert_matrix_aligned_with_roadmap_registry,
    scene_direction_labels_from_matrix,
)


def test_matrix_version_is_stable_string() -> None:
    assert MATRIX_CONTRACT_VERSION.startswith("goc_scene_direction_matrix_")


def test_matrix_covers_scene_functions() -> None:
    scene_rows = [r for r in SCENE_DIRECTION_SUBDECISION_ROWS if r["category"] == "scene_function"]
    assert len(scene_rows) == 8


def test_matrix_matches_roadmap_scene_direction_labels() -> None:
    assert_matrix_aligned_with_roadmap_registry()
    labels = scene_direction_labels_from_matrix()
    assert "establish_pressure" in labels
    assert "thin_edge" in labels


_G4_ROW_KEYS = frozenset(
    {
        "subdecision_label",
        "label_id",
        "category",
        "frozen_vocab_value",
        "implementation_reference",
        "decision_class",
        "owner_layer",
        "legal_input_seam",
        "legal_output_seam",
        "validation_seam",
        "failure_seam",
        "diagnostics_visibility",
    }
)


def test_each_matrix_row_has_full_g4_columns() -> None:
    for row in SCENE_DIRECTION_SUBDECISION_ROWS:
        assert set(row.keys()) == _G4_ROW_KEYS, row
