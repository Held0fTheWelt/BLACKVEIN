"""Admin APIs for narrative governance and revision foundation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from flask import g, jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.permissions import require_jwt_moderator_or_admin
from app.config.route_constants import route_status_codes
from app.extensions import limiter
from app.models import (
    NarrativeEvaluationCoverage,
    NarrativeEvaluationRun,
    NarrativeNotificationRule,
    NarrativePackage,
    NarrativePreview,
    NarrativeRevisionCandidate,
    NarrativeRevisionConflict,
    SiteSetting,
)
from app.models.narrative_contracts import DraftPatchBundle, ValidationFeedback
from app.services.narrative_governance_service import (
    NarrativeGovernanceError,
    acknowledge_notification,
    apply_revision_bundle_to_draft,
    build_preview,
    complete_evaluation_run,
    detect_conflicts_for_module,
    fallback_events,
    ingest_runtime_health_event,
    load_preview_into_runtime,
    list_notification_feed,
    list_packages,
    list_revision_candidates,
    runtime_diagnostics,
    package_history,
    promote_preview_to_active,
    record_evaluation_run,
    resolve_conflict,
    resolve_validation_feedback_for_retry,
    rollback_to_version,
    runtime_health_summary,
    start_preview_runtime_session,
    sync_runtime_health_from_world_engine,
    transition_revision,
    unload_preview_from_runtime,
    end_preview_runtime_session,
    upsert_evaluation_coverage,
    upsert_notification_rule,
)


def _meta() -> dict[str, str]:
    request_id = g.get("trace_id") or f"req_{uuid4().hex[:12]}"
    return {
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _ok(data: dict[str, object], status_code: int = route_status_codes.ok):
    return jsonify({"ok": True, "data": data, "meta": _meta()}), status_code


def _error(status_code: int, code: str, message: str, details: dict[str, object] | None = None):
    return (
        jsonify(
            {
                "ok": False,
                "error": {"code": code, "message": message, "details": details or {}},
                "meta": _meta(),
            }
        ),
        status_code,
    )


def _load_runtime_config() -> dict[str, object]:
    row = SiteSetting.query.filter_by(key="narrative_runtime_config").first()
    if row is None or not row.value:
        return {
            "narrative_director_enabled": True,
            "policy_profile": "canonical_strict",
            "output_validator": {
                "strategy": "schema_plus_semantic",
                "semantic_policy_check": True,
                "enable_corrective_feedback": True,
                "max_retry_attempts": 1,
                "fast_feedback_mode": True,
            },
            "fallback": {
                "safe_fallback_enabled": True,
                "alert_on_frequent_fallbacks": True,
                "fallback_alert_threshold": 5,
            },
        }
    return json.loads(row.value)


def _save_runtime_config(payload: dict[str, object]) -> str:
    row = SiteSetting.query.filter_by(key="narrative_runtime_config").first()
    if row is None:
        row = SiteSetting(key="narrative_runtime_config", value=json.dumps(payload))
    else:
        row.value = json.dumps(payload)
    from app.extensions import db

    db.session.add(row)
    db.session.commit()
    return f"audit_{uuid4().hex[:8]}"


@api_v1_bp.route("/admin/narrative/runtime/config", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
def admin_narrative_runtime_config():
    return _ok(_load_runtime_config())


@api_v1_bp.route("/admin/narrative/runtime/config", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def admin_narrative_runtime_config_update():
    payload = request.get_json(silent=True) or {}
    strategy = str((payload.get("output_validator") or {}).get("strategy") or "").strip()
    if strategy and strategy not in {"schema_only", "schema_plus_semantic", "strict_rule_engine"}:
        return _error(400, "invalid_validation_strategy", "Unknown output validation strategy.")
    merged = _load_runtime_config()
    merged.update(payload)
    audit_event_id = _save_runtime_config(merged)
    return _ok({"updated": True, "audit_event_id": audit_event_id})


@api_v1_bp.route("/admin/narrative/runtime/health", methods=["GET"])
@require_jwt_moderator_or_admin
def admin_narrative_runtime_health():
    module_id = request.args.get("module_id", "god_of_carnage")
    try:
        return _ok(runtime_health_summary(module_id))
    except NarrativeGovernanceError as exc:
        return _error(404, exc.code, str(exc), {"module_id": module_id})


@api_v1_bp.route("/admin/narrative/runtime/health/fallbacks", methods=["GET"])
@require_jwt_moderator_or_admin
def admin_narrative_runtime_health_fallbacks():
    module_id = request.args.get("module_id", "god_of_carnage")
    return _ok({"events": fallback_events(module_id)})


@api_v1_bp.route("/admin/narrative/runtime/health/events", methods=["GET"])
@require_jwt_moderator_or_admin
def admin_narrative_runtime_health_events():
    module_id = request.args.get("module_id", "god_of_carnage")
    events = fallback_events(module_id)
    return _ok({"events": events})


@api_v1_bp.route("/admin/narrative/runtime/health/events", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_runtime_health_events_ingest():
    payload = request.get_json(silent=True) or {}
    required = ("module_id", "event_type", "severity")
    missing = [item for item in required if not payload.get(item)]
    if missing:
        return _error(422, "runtime_health_event_invalid", "Missing required runtime health fields.", {"missing": missing})
    event = ingest_runtime_health_event(
        module_id=str(payload["module_id"]),
        event_type=str(payload["event_type"]),
        severity=str(payload["severity"]),
        scene_id=str(payload.get("scene_id")) if payload.get("scene_id") else None,
        turn_number=int(payload["turn_number"]) if payload.get("turn_number") is not None else None,
        failure_types=[str(item) for item in (payload.get("failure_types") or [])],
        payload=dict(payload.get("payload") or {}),
    )
    return _ok({"event": event}, status_code=201)


@api_v1_bp.route("/admin/narrative/runtime/health/sync", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_runtime_health_sync():
    payload = request.get_json(silent=True) or {}
    module_id = str(payload.get("module_id") or "god_of_carnage")
    try:
        result = sync_runtime_health_from_world_engine(module_id)
    except NarrativeGovernanceError as exc:
        return _error(503, exc.code, str(exc), {"module_id": module_id})
    return _ok(result)


@api_v1_bp.route("/admin/narrative/runtime/diagnostics", methods=["GET"])
@require_jwt_moderator_or_admin
def admin_narrative_runtime_diagnostics():
    module_id = request.args.get("module_id", "god_of_carnage")
    try:
        return _ok(runtime_diagnostics(module_id))
    except NarrativeGovernanceError as exc:
        return _error(503, exc.code, str(exc), {"module_id": module_id})


@api_v1_bp.route("/admin/narrative/runtime/previews/load", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_runtime_load_preview():
    payload = request.get_json(silent=True) or {}
    module_id = str(payload.get("module_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    if not module_id or not preview_id:
        return _error(404, "preview_not_found", "module_id and preview_id are required.")
    try:
        result = load_preview_into_runtime(
            module_id=module_id,
            preview_id=preview_id,
            isolation_mode=str(payload.get("isolation_mode") or "session_namespace"),
        )
    except NarrativeGovernanceError as exc:
        status_code = 409 if exc.code == "preview_session_isolation_unavailable" else 404
        return _error(status_code, exc.code, str(exc), {"module_id": module_id, "preview_id": preview_id})
    return _ok(result)


@api_v1_bp.route("/admin/narrative/runtime/previews/unload", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_runtime_unload_preview():
    payload = request.get_json(silent=True) or {}
    module_id = str(payload.get("module_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    if not module_id or not preview_id:
        return _error(404, "preview_not_loaded", "module_id and preview_id are required.")
    try:
        result = unload_preview_from_runtime(module_id=module_id, preview_id=preview_id)
    except NarrativeGovernanceError as exc:
        return _error(404, exc.code, str(exc), {"module_id": module_id, "preview_id": preview_id})
    return _ok(result)


@api_v1_bp.route("/admin/narrative/runtime/previews/start-session", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_runtime_start_preview_session():
    payload = request.get_json(silent=True) or {}
    module_id = str(payload.get("module_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    session_seed = str(payload.get("session_seed") or "").strip()
    if not module_id or not preview_id or not session_seed:
        return _error(
            422,
            "preview_session_isolation_unavailable",
            "module_id, preview_id and session_seed are required.",
        )
    try:
        result = start_preview_runtime_session(
            module_id=module_id,
            preview_id=preview_id,
            session_seed=session_seed,
            isolation_mode=str(payload.get("isolation_mode") or "session_namespace"),
        )
    except NarrativeGovernanceError as exc:
        return _error(409, exc.code, str(exc), {"module_id": module_id, "preview_id": preview_id})
    return _ok(result)


@api_v1_bp.route("/admin/narrative/runtime/previews/end-session", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_runtime_end_preview_session():
    payload = request.get_json(silent=True) or {}
    preview_session_id = str(payload.get("preview_session_id") or "").strip()
    if not preview_session_id:
        return _error(404, "preview_session_not_found", "preview_session_id is required.")
    try:
        result = end_preview_runtime_session(preview_session_id=preview_session_id)
    except NarrativeGovernanceError as exc:
        return _error(404, exc.code, str(exc), {"preview_session_id": preview_session_id})
    return _ok(result)


@api_v1_bp.route("/admin/narrative/packages", methods=["GET"])
@require_jwt_moderator_or_admin
def admin_narrative_packages():
    return _ok({"packages": list_packages()})


@api_v1_bp.route("/admin/narrative/packages/<module_id>/active", methods=["GET"])
@require_jwt_moderator_or_admin
def admin_narrative_package_active(module_id: str):
    row = NarrativePackage.query.filter_by(module_id=module_id).first()
    if row is None:
        return _error(404, "module_not_found", "Module package row does not exist.", {"module_id": module_id})
    return _ok({"module_id": module_id, "active_version": row.active_package_version, "manifest": row.to_dict()})


@api_v1_bp.route("/admin/narrative/packages/<module_id>/history", methods=["GET"])
@require_jwt_moderator_or_admin
def admin_narrative_package_history(module_id: str):
    try:
        return _ok({"module_id": module_id, "events": package_history(module_id)})
    except NarrativeGovernanceError as exc:
        return _error(404, exc.code, str(exc), {"module_id": module_id})


@api_v1_bp.route("/admin/narrative/packages/<module_id>/previews", methods=["GET"])
@require_jwt_moderator_or_admin
def admin_narrative_package_previews(module_id: str):
    rows = (
        NarrativePreview.query.filter_by(module_id=module_id)
        .order_by(NarrativePreview.created_at.desc())
        .all()
    )
    return _ok({"previews": [item.to_dict() for item in rows]})


@api_v1_bp.route("/admin/narrative/packages/<module_id>/build-preview", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_package_build_preview(module_id: str):
    payload = request.get_json(silent=True) or {}
    if not payload.get("draft_workspace_id"):
        return _error(404, "draft_workspace_not_found", "Draft workspace id is required.")
    try:
        result = build_preview(
            module_id=module_id,
            draft_workspace_id=str(payload["draft_workspace_id"]),
            source_revision=str(payload.get("source_revision") or "unspecified"),
            reason=str(payload.get("reason") or ""),
            actor_id=str(payload.get("requested_by") or "system"),
            preview_id=str(payload.get("preview_id")) if payload.get("preview_id") else None,
        )
    except NarrativeGovernanceError as exc:
        code = 409 if exc.code in {"package_artifacts_missing", "preview_build_blocked"} else 422
        return _error(code, exc.code, str(exc), {"module_id": module_id})
    return _ok(
        {
            "preview_id": result.preview_id,
            "package_version": result.package_version,
            "build_status": result.build_status,
            "validation_status": result.validation_status,
        }
    )


@api_v1_bp.route("/admin/narrative/packages/<module_id>/promote-preview", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_package_promote_preview(module_id: str):
    payload = request.get_json(silent=True) or {}
    preview_id = str(payload.get("preview_id") or "").strip()
    if not preview_id:
        return _error(404, "preview_not_found", "preview_id is required.")
    try:
        result = promote_preview_to_active(
            module_id=module_id,
            preview_id=preview_id,
            approved_by=str(payload.get("approved_by") or "operator"),
            notes=str(payload.get("notes") or ""),
        )
    except NarrativeGovernanceError as exc:
        if exc.code == "preview_not_found":
            status_code = 404
        elif exc.code in {
            "promotion_blocked_not_ready",
            "unresolved_revision_conflicts",
            "world_engine_reload_refused",
        }:
            status_code = 409 if exc.code != "world_engine_reload_refused" else 503
        else:
            status_code = 422
        return _error(status_code, exc.code, str(exc), {"module_id": module_id, "preview_id": preview_id})
    return _ok(result)


@api_v1_bp.route("/admin/narrative/packages/<module_id>/rollback-to/<package_version>", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_package_rollback(module_id: str, package_version: str):
    payload = request.get_json(silent=True) or {}
    try:
        result = rollback_to_version(
            module_id=module_id,
            target_version=package_version,
            requested_by=str(payload.get("requested_by") or "operator"),
            reason=str(payload.get("reason") or ""),
        )
    except NarrativeGovernanceError as exc:
        if exc.code.startswith("rollback_blocked"):
            status_code = 409
        elif exc.code == "world_engine_reload_refused":
            status_code = 503
        else:
            status_code = 404
        return _error(status_code, exc.code, str(exc), {"module_id": module_id, "package_version": package_version})
    return _ok(result)


@api_v1_bp.route("/admin/narrative/revisions", methods=["GET"])
@require_jwt_moderator_or_admin
def admin_narrative_revisions():
    module_id = request.args.get("module_id")
    return _ok({"revisions": list_revision_candidates(module_id)})


@api_v1_bp.route("/admin/narrative/revisions/<revision_id>", methods=["GET"])
@require_jwt_moderator_or_admin
def admin_narrative_revision_one(revision_id: str):
    row = NarrativeRevisionCandidate.query.filter_by(revision_id=revision_id).first()
    if row is None:
        return _error(404, "revision_not_found", "Revision candidate not found.", {"revision_id": revision_id})
    return _ok(row.to_dict())


@api_v1_bp.route("/admin/narrative/revisions/<revision_id>/transition", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_revision_transition(revision_id: str):
    payload = request.get_json(silent=True) or {}
    if not payload.get("to_status"):
        return _error(422, "invalid_revision_transition", "to_status is required.")
    try:
        result = transition_revision(
            revision_id=revision_id,
            to_status=str(payload["to_status"]),
            actor_id=str(payload.get("actor_id") or "operator"),
            actor_role=str(payload.get("by_role") or "operator"),
            notes=str(payload.get("notes") or ""),
        )
    except NarrativeGovernanceError as exc:
        if exc.code == "revision_not_found":
            status_code = 404
        elif exc.code == "transition_role_not_allowed":
            status_code = 403
        else:
            status_code = 409
        return _error(status_code, exc.code, str(exc), {"revision_id": revision_id})
    return _ok(result)


@api_v1_bp.route("/admin/narrative/revisions/<revision_id>/apply-to-draft", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_revision_apply_to_draft(revision_id: str):
    payload = request.get_json(silent=True) or {}
    draft_workspace_id = str(payload.get("draft_workspace_id") or "").strip()
    if not draft_workspace_id:
        return _error(404, "draft_workspace_not_found", "draft_workspace_id is required.")
    row = NarrativeRevisionCandidate.query.filter_by(revision_id=revision_id).first()
    if row is None:
        return _error(404, "revision_not_found", "Revision candidate not found.", {"revision_id": revision_id})
    bundle = DraftPatchBundle(
        patch_bundle_id=f"patch_{uuid4().hex[:10]}",
        module_id=row.module_id,
        draft_workspace_id=draft_workspace_id,
        revision_ids=[revision_id],
        target_refs=[row.target_ref],
        patch_operations=[{"operation": row.operation, "delta": row.structured_delta_json}],
        finding_ids=[row.source_finding_id] if row.source_finding_id else [],
        preview_id=None,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    try:
        result = apply_revision_bundle_to_draft(bundle=bundle, requested_by=str(payload.get("requested_by") or "system"))
    except NarrativeGovernanceError as exc:
        status_code = 409 if exc.code in {"revision_conflicts_unresolved", "revision_not_approved"} else 422
        return _error(status_code, exc.code, str(exc), {"revision_id": revision_id})
    return _ok(result)


@api_v1_bp.route("/admin/narrative/revision-conflicts", methods=["GET"])
@require_jwt_moderator_or_admin
def admin_narrative_revision_conflicts():
    module_id = request.args.get("module_id")
    query = NarrativeRevisionConflict.query
    if module_id:
        query = query.filter_by(module_id=module_id)
    rows = query.order_by(NarrativeRevisionConflict.created_at.desc()).all()
    return _ok({"conflicts": [item.to_dict() for item in rows]})


@api_v1_bp.route("/admin/narrative/revision-conflicts/<conflict_id>/resolve", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_revision_conflict_resolve(conflict_id: str):
    payload = request.get_json(silent=True) or {}
    strategy = str(payload.get("resolution_strategy") or "").strip()
    if not strategy:
        return _error(409, "invalid_conflict_resolution_strategy", "resolution_strategy is required.")
    try:
        result = resolve_conflict(
            conflict_id=conflict_id,
            strategy=strategy,
            winner_revision_id=str(payload.get("winner_revision_id")) if payload.get("winner_revision_id") else None,
            resolved_by=str(payload.get("resolved_by") or "operator"),
            notes=str(payload.get("notes") or ""),
        )
    except NarrativeGovernanceError as exc:
        if exc.code == "revision_conflict_not_found":
            status_code = 404
        elif exc.code == "invalid_conflict_resolution_strategy":
            status_code = 409
        else:
            status_code = 422
        return _error(status_code, exc.code, str(exc), {"conflict_id": conflict_id})
    return _ok(result)


@api_v1_bp.route("/admin/narrative/revision-conflicts/detect/<module_id>", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_revision_conflict_detect(module_id: str):
    conflicts = detect_conflicts_for_module(module_id)
    return _ok({"conflicts": conflicts})


@api_v1_bp.route("/admin/narrative/evaluations/run-preview", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_evaluations_run_preview():
    payload = request.get_json(silent=True) or {}
    module_id = str(payload.get("module_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    if not module_id or not preview_id:
        return _error(404, "preview_not_found", "module_id and preview_id are required.")
    run_types = [str(item) for item in (payload.get("run_types") or ["preview_comparison"])]
    if not run_types:
        return _error(422, "evaluation_run_type_invalid", "run_types must not be empty.")
    run = record_evaluation_run(
        module_id=module_id,
        preview_id=preview_id,
        package_version=None,
        run_type=run_types[0],
        status="started",
        scores={},
        promotion_readiness={"is_promotable": False, "blocking_reasons": ["evaluation_pending"]},
    )
    return _ok({"run_id": run["run_id"], "status": run["status"]})


@api_v1_bp.route("/admin/narrative/evaluations/<run_id>", methods=["GET"])
@require_jwt_moderator_or_admin
def admin_narrative_evaluations_one(run_id: str):
    row = NarrativeEvaluationRun.query.filter_by(run_id=run_id).first()
    if row is None:
        return _error(404, "evaluation_run_not_found", "Evaluation run not found.", {"run_id": run_id})
    return _ok(row.to_dict())


@api_v1_bp.route("/admin/narrative/evaluations/<run_id>/coverage", methods=["GET"])
@require_jwt_moderator_or_admin
def admin_narrative_evaluations_coverage(run_id: str):
    rows = NarrativeEvaluationCoverage.query.filter_by(run_id=run_id).all()
    if not rows:
        return _error(404, "evaluation_run_not_found", "Evaluation run coverage not found.", {"run_id": run_id})
    return _ok({"rows": [item.to_dict() for item in rows]})


@api_v1_bp.route("/admin/narrative/evaluations/<run_id>/complete", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_evaluations_complete(run_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        row = complete_evaluation_run(
            run_id=run_id,
            status=str(payload.get("status") or "completed"),
            scores={str(key): float(value) for key, value in dict(payload.get("scores") or {}).items()},
            promotion_readiness=dict(payload.get("promotion_readiness") or {}),
        )
    except (ValueError, NarrativeGovernanceError) as exc:
        status_code = 404 if isinstance(exc, NarrativeGovernanceError) and exc.code == "evaluation_run_not_found" else 422
        code = exc.code if isinstance(exc, NarrativeGovernanceError) else "evaluation_coverage_invalid"
        return _error(status_code, code, str(exc), {"run_id": run_id})
    return _ok(row)


@api_v1_bp.route("/admin/narrative/evaluations/<run_id>/coverage", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_evaluations_coverage_upsert(run_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        row = upsert_evaluation_coverage(
            run_id=run_id,
            coverage_kind=str(payload.get("coverage_kind") or "scenes"),
            covered_count=int(payload.get("covered_count") or 0),
            total_count=int(payload.get("total_count") or 0),
            missing_refs=[str(item) for item in (payload.get("missing_refs") or [])],
        )
    except (ValueError, NarrativeGovernanceError) as exc:
        return _error(422, "evaluation_coverage_invalid", str(exc), {"run_id": run_id})
    return _ok(row, status_code=201)


@api_v1_bp.route("/admin/narrative/evaluations", methods=["GET"])
@require_jwt_moderator_or_admin
def admin_narrative_evaluations_list():
    module_id = request.args.get("module_id")
    query = NarrativeEvaluationRun.query
    if module_id:
        query = query.filter_by(module_id=module_id)
    rows = query.order_by(NarrativeEvaluationRun.created_at.desc()).all()
    return _ok({"runs": [item.to_dict() for item in rows]})


@api_v1_bp.route("/admin/narrative/notifications/rules", methods=["GET"])
@require_jwt_moderator_or_admin
def admin_narrative_notifications_rules():
    rows = NarrativeNotificationRule.query.order_by(NarrativeNotificationRule.updated_at.desc()).all()
    return _ok({"rules": [item.to_dict() for item in rows]})


@api_v1_bp.route("/admin/narrative/notifications/rules", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_notifications_rules_upsert():
    payload = request.get_json(silent=True) or {}
    channels = [str(item) for item in (payload.get("channels") or [])]
    if any(item not in {"admin_ui", "email", "slack", "webhook"} for item in channels):
        return _error(400, "notification_channel_invalid", "One or more channels are invalid.")
    rule = upsert_notification_rule(
        rule_id=str(payload.get("rule_id") or f"notif_rule_{uuid4().hex[:8]}"),
        event_type=str(payload.get("event_type") or ""),
        condition=dict(payload.get("condition") or {}),
        channels=channels,
        recipients=[str(item) for item in (payload.get("recipients") or [])],
        enabled=bool(payload.get("enabled", True)),
    )
    return _ok(rule)


@api_v1_bp.route("/admin/narrative/notifications/feed", methods=["GET"])
@require_jwt_moderator_or_admin
def admin_narrative_notifications_feed():
    return _ok({"items": list_notification_feed()})


@api_v1_bp.route("/admin/narrative/notifications/feed/<notification_id>/ack", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_notifications_ack(notification_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        item = acknowledge_notification(notification_id=notification_id, by_actor=str(payload.get("acknowledged_by") or "operator"))
    except NarrativeGovernanceError as exc:
        return _error(404, exc.code, str(exc), {"notification_id": notification_id})
    return _ok(item)


@api_v1_bp.route("/admin/narrative/validation-feedback/retry-payload", methods=["POST"])
@require_jwt_moderator_or_admin
def admin_narrative_validation_feedback_retry_payload():
    payload = request.get_json(silent=True) or {}
    feedback = ValidationFeedback.model_validate(payload)
    return _ok(resolve_validation_feedback_for_retry(feedback))
