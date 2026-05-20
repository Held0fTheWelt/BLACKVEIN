"""Validation status fields surfaced on the final runtime result."""

from __future__ import annotations

_VALIDATION_STATUS_FIELDS = (
    ("scene_energy", "scene_energy_validation_status", "scene_energy_contract_violation"),
    ("pacing_rhythm", "pacing_rhythm_validation_status", "pacing_rhythm_contract_violation"),
    ("temporal_control", "temporal_control_validation_status", "temporal_control_contract_violation"),
    (
        "improvisational_coherence",
        "improvisational_coherence_validation_status",
        "improvisational_coherence_contract_violation",
    ),
    ("social_pressure", "social_pressure_validation_status", "social_pressure_contract_violation"),
    ("tonal_consistency", "tonal_consistency_validation_status", "tonal_consistency_contract_violation"),
    ("relationship_state", "relationship_state_validation_status", "relationship_state_contract_violation"),
    ("genre_awareness", "genre_awareness_validation_status", "genre_awareness_contract_violation"),
    (
        "symbolic_object_resonance",
        "symbolic_object_resonance_validation_status",
        "symbolic_object_resonance_contract_violation",
    ),
    ("sensory_context", "sensory_context_validation_status", "sensory_context_contract_violation"),
    ("information_disclosure", "information_disclosure_validation_status", "information_disclosure_contract_violation"),
    ("dramatic_irony", "dramatic_irony_validation_status", "dramatic_irony_contract_violation"),
    ("expectation_variation", "expectation_variation_validation_status", "expectation_variation_contract_violation"),
    ("narrative_momentum", "narrative_momentum_validation_status", "narrative_momentum_contract_violation"),
    (
        "meta_narrative_awareness",
        "meta_narrative_awareness_validation_status",
        "meta_narrative_awareness_contract_violation",
    ),
    ("npc_initiative", "npc_initiative_validation_status", "npc_agency_contract_violation"),
)
