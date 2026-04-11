"""Bounded exploration — Kernimplementierung (DS-022; von research_exploration_bounded re-exportiert)."""

from __future__ import annotations

from collections import deque
import time
from typing import Any

from ai_stack.research_contract import (
    ContradictionStatus,
    ExplorationAbortReason,
    ExplorationBudget,
    ExplorationNodeRecord,
    ExplorationOutcome,
    ExplorationRelationType,
    Perspective,
    ResearchStatus,
)
from ai_stack.research_exploration_bounded_expand_loop import (
    exploration_expand_counters_factory,
    run_bounded_exploration_expand_loop,
)
from ai_stack.research_exploration_bounded_primitives import (
    ExplorationResult,
    deterministic_node_id,
    novelty_score,
    normalize_text,
)


def run_bounded_exploration(
    *,
    seed_aspects: list[dict[str, Any]],
    budget: ExplorationBudget | None,
) -> ExplorationResult:
    """Run deterministic bounded exploration.

    No internal execution path is allowed without a validated budget object.
    """
    if budget is None:
        raise ValueError("exploration_budget_required")
    budget.validate()

    start = time.time()
    ordered_seeds = sorted(seed_aspects, key=lambda row: (str(row.get("aspect_id", "")), str(row.get("statement", ""))))
    if not ordered_seeds:
        return ExplorationResult(
            nodes=[],
            edges=[],
            abort_reason=ExplorationAbortReason.COMPLETED_WITHIN_BUDGET.value,
            promoted_candidate_count=0,
            rejected_branch_count=0,
            unresolved_branch_count=0,
            pruned_branch_count=0,
            consumed_budget={
                "llm_calls": 0,
                "tokens": 0,
                "nodes": 0,
                "branches": 0,
                "low_evidence_expansions": 0,
                "elapsed_wall_time_ms": int((time.time() - start) * 1000),
            },
        )

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_hypothesis: set[str] = set()
    queue: deque[tuple[dict[str, Any], int]] = deque()

    counters = exploration_expand_counters_factory()
    abort_reason = ExplorationAbortReason.COMPLETED_WITHIN_BUDGET.value

    for seed_idx, aspect in enumerate(ordered_seeds):
        if len(nodes) >= budget.max_total_nodes:
            abort_reason = ExplorationAbortReason.NODE_BUDGET_EXHAUSTED.value
            break
        statement = str(aspect.get("statement", "")).strip()
        if not statement:
            continue
        perspective = Perspective(str(aspect.get("perspective", Perspective.PLAYWRIGHT.value)))
        hypothesis = f"seed:{statement}"
        node_id = deterministic_node_id(str(aspect.get("aspect_id", seed_idx)), ExplorationRelationType.EXTEND, 0, seed_idx)
        node = ExplorationNodeRecord(
            node_id=node_id,
            parent_node_id=None,
            seed_aspect_id=str(aspect.get("aspect_id", "")),
            perspective=perspective,
            hypothesis=hypothesis,
            rationale="seed_from_aspect",
            speculative_level=0.12,
            evidence_anchor_ids=list(aspect.get("evidence_anchor_ids", [])),
            novelty_score=novelty_score(hypothesis),
            status=ResearchStatus.EXPLORATORY,
            outcome=ExplorationOutcome.KEPT_FOR_VALIDATION,
        ).to_dict()
        nodes.append(node)
        seen_hypothesis.add(normalize_text(hypothesis))
        queue.append((node, 0))

    abort_reason = run_bounded_exploration_expand_loop(
        budget=budget,
        start=start,
        queue=queue,
        nodes=nodes,
        edges=edges,
        seen_hypothesis=seen_hypothesis,
        counters=counters,
        abort_reason=abort_reason,
    )

    consumed = {
        "llm_calls": counters.llm_calls,
        "tokens": counters.token_use,
        "nodes": len(nodes),
        "branches": counters.branch_count,
        "low_evidence_expansions": counters.low_evidence_expansions,
        "elapsed_wall_time_ms": int((time.time() - start) * 1000),
    }
    return ExplorationResult(
        nodes=nodes,
        edges=edges,
        abort_reason=abort_reason,
        promoted_candidate_count=counters.promoted_count,
        rejected_branch_count=counters.rejected_count,
        unresolved_branch_count=counters.unresolved_count,
        pruned_branch_count=counters.pruned_count,
        consumed_budget=consumed,
    )


def deterministic_contradiction_scan(statement: str) -> ContradictionStatus:
    lowered = normalize_text(statement)
    if "hard_conflict" in lowered or "contradiction" in lowered:
        return ContradictionStatus.HARD_CONFLICT
    if "counterread" in lowered or "counter_reading" in lowered:
        return ContradictionStatus.COUNTERVIEW_PRESENT
    if "unclear" in lowered or "unresolved" in lowered:
        return ContradictionStatus.UNRESOLVED
    if "tension" in lowered or "contrast" in lowered:
        return ContradictionStatus.SOFT_CONFLICT
    return ContradictionStatus.NONE
