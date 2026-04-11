"""HITL governance decision on improvement recommendation packages — DS-051."""

from __future__ import annotations

from typing import Any

from app.contracts.improvement_operating_loop import ImprovementLoopStage
from app.contracts.writers_room_artifact_class import WritersRoomArtifactClass

from app.services.improvement_service import (
    IMPROVEMENT_PUBLICATION_CONTRACT_VERSION,
    ImprovementStore,
    _evaluation_metrics_fingerprint,
    _utc_now,
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
    if normalized not in {"accept", "reject", "revise"}:
        raise ValueError("decision_must_be_accept_reject_or_revise")
    if current in {"governance_accepted", "governance_rejected"}:
        raise ValueError("recommendation_already_finalized")
    if current not in {"pending_governance_review", "governance_revision_requested"}:
        raise ValueError("invalid_governance_state_for_decision")

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

    if next_status == "governance_accepted":
        package["improvement_output_artifact_class"] = WritersRoomArtifactClass.approved_authored_artifact.value
        post_verification: dict[str, Any] = {
            "contract_version": IMPROVEMENT_PUBLICATION_CONTRACT_VERSION,
            "experiment_id": experiment_id,
            "evaluation_metrics_sha256_16": metrics_fp,
            "outcome": "verified_against_stored_evaluation",
            "recorded_at": now,
            "scope": "re_read_persisted_evaluation_metrics",
        }
    else:
        package["improvement_output_artifact_class"] = WritersRoomArtifactClass.rejected_artifact.value
        post_verification = {
            "contract_version": IMPROVEMENT_PUBLICATION_CONTRACT_VERSION,
            "experiment_id": experiment_id,
            "outcome": "not_applicable",
            "recorded_at": now,
            "scope": "terminal_rejection_no_publication",
        }

    progress = package.get("improvement_loop_progress")
    if not isinstance(progress, list):
        progress = []
    progress.append(
        {
            "loop_stage": ImprovementLoopStage.approval_rejection.value,
            "completed_at": now,
            "id": "human_governance_decision",
            "resource_id": package_id,
            "detail": {"decision": normalized},
        }
    )
    progress.append(
        {
            "loop_stage": ImprovementLoopStage.publication.value,
            "completed_at": now,
            "id": "governance_registry_publication_record",
            "resource_id": package_id,
            "detail": {"terminal_governance_status": next_status},
        }
    )
    progress.append(
        {
            "loop_stage": ImprovementLoopStage.post_change_verification.value,
            "completed_at": now,
            "id": "post_change_verification_trace",
            "resource_id": package_id,
            "detail": {"outcome": post_verification.get("outcome")},
        }
    )
    package["improvement_loop_progress"] = progress

    package["publication_verification_trace"] = {
        "contract_version": IMPROVEMENT_PUBLICATION_CONTRACT_VERSION,
        "terminal_governance_status": next_status,
        "recorded_at": now,
        "declared_runtime_promotion": False,
        "verification_scope": "governance_registry_with_post_decision_verification_record",
        "publication_surface": "improvement_recommendation_registry",
        "published_record_id": package_id,
        "improvement_entry_class": package.get("improvement_entry_class"),
        "improvement_output_artifact_class": package.get("improvement_output_artifact_class"),
        "post_change_verification": post_verification,
        "requires_follow_up_audit": True,
        "note": (
            "Acceptance records HITL approval of the recommendation package only. "
            "Canonical authored truth promotion remains a separate governed action."
        ),
    }
    storage.write_json("recommendations", package_id, package)
    return package
