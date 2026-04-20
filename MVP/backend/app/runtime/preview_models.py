"""Canonical contracts for guarded preview-writes (dry-run only)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PreviewDeltaProposal(BaseModel):
    """One proposed state delta for preview evaluation."""

    target_path: str
    next_value: Any
    delta_type: str | None = None
    rationale: str = ""


class PreviewDeltaRequest(BaseModel):
    """Structured dry-run preview request for guarded evaluation."""

    preview_request_id: str = Field(default_factory=lambda: uuid4().hex)
    scene_id: str | None = None
    proposed_state_deltas: list[PreviewDeltaProposal] = Field(default_factory=list)
    detected_triggers: list[str] = Field(default_factory=list)
    proposed_scene_id: str | None = None
    requested_by_agent_id: str | None = None
    reasoning_summary: str | None = None
    tool_request_context: dict[str, Any] = Field(default_factory=dict)


class PreviewDeltaResult(BaseModel):
    """Structured preview result for model feedback and diagnostics."""

    preview_allowed: bool
    accepted_deltas: list[str] = Field(default_factory=list)
    rejected_deltas: list[str] = Field(default_factory=list)
    partial_acceptance: bool = False
    guard_outcome: str
    rejection_reasons: list[str] = Field(default_factory=list)
    warning_reasons: list[str] = Field(default_factory=list)
    suggested_corrections: list[str] = Field(default_factory=list)
    normalized_feedback: dict[str, Any] = Field(default_factory=dict)
    summary: str
    preview_safe_no_write: bool = True
    accepted_delta_count: int = 0
    rejected_delta_count: int = 0
    input_delta_count: int = 0
    input_targets: list[str] = Field(default_factory=list)
