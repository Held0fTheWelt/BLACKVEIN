"""Types for improvement experiment capability pipeline (leaf — breaks pipeline ↔ finalize cycle)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ImprovementExperimentCapabilityOutcome:
    package_response: dict[str, Any]
    context_payload: dict[str, Any]
    retrieval_trace: dict[str, Any]
    transcript_meta: dict[str, Any]
    review_bundle: Any
    workflow_stages: list[dict[str, Any]]
