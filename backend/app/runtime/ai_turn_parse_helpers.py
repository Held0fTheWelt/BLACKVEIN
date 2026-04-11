from __future__ import annotations

from typing import Any

from app.content.module_models import ContentModule
from app.runtime.ai_decision import ParseResult
from app.runtime.runtime_models import SessionState
from app.runtime.validators import validate_action_structure, validate_action_type


def preview_diagnostics_after_parse(
    parse_result: ParseResult,
    preview_records: list[dict[str, Any]],
    build_preview_payload_fn: Any,
) -> dict[str, Any] | None:
    if not preview_records:
        return None
    final_targets = (
        [delta.target_path for delta in (parse_result.decision.proposed_deltas or [])]
        if parse_result.success and parse_result.decision
        else []
    )
    return build_preview_payload_fn(
        records=preview_records,
        final_targets=final_targets,
    )


def collect_policy_validation_errors(
    parse_result: ParseResult,
    module: ContentModule,
    session: SessionState,
) -> list[str]:
    policy_validation_errors: list[str] = []
    for delta in parse_result.decision.proposed_deltas:
        delta_type = delta.delta_type or "state_update"
        is_valid, error = validate_action_type(delta_type)
        if not is_valid:
            policy_validation_errors.append(error)
            continue
        action_data = {
            "target_path": delta.target_path,
            "next_value": delta.next_value,
        }
        is_valid, structure_errors = validate_action_structure(
            delta_type, action_data, module=module, session=session
        )
        if not is_valid:
            policy_validation_errors.extend(structure_errors)
    return policy_validation_errors
