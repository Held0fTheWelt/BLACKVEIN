"""Shape the public runtime-validation payload returned to the executor."""

from __future__ import annotations

from .contracts import _RuntimeAspectBuild
from .dependencies import *
from .validation_status_fields import _VALIDATION_STATUS_FIELDS

def _result(ctx: _RuntimeAspectBuild) -> dict[str, Any]:
    return {
        "outcome": ctx.outcome,
        "actor_lane_validation": ctx.actor_lane_validation,
        "turn_aspect_ledger": ctx.ledger,
        "narrator_authority": ctx.narrator_authority,
        "npc_authority": ctx.npc_authority,
        "capability_selection": ctx.capability_selection,
        "voice_consistency_validation": ctx.validations.get("voice_consistency"),
        "scene_energy_validation": ctx.validations.get("scene_energy"),
        "pacing_rhythm_validation": ctx.validations.get("pacing_rhythm"),
        "temporal_control_validation": ctx.validations.get("temporal_control"),
        "improvisational_coherence_validation": ctx.validations.get("improvisational_coherence"),
        "social_pressure_validation": ctx.validations.get("social_pressure"),
        "tonal_consistency_validation": ctx.validations.get("tonal_consistency"),
        "relationship_state_validation": ctx.validations.get("relationship_state"),
        "genre_awareness_validation": ctx.validations.get("genre_awareness"),
        "symbolic_object_resonance_validation": ctx.validations.get("symbolic_object_resonance"),
        "sensory_context_validation": ctx.validations.get("sensory_context"),
        "information_disclosure_validation": ctx.validations.get("information_disclosure"),
        "dramatic_irony_validation": ctx.validations.get("dramatic_irony"),
        "expectation_variation_validation": ctx.validations.get("expectation_variation"),
        "narrative_momentum_validation": ctx.validations.get("narrative_momentum"),
        "meta_narrative_awareness_validation": ctx.validations.get("meta_narrative_awareness"),
        "npc_initiative_validation": ctx.validations.get("npc_initiative"),
        "authority_failure": ctx.failures.get("authority_failure"),
        "capability_failure": ctx.failures.get("capability_failure"),
        "scene_energy_failure": ctx.failures.get("scene_energy_failure"),
        "temporal_control_failure": ctx.failures.get("temporal_control_failure"),
        "improvisational_coherence_failure": ctx.failures.get("improvisational_coherence_failure"),
        "social_pressure_failure": ctx.failures.get("social_pressure_failure"),
        "tonal_consistency_failure": ctx.failures.get("tonal_consistency_failure"),
        "relationship_state_failure": ctx.failures.get("relationship_state_failure"),
        "genre_awareness_failure": ctx.failures.get("genre_awareness_failure"),
        "symbolic_object_resonance_failure": ctx.failures.get("symbolic_object_resonance_failure"),
        "sensory_context_failure": ctx.failures.get("sensory_context_failure"),
        "information_disclosure_failure": ctx.failures.get("information_disclosure_failure"),
        "dramatic_irony_failure": ctx.failures.get("dramatic_irony_failure"),
        "expectation_variation_failure": ctx.failures.get("expectation_variation_failure"),
        "narrative_momentum_failure": ctx.failures.get("narrative_momentum_failure"),
        "meta_narrative_awareness_failure": ctx.failures.get("meta_narrative_awareness_failure"),
        "npc_agency_failure": ctx.failures.get("npc_agency_failure"),
    }
