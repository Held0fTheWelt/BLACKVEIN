"""Writers Room packaging stage — Recommendation Bundling sub-stage (DS-002 stage 4)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.contracts.writers_room_artifact_class import (
    WritersRoomArtifactClass,
    build_writers_room_artifact_record,
)


def bundle_recommendations_from_output(
    *,
    structured: dict[str, Any] | None,
    generation: dict[str, Any],
    proposal_id: str,
    module_id: str,
    evidence_paths: list[str],
) -> list[dict[str, Any]]:
    """Aggregate recommendations from structured output and generation content.

    Combines base recommendations with structured output items and generation excerpt.

    Args:
        structured: Parsed structured output metadata (may be None).
        generation: Model generation dict with content.
        proposal_id: Proposal identifier for artifact linking.
        module_id: Module identifier for governance tracing.
        evidence_paths: List of source paths for evidence references.

    Returns:
        List of recommendation artifacts with bodies and evidence refs.
    """
    recommendation_texts = [
        "Verify scene-level continuity against retrieved evidence before publishing.",
        "Prioritize contradictory characterization notes for human review.",
        "Preserve recommendation-only status until admin approval.",
    ]
    if structured:
        for item in structured.get("recommendations") or []:
            if item:
                recommendation_texts.append(str(item))
    if generation["content"]:
        recommendation_texts.append(generation["content"][:220])

    rec_refs = [p for p in evidence_paths if p][:5]
    recommendation_artifacts: list[dict[str, Any]] = []
    for idx, body in enumerate(recommendation_texts, start=1):
        rid = f"rec_{proposal_id}_{idx}"
        recommendation_artifacts.append(
            {
                **build_writers_room_artifact_record(
                    artifact_id=rid,
                    artifact_class=WritersRoomArtifactClass.analysis_artifact,
                    source_module_id=module_id,
                    evidence_refs=list(rec_refs),
                    proposal_scope="writers_room_bounded_recommendation",
                    approval_state="pending_review",
                ),
                "body": body,
            }
        )

    return recommendation_artifacts
