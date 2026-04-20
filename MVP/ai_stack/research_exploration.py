"""Bounded deterministic exploration engine (single owner for branching/pruning/budget/abort)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import hashlib
import time
from typing import Any

from ai_stack.research_contract import (
    ContradictionStatus,
    ExplorationAbortReason,
    ExplorationBudget,
    ExplorationEdgeRecord,
    ExplorationNodeRecord,
    ExplorationOutcome,
    ExplorationRelationType,
    Perspective,
    ResearchStatus,
)


_RELATION_ORDER: tuple[ExplorationRelationType, ...] = (
    ExplorationRelationType.EXTEND,
    ExplorationRelationType.CONTRAST,
    ExplorationRelationType.COUNTERREAD,
    ExplorationRelationType.STAGING_IMPLICATION,
    ExplorationRelationType.THEME_LINK,
    ExplorationRelationType.CHARACTER_MOTIVE_LINK,
    ExplorationRelationType.STRUCTURAL_ANALOGY,
    ExplorationRelationType.TENSION_SOURCE_PROBE,
    ExplorationRelationType.IMPROVEMENT_PROBE,
)


def _normalize_text(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _novelty_score(hypothesis: str) -> float:
    tokens = _normalize_text(hypothesis).split()
    if not tokens:
        return 0.0
    unique = len(set(tokens))
    score = unique / len(tokens)
    return round(min(1.0, max(0.0, score)), 4)


def _deterministic_node_id(seed: str, relation: ExplorationRelationType, depth: int, ordinal: int) -> str:
    raw = f"{seed}|{relation.value}|{depth}|{ordinal}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:14]
    return f"node_{digest}"


def _deterministic_edge_id(from_node: str, to_node: str, relation: ExplorationRelationType) -> str:
    raw = f"{from_node}|{to_node}|{relation.value}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:14]
    return f"edge_{digest}"


def _branch_hypothesis(base: str, relation: ExplorationRelationType) -> str:
    prefix_map = {
        ExplorationRelationType.EXTEND: "extended_reading",
        ExplorationRelationType.CONTRAST: "contrast_reading",
        ExplorationRelationType.COUNTERREAD: "counter_reading",
        ExplorationRelationType.STAGING_IMPLICATION: "staging_implication",
        ExplorationRelationType.THEME_LINK: "theme_link",
        ExplorationRelationType.CHARACTER_MOTIVE_LINK: "motive_link",
        ExplorationRelationType.STRUCTURAL_ANALOGY: "structural_analogy",
        ExplorationRelationType.TENSION_SOURCE_PROBE: "tension_probe",
        ExplorationRelationType.IMPROVEMENT_PROBE: "improvement_probe",
    }
    marker = prefix_map[relation]
    return f"{marker}: {base}".strip()


def _speculative_level_for_relation(relation: ExplorationRelationType, depth: int) -> float:
    base = {
        ExplorationRelationType.EXTEND: 0.25,
        ExplorationRelationType.CONTRAST: 0.35,
        ExplorationRelationType.COUNTERREAD: 0.45,
        ExplorationRelationType.STAGING_IMPLICATION: 0.4,
        ExplorationRelationType.THEME_LINK: 0.5,
        ExplorationRelationType.CHARACTER_MOTIVE_LINK: 0.48,
        ExplorationRelationType.STRUCTURAL_ANALOGY: 0.58,
        ExplorationRelationType.TENSION_SOURCE_PROBE: 0.62,
        ExplorationRelationType.IMPROVEMENT_PROBE: 0.44,
    }[relation]
    return round(min(1.0, base + (depth * 0.06)), 3)


def _candidate_eligible(node: dict[str, Any]) -> bool:
    return (
        bool(node.get("evidence_anchor_ids"))
        and node.get("status") == ResearchStatus.EXPLORATORY.value
        and node.get("outcome") == ExplorationOutcome.KEPT_FOR_VALIDATION.value
        and float(node.get("novelty_score", 0.0)) >= 0.2
    )


@dataclass(slots=True)
class ExplorationResult:
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    abort_reason: str
    promoted_candidate_count: int
    rejected_branch_count: int
    unresolved_branch_count: int
    pruned_branch_count: int
    consumed_budget: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": list(self.nodes),
            "edges": list(self.edges),
            "abort_reason": self.abort_reason,
            "promoted_candidate_count": self.promoted_candidate_count,
            "rejected_branch_count": self.rejected_branch_count,
            "unresolved_branch_count": self.unresolved_branch_count,
            "pruned_branch_count": self.pruned_branch_count,
            "consumed_budget": dict(self.consumed_budget),
        }


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

    llm_calls = 0
    token_use = 0
    branch_count = 0
    low_evidence_expansions = 0
    rejected_count = 0
    unresolved_count = 0
    pruned_count = 0
    promoted_count = 0
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
        node_id = _deterministic_node_id(str(aspect.get("aspect_id", seed_idx)), ExplorationRelationType.EXTEND, 0, seed_idx)
        node = ExplorationNodeRecord(
            node_id=node_id,
            parent_node_id=None,
            seed_aspect_id=str(aspect.get("aspect_id", "")),
            perspective=perspective,
            hypothesis=hypothesis,
            rationale="seed_from_aspect",
            speculative_level=0.12,
            evidence_anchor_ids=list(aspect.get("evidence_anchor_ids", [])),
            novelty_score=_novelty_score(hypothesis),
            status=ResearchStatus.EXPLORATORY,
            outcome=ExplorationOutcome.KEPT_FOR_VALIDATION,
        ).to_dict()
        nodes.append(node)
        seen_hypothesis.add(_normalize_text(hypothesis))
        queue.append((node, 0))

    while queue:
        current, depth = queue.popleft()
        elapsed_ms = int((time.time() - start) * 1000)
        if elapsed_ms >= budget.time_budget_ms:
            abort_reason = ExplorationAbortReason.TIME_BUDGET_EXHAUSTED.value
            break
        if len(nodes) >= budget.max_total_nodes:
            abort_reason = ExplorationAbortReason.NODE_BUDGET_EXHAUSTED.value
            break
        if depth >= budget.max_depth:
            if abort_reason == ExplorationAbortReason.COMPLETED_WITHIN_BUDGET.value:
                abort_reason = ExplorationAbortReason.DEPTH_LIMIT_REACHED.value
            continue

        child_budget = min(budget.max_branches_per_node, len(_RELATION_ORDER))
        used_child = 0
        for relation in _RELATION_ORDER:
            if used_child >= child_budget:
                if abort_reason == ExplorationAbortReason.COMPLETED_WITHIN_BUDGET.value:
                    abort_reason = ExplorationAbortReason.BRANCH_BUDGET_EXHAUSTED.value
                break
            if llm_calls >= budget.llm_call_budget:
                abort_reason = ExplorationAbortReason.LLM_BUDGET_EXHAUSTED.value
                break
            if token_use >= budget.token_budget:
                abort_reason = ExplorationAbortReason.TOKEN_BUDGET_EXHAUSTED.value
                break
            if len(nodes) >= budget.max_total_nodes:
                abort_reason = ExplorationAbortReason.NODE_BUDGET_EXHAUSTED.value
                break

            parent_hyp = str(current.get("hypothesis", ""))
            child_hyp = _branch_hypothesis(parent_hyp, relation)
            normalized = _normalize_text(child_hyp)
            if normalized in seen_hypothesis:
                pruned_count += 1
                if budget.abort_on_redundancy:
                    abort_reason = ExplorationAbortReason.REDUNDANCY_ABORT.value
                    break
                continue

            speculative_level = _speculative_level_for_relation(relation, depth + 1)
            if budget.abort_on_speculative_drift and speculative_level >= 0.9:
                pruned_count += 1
                abort_reason = ExplorationAbortReason.SPECULATIVE_DRIFT_ABORT.value
                break

            evidence_ids = list(current.get("evidence_anchor_ids", []))
            if relation in (ExplorationRelationType.CONTRAST, ExplorationRelationType.COUNTERREAD):
                evidence_ids = evidence_ids[:1]
            if not evidence_ids:
                low_evidence_expansions += 1
                if low_evidence_expansions > budget.max_low_evidence_expansions:
                    abort_reason = ExplorationAbortReason.LOW_EVIDENCE_LIMIT_REACHED.value
                    break

            llm_calls += 1
            token_use += max(10, len(child_hyp.split()))
            branch_count += 1
            child_id = _deterministic_node_id(current["node_id"], relation, depth + 1, used_child)
            novelty = _novelty_score(child_hyp)
            outcome = ExplorationOutcome.KEPT_FOR_VALIDATION
            if novelty < 0.18:
                outcome = ExplorationOutcome.REJECTED
                rejected_count += 1
            elif novelty < 0.24:
                outcome = ExplorationOutcome.UNRESOLVED
                unresolved_count += 1

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
                edge_id=_deterministic_edge_id(current["node_id"], child_id, relation),
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
                if _candidate_eligible(child):
                    promoted_count += 1

        if abort_reason in (
            ExplorationAbortReason.REDUNDANCY_ABORT.value,
            ExplorationAbortReason.SPECULATIVE_DRIFT_ABORT.value,
            ExplorationAbortReason.LLM_BUDGET_EXHAUSTED.value,
            ExplorationAbortReason.TOKEN_BUDGET_EXHAUSTED.value,
            ExplorationAbortReason.NODE_BUDGET_EXHAUSTED.value,
            ExplorationAbortReason.TIME_BUDGET_EXHAUSTED.value,
            ExplorationAbortReason.LOW_EVIDENCE_LIMIT_REACHED.value,
        ):
            break

    consumed = {
        "llm_calls": llm_calls,
        "tokens": token_use,
        "nodes": len(nodes),
        "branches": branch_count,
        "low_evidence_expansions": low_evidence_expansions,
        "elapsed_wall_time_ms": int((time.time() - start) * 1000),
    }
    return ExplorationResult(
        nodes=nodes,
        edges=edges,
        abort_reason=abort_reason,
        promoted_candidate_count=promoted_count,
        rejected_branch_count=rejected_count,
        unresolved_branch_count=unresolved_count,
        pruned_branch_count=pruned_count,
        consumed_budget=consumed,
    )


def deterministic_contradiction_scan(statement: str) -> ContradictionStatus:
    lowered = _normalize_text(statement)
    if "hard_conflict" in lowered or "contradiction" in lowered:
        return ContradictionStatus.HARD_CONFLICT
    if "counterread" in lowered or "counter_reading" in lowered:
        return ContradictionStatus.COUNTERVIEW_PRESENT
    if "unclear" in lowered or "unresolved" in lowered:
        return ContradictionStatus.UNRESOLVED
    if "tension" in lowered or "contrast" in lowered:
        return ContradictionStatus.SOFT_CONFLICT
    return ContradictionStatus.NONE
