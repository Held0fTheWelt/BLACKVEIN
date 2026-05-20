"""Outcome fields that apply failure metadata to aspect records."""

from __future__ import annotations

_OUTCOME_FAILURE_SPECS = (
    ("dramatic_irony_failure", "dramatic_irony_validation_v1", "dramatic_irony_contract_violation", "dramatic_irony_validation_failed", False),
    (
        "expectation_variation_failure",
        "expectation_variation_validation_v1",
        "expectation_variation_contract_violation",
        "expectation_variation_validation_failed",
        False,
    ),
    (
        "narrative_momentum_failure",
        "narrative_momentum_validation_v1",
        "narrative_momentum_contract_violation",
        "narrative_momentum_validation_failed",
        False,
    ),
    (
        "meta_narrative_awareness_failure",
        "meta_narrative_awareness_validation_v1",
        "meta_narrative_awareness_contract_violation",
        "meta_narrative_awareness_validation_failed",
        False,
    ),
    ("scene_energy_failure", "scene_energy_validation_v1", "scene_energy_contract_violation", "scene_energy_validation_failed", True),
    ("pacing_rhythm_failure", "pacing_rhythm_validation_v1", "pacing_rhythm_contract_violation", "pacing_rhythm_validation_failed", False),
    (
        "temporal_control_failure",
        "temporal_control_validation_v1",
        "temporal_control_contract_violation",
        "temporal_control_validation_failed",
        False,
    ),
    (
        "improvisational_coherence_failure",
        "improvisational_coherence_validation_v1",
        "improvisational_coherence_contract_violation",
        "improvisational_coherence_validation_failed",
        False,
    ),
    ("social_pressure_failure", "social_pressure_validation_v1", "social_pressure_contract_violation", "social_pressure_validation_failed", False),
    (
        "tonal_consistency_failure",
        "tonal_consistency_validation_v1",
        "tonal_consistency_contract_violation",
        "tonal_consistency_validation_failed",
        False,
    ),
    (
        "relationship_state_failure",
        "relationship_state_validation_v1",
        "relationship_state_contract_violation",
        "relationship_state_validation_failed",
        False,
    ),
    ("genre_awareness_failure", "genre_awareness_validation_v1", "genre_awareness_contract_violation", "genre_awareness_validation_failed", False),
    (
        "symbolic_object_resonance_failure",
        "symbolic_object_resonance_validation_v1",
        "symbolic_object_resonance_contract_violation",
        "symbolic_object_resonance_validation_failed",
        False,
    ),
    ("sensory_context_failure", "sensory_context_validation_v1", "sensory_context_contract_violation", "sensory_context_validation_failed", False),
    (
        "information_disclosure_failure",
        "information_disclosure_validation_v1",
        "information_disclosure_contract_violation",
        "information_disclosure_validation_failed",
        False,
    ),
)
