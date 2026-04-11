"""Workflow manifest and artifact index helpers for the Writers Room pipeline (DS-002)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_workflow_stage(
    manifest_stages: list[dict[str, Any]],
    *,
    stage_id: str,
    artifact_key: str | None = None,
) -> None:
    entry: dict[str, Any] = {"id": stage_id, "completed_at": _utc_now()}
    if artifact_key:
        entry["artifact_key"] = artifact_key
    manifest_stages.append(entry)


def _workflow_stage_ids(manifest_stages: list[dict[str, Any]]) -> list[str]:
    return [str(s.get("id", "")) for s in manifest_stages if isinstance(s, dict)]


def _append_manifest_entry(
    manifest: list[dict[str, str]],
    obj: dict[str, Any] | None,
) -> None:
    if not isinstance(obj, dict):
        return
    aid = obj.get("artifact_id")
    acl = obj.get("artifact_class")
    if aid is not None and acl is not None:
        manifest.append({"artifact_id": str(aid), "artifact_class": str(acl)})


def _writers_room_artifact_manifest(package: dict[str, Any]) -> list[dict[str, str]]:
    """Derived index only — same taxonomy as stamped objects (gate G7)."""
    manifest: list[dict[str, str]] = []
    for item in package.get("issues") or []:
        _append_manifest_entry(manifest, item if isinstance(item, dict) else None)
    for item in package.get("recommendation_artifacts") or []:
        _append_manifest_entry(manifest, item if isinstance(item, dict) else None)
    for item in package.get("patch_candidates") or []:
        _append_manifest_entry(manifest, item if isinstance(item, dict) else None)
    for item in package.get("variant_candidates") or []:
        _append_manifest_entry(manifest, item if isinstance(item, dict) else None)
    for key in (
        "proposal_package",
        "comment_bundle",
        "review_summary",
        "model_generation",
        "retrieval_trace",
        "review_bundle",
        "governance_truth",
        "langchain_retriever_preview",
    ):
        _append_manifest_entry(manifest, package.get(key) if isinstance(package.get(key), dict) else None)
    cb = package.get("comment_bundle")
    if isinstance(cb, dict):
        for c in cb.get("comments") or []:
            _append_manifest_entry(manifest, c if isinstance(c, dict) else None)
    for notice in package.get("legacy_paths") or []:
        _append_manifest_entry(manifest, notice if isinstance(notice, dict) else None)
    goa = package.get("governance_outcome_artifact")
    if isinstance(goa, dict):
        _append_manifest_entry(manifest, goa)
    return manifest
