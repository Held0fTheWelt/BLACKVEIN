"""Deterministic verification and promotion logic (single owner)."""

from __future__ import annotations

from typing import Any

from ai_stack.research_claims import is_schema_valid_claim_payload
from ai_stack.research_contract import (
    ContradictionStatus,
    Perspective,
    ResearchClaimRecord,
    ResearchStatus,
    ensure_status_transition_allowed,
)
from ai_stack.research_exploration import deterministic_contradiction_scan
from ai_stack.research_store import ResearchStore


DEFAULT_SUPPORT_THRESHOLD = 0.6


def _support_level(anchor_count: int, avg_confidence: float) -> float:
    coverage = min(1.0, anchor_count / 3.0)
    score = (0.55 * coverage) + (0.45 * avg_confidence)
    return round(max(0.0, min(1.0, score)), 4)


def _avg_anchor_confidence(anchor_ids: list[str], anchors_by_id: dict[str, dict[str, Any]]) -> float:
    if not anchor_ids:
        return 0.0
    values: list[float] = []
    for anchor_id in anchor_ids:
        row = anchors_by_id.get(anchor_id)
        if not isinstance(row, dict):
            continue
        confidence = row.get("confidence")
        if isinstance(confidence, (float, int)):
            values.append(float(confidence))
    if not values:
        return 0.0
    return sum(values) / len(values)


def evaluate_candidate_from_exploration_node(node: dict[str, Any]) -> tuple[bool, str]:
    payload = {
        "claim_type": "improvement_lead",
        "statement": node.get("hypothesis"),
        "evidence_anchor_ids": node.get("evidence_anchor_ids", []),
        "perspective": node.get("perspective"),
    }
    if not node.get("evidence_anchor_ids"):
        return False, "promotion_block:no_evidence_anchor"
    if node.get("outcome") != "kept_for_validation":
        return False, "promotion_block:not_kept_for_validation"
    contradiction = deterministic_contradiction_scan(str(node.get("hypothesis", "")))
    if contradiction == ContradictionStatus.HARD_CONFLICT:
        return False, "promotion_block:hard_conflict"
    if not is_schema_valid_claim_payload(payload):
        return False, "promotion_block:invalid_claim_shape"
    if node.get("status") != ResearchStatus.EXPLORATORY.value:
        return False, "promotion_block:not_exploratory_status"
    return True, "promotion_allowed"


def verify_and_promote_claims(
    *,
    store: ResearchStore,
    work_id: str,
    candidate_payloads: list[dict[str, Any]],
    support_threshold: float = DEFAULT_SUPPORT_THRESHOLD,
) -> dict[str, Any]:
    anchors = store.list_anchors()
    anchors_by_id = {row["anchor_id"]: row for row in anchors}
    decisions: list[dict[str, Any]] = []
    stored_claims: list[dict[str, Any]] = []

    for payload in sorted(candidate_payloads, key=lambda row: (str(row.get("statement", "")), str(row.get("perspective", "")))):
        statement = str(payload.get("statement", "")).strip()
        if not statement:
            continue
        perspective_raw = str(payload.get("perspective", Perspective.PLAYWRIGHT.value))
        perspective = Perspective(perspective_raw if perspective_raw in {p.value for p in Perspective} else Perspective.PLAYWRIGHT.value)
        evidence_anchor_ids = list(payload.get("evidence_anchor_ids", []))
        if any(anchor_id not in anchors_by_id for anchor_id in evidence_anchor_ids):
            decisions.append({"statement": statement, "decision": "blocked", "reason": "unknown_evidence_anchor"})
            continue
        contradiction = deterministic_contradiction_scan(statement)
        avg_conf = _avg_anchor_confidence(evidence_anchor_ids, anchors_by_id)
        support = _support_level(len(evidence_anchor_ids), avg_conf)

        # exploratory -> candidate
        exploratory_status = ResearchStatus.EXPLORATORY
        candidate_status = ResearchStatus.CANDIDATE
        try:
            ensure_status_transition_allowed(exploratory_status, candidate_status)
        except ValueError as exc:
            decisions.append({"statement": statement, "decision": "blocked", "reason": str(exc)})
            continue
        if not evidence_anchor_ids:
            decisions.append({"statement": statement, "decision": "blocked", "reason": "no_evidence_anchor"})
            continue
        if contradiction == ContradictionStatus.HARD_CONFLICT:
            decisions.append({"statement": statement, "decision": "blocked", "reason": "hard_conflict"})
            continue
        if not is_schema_valid_claim_payload(
            {
                "claim_type": payload.get("claim_type", "improvement_lead"),
                "statement": statement,
                "evidence_anchor_ids": evidence_anchor_ids,
                "perspective": perspective.value,
            }
        ):
            decisions.append({"statement": statement, "decision": "blocked", "reason": "invalid_claim_payload"})
            continue

        # candidate -> validated
        try:
            ensure_status_transition_allowed(candidate_status, ResearchStatus.VALIDATED)
        except ValueError as exc:
            decisions.append({"statement": statement, "decision": "blocked", "reason": str(exc)})
            continue
        if support < support_threshold:
            decisions.append({"statement": statement, "decision": "blocked", "reason": "support_below_threshold"})
            continue
        if contradiction == ContradictionStatus.HARD_CONFLICT:
            decisions.append({"statement": statement, "decision": "blocked", "reason": "hard_conflict"})
            continue

        # validated -> approved_research
        try:
            ensure_status_transition_allowed(ResearchStatus.VALIDATED, ResearchStatus.APPROVED_RESEARCH)
        except ValueError as exc:
            decisions.append({"statement": statement, "decision": "blocked", "reason": str(exc)})
            continue
        if contradiction == ContradictionStatus.UNRESOLVED and support < 0.75:
            decisions.append({"statement": statement, "decision": "blocked", "reason": "unresolved_mandatory_blocker"})
            continue

        # approved_research -> canon_applicable
        final_status = ResearchStatus.APPROVED_RESEARCH
        if payload.get("canon_relevance_hint") is True:
            ensure_status_transition_allowed(ResearchStatus.APPROVED_RESEARCH, ResearchStatus.CANON_APPLICABLE)
            final_status = ResearchStatus.CANON_APPLICABLE

        claim = ResearchClaimRecord(
            claim_id=store.next_id("claim"),
            work_id=work_id,
            perspective=perspective,
            claim_type=str(payload.get("claim_type") or "improvement_lead"),
            statement=statement,
            evidence_anchor_ids=evidence_anchor_ids,
            support_level=support,
            contradiction_status=contradiction,
            status=final_status,
            notes=str(payload.get("notes") or "verification_pass_recorded"),
        ).to_dict()
        stored = store.upsert_claim(claim)
        stored_claims.append(stored)
        decisions.append(
            {
                "claim_id": stored["claim_id"],
                "statement": statement,
                "decision": "promoted",
                "status": final_status.value,
                "support_level": support,
                "contradiction_status": contradiction.value,
            }
        )

    return {
        "claims": stored_claims,
        "decisions": decisions,
        "support_threshold": support_threshold,
    }
