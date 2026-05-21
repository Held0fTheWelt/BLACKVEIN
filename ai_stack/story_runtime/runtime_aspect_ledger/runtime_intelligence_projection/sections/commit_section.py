"""Projection section builder for `commit`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_COMMIT_SECTION_PARAMS = ('commit_actual', 'commit_rec', 'validation_rec')


def build_commit_section(**values: Any) -> dict[str, Any]:
    commit_actual = values['commit_actual']
    commit_rec = values['commit_rec']
    validation_rec = values['validation_rec']
    return {
                    "committed": bool(
                        commit_actual.get("committed")
                        if "committed" in commit_actual
                        else commit_actual.get("commit_applied")
                    ),
                    "degraded": bool(commit_actual.get("degraded")),
                    "quality_class": commit_actual.get("quality_class"),
                    "validation_status": validation_rec.get("status"),
                    "fallback_used": bool(commit_actual.get("fallback_used")),
                    "status": commit_rec.get("status"),
                }

