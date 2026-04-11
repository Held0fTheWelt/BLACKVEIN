"""HITL governance decision on improvement recommendation packages — DS-051."""

from __future__ import annotations

from typing import Any

from app.contracts.improvement_operating_loop import ImprovementLoopStage

from app.services.improvement_service import (
    ImprovementStore,
    _evaluation_metrics_fingerprint,
    _utc_now,
)
from app.services.improvement_service_policy_evaluators import (
    check_governance_state_valid_for_decision,
    check_recommendation_already_finalized,
    validate_improvement_decision,
    build_artifact_class_and_verification,
    build_improvement_loop_progress,
    build_publication_verification_trace,
)


def apply_improvement_recommendation_decision(
    *,
    package_id: str,
    actor_id: str,
    decision: str,
    note: str | None = None,
    store: ImprovementStore | None = None,
) -> dict[str, Any]:
    """Human governance decision on a persisted recommendation package (HITL).

    Decisions: accept | reject | revise (revise is non-terminal).
    """
    storage = store or ImprovementStore.default()
    package = storage.read_json("recommendations", package_id)
    state = package.get("governance_review_state")
    if not isinstance(state, dict):
        state = {
            "status": package.get("review_status") or "pending_governance_review",
            "updated_at": _utc_now(),
            "updated_by": actor_id,
            "history": [],
        }
    current = str(state.get("status", "pending_governance_review"))
    normalized = decision.strip().lower()

    # Apply policy validation guards
    validate_improvement_decision(decision)
    check_recommendation_already_finalized(current)
    check_governance_state_valid_for_decision(current)

    history = state.get("history")
    if not isinstance(history, list):
        history = []

    if normalized == "revise":
        next_status = "governance_revision_requested"
        history.append(
            {
                "decision": "revise",
                "status": next_status,
                "changed_at": _utc_now(),
                "changed_by": actor_id,
                "note": note or "",
            }
        )
        state["status"] = next_status
        state["updated_at"] = _utc_now()
        state["updated_by"] = actor_id
        state["history"] = history
        package["governance_review_state"] = state
        package["review_status"] = next_status
        package["next_action"] = "revision_required_before_promotion"
        package.pop("human_decision", None)
        package.pop("publication_verification_trace", None)
        storage.write_json("recommendations", package_id, package)
        return package

    next_status = "governance_accepted" if normalized == "accept" else "governance_rejected"
    history.append(
        {
            "decision": normalized,
            "status": next_status,
            "changed_at": _utc_now(),
            "changed_by": actor_id,
            "note": note or "",
        }
    )
    state["status"] = next_status
    state["updated_at"] = _utc_now()
    state["updated_by"] = actor_id
    state["history"] = history
    package["governance_review_state"] = state
    package["review_status"] = next_status
    package["next_action"] = "closed_accepted" if next_status == "governance_accepted" else "closed_rejected"
    package["human_decision"] = {
        "decision": normalized,
        "decided_by": actor_id,
        "decided_at": _utc_now(),
        "note": note or "",
    }
    now = _utc_now()
    exp_block = package.get("experiment") if isinstance(package.get("experiment"), dict) else {}
    experiment_id = exp_block.get("experiment_id")
    evaluation = package.get("evaluation") if isinstance(package.get("evaluation"), dict) else {}
    metrics_fp = _evaluation_metrics_fingerprint(evaluation)

    # Build artifact class and post-verification record based on decision
    artifact_class_value, post_verification = build_artifact_class_and_verification(
        decision=normalized,
        now=now,
        experiment_id=experiment_id,
        metrics_fp=metrics_fp,
    )
    package["improvement_output_artifact_class"] = artifact_class_value
    package["post_verification"] = post_verification

    # Build improvement loop progress entries
    progress = package.get("improvement_loop_progress")
    if not isinstance(progress, list):
        progress = []
    progress.extend(build_improvement_loop_progress(normalized, now, package_id))
    package["improvement_loop_progress"] = progress

    # Build publication verification trace record
    package["publication_verification_trace"] = build_publication_verification_trace(
        decision=normalized,
        now=now,
        package=package,
        next_status=next_status,
    )
    storage.write_json("recommendations", package_id, package)
    return package
