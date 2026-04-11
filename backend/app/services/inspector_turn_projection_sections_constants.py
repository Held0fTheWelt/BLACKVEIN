"""Konstanten für Inspector-Projektions-Sektionen (DS-018)."""

from __future__ import annotations

COMPARISON_RESERVED_FIELDS: tuple[str, ...] = (
    "timeline_alignment",
    "cross_run_delta",
    "coverage_heatmap",
)

LEGACY_GATE_SUMMARY_KEYS: frozenset[str] = frozenset(
    {
        "dominant_rejection_category",
        "scene_function_mismatch_score",
        "character_implausibility_score",
        "continuity_pressure_score",
        "fluency_risk_score",
    }
)

SEMANTIC_FLOW_STAGES: tuple[tuple[str, str], ...] = (
    ("player_input", "Player input"),
    ("semantic_move", "Semantic move"),
    ("social_state", "Social state"),
    ("character_mind", "Character mind"),
    ("scene_plan", "Scene plan"),
    ("proposed_narrative", "Candidate / proposed narrative"),
    ("dramatic_effect_gate", "Dramatic effect gate"),
    ("validation", "Validation"),
    ("commit", "Commit"),
    ("visible_output", "Visible output"),
)

PLANNER_BOUND_STAGES: frozenset[str] = frozenset(
    {"semantic_move", "social_state", "character_mind", "scene_plan"}
)

SUPPORT_NOTE_FULL_GOC = (
    "Full GoC dramatic-effect evaluation path; bounded semantic planner contracts apply for this module."
)
SUPPORT_NOTE_NON_GOC = (
    "Non-GoC module: dramatic-effect evaluation uses the canonical non-GoC evaluator; "
    "semantic planner maturity is GoC-local — do not assume GoC-equivalent semantics here."
)
