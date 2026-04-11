"""Hilfsfunktionen und Datentypen für bounded exploration (Feinsplit von research_exploration_bounded_core)."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

from ai_stack.research_contract import ExplorationRelationType, ResearchStatus, ExplorationOutcome

RELATION_ORDER: tuple[ExplorationRelationType, ...] = (
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


def normalize_text(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def novelty_score(hypothesis: str) -> float:
    tokens = normalize_text(hypothesis).split()
    if not tokens:
        return 0.0
    unique = len(set(tokens))
    score = unique / len(tokens)
    return round(min(1.0, max(0.0, score)), 4)


def deterministic_node_id(seed: str, relation: ExplorationRelationType, depth: int, ordinal: int) -> str:
    raw = f"{seed}|{relation.value}|{depth}|{ordinal}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:14]
    return f"node_{digest}"


def deterministic_edge_id(from_node: str, to_node: str, relation: ExplorationRelationType) -> str:
    raw = f"{from_node}|{to_node}|{relation.value}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:14]
    return f"edge_{digest}"


def branch_hypothesis(base: str, relation: ExplorationRelationType) -> str:
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


def speculative_level_for_relation(relation: ExplorationRelationType, depth: int) -> float:
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


def candidate_eligible(node: dict[str, Any]) -> bool:
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
