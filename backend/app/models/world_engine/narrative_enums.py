"""Typed enums for narrative governance domain contracts."""

from __future__ import annotations

from enum import Enum


class NarrativeValidationStrategy(str, Enum):
    """Runtime output validation strategy."""

    SCHEMA_ONLY = "schema_only"
    SCHEMA_PLUS_SEMANTIC = "schema_plus_semantic"
    STRICT_RULE_ENGINE = "strict_rule_engine"


class NarrativePackageEventType(str, Enum):
    """Package lifecycle history event types."""

    BUILD = "build"
    PROMOTE = "promote"
    ROLLBACK = "rollback"
    RETIRE_PREVIEW = "retire_preview"
    BOOTSTRAP_IMPORT = "bootstrap_import"


class NarrativePreviewBuildStatus(str, Enum):
    """Preview build status values."""

    BUILT = "built"
    BUILDING = "building"
    FAILED = "failed"
    IMPORTED_LEGACY = "imported_legacy"


class NarrativeEvaluationStatus(str, Enum):
    """Evaluation run and preview evaluation status."""

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    IMPORTED_LEGACY = "imported_legacy"


class NarrativeRevisionStatus(str, Enum):
    """Canonical revision workflow states."""

    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REWORK = "needs_rework"
    APPLIED_TO_DRAFT = "applied_to_draft"
    READY_FOR_PROMOTION = "ready_for_promotion"
    PROMOTED = "promoted"
    ARCHIVED = "archived"


class NarrativeConflictType(str, Enum):
    """Revision conflict kinds."""

    TARGET_OVERLAP = "target_overlap"
    SEMANTIC_CONTRADICTION = "semantic_contradiction"
    DEPENDENCY_VIOLATION = "dependency_violation"


class NarrativeConflictResolutionStatus(str, Enum):
    """Resolution progress states for revision conflicts."""

    PENDING = "pending"
    RESOLVED = "resolved"


class NarrativeConflictResolutionStrategy(str, Enum):
    """Allowed conflict resolution strategies."""

    MANUAL_SELECT_WINNER = "manual_select_winner"
    MANUAL_MERGE_THEN_REBUILD = "manual_merge_then_rebuild"
    DISMISS_LOSER = "dismiss_loser"
    ARCHIVE_CONFLICTING_BATCH = "archive_conflicting_batch"


class NarrativeNotificationChannel(str, Enum):
    """Supported notification delivery channels."""

    ADMIN_UI = "admin_ui"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"


class NarrativeNotificationSeverity(str, Enum):
    """Notification severity classes."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class NarrativeEventType(str, Enum):
    """Governance and runtime event types."""

    FINDING_CREATED = "finding_created"
    FINDING_HIGH_CONFIDENCE = "finding_high_confidence"
    REVISION_CONFLICT_DETECTED = "revision_conflict_detected"
    REVISION_STATE_CHANGED = "revision_state_changed"
    PREVIEW_BUILD_CREATED = "preview_build_created"
    EVALUATION_FAILED = "evaluation_failed"
    PROMOTION_COMPLETED = "promotion_completed"
    ROLLBACK_COMPLETED = "rollback_completed"
    DRIFT_THRESHOLD_EXCEEDED = "drift_threshold_exceeded"
    CORRECTIVE_RETRY_USED = "corrective_retry_used"
    SAFE_FALLBACK_USED = "safe_fallback_used"
    FALLBACK_THRESHOLD_EXCEEDED = "fallback_threshold_exceeded"


class PlayerAffectSignalType(str, Enum):
    """Input signal channels used for affect assessment."""

    ACTION_PATTERN = "action_pattern"
    PAUSE_PATTERN = "pause_pattern"
    REPETITION = "repetition"
    EXPLICIT_TEXT = "explicit_text"
    OPERATOR_FLAG = "operator_flag"


class PlayerAffectState(str, Enum):
    """Normalized affect states for runtime-safe adaptation seams."""

    CALM = "calm"
    CURIOUS = "curious"
    ENGAGED = "engaged"
    HESITANT = "hesitant"
    CONFUSED = "confused"
    FRUSTRATED = "frustrated"
    OVERWHELMED = "overwhelmed"
    DEFIANT = "defiant"
    EXCITED = "excited"
