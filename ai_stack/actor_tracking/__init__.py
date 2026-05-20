"""W5 Actor Situation Tracker (W5-AST).

Append-only, source-tagged, truth-leveled actor-situation authority for
Who / Where / What / How / Why. See ADR-0063 and
``docs/MVPs/w5_actor_situation_migration.md`` for the full contract.

Phase 1 is shadow-only: extraction runs after committed runtime events and
persists snapshots on ``StorySession``, but no consumer reads W5 yet.
"""

from __future__ import annotations

from ai_stack.actor_tracking.models import (
    W5_FACT_SCHEMA_VERSION,
    W5_PROJECTION_SCHEMA_VERSION,
    W5_SNAPSHOT_SCHEMA_VERSION,
    W5ActionState,
    W5ActorSituation,
    W5ActorType,
    W5Conflict,
    W5ConflictResolutionStatus,
    W5Dimension,
    W5Fact,
    W5FactStatus,
    W5FreshnessStatus,
    W5Projection,
    W5ProjectionConsumer,
    W5Snapshot,
    W5Source,
    W5TruthLevel,
    W5ValidationFailureCode,
    W5VisibilityScope,
    why_truth_level_is_admitted,
)
from ai_stack.actor_tracking.extractor import (
    extract_w5_snapshot_from_committed_event,
)
from ai_stack.actor_tracking.projection import (
    build_w5_projection_for_director,
    build_w5_projection_for_narrator,
    build_w5_projection_for_npc,
    build_w5_projection_for_player_shell,
)
from ai_stack.actor_tracking.validation import (
    W5_VALIDATION_SCHEMA_VERSION,
    validate_w5_actor_situation,
    w5_ast_validation_enabled,
    w5_validation_fallback,
)
from ai_stack.actor_tracking.diagnostics import (
    W5_ADMIN_DIAGNOSTIC_SCHEMA_VERSION,
    W5_RUNTIME_METADATA_SCHEMA_VERSION,
    build_w5_admin_actor_view,
    build_w5_admin_conflicts_view,
    build_w5_admin_empty_view,
    build_w5_admin_narrator_projection_preview,
    build_w5_admin_npc_projection_preview,
    build_w5_admin_snapshot_view,
    build_w5_admin_validation_view,
    build_w5_langfuse_metadata,
    build_w5_runtime_metadata,
    coerce_w5_snapshot,
    w5_projection_flag_states,
)

__all__ = [
    "W5_FACT_SCHEMA_VERSION",
    "W5_PROJECTION_SCHEMA_VERSION",
    "W5_SNAPSHOT_SCHEMA_VERSION",
    "W5_ADMIN_DIAGNOSTIC_SCHEMA_VERSION",
    "W5_RUNTIME_METADATA_SCHEMA_VERSION",
    "W5_VALIDATION_SCHEMA_VERSION",
    "W5ActionState",
    "W5ActorSituation",
    "W5ActorType",
    "W5Conflict",
    "W5ConflictResolutionStatus",
    "W5Dimension",
    "W5Fact",
    "W5FactStatus",
    "W5FreshnessStatus",
    "W5Projection",
    "W5ProjectionConsumer",
    "W5Snapshot",
    "W5Source",
    "W5TruthLevel",
    "W5ValidationFailureCode",
    "W5VisibilityScope",
    "build_w5_projection_for_director",
    "build_w5_projection_for_narrator",
    "build_w5_projection_for_npc",
    "build_w5_projection_for_player_shell",
    "build_w5_admin_actor_view",
    "build_w5_admin_conflicts_view",
    "build_w5_admin_empty_view",
    "build_w5_admin_narrator_projection_preview",
    "build_w5_admin_npc_projection_preview",
    "build_w5_admin_snapshot_view",
    "build_w5_admin_validation_view",
    "build_w5_langfuse_metadata",
    "build_w5_runtime_metadata",
    "coerce_w5_snapshot",
    "extract_w5_snapshot_from_committed_event",
    "validate_w5_actor_situation",
    "w5_ast_validation_enabled",
    "w5_projection_flag_states",
    "w5_validation_fallback",
    "why_truth_level_is_admitted",
]
