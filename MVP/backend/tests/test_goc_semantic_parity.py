"""Parity: roadmap semantic surface in ai_stack matches backend routing enums (gate G1 / G2)."""

from __future__ import annotations

from app.runtime.decision_policy import AIActionType
from app.runtime.model_routing_contracts import LLMOrSLM, RouteReasonCode, TaskKind

from ai_stack.goc_roadmap_semantic_surface import (
    DECISION_CLASSES,
    MODEL_ROLES,
    ROUTING_LABELS,
    TASK_TYPES,
)


def test_task_types_match_taskkind_enum() -> None:
    assert TASK_TYPES == frozenset(m.value for m in TaskKind)


def test_model_roles_match_llm_or_slm() -> None:
    assert MODEL_ROLES == frozenset(m.value for m in LLMOrSLM)


def test_routing_labels_cover_route_reason_enum() -> None:
    assert ROUTING_LABELS == frozenset(m.value for m in RouteReasonCode)


def test_decision_classes_match_ai_action_type() -> None:
    assert DECISION_CLASSES == frozenset(m.value for m in AIActionType)
