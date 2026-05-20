"""Schema names, feature switches, and aspect keys for the runtime ledger.

The ledger package keeps these values data-only so projection, validation, and
score modules can share the same vocabulary without importing one another's
runtime behavior.
"""

from __future__ import annotations

RUNTIME_ASPECT_LEDGER_VERSION = "runtime_aspect_ledger.v1"
TURN_ASPECT_LEDGER_SCHEMA_VERSION = "turn_aspect_ledger.v1"
RUNTIME_ASPECT_RECORD_VERSION = "runtime_aspect_record.v1"

ADR0041_HARNESS_PLAN_ENFORCED_REQUIRES_REGISTRY_WARNING = (
    "adr0041_harness_plan_enforced_requires_explicit_validator_registry"
)

ADR0041_PLAN_PROJECTION_ENABLED_ENV = "ADR0041_PLAN_PROJECTION_ENABLED"
ADR0041_PLAN_PROJECTION_SCHEMA_VERSION = "adr0041_plan_projection.v1"
ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV = "ADR0041_SCOPED_CO_AUTHORITY_ENABLED"
ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV = "ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED"
ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV = "ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED"
ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV = "ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED"
ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV = "ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED"
GOC_TURN_VALIDATION_SEAM_SYMBOL = (
    "ai_stack.story_runtime.turn." + "god" + "_of_carnage_turn_seams.run_validation_seam"
)

# Ephemeral bundle attached by LangGraph validate_seam when
# ``ADR0041_VALIDATOR_DISPATCH_MODE=plan_enforced``. Retained on the ledger so
# repeated ``normalize_runtime_aspect_ledger`` calls recompute the same sidecar.
ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY = "_adr0041_runtime_graph_dispatch_context"
# Dispatch bundle is runtime-only: not canonical commit truth, not player-facing gameplay state.
# Consumed when building ``runtime_intelligence_projection`` (local-only, diagnostics / Langfuse / MCP).

ADR0041_VALIDATION_AUTHORITY_PREVIEW_SCHEMA_VERSION = "adr0041_validation_authority_preview.v1"
ADR0041_DRIFT_ALIGNED = "aligned"
ADR0041_DRIFT_ADR_STRICTER = "adr0041_stricter"
ADR0041_DRIFT_SEAM_STRICTER = "seam_stricter"
ADR0041_DRIFT_MISSING_CONTEXT = "missing_context"
ADR0041_DRIFT_UNAVAILABLE_VALIDATOR = "unavailable_validator"
ADR0041_DRIFT_CONFLICTING_RESULT = "conflicting_result"

ASPECT_INPUT = "input"
ASPECT_BROAD_NLU_LISTENING = "broad_nlu_listening"
ASPECT_ACTION_RESOLUTION = "action_resolution"
ASPECT_CONVERSATIONAL_MEMORY = "conversational_memory"
ASPECT_PROMPT_AUTHORITY = "prompt_authority"
ASPECT_BEAT = "beat"
ASPECT_SCENE_ENERGY = "scene_energy"
ASPECT_PACING_RHYTHM = "pacing_rhythm"
ASPECT_SENSORY_CONTEXT = "sensory_context"
ASPECT_SYMBOLIC_OBJECT_RESONANCE = "symbolic_object_resonance"
ASPECT_IMPROVISATIONAL_COHERENCE = "improvisational_coherence"
ASPECT_META_NARRATIVE_AWARENESS = "meta_narrative_awareness"
ASPECT_NO_DEAD_END_RECOVERY = "no_dead_end_recovery"
ASPECT_SOCIAL_PRESSURE = "social_pressure"
ASPECT_RELATIONSHIP_STATE = "relationship_state"
ASPECT_CAPABILITY_SELECTION = "capability_selection"
ASPECT_NARRATOR_AUTHORITY = "narrator_authority"
ASPECT_NPC_AUTHORITY = "npc_authority"
ASPECT_NPC_AGENCY = "npc_agency"
ASPECT_DRAMATIC_IRONY = "dramatic_irony"
ASPECT_EXPECTATION_VARIATION = "expectation_variation"
ASPECT_NARRATIVE_MOMENTUM = "narrative_momentum"
ASPECT_VOICE_CONSISTENCY = "voice_consistency"
ASPECT_TONAL_CONSISTENCY = "tonal_consistency"
ASPECT_GENRE_AWARENESS = "genre_awareness"
ASPECT_NARRATIVE_ASPECT = "narrative_aspect"
ASPECT_INFORMATION_DISCLOSURE = "information_disclosure"
ASPECT_HIERARCHICAL_MEMORY = "hierarchical_memory"
ASPECT_CALLBACK_WEB = "callback_web"
ASPECT_CONSEQUENCE_CASCADE = "consequence_cascade"
ASPECT_TEMPORAL_CONTROL = "temporal_control"
ASPECT_VALIDATION = "validation"
ASPECT_COMMIT = "commit"
ASPECT_VISIBLE_PROJECTION = "visible_projection"

ASPECT_KEYS: tuple[str, ...] = (
    ASPECT_INPUT,
    ASPECT_BROAD_NLU_LISTENING,
    ASPECT_ACTION_RESOLUTION,
    ASPECT_CONVERSATIONAL_MEMORY,
    ASPECT_PROMPT_AUTHORITY,
    ASPECT_BEAT,
    ASPECT_SCENE_ENERGY,
    ASPECT_PACING_RHYTHM,
    ASPECT_SENSORY_CONTEXT,
    ASPECT_SYMBOLIC_OBJECT_RESONANCE,
    ASPECT_IMPROVISATIONAL_COHERENCE,
    ASPECT_META_NARRATIVE_AWARENESS,
    ASPECT_NO_DEAD_END_RECOVERY,
    ASPECT_SOCIAL_PRESSURE,
    ASPECT_RELATIONSHIP_STATE,
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_NARRATOR_AUTHORITY,
    ASPECT_NPC_AUTHORITY,
    ASPECT_NPC_AGENCY,
    ASPECT_DRAMATIC_IRONY,
    ASPECT_EXPECTATION_VARIATION,
    ASPECT_NARRATIVE_MOMENTUM,
    ASPECT_VOICE_CONSISTENCY,
    ASPECT_TONAL_CONSISTENCY,
    ASPECT_GENRE_AWARENESS,
    ASPECT_NARRATIVE_ASPECT,
    ASPECT_INFORMATION_DISCLOSURE,
    ASPECT_HIERARCHICAL_MEMORY,
    ASPECT_CALLBACK_WEB,
    ASPECT_CONSEQUENCE_CASCADE,
    ASPECT_TEMPORAL_CONTROL,
    ASPECT_VALIDATION,
    ASPECT_COMMIT,
    ASPECT_VISIBLE_PROJECTION,
)

ASPECT_STATUSES: frozenset[str] = frozenset(
    {"passed", "failed", "partial", "missing", "not_applicable"}
)

ASPECT_FAILURE_CLASSES: frozenset[str] = frozenset(
    {
        "hard_contract_failure",
        "recoverable_dramatic_failure",
        "degradation_only",
        "observability_gap",
        "projection_failure",
    }
)
