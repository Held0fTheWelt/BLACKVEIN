"""Contracts for deterministic runtime context synthesis.

The synthesis bundle is model-prompt support only. It records how available
runtime context should constrain generation, but it never decides commit state
or becomes an authoritative story surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CONTEXT_SYNTHESIS_SCHEMA_VERSION = "context_synthesis_bundle.v1"
CONTEXT_SYNTHESIS_AUTHORITY = "proposal_support_only"
CONTEXT_SYNTHESIS_FORBIDDEN_TRUTH_FIELDS = (
    "commit_decision",
    "state_delta",
    "final_story_text",
    "visible_output_bundle",
)


def _tuple(value: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    return tuple(str(item) for item in value if str(item).strip())


@dataclass(slots=True)
class ContextEvidenceItem:
    """A bounded evidence item available to synthesis."""

    item_id: str
    summary: str
    kind: str = "supporting_evidence"
    source_refs: tuple[str, ...] = ()
    source_evidence_lane: str = "unknown"
    source_visibility_class: str = "unknown"
    confidence: str = "medium"
    derived_from: tuple[str, ...] = ()
    runtime_use: str = "prompt_support"
    canonical_priority: int = 0
    pack_role: str = ""
    score: str = ""
    why_selected: str = ""
    policy_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "summary": self.summary,
            "kind": self.kind,
            "source_refs": list(_tuple(self.source_refs)),
            "source_evidence_lane": self.source_evidence_lane,
            "source_visibility_class": self.source_visibility_class,
            "confidence": self.confidence,
            "derived_from": list(_tuple(self.derived_from)),
            "runtime_use": self.runtime_use,
            "canonical_priority": self.canonical_priority,
            "pack_role": self.pack_role,
            "score": self.score,
            "why_selected": self.why_selected,
            "policy_note": self.policy_note,
        }


@dataclass(slots=True)
class SynthesisObligation:
    """A prompt obligation derived from evidence or runtime state."""

    code: str
    instruction: str
    evidence_item_ids: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    target: str = "model_prompt"
    severity: str = "required"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "instruction": self.instruction,
            "evidence_item_ids": list(_tuple(self.evidence_item_ids)),
            "source_refs": list(_tuple(self.source_refs)),
            "target": self.target,
            "severity": self.severity,
        }


@dataclass(slots=True)
class SynthesisConflict:
    """A synthesis conflict that requires conservative handling."""

    code: str
    description: str
    evidence_item_ids: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    resolution_policy: str = "prefer_validator_and_canonical_runtime_state"
    severity: str = "review"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "description": self.description,
            "evidence_item_ids": list(_tuple(self.evidence_item_ids)),
            "source_refs": list(_tuple(self.source_refs)),
            "resolution_policy": self.resolution_policy,
            "severity": self.severity,
        }


@dataclass(slots=True)
class SynthesisGap:
    """A missing or degraded context surface."""

    code: str
    description: str
    required_for: str = "auditability"
    severity: str = "info"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "description": self.description,
            "required_for": self.required_for,
            "severity": self.severity,
        }


@dataclass(slots=True)
class ContextSynthesisInput:
    """Raw runtime surfaces consumed by the synthesis engine."""

    retrieval: dict[str, Any] = field(default_factory=dict)
    context_text: str = ""
    scene_assessment: dict[str, Any] = field(default_factory=dict)
    semantic_move_record: dict[str, Any] = field(default_factory=dict)
    social_state_record: dict[str, Any] = field(default_factory=dict)
    turn_aspect_ledger: dict[str, Any] = field(default_factory=dict)
    hierarchical_memory_context: dict[str, Any] = field(default_factory=dict)
    validation_feedback: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "retrieval": dict(self.retrieval),
            "context_text": self.context_text,
            "scene_assessment": dict(self.scene_assessment),
            "semantic_move_record": dict(self.semantic_move_record),
            "social_state_record": dict(self.social_state_record),
            "turn_aspect_ledger": dict(self.turn_aspect_ledger),
            "hierarchical_memory_context": dict(self.hierarchical_memory_context),
            "validation_feedback": dict(self.validation_feedback),
        }


@dataclass(slots=True)
class ContextSynthesisBundle:
    """Deterministic synthesis output for prompt support and diagnostics."""

    status: str
    evidence_items: tuple[ContextEvidenceItem, ...] = ()
    obligations: tuple[SynthesisObligation, ...] = ()
    conflicts: tuple[SynthesisConflict, ...] = ()
    gaps: tuple[SynthesisGap, ...] = ()
    input_sources: tuple[str, ...] = ()
    source_lane_mix: dict[str, int] = field(default_factory=dict)
    prompt_sections: tuple[str, ...] = (
        "authority_boundary",
        "evidence_summary",
        "obligations",
        "gaps",
        "conflicts",
    )
    schema_version: str = CONTEXT_SYNTHESIS_SCHEMA_VERSION
    authority: str = CONTEXT_SYNTHESIS_AUTHORITY
    forbidden_as_truth: bool = True
    forbidden_truth_fields: tuple[str, ...] = CONTEXT_SYNTHESIS_FORBIDDEN_TRUTH_FIELDS

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "authority": self.authority,
            "forbidden_as_truth": self.forbidden_as_truth,
            "forbidden_truth_fields": list(_tuple(self.forbidden_truth_fields)),
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "obligations": [item.to_dict() for item in self.obligations],
            "conflicts": [item.to_dict() for item in self.conflicts],
            "gaps": [item.to_dict() for item in self.gaps],
            "input_sources": list(_tuple(self.input_sources)),
            "source_lane_mix": dict(self.source_lane_mix),
            "prompt_sections": list(_tuple(self.prompt_sections)),
        }
