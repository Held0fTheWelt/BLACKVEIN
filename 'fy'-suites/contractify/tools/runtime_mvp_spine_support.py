"""Shared helper types for runtime MVP spine section modules."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from contractify.tools.models import ConflictFinding, ContractRecord, ProjectionRecord

RUNTIME_AUTHORITY = "runtime_authority"
SLICE_NORMATIVE = "slice_normative"
IMPLEMENTATION_EVIDENCE = "implementation_evidence"
VERIFICATION_EVIDENCE = "verification_evidence"
PROJECTION_LOW = "projection_low"

@dataclass(frozen=True)
class SpineHelpers:
    contract: Callable[..., ContractRecord]
    projection: Callable[..., ProjectionRecord]
    existing: Callable[..., list[str]]
    one_of: Callable[..., list[str]]
    adr0001: Callable[[Path], str]
    adr0002: Callable[[Path], str]
    adr0003: Callable[[Path], str]
    path_target_id: Callable[[dict[str, str], str], str]
    make_review_conflict: Callable[..., ConflictFinding | None]
