"""Bounded exploration BFS expand phase — DS-048."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from ai_stack.research_contract import (
    ExplorationAbortReason,
    ExplorationBudget,
    ExplorationEdgeRecord,
    ExplorationNodeRecord,
    ExplorationOutcome,
    ExplorationRelationType,
    Perspective,
    ResearchStatus,
)
from ai_stack.research_exploration_bounded_primitives import (
    RELATION_ORDER,
    branch_hypothesis,
    candidate_eligible,
    deterministic_edge_id,
    deterministic_node_id,
    novelty_score,
    normalize_text,
    speculative_level_for_relation,
)


@dataclass
class _ExplorationExpandCounters:
    llm_calls: int = 0
    token_use: int = 0
    branch_count: int = 0
    low_evidence_expansions: int = 0
    rejected_count: int = 0
    unresolved_count: int = 0
    pruned_count: int = 0
    promoted_count: int = 0


_TERMINAL_ABORTS = frozenset(
    {
        ExplorationAbortReason.REDUNDANCY_ABORT.value,
        ExplorationAbortReason.SPECULATIVE_DRIFT_ABORT.value,
        ExplorationAbortReason.LLM_BUDGET_EXHAUSTED.value,
        ExplorationAbortReason.TOKEN_BUDGET_EXHAUSTED.value,
        ExplorationAbortReason.NODE_BUDGET_EXHAUSTED.value,
        ExplorationAbortReason.TIME_BUDGET_EXHAUSTED.value,
        ExplorationAbortReason.LOW_EVIDENCE_LIMIT_REACHED.value,
    }
)


def run_bounded_exploration_expand_loop(
    *,
    budget: ExplorationBudget,
    start: float,
    queue: deque[tuple[dict[str, Any], int]],
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    seen_hypothesis: set[str],
    counters: _ExplorationExpandCounters,
    abort_reason: str,
) -> str:
    """Run main BFS expansion until queue empty or budget/abort."""
    ar = abort_reason
    while queue:
        current, depth = queue.popleft()
        elapsed_ms = int((time.time() - start) * 1000)
        if elapsed_ms >= budget.time_budget_ms:
            ar = ExplorationAbortReason.TIME_BUDGET_EXHAUSTED.value
            break
        if len(nodes) >= budget.max_total_nodes:
            ar = ExplorationAbortReason.NODE_BUDGET_EXHAUSTED.value
            break
        if depth >= budget.max_depth:
            if ar == ExplorationAbortReason.COMPLETED_WITHIN_BUDGET.value:
                ar = ExplorationAbortReason.DEPTH_LIMIT_REACHED.value
            continue

        child_budget = min(budget.max_branches_per_node, len(RELATION_ORDER))
        used_child = 0
        for relation in RELATION_ORDER:
            if used_child >= child_budget:
                if ar == ExplorationAbortReason.COMPLETED_WITHIN_BUDGET.value:
                    ar = ExplorationAbortReason.BRANCH_BUDGET_EXHAUSTED.value
                break
            if counters.llm_calls >= budget.llm_call_budget:
                ar = ExplorationAbortReason.LLM_BUDGET_EXHAUSTED.value
                break
            if counters.token_use >= budget.token_budget:
                ar = ExplorationAbortReason.TOKEN_BUDGET_EXHAUSTED.value
                break
            if len(nodes) >= budget.max_total_nodes:
                ar = ExplorationAbortReason.NODE_BUDGET_EXHAUSTED.value
                break

            parent_hyp = str(current.get("hypothesis", ""))
            child_hyp = branch_hypothesis(parent_hyp, relation)
            normalized = normalize_text(child_hyp)
            if normalized in seen_hypothesis:
                counters.pruned_count += 1
                if budget.abort_on_redundancy:
                    ar = ExplorationAbortReason.REDUNDANCY_ABORT.value
                    break
                continue

            speculative_level = speculative_level_for_relation(relation, depth + 1)
            if budget.abort_on_speculative_drift and speculative_level >= 0.9:
                counters.pruned_count += 1
                ar = ExplorationAbortReason.SPECULATIVE_DRIFT_ABORT.value
                break

            evidence_ids = list(current.get("evidence_anchor_ids", []))
            if relation in (ExplorationRelationType.CONTRAST, ExplorationRelationType.COUNTERREAD):
                evidence_ids = evidence_ids[:1]
            if not evidence_ids:
                counters.low_evidence_expansions += 1
                if counters.low_evidence_expansions > budget.max_low_evidence_expansions:
                    ar = ExplorationAbortReason.LOW_EVIDENCE_LIMIT_REACHED.value
                    break

            counters.llm_calls += 1
            counters.token_use += max(10, len(child_hyp.split()))
            counters.branch_count += 1
            child_id = deterministic_node_id(current["node_id"], relation, depth + 1, used_child)
            novelty = novelty_score(child_hyp)
            outcome = ExplorationOutcome.KEPT_FOR_VALIDATION
            if novelty < 0.18:
                outcome = ExplorationOutcome.REJECTED
                counters.rejected_count += 1
            elif novelty < 0.24:
                outcome = ExplorationOutcome.UNRESOLVED
                counters.unresolved_count += 1

            child = ExplorationNodeRecord(
                node_id=child_id,
                parent_node_id=current["node_id"],
                seed_aspect_id=str(current.get("seed_aspect_id", "")),
                perspective=Perspective(str(current.get("perspective", Perspective.PLAYWRIGHT.value))),
                hypothesis=child_hyp,
                rationale=f"derived_via:{relation.value}",
                speculative_level=speculative_level,
                evidence_anchor_ids=evidence_ids,
                novelty_score=novelty,
                status=ResearchStatus.EXPLORATORY,
                outcome=outcome,
            ).to_dict()
            edge = ExplorationEdgeRecord(
                edge_id=deterministic_edge_id(current["node_id"], child_id, relation),
                from_node_id=current["node_id"],
                to_node_id=child_id,
                relation_type=relation,
            ).to_dict()

            nodes.append(child)
            edges.append(edge)
            seen_hypothesis.add(normalized)
            used_child += 1

            if outcome == ExplorationOutcome.KEPT_FOR_VALIDATION:
                queue.append((child, depth + 1))
                if candidate_eligible(child):
                    counters.promoted_count += 1

        if ar in _TERMINAL_ABORTS:
            break

    return ar


def exploration_expand_counters_factory() -> _ExplorationExpandCounters:
    return _ExplorationExpandCounters()
