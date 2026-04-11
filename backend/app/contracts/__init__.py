"""Shared canonical contracts for GoC governance surfaces (non-runtime logic)."""

from app.contracts.improvement_entry_class import (
    ImprovementEntryClass,
    coalesce_improvement_entry_class_from_stored_record,
    default_improvement_entry_class,
    parse_improvement_entry_class,
    resolve_improvement_entry_class_for_create,
)
from app.contracts.improvement_operating_loop import (
    IMPROVEMENT_OPERATING_LOOP_CONTRACT_VERSION,
    ImprovementLoopStage,
)
from app.contracts.inspector_turn_projection import (
    INSPECTOR_COMPARISON_PROJECTION_SCHEMA_VERSION,
    INSPECTOR_COVERAGE_HEALTH_PROJECTION_SCHEMA_VERSION,
    INSPECTOR_PROVENANCE_RAW_PROJECTION_SCHEMA_VERSION,
    INSPECTOR_REQUIRED_SECTION_KEYS,
    INSPECTOR_SECTION_STATUS_SUPPORTED,
    INSPECTOR_SECTION_STATUS_UNAVAILABLE,
    INSPECTOR_SECTION_STATUS_UNSUPPORTED,
    INSPECTOR_TIMELINE_PROJECTION_SCHEMA_VERSION,
    INSPECTOR_TURN_PROJECTION_SCHEMA_VERSION,
    build_inspector_turn_projection_root,
    build_inspector_view_projection_root,
    make_supported_section,
    make_unavailable_section,
    make_unsupported_section,
)
from app.contracts.writers_room_artifact_class import (
    GOC_SHARED_SEMANTIC_CONTRACT_VERSION,
    WRITERS_ROOM_OPERATING_METADATA_KEYS,
    WritersRoomArtifactClass,
    build_writers_room_artifact_record,
    normalize_writers_room_artifact_class,
)

__all__ = [
    "GOC_SHARED_SEMANTIC_CONTRACT_VERSION",
    "IMPROVEMENT_OPERATING_LOOP_CONTRACT_VERSION",
    "WRITERS_ROOM_OPERATING_METADATA_KEYS",
    "ImprovementEntryClass",
    "ImprovementLoopStage",
    "INSPECTOR_COMPARISON_PROJECTION_SCHEMA_VERSION",
    "INSPECTOR_COVERAGE_HEALTH_PROJECTION_SCHEMA_VERSION",
    "INSPECTOR_PROVENANCE_RAW_PROJECTION_SCHEMA_VERSION",
    "INSPECTOR_REQUIRED_SECTION_KEYS",
    "INSPECTOR_SECTION_STATUS_SUPPORTED",
    "INSPECTOR_SECTION_STATUS_UNAVAILABLE",
    "INSPECTOR_SECTION_STATUS_UNSUPPORTED",
    "INSPECTOR_TIMELINE_PROJECTION_SCHEMA_VERSION",
    "INSPECTOR_TURN_PROJECTION_SCHEMA_VERSION",
    "WritersRoomArtifactClass",
    "build_inspector_turn_projection_root",
    "build_inspector_view_projection_root",
    "build_writers_room_artifact_record",
    "coalesce_improvement_entry_class_from_stored_record",
    "default_improvement_entry_class",
    "make_supported_section",
    "make_unavailable_section",
    "make_unsupported_section",
    "parse_improvement_entry_class",
    "resolve_improvement_entry_class_for_create",
    "normalize_writers_room_artifact_class",
]
