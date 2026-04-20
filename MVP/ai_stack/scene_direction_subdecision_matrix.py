"""Explicit scene-direction subdecision matrix for GoC (roadmap §4.2, gate G4).

Machine-readable source of truth for frozen subdecision labels and G4 seam metadata.
Must stay consistent with ``ai_stack.scene_director_goc`` and ``ai_stack.goc_frozen_vocab``.
"""

from __future__ import annotations

from typing import Any, Final

from ai_stack.goc_frozen_vocab import (
    CONTINUITY_CLASSES,
    PACING_MODES,
    SCENE_FUNCTIONS,
    SILENCE_BREVITY_MODES,
    TRANSITION_PATTERNS,
    VISIBILITY_CLASSES,
)

MATRIX_CONTRACT_VERSION: Final[str] = "goc_scene_direction_matrix_v1"

_CATEGORY_MEMBERS: Final[dict[str, frozenset[str]]] = {
    "scene_function": SCENE_FUNCTIONS,
    "pacing_mode": PACING_MODES,
    "silence_brevity_mode": SILENCE_BREVITY_MODES,
    "continuity_class": CONTINUITY_CLASSES,
    "visibility_class": VISIBILITY_CLASSES,
    "transition_pattern": TRANSITION_PATTERNS,
}

# G4 matrix columns (roadmap §6.4): defaults per category (same owner/seam pattern for all labels in category).
_CATEGORY_G4_DEFAULTS: Final[dict[str, dict[str, str]]] = {
    "scene_function": {
        "decision_class": "scene_direction",
        "owner_layer": "deterministic_core",
        "legal_input_seam": "interpret_input,director_assess_scene,goc_resolve_canonical_content",
        "legal_output_seam": "director_select_dramatic_parameters",
        "validation_seam": "validate_seam",
        "failure_seam": "validate_seam",
        "diagnostics_visibility": "graph_diagnostics.dramatic_review,operator_canonical_turn_record",
    },
    "pacing_mode": {
        "decision_class": "scene_direction",
        "owner_layer": "deterministic_core",
        "legal_input_seam": "interpret_input,director_assess_scene",
        "legal_output_seam": "director_select_dramatic_parameters",
        "validation_seam": "validate_seam",
        "failure_seam": "validate_seam",
        "diagnostics_visibility": "graph_diagnostics.dramatic_review",
    },
    "silence_brevity_mode": {
        "decision_class": "scene_direction",
        "owner_layer": "deterministic_core",
        "legal_input_seam": "interpret_input,director_assess_scene",
        "legal_output_seam": "director_select_dramatic_parameters",
        "validation_seam": "validate_seam",
        "failure_seam": "validate_seam",
        "diagnostics_visibility": "graph_diagnostics.dramatic_review",
    },
    "continuity_class": {
        "decision_class": "continuity_carry",
        "owner_layer": "deterministic_core",
        "legal_input_seam": "prior_continuity_impacts,director_assess_scene",
        "legal_output_seam": "director_select_dramatic_parameters,commit_seam",
        "validation_seam": "validate_seam",
        "failure_seam": "validate_seam",
        "diagnostics_visibility": "graph_diagnostics.dramatic_review",
    },
    "visibility_class": {
        "decision_class": "bounded_realization",
        "owner_layer": "model_assisted_realization",
        "legal_input_seam": "render_visible,committed_result,validation_outcome",
        "legal_output_seam": "render_visible",
        "validation_seam": "validate_seam",
        "failure_seam": "render_visible",
        "diagnostics_visibility": "visibility_class_markers,operator_canonical_turn_record",
    },
    "transition_pattern": {
        "decision_class": "bounded_realization",
        "owner_layer": "deterministic_core",
        "legal_input_seam": "commit_seam,validation_outcome,graph_errors",
        "legal_output_seam": "render_visible",
        "validation_seam": "validate_seam",
        "failure_seam": "package_output",
        "diagnostics_visibility": "graph_diagnostics_summary,transition_pattern",
    },
}


def assert_subdecision_label_in_matrix(category: str, value: str) -> str:
    """Return ``value`` if it is a registered matrix label for ``category``; else raise."""
    allowed = _CATEGORY_MEMBERS.get(category)
    if allowed is None:
        raise ValueError(f"unknown scene-direction matrix category: {category!r}")
    if value not in allowed:
        raise ValueError(f"label {value!r} not in matrix category {category!r}")
    return value


def _rows_for_frozen_set(
    *,
    category: str,
    members: frozenset[str],
    impl_ref: str,
) -> list[dict[str, Any]]:
    g4 = _CATEGORY_G4_DEFAULTS[category]
    rows: list[dict[str, Any]] = []
    for label in sorted(members):
        rows.append(
            {
                "subdecision_label": f"{category}:{label}",
                "label_id": f"{category}:{label}",
                "category": category,
                "frozen_vocab_value": label,
                "implementation_reference": impl_ref,
                "decision_class": g4["decision_class"],
                "owner_layer": g4["owner_layer"],
                "legal_input_seam": g4["legal_input_seam"],
                "legal_output_seam": g4["legal_output_seam"],
                "validation_seam": g4["validation_seam"],
                "failure_seam": g4["failure_seam"],
                "diagnostics_visibility": g4["diagnostics_visibility"],
            }
        )
    return rows


SCENE_DIRECTION_SUBDECISION_ROWS: Final[list[dict[str, Any]]] = (
    _rows_for_frozen_set(
        category="scene_function",
        members=SCENE_FUNCTIONS,
        impl_ref="ai_stack.scene_director_goc:build_responder_and_function",
    )
    + _rows_for_frozen_set(
        category="pacing_mode",
        members=PACING_MODES,
        impl_ref="ai_stack.scene_director_goc:build_pacing_and_silence",
    )
    + _rows_for_frozen_set(
        category="silence_brevity_mode",
        members=SILENCE_BREVITY_MODES,
        impl_ref="ai_stack.scene_director_goc:build_pacing_and_silence",
    )
    + _rows_for_frozen_set(
        category="continuity_class",
        members=CONTINUITY_CLASSES,
        impl_ref="ai_stack.scene_director_goc:prior_continuity_classes,build_responder_and_function",
    )
    + _rows_for_frozen_set(
        category="visibility_class",
        members=VISIBILITY_CLASSES,
        impl_ref="ai_stack.goc_turn_seams:run_visible_render",
    )
    + _rows_for_frozen_set(
        category="transition_pattern",
        members=TRANSITION_PATTERNS,
        impl_ref="ai_stack.langgraph_runtime:_render_visible,package_output",
    )
)


def scene_direction_labels_from_matrix() -> frozenset[str]:
    """Return the set of all ``frozen_vocab_value`` entries in the matrix."""
    return frozenset(str(r["frozen_vocab_value"]) for r in SCENE_DIRECTION_SUBDECISION_ROWS)


def assert_matrix_aligned_with_roadmap_registry() -> None:
    """Cross-check matrix coverage vs ``goc_roadmap_semantic_surface`` union (development / tests)."""
    from ai_stack.goc_roadmap_semantic_surface import SCENE_DIRECTION_SUBDECISION_LABELS

    derived = scene_direction_labels_from_matrix()
    if derived != SCENE_DIRECTION_SUBDECISION_LABELS:
        missing = SCENE_DIRECTION_SUBDECISION_LABELS - derived
        extra = derived - SCENE_DIRECTION_SUBDECISION_LABELS
        raise AssertionError(f"scene direction matrix drift: missing={missing!r} extra={extra!r}")
