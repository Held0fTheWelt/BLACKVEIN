"""Writers' Room artifact taxonomy (``docs/ROADMAP_MVP_GoC.md`` §6.7–7.3, gate G7)."""

from __future__ import annotations

from enum import Enum
from typing import Any

# Bumped when frozen vocabulary or artifact schema contract changes materially.
GOC_SHARED_SEMANTIC_CONTRACT_VERSION = "goc_frozen_vocab_surface_v1"

# Roadmap §7.3 — required metadata keys on governed Writers' Room artifact records.
WRITERS_ROOM_OPERATING_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "artifact_id",
        "artifact_class",
        "source_module_id",
        "shared_semantic_contract_version",
        "evidence_refs",
        "proposal_scope",
        "approval_state",
    }
)


class WritersRoomArtifactClass(str, Enum):
    """First-class artifact classes for bounded Writers' Room outputs."""

    analysis_artifact = "analysis_artifact"
    proposal_artifact = "proposal_artifact"
    candidate_authored_artifact = "candidate_authored_artifact"
    approved_authored_artifact = "approved_authored_artifact"
    rejected_artifact = "rejected_artifact"


def normalize_writers_room_artifact_class(raw: str | None) -> WritersRoomArtifactClass:
    """Parse a roadmap artifact class string; raises ValueError if missing or unknown."""
    if raw is None or not str(raw).strip():
        raise ValueError("writers_room_artifact_class_required")
    try:
        return WritersRoomArtifactClass(str(raw).strip())
    except ValueError as exc:
        raise ValueError(f"unknown_writers_room_artifact_class:{raw!r}") from exc


def build_writers_room_artifact_record(
    *,
    artifact_id: str,
    artifact_class: WritersRoomArtifactClass,
    source_module_id: str,
    evidence_refs: list[str],
    proposal_scope: str,
    approval_state: str,
) -> dict[str, Any]:
    """Return roadmap §7.3 metadata as a single dict (merge with domain fields as needed)."""
    return {
        "artifact_id": artifact_id,
        "artifact_class": artifact_class.value,
        "source_module_id": source_module_id,
        "shared_semantic_contract_version": GOC_SHARED_SEMANTIC_CONTRACT_VERSION,
        "evidence_refs": list(evidence_refs),
        "proposal_scope": proposal_scope,
        "approval_state": approval_state,
    }
