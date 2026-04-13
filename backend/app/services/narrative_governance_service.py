"""Core backend services for narrative governance MVP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
from uuid import uuid4

from app.extensions import db
from app.models import (
    NarrativeEvaluationCoverage,
    NarrativeEvaluationRun,
    NarrativeNotification,
    NarrativeNotificationRule,
    NarrativePackage,
    NarrativePackageHistoryEvent,
    NarrativePreview,
    NarrativeRevisionCandidate,
    NarrativeRevisionConflict,
    NarrativeRevisionStatusHistory,
    NarrativeRuntimeHealthEvent,
    NarrativeRuntimeHealthRollup,
    SiteSetting,
)
from app.models.narrative_contracts import DraftPatchBundle, ValidationFeedback
from app.models.narrative_enums import NarrativeEventType
from app.services.game_service import (
    GameServiceError,
    end_narrative_preview_session,
    get_narrative_runtime_health,
    get_narrative_runtime_state,
    get_narrative_runtime_validator_config,
    load_narrative_preview_package,
    reload_active_narrative_package,
    start_narrative_preview_session,
    unload_narrative_preview_package,
)


class NarrativeGovernanceError(RuntimeError):
    """Base narrative governance service error."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _compiled_module_root(module_id: str) -> Path:
    return Path(__file__).resolve().parents[3] / "content" / "compiled_packages" / module_id


def _load_json_file(path: Path) -> dict[str, object]:
    """Read and decode a JSON object file."""
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _ensure_artifact_paths(module_id: str, package_version: str, *, preview_id: str | None = None) -> Path:
    root = _compiled_module_root(module_id)
    if preview_id:
        artifact_dir = root / "previews" / preview_id
    else:
        artifact_dir = root / "versions" / package_version
    if not artifact_dir.exists():
        raise NarrativeGovernanceError(
            f"Compiled artifact directory does not exist: {artifact_dir}",
            code="package_artifacts_missing",
        )
    for filename in ("manifest.json", "package.json", "validation_report.json"):
        if not (artifact_dir / filename).exists():
            raise NarrativeGovernanceError(
                f"Compiled artifact is incomplete: missing {filename}",
                code="rollback_blocked_incomplete_artifacts",
            )
    return artifact_dir


def _resolve_preview_artifact(
    *,
    module_id: str,
    draft_workspace_id: str,
    source_revision: str,
    preview_id: str | None,
) -> tuple[str, Path]:
    """Resolve existing preview artifact directory without generating synthetic preview ids."""
    root = _compiled_module_root(module_id) / "previews"
    if preview_id:
        artifact_dir = _ensure_artifact_paths(module_id, "", preview_id=preview_id)
        return preview_id, artifact_dir
    if not root.exists():
        raise NarrativeGovernanceError(
            f"Preview artifacts do not exist for module {module_id}.",
            code="preview_build_blocked",
        )

    candidates: list[tuple[int, float, str, Path]] = []
    source_prefix = source_revision[:12]
    for child in root.iterdir():
        if not child.is_dir():
            continue
        try:
            _ensure_artifact_paths(module_id, "", preview_id=child.name)
        except NarrativeGovernanceError:
            continue
        metadata = _load_json_file(child / "preview_metadata.json")
        manifest = _load_json_file(child / "manifest.json")
        score = 0
        if metadata.get("draft_workspace_id") == draft_workspace_id:
            score += 5
        if metadata.get("source_revision") == source_revision:
            score += 5
        if str(manifest.get("source_revision") or "").startswith(source_prefix):
            score += 3
        if str(metadata.get("source_revision") or "").startswith(source_prefix):
            score += 2
        mtime = child.stat().st_mtime
        candidates.append((score, mtime, child.name, child))

    if not candidates:
        raise NarrativeGovernanceError(
            "Preview artifacts are missing or incomplete for requested draft/source combination.",
            code="preview_build_blocked",
        )
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best = candidates[0]
    if len(candidates) > 1 and best[0] == 0 and candidates[1][0] == 0:
        raise NarrativeGovernanceError(
            "Multiple preview artifacts found but none match the requested draft/source metadata.",
            code="preview_build_blocked",
        )
    return best[2], best[3]


def _derive_active_version(preview_package_version: str) -> str:
    """Derive immutable active version from preview package version."""
    marker = "-preview"
    if marker in preview_package_version:
        base = preview_package_version.split(marker, 1)[0].strip()
        if base:
            return base
    return preview_package_version


def _copy_preview_into_version(*, module_id: str, preview_id: str, target_version: str) -> Path:
    """Copy immutable preview artifacts into versions namespace."""
    source_dir = _ensure_artifact_paths(module_id, "", preview_id=preview_id)
    target_dir = _compiled_module_root(module_id) / "versions" / target_version
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("manifest.json", "package.json", "validation_report.json"):
        shutil.copy2(source_dir / filename, target_dir / filename)
    return target_dir


def _raise_world_engine_reload_refused(*, module_id: str, target_version: str, reason: str) -> None:
    raise NarrativeGovernanceError(
        f"World-engine refused active reload for {module_id}@{target_version}: {reason}",
        code="world_engine_reload_refused",
    )


def _request_world_engine_active_reload(*, module_id: str, target_version: str) -> dict[str, object]:
    """Request world-engine active reload and enforce explicit refusal mapping."""
    try:
        return reload_active_narrative_package(
            module_id=module_id,
            expected_active_version=target_version,
        )
    except GameServiceError as exc:
        _raise_world_engine_reload_refused(
            module_id=module_id,
            target_version=target_version,
            reason=str(exc),
        )


def _is_condition_match(condition: dict[str, object], payload: dict[str, object]) -> bool:
    """Evaluate basic JSON-rule condition operators for notification rules."""
    if not condition:
        return True
    for key, expected in condition.items():
        actual = payload.get(key)
        if isinstance(expected, dict):
            for op, value in expected.items():
                if op == "$gte":
                    if not isinstance(actual, (int, float)) or actual < value:
                        return False
                elif op == "$lte":
                    if not isinstance(actual, (int, float)) or actual > value:
                        return False
                elif op == "$eq":
                    if actual != value:
                        return False
                elif op == "$in":
                    if not isinstance(value, list) or actual not in value:
                        return False
                else:
                    return False
        else:
            if actual != expected:
                return False
    return True


def emit_narrative_event(
    *,
    event_type: str,
    severity: str,
    module_id: str | None,
    related_ref: str | None,
    payload: dict[str, object],
) -> str:
    """Emit a governance event and evaluate notification rules for feed routing."""
    event_payload: dict[str, object] = {"module_id": module_id, "related_ref": related_ref, **payload}
    rules = NarrativeNotificationRule.query.filter_by(event_type=event_type, enabled=True).all()
    matched_rules = [rule for rule in rules if _is_condition_match(rule.condition_json or {}, event_payload)]
    if not matched_rules:
        matched_rules = []

    notification_ids: list[str] = []
    if matched_rules:
        for rule in matched_rules:
            notification_id = _new_id("notif")
            notification = NarrativeNotification(
                notification_id=notification_id,
                event_type=event_type,
                severity=severity,
                title=f"{event_type.replace('_', ' ').title()}",
                body=str(payload.get("message", ""))[:2000] or None,
                payload_json={
                    **event_payload,
                    "rule_id": rule.rule_id,
                    "channels": [str(item) for item in (rule.channels_json or [])],
                    "recipients": [str(item) for item in (rule.recipients_json or [])],
                },
                created_at=_utc_now(),
            )
            db.session.add(notification)
            notification_ids.append(notification_id)
    else:
        notification_id = _new_id("notif")
        notification = NarrativeNotification(
            notification_id=notification_id,
            event_type=event_type,
            severity=severity,
            title=f"{event_type.replace('_', ' ').title()}",
            body=str(payload.get("message", ""))[:2000] or None,
            payload_json={**event_payload, "channels": ["admin_ui"], "recipients": []},
            created_at=_utc_now(),
        )
        db.session.add(notification)
        notification_ids.append(notification_id)

    db.session.flush()
    return notification_ids[0]


@dataclass(slots=True)
class PreviewBuildResult:
    preview_id: str
    package_version: str
    build_status: str
    validation_status: str


def build_preview(
    *,
    module_id: str,
    draft_workspace_id: str,
    source_revision: str,
    reason: str,
    actor_id: str | None,
    preview_id: str | None = None,
) -> PreviewBuildResult:
    """Register a preview build from existing compiled preview artifacts."""
    resolved_preview_id, artifact_root = _resolve_preview_artifact(
        module_id=module_id,
        draft_workspace_id=draft_workspace_id,
        source_revision=source_revision,
        preview_id=preview_id,
    )
    manifest = _load_json_file(artifact_root / "manifest.json")
    validation_report = _load_json_file(artifact_root / "validation_report.json")
    package_version = str(manifest.get("package_version") or f"{source_revision[:12]}-preview")
    validation_status = str(validation_report.get("validation_status") or "passing")
    preview = NarrativePreview(
        preview_id=resolved_preview_id,
        module_id=module_id,
        package_version=package_version,
        draft_workspace_id=draft_workspace_id,
        build_status="built",
        validation_status=validation_status,
        evaluation_status="not_run",
        promotion_readiness_json={"is_promotable": False, "blocking_reasons": ["evaluation_missing"]},
        artifact_root_path=str(artifact_root),
        created_by=actor_id,
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    db.session.add(preview)
    db.session.add(
        NarrativePackageHistoryEvent(
            module_id=module_id,
            event_type="build",
            package_version=package_version,
            preview_id=resolved_preview_id,
            actor_id=actor_id,
            reason=reason,
            metadata_json={"source_revision": source_revision, "draft_workspace_id": draft_workspace_id},
            occurred_at=_utc_now(),
        )
    )
    emit_narrative_event(
        event_type=NarrativeEventType.PREVIEW_BUILD_CREATED.value,
        severity="info",
        module_id=module_id,
        related_ref=resolved_preview_id,
        payload={"message": f"Preview {resolved_preview_id} built for {module_id}."},
    )
    db.session.commit()
    return PreviewBuildResult(
        preview_id=resolved_preview_id,
        package_version=package_version,
        build_status="built",
        validation_status=validation_status,
    )


def transition_revision(
    *,
    revision_id: str,
    to_status: str,
    actor_id: str | None,
    actor_role: str | None,
    notes: str | None,
) -> dict[str, str]:
    """Apply guarded revision state-machine transition."""
    candidate = NarrativeRevisionCandidate.query.filter_by(revision_id=revision_id).first()
    if candidate is None:
        raise NarrativeGovernanceError("Revision candidate not found.", code="revision_not_found")

    allowed: dict[str, set[str]] = {
        "pending": {"in_review", "rejected"},
        "in_review": {"approved", "rejected", "needs_rework"},
        "needs_rework": {"in_review", "archived"},
        "approved": {"applied_to_draft"},
        "applied_to_draft": {"ready_for_promotion", "needs_rework"},
        "ready_for_promotion": {"promoted", "needs_rework", "archived"},
        "rejected": {"archived"},
        "promoted": {"archived"},
        "archived": set(),
    }
    from_status = candidate.review_status
    role = (actor_role or "").strip().lower()
    if to_status not in allowed.get(from_status, set()):
        raise NarrativeGovernanceError(
            f"Invalid revision transition from {from_status} to {to_status}.",
            code="invalid_revision_transition",
        )
    role_allowed: dict[tuple[str, str], set[str]] = {
        ("pending", "in_review"): {"operator", "reviewer", "admin"},
        ("pending", "rejected"): {"operator", "reviewer", "admin"},
        ("in_review", "approved"): {"operator", "reviewer", "admin"},
        ("in_review", "rejected"): {"operator", "reviewer", "admin"},
        ("in_review", "needs_rework"): {"operator", "reviewer", "admin"},
        ("needs_rework", "in_review"): {"operator", "reviewer", "admin"},
        ("needs_rework", "archived"): {"operator", "reviewer", "admin"},
        ("approved", "applied_to_draft"): {"system"},
        ("applied_to_draft", "ready_for_promotion"): {"system"},
        ("applied_to_draft", "needs_rework"): {"operator", "reviewer", "admin"},
        ("ready_for_promotion", "promoted"): {"operator", "admin"},
        ("ready_for_promotion", "needs_rework"): {"operator", "reviewer", "admin"},
        ("ready_for_promotion", "archived"): {"operator", "reviewer", "admin"},
        ("rejected", "archived"): {"operator", "reviewer", "admin"},
        ("promoted", "archived"): {"operator", "admin"},
    }
    allowed_roles = role_allowed.get((from_status, to_status), {"operator", "admin"})
    if role not in allowed_roles:
        raise NarrativeGovernanceError(
            f"Role '{actor_role}' is not allowed to transition {from_status} -> {to_status}.",
            code="transition_role_not_allowed",
        )
    candidate.review_status = to_status
    candidate.updated_at = _utc_now()
    db.session.add(
        NarrativeRevisionStatusHistory(
            revision_id=revision_id,
            from_status=from_status,
            to_status=to_status,
            actor_id=actor_id,
            actor_role=actor_role,
            notes=notes,
            occurred_at=_utc_now(),
        )
    )
    emit_narrative_event(
        event_type=NarrativeEventType.REVISION_STATE_CHANGED.value,
        severity="info",
        module_id=candidate.module_id,
        related_ref=revision_id,
        payload={"from_status": from_status, "to_status": to_status},
    )
    db.session.commit()
    return {"revision_id": revision_id, "from_status": from_status, "to_status": to_status}


def detect_conflicts_for_module(module_id: str) -> list[dict[str, str | list[str]]]:
    """Detect and persist basic target-overlap conflicts for open revisions."""
    rows = NarrativeRevisionCandidate.query.filter(
        NarrativeRevisionCandidate.module_id == module_id,
        NarrativeRevisionCandidate.review_status.in_(["pending", "in_review", "approved"]),
    ).all()
    groups: dict[tuple[str, str], list[NarrativeRevisionCandidate]] = {}
    for row in rows:
        groups.setdefault((row.target_kind, row.target_ref), []).append(row)
    created: list[dict[str, str | list[str]]] = []
    for (target_kind, target_ref), grouped in groups.items():
        if len(grouped) < 2:
            continue
        ids = sorted([item.revision_id for item in grouped])
        existing = NarrativeRevisionConflict.query.filter_by(
            module_id=module_id,
            conflict_type="target_overlap",
            target_kind=target_kind,
            target_ref=target_ref,
            resolution_status="pending",
        ).first()
        if existing is not None:
            existing.candidate_ids_json = ids
            conflict_id = existing.conflict_id
        else:
            conflict_id = _new_id("conf")
            db.session.add(
                NarrativeRevisionConflict(
                    conflict_id=conflict_id,
                    module_id=module_id,
                    candidate_ids_json=ids,
                    conflict_type="target_overlap",
                    target_kind=target_kind,
                    target_ref=target_ref,
                    resolution_status="pending",
                    created_at=_utc_now(),
                )
            )
            emit_narrative_event(
                event_type=NarrativeEventType.REVISION_CONFLICT_DETECTED.value,
                severity="warning",
                module_id=module_id,
                related_ref=conflict_id,
                payload={"target_ref": target_ref, "candidate_ids": ids},
            )
        created.append(
            {
                "conflict_id": conflict_id,
                "target_kind": target_kind,
                "target_ref": target_ref,
                "candidate_ids": ids,
            }
        )
    db.session.commit()
    return created


def apply_revision_bundle_to_draft(
    *,
    bundle: DraftPatchBundle,
    requested_by: str,
) -> dict[str, object]:
    """Validate and persist draft-apply audit status for a patch bundle."""
    unresolved = NarrativeRevisionConflict.query.filter(
        NarrativeRevisionConflict.module_id == bundle.module_id,
        NarrativeRevisionConflict.resolution_status == "pending",
    ).count()
    if unresolved:
        raise NarrativeGovernanceError(
            "Unresolved revision conflicts block apply-to-draft.",
            code="revision_conflicts_unresolved",
        )
    revisions = NarrativeRevisionCandidate.query.filter(
        NarrativeRevisionCandidate.revision_id.in_(bundle.revision_ids),
    ).all()
    revision_map = {item.revision_id: item for item in revisions}
    for revision_id in bundle.revision_ids:
        candidate = revision_map.get(revision_id)
        if candidate is None:
            raise NarrativeGovernanceError("Revision candidate not found.", code="revision_not_found")
        if candidate.review_status != "approved":
            raise NarrativeGovernanceError(
                "Apply-to-draft requires approved revisions only.",
                code="revision_not_approved",
            )
        if not candidate.target_ref:
            raise NarrativeGovernanceError(
                "Draft target reference no longer resolves.",
                code="draft_target_ref_not_resolved",
            )
        candidate.review_status = "applied_to_draft"
        candidate.updated_at = _utc_now()
        db.session.add(
            NarrativeRevisionStatusHistory(
                revision_id=candidate.revision_id,
                from_status="approved",
                to_status="applied_to_draft",
                actor_id=requested_by,
                actor_role="system",
                notes=f"Applied via patch bundle {bundle.patch_bundle_id}",
                occurred_at=_utc_now(),
            )
        )
    db.session.commit()
    return {
        "patch_bundle_id": bundle.patch_bundle_id,
        "draft_workspace_id": bundle.draft_workspace_id,
        "applied": True,
        "applied_revision_ids": bundle.revision_ids,
    }


def record_evaluation_run(
    *,
    module_id: str,
    preview_id: str | None,
    package_version: str | None,
    run_type: str,
    status: str,
    scores: dict[str, float],
    promotion_readiness: dict[str, object] | None = None,
) -> dict[str, object]:
    """Create or update a single evaluation run record."""
    run_id = _new_id("eval")
    row = NarrativeEvaluationRun(
        run_id=run_id,
        module_id=module_id,
        preview_id=preview_id,
        package_version=package_version,
        run_type=run_type,
        status=status,
        scores_json=scores,
        promotion_readiness_json=promotion_readiness or {},
        created_at=_utc_now(),
        completed_at=_utc_now() if status == "completed" else None,
    )
    db.session.add(row)
    if preview_id:
        preview = NarrativePreview.query.filter_by(preview_id=preview_id, module_id=module_id).first()
        if preview is not None:
            preview.evaluation_status = status
            if promotion_readiness is not None:
                preview.promotion_readiness_json = promotion_readiness
            preview.updated_at = _utc_now()
    if status == "failed":
        emit_narrative_event(
            event_type=NarrativeEventType.EVALUATION_FAILED.value,
            severity="critical",
            module_id=module_id,
            related_ref=run_id,
            payload={"scores": scores},
        )
    db.session.commit()
    return row.to_dict()


def upsert_evaluation_coverage(
    *,
    run_id: str,
    coverage_kind: str,
    covered_count: int,
    total_count: int,
    missing_refs: list[str],
) -> dict[str, object]:
    """Persist normalized coverage rows."""
    if total_count <= 0:
        raise NarrativeGovernanceError("Coverage total must be positive.", code="evaluation_coverage_invalid")
    pct = covered_count / total_count
    row = NarrativeEvaluationCoverage.query.filter_by(run_id=run_id, coverage_kind=coverage_kind).first()
    if row is None:
        row = NarrativeEvaluationCoverage(
            run_id=run_id,
            coverage_kind=coverage_kind,
            covered_count=covered_count,
            total_count=total_count,
            coverage_percentage=pct,
            missing_refs_json=missing_refs,
            created_at=_utc_now(),
        )
    else:
        row.covered_count = covered_count
        row.total_count = total_count
        row.coverage_percentage = pct
        row.missing_refs_json = missing_refs
    db.session.add(row)
    db.session.commit()
    return row.to_dict()


def complete_evaluation_run(
    *,
    run_id: str,
    status: str,
    scores: dict[str, float],
    promotion_readiness: dict[str, object],
) -> dict[str, object]:
    """Finalize one evaluation run and propagate preview readiness state."""
    row = NarrativeEvaluationRun.query.filter_by(run_id=run_id).first()
    if row is None:
        raise NarrativeGovernanceError("Evaluation run not found.", code="evaluation_run_not_found")
    if status not in {"completed", "failed"}:
        raise NarrativeGovernanceError("Invalid evaluation completion status.", code="evaluation_run_type_invalid")
    row.status = status
    row.scores_json = scores
    row.promotion_readiness_json = promotion_readiness
    row.completed_at = _utc_now()
    if row.preview_id:
        preview = NarrativePreview.query.filter_by(preview_id=row.preview_id, module_id=row.module_id).first()
        if preview is not None:
            preview.evaluation_status = status
            preview.promotion_readiness_json = promotion_readiness
            preview.updated_at = _utc_now()
    if status == "failed":
        emit_narrative_event(
            event_type=NarrativeEventType.EVALUATION_FAILED.value,
            severity="critical",
            module_id=row.module_id,
            related_ref=run_id,
            payload={"scores": scores},
        )
    db.session.commit()
    return row.to_dict()


def rollback_to_version(
    *,
    module_id: str,
    target_version: str,
    requested_by: str,
    reason: str,
) -> dict[str, object]:
    """Perform guarded rollback and append package history event."""
    package = NarrativePackage.query.filter_by(module_id=module_id).first()
    if package is None:
        raise NarrativeGovernanceError("Module package row not found.", code="module_not_found")
    if package.active_package_version == target_version:
        raise NarrativeGovernanceError(
            "Rollback target is already active.",
            code="rollback_blocked_same_version",
        )
    artifact_root = _ensure_artifact_paths(module_id, target_version)
    previous = package.active_package_version
    package.active_package_version = target_version
    package.active_manifest_path = str(artifact_root / "manifest.json")
    package.active_package_path = str(artifact_root / "package.json")
    package.validation_status = "passing"
    package.updated_at = _utc_now()
    _request_world_engine_active_reload(module_id=module_id, target_version=target_version)
    event = NarrativePackageHistoryEvent(
        module_id=module_id,
        event_type="rollback",
        package_version=target_version,
        from_version=previous,
        to_version=target_version,
        actor_id=requested_by,
        reason=reason,
        metadata_json={"reload_status": "accepted"},
        occurred_at=_utc_now(),
    )
    db.session.add(event)
    emit_narrative_event(
        event_type=NarrativeEventType.ROLLBACK_COMPLETED.value,
        severity="critical",
        module_id=module_id,
        related_ref=target_version,
        payload={"previous_active_version": previous, "new_active_version": target_version},
    )
    db.session.commit()
    return {
        "rollback_id": _new_id("rb"),
        "previous_active_version": previous,
        "new_active_version": target_version,
        "history_event_id": str(event.id),
        "reload_status": "accepted",
    }


def promote_preview_to_active(
    *,
    module_id: str,
    preview_id: str,
    approved_by: str,
    notes: str | None,
) -> dict[str, object]:
    """Promote one evaluated preview into immutable active runtime version."""
    preview = NarrativePreview.query.filter_by(module_id=module_id, preview_id=preview_id).first()
    if preview is None:
        raise NarrativeGovernanceError("Preview not found.", code="preview_not_found")
    readiness = preview.promotion_readiness_json or {}
    if not bool(readiness.get("is_promotable")):
        raise NarrativeGovernanceError(
            "Preview promotion is blocked because readiness gates are not passing.",
            code="promotion_blocked_not_ready",
        )
    unresolved_conflicts = NarrativeRevisionConflict.query.filter(
        NarrativeRevisionConflict.module_id == module_id,
        NarrativeRevisionConflict.resolution_status == "pending",
    ).count()
    if unresolved_conflicts:
        raise NarrativeGovernanceError(
            "Promotion blocked due to unresolved revision conflicts.",
            code="unresolved_revision_conflicts",
        )
    target_version = _derive_active_version(preview.package_version)
    target_root = _copy_preview_into_version(module_id=module_id, preview_id=preview_id, target_version=target_version)
    manifest = _load_json_file(target_root / "manifest.json")
    source_revision = str(manifest.get("source_revision") or "unknown")

    package = NarrativePackage.query.filter_by(module_id=module_id).first()
    previous_version = package.active_package_version if package else None
    if package is None:
        package = NarrativePackage(
            module_id=module_id,
            active_package_version=target_version,
            active_manifest_path=str(target_root / "manifest.json"),
            active_package_path=str(target_root / "package.json"),
            active_source_revision=source_revision,
            validation_status="passing",
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )
    else:
        package.active_package_version = target_version
        package.active_manifest_path = str(target_root / "manifest.json")
        package.active_package_path = str(target_root / "package.json")
        package.active_source_revision = source_revision
        package.validation_status = "passing"
        package.updated_at = _utc_now()
    db.session.add(package)

    _request_world_engine_active_reload(module_id=module_id, target_version=target_version)
    event = NarrativePackageHistoryEvent(
        module_id=module_id,
        event_type="promote",
        package_version=target_version,
        from_version=previous_version,
        to_version=target_version,
        preview_id=preview_id,
        actor_id=approved_by,
        reason=notes,
        metadata_json={"reload_status": "accepted"},
        occurred_at=_utc_now(),
    )
    db.session.add(event)
    emit_narrative_event(
        event_type=NarrativeEventType.PROMOTION_COMPLETED.value,
        severity="info",
        module_id=module_id,
        related_ref=preview_id,
        payload={
            "message": f"Preview {preview_id} promoted to active version {target_version}.",
            "new_active_version": target_version,
            "previous_active_version": previous_version,
        },
    )
    preview.updated_at = _utc_now()
    db.session.commit()
    return {
        "promotion_id": _new_id("prom"),
        "new_active_version": target_version,
        "history_event_id": str(event.id),
        "reload_status": "accepted",
    }


def resolve_conflict(
    *,
    conflict_id: str,
    strategy: str,
    winner_revision_id: str | None,
    resolved_by: str,
    notes: str | None,
) -> dict[str, object]:
    """Resolve a pending revision conflict with explicit strategy."""
    conflict = NarrativeRevisionConflict.query.filter_by(conflict_id=conflict_id).first()
    if conflict is None:
        raise NarrativeGovernanceError(
            "Revision conflict not found.",
            code="revision_conflict_not_found",
        )
    allowed_strategies = {
        "manual_select_winner",
        "manual_merge_then_rebuild",
        "dismiss_loser",
        "archive_conflicting_batch",
    }
    if strategy not in allowed_strategies:
        raise NarrativeGovernanceError(
            "Invalid conflict resolution strategy.",
            code="invalid_conflict_resolution_strategy",
        )
    if strategy in {"manual_select_winner", "dismiss_loser"}:
        if winner_revision_id is None:
            raise NarrativeGovernanceError(
                "Winner revision id is required for manual_select_winner.",
                code="winner_revision_not_in_conflict",
            )
        if winner_revision_id not in set(conflict.candidate_ids_json or []):
            raise NarrativeGovernanceError(
                "Winner revision id must exist in conflict candidates.",
                code="winner_revision_not_in_conflict",
            )
        conflict.winner_revision_id = winner_revision_id
    if strategy == "manual_merge_then_rebuild":
        if not (notes or "").strip():
            raise NarrativeGovernanceError(
                "manual_merge_then_rebuild requires explicit notes.",
                code="invalid_conflict_resolution_strategy",
            )
    if strategy == "archive_conflicting_batch":
        for revision_id in conflict.candidate_ids_json or []:
            candidate = NarrativeRevisionCandidate.query.filter_by(revision_id=revision_id).first()
            if candidate and candidate.review_status != "archived":
                previous_status = candidate.review_status
                candidate.review_status = "archived"
                candidate.updated_at = _utc_now()
                db.session.add(
                    NarrativeRevisionStatusHistory(
                        revision_id=revision_id,
                        from_status=previous_status,
                        to_status="archived",
                        actor_id=resolved_by,
                        actor_role="operator",
                        notes=f"Archived via conflict {conflict_id}",
                        occurred_at=_utc_now(),
                    )
                )
    if strategy in {"manual_select_winner", "dismiss_loser"} and winner_revision_id:
        for revision_id in conflict.candidate_ids_json or []:
            if revision_id == winner_revision_id:
                continue
            candidate = NarrativeRevisionCandidate.query.filter_by(revision_id=revision_id).first()
            if candidate and candidate.review_status != "archived":
                previous_status = candidate.review_status
                candidate.review_status = "archived"
                candidate.updated_at = _utc_now()
                db.session.add(
                    NarrativeRevisionStatusHistory(
                        revision_id=revision_id,
                        from_status=previous_status,
                        to_status="archived",
                        actor_id=resolved_by,
                        actor_role="operator",
                        notes=f"Archived via conflict {conflict_id}",
                        occurred_at=_utc_now(),
                    )
                )
    conflict.resolution_strategy = strategy
    conflict.resolution_status = "resolved"
    conflict.resolved_by = resolved_by
    conflict.resolved_at = _utc_now()
    conflict.notes = notes
    db.session.commit()
    return conflict.to_dict()


def upsert_notification_rule(
    *,
    rule_id: str,
    event_type: str,
    condition: dict[str, object],
    channels: list[str],
    recipients: list[str],
    enabled: bool,
) -> dict[str, object]:
    """Create or update a governance notification rule."""
    row = NarrativeNotificationRule.query.filter_by(rule_id=rule_id).first()
    if row is None:
        row = NarrativeNotificationRule(
            rule_id=rule_id,
            event_type=event_type,
            condition_json=condition,
            channels_json=channels,
            recipients_json=recipients,
            enabled=enabled,
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )
    else:
        row.event_type = event_type
        row.condition_json = condition
        row.channels_json = channels
        row.recipients_json = recipients
        row.enabled = enabled
        row.updated_at = _utc_now()
    db.session.add(row)
    db.session.commit()
    return row.to_dict()


def list_notification_feed(*, only_unacknowledged: bool = False, limit: int = 50) -> list[dict[str, object]]:
    """Return operator notification feed rows."""
    query = NarrativeNotification.query.order_by(NarrativeNotification.created_at.desc())
    if only_unacknowledged:
        query = query.filter_by(acknowledged=False)
    return [row.to_dict() for row in query.limit(max(1, min(limit, 200))).all()]


def acknowledge_notification(*, notification_id: str, by_actor: str) -> dict[str, object]:
    """Acknowledge one governance notification."""
    row = NarrativeNotification.query.filter_by(notification_id=notification_id).first()
    if row is None:
        raise NarrativeGovernanceError("Notification not found.", code="notification_not_found")
    row.acknowledged = True
    row.acknowledged_by = by_actor
    row.acknowledged_at = _utc_now()
    db.session.commit()
    return row.to_dict()


def ingest_runtime_health_event(
    *,
    module_id: str,
    event_type: str,
    severity: str,
    scene_id: str | None,
    turn_number: int | None,
    failure_types: list[str],
    payload: dict[str, object],
) -> dict[str, object]:
    """Ingest one runtime health event and optionally emit threshold alerts."""
    row = NarrativeRuntimeHealthEvent(
        event_id=_new_id("rt_evt"),
        module_id=module_id,
        scene_id=scene_id,
        turn_number=turn_number,
        event_type=event_type,
        severity=severity,
        failure_types_json=failure_types,
        payload_json=payload,
        occurred_at=_utc_now(),
    )
    db.session.add(row)
    emit_narrative_event(
        event_type=event_type,
        severity=severity,
        module_id=module_id,
        related_ref=row.event_id,
        payload={"scene_id": scene_id, "turn_number": turn_number, "failure_types": failure_types},
    )
    window_start = _utc_now() - timedelta(hours=1)
    total = NarrativeRuntimeHealthEvent.query.filter(
        NarrativeRuntimeHealthEvent.module_id == module_id,
        NarrativeRuntimeHealthEvent.occurred_at >= window_start,
    ).count()
    fallback = NarrativeRuntimeHealthEvent.query.filter(
        NarrativeRuntimeHealthEvent.module_id == module_id,
        NarrativeRuntimeHealthEvent.occurred_at >= window_start,
        NarrativeRuntimeHealthEvent.event_type == NarrativeEventType.SAFE_FALLBACK_USED.value,
    ).count()
    retry = NarrativeRuntimeHealthEvent.query.filter(
        NarrativeRuntimeHealthEvent.module_id == module_id,
        NarrativeRuntimeHealthEvent.occurred_at >= window_start,
        NarrativeRuntimeHealthEvent.event_type == NarrativeEventType.CORRECTIVE_RETRY_USED.value,
    ).count()
    success = max(total - fallback - retry, 0)
    rollup = NarrativeRuntimeHealthRollup(
        module_id=module_id,
        window_key="last_hour",
        window_start=window_start,
        window_end=_utc_now(),
        total_turns=total,
        first_pass_success_rate=(success / total) if total else 0.0,
        corrective_retry_rate=(retry / total) if total else 0.0,
        safe_fallback_rate=(fallback / total) if total else 0.0,
        top_failure_types_json=failure_types[:5],
        created_at=_utc_now(),
    )
    db.session.add(rollup)
    config: dict[str, object] = {}
    row_cfg = SiteSetting.query.filter_by(key="narrative_runtime_config").first()
    if row_cfg and row_cfg.value:
        try:
            parsed = json.loads(row_cfg.value)
            if isinstance(parsed, dict):
                config = parsed
        except json.JSONDecodeError:
            config = {}
    fallback_cfg = config.get("fallback") if isinstance(config.get("fallback"), dict) else {}
    alert_enabled = bool(fallback_cfg.get("alert_on_frequent_fallbacks", True))
    threshold = int(fallback_cfg.get("fallback_alert_threshold", 5) or 5)
    if (
        alert_enabled
        and fallback >= threshold
        and event_type == NarrativeEventType.SAFE_FALLBACK_USED.value
    ):
        emit_narrative_event(
            event_type=NarrativeEventType.FALLBACK_THRESHOLD_EXCEEDED.value,
            severity="critical",
            module_id=module_id,
            related_ref=scene_id,
            payload={
                "message": "Safe fallback threshold exceeded in the last hour.",
                "safe_fallback_count_last_hour": fallback,
                "threshold": threshold,
            },
        )
    db.session.commit()
    return row.to_dict()


def runtime_health_summary(module_id: str) -> dict[str, object]:
    """Return latest rollup summary for a module."""
    row = (
        NarrativeRuntimeHealthRollup.query.filter_by(module_id=module_id)
        .order_by(NarrativeRuntimeHealthRollup.window_start.desc())
        .first()
    )
    if row is None:
        raise NarrativeGovernanceError("Module runtime health not found.", code="module_not_found")
    return row.to_dict()


def fallback_events(module_id: str, limit: int = 50) -> list[dict[str, object]]:
    """Return recent fallback-related runtime events."""
    rows = (
        NarrativeRuntimeHealthEvent.query.filter(
            NarrativeRuntimeHealthEvent.module_id == module_id,
            NarrativeRuntimeHealthEvent.event_type.in_(
                [
                    NarrativeEventType.SAFE_FALLBACK_USED.value,
                    NarrativeEventType.CORRECTIVE_RETRY_USED.value,
                    NarrativeEventType.FALLBACK_THRESHOLD_EXCEEDED.value,
                ]
            ),
        )
        .order_by(NarrativeRuntimeHealthEvent.occurred_at.desc())
        .limit(max(1, min(limit, 200)))
        .all()
    )
    return [row.to_dict() for row in rows]


def list_packages() -> list[dict[str, object]]:
    """List package rows with latest preview context."""
    rows = NarrativePackage.query.order_by(NarrativePackage.module_id.asc()).all()
    payload: list[dict[str, object]] = []
    for row in rows:
        preview = (
            NarrativePreview.query.filter_by(module_id=row.module_id)
            .order_by(NarrativePreview.created_at.desc())
            .first()
        )
        promotable = bool((preview.promotion_readiness_json or {}).get("is_promotable")) if preview else False
        payload.append(
            {
                "module_id": row.module_id,
                "active_version": row.active_package_version,
                "latest_preview_id": preview.preview_id if preview else None,
                "promotion_ready": promotable,
            }
        )
    return payload


def package_history(module_id: str) -> list[dict[str, object]]:
    """Return append-only package history rows for one module."""
    rows = (
        NarrativePackageHistoryEvent.query.filter_by(module_id=module_id)
        .order_by(NarrativePackageHistoryEvent.occurred_at.desc())
        .all()
    )
    if not rows:
        package_exists = NarrativePackage.query.filter_by(module_id=module_id).first()
        if package_exists is None:
            raise NarrativeGovernanceError("Module not found.", code="module_not_found")
        return []
    return [row.to_dict() for row in rows]


def list_revision_candidates(module_id: str | None = None) -> list[dict[str, object]]:
    """List revisions with inline conflict flag."""
    query = NarrativeRevisionCandidate.query
    if module_id:
        query = query.filter_by(module_id=module_id)
    rows = query.order_by(NarrativeRevisionCandidate.created_at.desc()).all()
    payload: list[dict[str, object]] = []
    for row in rows:
        conflict_exists = NarrativeRevisionConflict.query.filter(
            NarrativeRevisionConflict.module_id == row.module_id,
            NarrativeRevisionConflict.resolution_status == "pending",
            NarrativeRevisionConflict.target_kind == row.target_kind,
            NarrativeRevisionConflict.target_ref == row.target_ref,
        ).count()
        item = row.to_dict()
        item["has_conflicts"] = bool(conflict_exists)
        payload.append(item)
    return payload


def resolve_validation_feedback_for_retry(feedback: ValidationFeedback) -> dict[str, object]:
    """Convert validation feedback contract into deterministic retry payload."""
    return {
        "passed": feedback.passed,
        "violations": [item.model_dump(mode="json") for item in feedback.violations],
        "corrections_needed": feedback.corrections_needed,
        "legal_alternatives": feedback.legal_alternatives,
    }


def load_preview_into_runtime(*, module_id: str, preview_id: str, isolation_mode: str = "session_namespace") -> dict[str, object]:
    """Load preview package into world-engine preview runtime."""
    try:
        return load_narrative_preview_package(
            module_id=module_id,
            preview_id=preview_id,
            isolation_mode=isolation_mode,
        )
    except GameServiceError as exc:
        raise NarrativeGovernanceError(
            f"Failed to load preview into world-engine runtime: {exc}",
            code="preview_session_isolation_unavailable",
        ) from exc


def unload_preview_from_runtime(*, module_id: str, preview_id: str) -> dict[str, object]:
    """Unload preview package from world-engine preview runtime."""
    try:
        return unload_narrative_preview_package(module_id=module_id, preview_id=preview_id)
    except GameServiceError as exc:
        raise NarrativeGovernanceError(
            f"Failed to unload preview from world-engine runtime: {exc}",
            code="preview_not_loaded",
        ) from exc


def start_preview_runtime_session(
    *,
    module_id: str,
    preview_id: str,
    session_seed: str,
    isolation_mode: str = "session_namespace",
) -> dict[str, object]:
    """Start isolated world-engine preview runtime session."""
    try:
        return start_narrative_preview_session(
            module_id=module_id,
            preview_id=preview_id,
            session_seed=session_seed,
            isolation_mode=isolation_mode,
        )
    except GameServiceError as exc:
        raise NarrativeGovernanceError(
            f"Failed to start preview session in world-engine runtime: {exc}",
            code="preview_session_isolation_unavailable",
        ) from exc


def end_preview_runtime_session(*, preview_session_id: str) -> dict[str, object]:
    """End isolated world-engine preview runtime session."""
    try:
        return end_narrative_preview_session(preview_session_id=preview_session_id)
    except GameServiceError as exc:
        raise NarrativeGovernanceError(
            f"Failed to end preview session in world-engine runtime: {exc}",
            code="preview_session_not_found",
        ) from exc


def runtime_diagnostics(module_id: str) -> dict[str, object]:
    """Return world-engine runtime diagnostics for governance operators."""
    try:
        state = get_narrative_runtime_state(module_id=module_id)
        validator_config = get_narrative_runtime_validator_config()
        health = get_narrative_runtime_health()
    except GameServiceError as exc:
        raise NarrativeGovernanceError(
            f"Failed to fetch world-engine runtime diagnostics: {exc}",
            code="runtime_state_unavailable",
        ) from exc
    return {
        "module_id": module_id,
        "state": state,
        "validator_config": validator_config,
        "health": health,
    }


def sync_runtime_health_from_world_engine(module_id: str) -> dict[str, object]:
    """Ingest world-engine runtime health events into backend governance state."""
    snapshot = get_narrative_runtime_health()
    events = snapshot.get("events")
    if not isinstance(events, list):
        raise NarrativeGovernanceError(
            "World-engine runtime health payload does not contain events list.",
            code="runtime_state_unavailable",
        )
    ingested = 0
    for item in events:
        if not isinstance(item, dict):
            continue
        event_module_id = str(item.get("module_id") or module_id)
        if event_module_id != module_id:
            continue
        event_type = str(item.get("event_type") or "")
        if event_type not in {
            NarrativeEventType.CORRECTIVE_RETRY_USED.value,
            NarrativeEventType.SAFE_FALLBACK_USED.value,
        }:
            continue
        ingest_runtime_health_event(
            module_id=module_id,
            event_type=event_type,
            severity="warning" if event_type == NarrativeEventType.CORRECTIVE_RETRY_USED.value else "critical",
            scene_id=str(item.get("scene_id")) if item.get("scene_id") else None,
            turn_number=None,
            failure_types=[],
            payload={"source": "world_engine_runtime_health"},
        )
        ingested += 1
    state = get_narrative_runtime_state(module_id=module_id)
    validator_config = get_narrative_runtime_validator_config()
    return {
        "module_id": module_id,
        "ingested_events": ingested,
        "world_engine_runtime_state": state,
        "world_engine_validator_config": validator_config,
    }
