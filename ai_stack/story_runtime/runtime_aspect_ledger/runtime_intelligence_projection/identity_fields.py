"""Root identity fields for the runtime-intelligence projection."""

from __future__ import annotations

from typing import Any

from ..constants import *

IDENTITY_FIELD_PARAMS = (
    'semantic_capability_selection',
    'semantic_validator_dispatch_report',
    'semantic_validator_execution_plan',
    'src',
)


def build_identity_fields(**values: Any) -> dict[str, Any]:
    semantic_capability_selection = values['semantic_capability_selection']
    semantic_validator_dispatch_report = values['semantic_validator_dispatch_report']
    semantic_validator_execution_plan = values['semantic_validator_execution_plan']
    src = values['src']
    return {
        'schema_version': TURN_ASPECT_LEDGER_SCHEMA_VERSION,
        'module_id': src.get("module_id"),
        'runtime_profile_id': src.get("runtime_profile_id"),
        'canonical_turn_id': src.get("canonical_turn_id"),
        'story_session_id': src.get("story_session_id") or src.get("session_id"),
        'turn_number': src.get("turn_number"),
        'capability_selection': semantic_capability_selection,
        'validator_execution_plan': semantic_validator_execution_plan,
        'validator_dispatch_report': semantic_validator_dispatch_report,
    }
