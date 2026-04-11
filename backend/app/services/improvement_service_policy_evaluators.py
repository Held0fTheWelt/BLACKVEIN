"""Policy evaluators and validation guards for improvement recommendation decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ImprovementRecommendationPolicy:
    """Configuration object for improvement recommendation evaluation policies."""

    valid_decisions: frozenset[str] = frozenset({"accept", "reject", "revise"})
    terminal_statuses: frozenset[str] = frozenset(
        {"governance_accepted", "governance_rejected"}
    )
    allowed_revision_states: frozenset[str] = frozenset(
        {"pending_governance_review", "governance_revision_requested"}
    )


def validate_improvement_decision(decision: str) -> None:
    """Validate that decision is one of the allowed values.

    Args:
        decision: Decision string to validate (accept, reject, revise)

    Raises:
        ValueError: If decision is not in {accept, reject, revise}
    """
    normalized = decision.strip().lower()
    policy = ImprovementRecommendationPolicy()
    if normalized not in policy.valid_decisions:
        raise ValueError("decision_must_be_accept_reject_or_revise")


def check_recommendation_already_finalized(current_status: str) -> None:
    """Check if recommendation is already in a terminal state.

    Args:
        current_status: Current governance review status

    Raises:
        ValueError: If recommendation is already finalized
    """
    policy = ImprovementRecommendationPolicy()
    if current_status in policy.terminal_statuses:
        raise ValueError("recommendation_already_finalized")


def check_governance_state_valid_for_decision(current_status: str) -> None:
    """Check if current governance state allows a decision to be applied.

    Args:
        current_status: Current governance review status

    Raises:
        ValueError: If current state doesn't allow a decision
    """
    policy = ImprovementRecommendationPolicy()
    if current_status not in policy.allowed_revision_states:
        raise ValueError("invalid_governance_state_for_decision")


def build_artifact_class_and_verification(
    decision: str,
    now: str,
    experiment_id: str | None,
    metrics_fp: str,
) -> tuple[str, dict[str, Any]]:
    """Build artifact class value and post-verification record based on decision.

    Args:
        decision: Normalized decision (accept or reject)
        now: Current timestamp
        experiment_id: Experiment ID from package
        metrics_fp: Evaluation metrics fingerprint

    Returns:
        Tuple of (artifact_class_value, post_verification_dict)
    """
    from app.contracts.writers_room_artifact_class import WritersRoomArtifactClass
    from app.services.improvement_service import IMPROVEMENT_PUBLICATION_CONTRACT_VERSION

    if decision == "accept":
        artifact_class = WritersRoomArtifactClass.approved_authored_artifact.value
        post_verification = {
            "contract_version": IMPROVEMENT_PUBLICATION_CONTRACT_VERSION,
            "experiment_id": experiment_id,
            "evaluation_metrics_sha256_16": metrics_fp,
            "outcome": "verified_against_stored_evaluation",
            "recorded_at": now,
            "scope": "re_read_persisted_evaluation_metrics",
        }
    else:  # reject
        artifact_class = WritersRoomArtifactClass.rejected_artifact.value
        post_verification = {
            "contract_version": IMPROVEMENT_PUBLICATION_CONTRACT_VERSION,
            "experiment_id": experiment_id,
            "outcome": "not_applicable",
            "recorded_at": now,
            "scope": "terminal_rejection_no_publication",
        }

    return artifact_class, post_verification


def build_improvement_loop_progress(
    decision: str,
    now: str,
    package_id: str,
) -> list[dict[str, Any]]:
    """Build improvement loop progress entries for accept/reject decision.

    Args:
        decision: Normalized decision (accept or reject)
        now: Current timestamp
        package_id: Package ID for resource reference

    Returns:
        List of 3 progress entry dicts (approval_rejection, publication, post_change_verification)
    """
    from app.contracts.improvement_operating_loop import ImprovementLoopStage

    progress: list[dict[str, Any]] = [
        {
            "loop_stage": ImprovementLoopStage.approval_rejection.value,
            "completed_at": now,
            "id": "human_governance_decision",
            "resource_id": package_id,
            "detail": {"decision": decision},
        },
        {
            "loop_stage": ImprovementLoopStage.publication.value,
            "completed_at": now,
            "id": "governance_registry_publication_record",
            "resource_id": package_id,
            "detail": {
                "terminal_governance_status": (
                    "governance_accepted" if decision == "accept" else "governance_rejected"
                )
            },
        },
        {
            "loop_stage": ImprovementLoopStage.post_change_verification.value,
            "completed_at": now,
            "id": "post_change_verification_trace",
            "resource_id": package_id,
            "detail": {
                "outcome": (
                    "verified_against_stored_evaluation"
                    if decision == "accept"
                    else "not_applicable"
                )
            },
        },
    ]
    return progress


def build_publication_verification_trace(
    decision: str,
    now: str,
    package: dict[str, Any],
    next_status: str,
) -> dict[str, Any]:
    """Build publication verification trace record for final decision record.

    Args:
        decision: Normalized decision (accept or reject)
        now: Current timestamp
        package: Package dict (for artifact class info)
        next_status: Terminal governance status

    Returns:
        Publication verification trace dict
    """
    from app.services.improvement_service import IMPROVEMENT_PUBLICATION_CONTRACT_VERSION

    return {
        "contract_version": IMPROVEMENT_PUBLICATION_CONTRACT_VERSION,
        "terminal_governance_status": next_status,
        "recorded_at": now,
        "declared_runtime_promotion": False,
        "verification_scope": "governance_registry_with_post_decision_verification_record",
        "publication_surface": "improvement_recommendation_registry",
        "published_record_id": package.get("package_id", "unknown"),
        "improvement_entry_class": package.get("improvement_entry_class"),
        "improvement_output_artifact_class": package.get("improvement_output_artifact_class"),
        "post_change_verification": package.get("post_verification", {}),
        "requires_follow_up_audit": True,
        "note": (
            "Acceptance records HITL approval of the recommendation package only. "
            "Canonical authored truth promotion remains a separate governed action."
        ),
    }
