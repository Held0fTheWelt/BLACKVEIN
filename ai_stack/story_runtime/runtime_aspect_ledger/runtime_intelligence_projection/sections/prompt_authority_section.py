"""Projection section builder for `prompt_authority`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_PROMPT_AUTHORITY_SECTION_PARAMS = ('prompt_authority_actual', 'prompt_authority_expected', 'prompt_authority_rec', 'prompt_authority_selected')


def build_prompt_authority_section(**values: Any) -> dict[str, Any]:
    prompt_authority_actual = values['prompt_authority_actual']
    prompt_authority_expected = values['prompt_authority_expected']
    prompt_authority_rec = values['prompt_authority_rec']
    prompt_authority_selected = values['prompt_authority_selected']
    return {
                    "schema_version": prompt_authority_expected.get("schema_version"),
                    "authoritative_sections": prompt_authority_selected.get(
                        "authoritative_sections"
                    )
                    or [],
                    "source_refs": prompt_authority_selected.get("source_refs") or [],
                    "selected_capabilities": prompt_authority_selected.get(
                        "selected_capabilities"
                    )
                    or [],
                    "selected_memory_ref_ids": prompt_authority_selected.get(
                        "selected_memory_ref_ids"
                    )
                    or [],
                    "authority_mode": prompt_authority_actual.get("authority_mode"),
                    "prompt_authority_applied_to_packet": bool(
                        prompt_authority_actual.get("prompt_authority_applied_to_packet")
                    ),
                    "commit_gate_changed": bool(
                        prompt_authority_actual.get("commit_gate_changed")
                    ),
                    "readiness_gate_changed": bool(
                        prompt_authority_actual.get("readiness_gate_changed")
                    ),
                    "validation_outcome_changed": bool(
                        prompt_authority_actual.get("validation_outcome_changed")
                    ),
                    "contract_pass": prompt_authority_actual.get("contract_pass"),
                    "failure_reason": prompt_authority_rec.get("failure_reason")
                    or (
                        _record_reasons(prompt_authority_rec)[0]
                        if _record_reasons(prompt_authority_rec)
                        else None
                    ),
                    "status": prompt_authority_rec.get("status"),
                }

