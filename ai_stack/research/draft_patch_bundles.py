"""Canonical DraftPatchBundle helper for research-to-revision flow."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class DraftPatchBundle(BaseModel):
    """Typed patch bundle artifact passed to writers-room draft apply."""

    patch_bundle_id: str
    module_id: str
    draft_workspace_id: str
    revision_ids: list[str]
    target_refs: list[str]
    patch_operations: list[dict[str, object]]
    requires_preview_rebuild: bool = True
    requires_evaluation: bool = True
    finding_ids: list[str] = Field(default_factory=list)
    preview_id: str | None = None
    created_at: str


def build_draft_patch_bundle(
    *,
    module_id: str,
    draft_workspace_id: str,
    revision_ids: list[str],
    target_refs: list[str],
    patch_operations: list[dict[str, object]],
    finding_ids: list[str] | None = None,
    preview_id: str | None = None,
) -> DraftPatchBundle:
    """Create canonical patch bundle with deterministic provenance fields."""
    return DraftPatchBundle(
        patch_bundle_id=f"patch_bundle_{uuid4().hex[:12]}",
        module_id=module_id,
        draft_workspace_id=draft_workspace_id,
        revision_ids=revision_ids,
        target_refs=target_refs,
        patch_operations=patch_operations,
        finding_ids=finding_ids or [],
        preview_id=preview_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
