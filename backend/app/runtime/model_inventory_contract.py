"""Operational model inventory contract — required routing tuples per product surface.

Used for coverage validation and documentation alignment. Does not alter routing policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.runtime.model_routing_contracts import TaskKind, WorkflowPhase


class InventorySurface(str, Enum):
    """Named surfaces that rely on disciplined specs or registry state."""

    runtime_staged = "runtime_staged"
    writers_room = "writers_room"
    improvement_bounded = "improvement_bounded"


@dataclass(frozen=True, slots=True)
class RequiredRoutingTuple:
    """One routing request shape that a surface may issue."""

    workflow_phase: WorkflowPhase
    task_kind: TaskKind
    requires_structured_output: bool


# Task 1 staged Runtime: preflight, signal, ranking, default synthesis (session may override task_kind).
RUNTIME_STAGED_REQUIRED: tuple[RequiredRoutingTuple, ...] = (
    RequiredRoutingTuple(
        workflow_phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        requires_structured_output=True,
    ),
    RequiredRoutingTuple(
        workflow_phase=WorkflowPhase.interpretation,
        task_kind=TaskKind.repetition_consistency_check,
        requires_structured_output=True,
    ),
    RequiredRoutingTuple(
        workflow_phase=WorkflowPhase.interpretation,
        task_kind=TaskKind.ranking,
        requires_structured_output=True,
    ),
    RequiredRoutingTuple(
        workflow_phase=WorkflowPhase.generation,
        task_kind=TaskKind.narrative_formulation,
        requires_structured_output=True,
    ),
)

# Writers-Room workflow package: optional preflight + structured synthesis.
WRITERS_ROOM_REQUIRED: tuple[RequiredRoutingTuple, ...] = (
    RequiredRoutingTuple(
        workflow_phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        requires_structured_output=False,
    ),
    RequiredRoutingTuple(
        workflow_phase=WorkflowPhase.generation,
        task_kind=TaskKind.narrative_formulation,
        requires_structured_output=True,
    ),
)

# Improvement bounded enrichment: preflight + revision-phase synthesis.
IMPROVEMENT_BOUNDED_REQUIRED: tuple[RequiredRoutingTuple, ...] = (
    RequiredRoutingTuple(
        workflow_phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        requires_structured_output=False,
    ),
    RequiredRoutingTuple(
        workflow_phase=WorkflowPhase.revision,
        task_kind=TaskKind.revision_synthesis,
        requires_structured_output=False,
    ),
)

SURFACE_REQUIREMENTS: dict[InventorySurface, tuple[RequiredRoutingTuple, ...]] = {
    InventorySurface.runtime_staged: RUNTIME_STAGED_REQUIRED,
    InventorySurface.writers_room: WRITERS_ROOM_REQUIRED,
    InventorySurface.improvement_bounded: IMPROVEMENT_BOUNDED_REQUIRED,
}


def requirements_for_surface(surface: InventorySurface) -> tuple[RequiredRoutingTuple, ...]:
    """Return the canonical required tuples for a surface."""
    return SURFACE_REQUIREMENTS[surface]
