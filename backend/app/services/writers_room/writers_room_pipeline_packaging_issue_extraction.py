"""Writers Room packaging stage — Issue Extraction sub-stage (DS-002 stage 4)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.contracts.writers_room_artifact_class import (
    WritersRoomArtifactClass,
    build_writers_room_artifact_record,
)


def extract_issues_from_packaging(
    *,
    source_rows: list[dict[str, Any]],
    module_id: str,
    evidence_tag: str,
) -> list[dict[str, Any]]:
    """Extract canon alignment issues from retrieval results.

    Processes up to 3 source rows and creates issue artifacts with severity/confidence mapping.

    Args:
        source_rows: Ranked retrieval results with source paths.
        module_id: Module identifier for governance tracing.
        evidence_tag: Evidence tier classification (e.g. 'strong', 'moderate', 'weak').

    Returns:
        List of issue artifacts with severity, type, description, and evidence references.
    """
    issues: list[dict[str, Any]] = []
    for index, source in enumerate(source_rows[:3], start=1):
        path = str(source.get("source_path", "") or "")
        ib = build_writers_room_artifact_record(
            artifact_id=f"issue_{index}",
            artifact_class=WritersRoomArtifactClass.analysis_artifact,
            source_module_id=module_id,
            evidence_refs=[path] if path else [],
            proposal_scope="retrieval_linked_issue",
            approval_state="pending_review",
        )
        issues.append(
            {
                **ib,
                "id": ib["artifact_id"],
                "severity": "medium",
                "type": "consistency",
                "description": f"Review source {path} for canon alignment in {module_id}.",
                "evidence_source": path,
                "linked_source_path": path,
                "evidence_tier": evidence_tag,
                "confidence_kind": "retrieval_heuristic",
                "revision_sensitivity": "high" if evidence_tag in {"strong", "moderate"} else "standard",
                "rationale": f"Issue derived from ranked retrieval hit for {path or 'unknown'}.",
            }
        )

    return issues
