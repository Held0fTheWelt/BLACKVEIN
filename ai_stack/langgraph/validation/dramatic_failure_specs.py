"""Outcome keys that map dramatic validation failures into retry signals."""

from __future__ import annotations

_DRAMATIC_FAILURE_SPECS = (
    ("scene_energy", "scene_energy_validation_failed", "feedback_code", "failure_codes", "failure_codes"),
    ("pacing_rhythm", "pacing_rhythm_validation_failed", "feedback_code", "failure_codes", "failure_codes"),
    ("temporal_control", "temporal_control_validation_failed", "feedback_code", "failure_codes", "failure_codes"),
    (
        "improvisational_coherence",
        "improvisational_coherence_validation_failed",
        "feedback_code",
        "failure_codes",
        "failure_codes",
    ),
    ("social_pressure", "social_pressure_validation_failed", "feedback_code", "failure_codes", "failure_codes"),
    ("tonal_consistency", "tonal_consistency_validation_failed", "feedback_code", "failure_codes", "failure_codes"),
    ("relationship_state", "relationship_state_validation_failed", None, "failure_codes", "failure_codes"),
    ("genre_awareness", "genre_awareness_validation_failed", "feedback_code", "failure_codes", "failure_codes"),
    (
        "symbolic_object_resonance",
        "symbolic_object_resonance_validation_failed",
        "feedback_code",
        "failure_codes",
        "failure_codes",
    ),
    ("sensory_context", "sensory_context_validation_failed", "feedback_code", "failure_codes", "failure_codes"),
    (
        "information_disclosure",
        "information_disclosure_validation_failed",
        "feedback_code",
        "failure_codes",
        "failure_codes",
    ),
    ("dramatic_irony", "dramatic_irony_validation_failed", "feedback_code", "violation_codes", "violation_codes"),
    (
        "expectation_variation",
        "expectation_variation_validation_failed",
        "feedback_code",
        "failure_codes",
        "failure_codes",
    ),
    ("narrative_momentum", "narrative_momentum_validation_failed", "feedback_code", "failure_codes", "failure_codes"),
    (
        "meta_narrative_awareness",
        "meta_narrative_awareness_validation_failed",
        "feedback_code",
        "failure_codes",
        "failure_codes",
    ),
)
