"""Unit tests for narrative governance service guards and workflows."""

from __future__ import annotations

import pytest

from app.extensions import db
from app.models import (
    NarrativeNotification,
    NarrativeNotificationRule,
    NarrativePackage,
    NarrativePackageHistoryEvent,
    NarrativePreview,
    NarrativeRevisionCandidate,
    NarrativeRevisionConflict,
    SiteSetting,
)
from app.models.narrative_contracts import DraftPatchBundle
from app.services import narrative_governance_service as governance_service
from app.services.narrative_governance_service import (
    NarrativeGovernanceError,
    apply_revision_bundle_to_draft,
    detect_conflicts_for_module,
    emit_narrative_event,
    ingest_runtime_health_event,
    promote_preview_to_active,
    rollback_to_version,
    transition_revision,
)


def _seed_revision(revision_id: str, review_status: str, target_ref: str) -> NarrativeRevisionCandidate:
    return NarrativeRevisionCandidate(
        revision_id=revision_id,
        module_id="god_of_carnage",
        source_finding_id=None,
        target_kind="actor_mind",
        target_ref=target_ref,
        operation="replace_clause",
        structured_delta_json={"path": target_ref, "value": "patched"},
        expected_effects_json=["stability"],
        risk_flags_json=[],
        review_status=review_status,
        requires_review=True,
        mutation_allowed=False,
        created_by="system",
    )


def test_detect_conflicts_creates_target_overlap_rows(app):
    with app.app_context():
        db.session.add(_seed_revision("rev_a", "pending", "actor_minds.veronique"))
        db.session.add(_seed_revision("rev_b", "in_review", "actor_minds.veronique"))
        db.session.commit()

        conflicts = detect_conflicts_for_module("god_of_carnage")
        assert len(conflicts) == 1
        assert conflicts[0]["target_ref"] == "actor_minds.veronique"
        stored = NarrativeRevisionConflict.query.filter_by(module_id="god_of_carnage").all()
        assert len(stored) == 1


def test_transition_revision_blocks_invalid_edges(app):
    with app.app_context():
        db.session.add(_seed_revision("rev_invalid", "pending", "actor_minds.alain"))
        db.session.commit()
        with pytest.raises(NarrativeGovernanceError) as exc:
            transition_revision(
                revision_id="rev_invalid",
                to_status="promoted",
                actor_id="operator",
                actor_role="operator",
                notes=None,
            )
        assert exc.value.code == "invalid_revision_transition"


def test_apply_to_draft_requires_approved_and_no_conflicts(app):
    with app.app_context():
        db.session.add(_seed_revision("rev_apply", "approved", "actor_minds.michel"))
        db.session.commit()
        bundle = DraftPatchBundle(
            patch_bundle_id="patch_bundle_1",
            module_id="god_of_carnage",
            draft_workspace_id="draft_goc_001",
            revision_ids=["rev_apply"],
            target_refs=["actor_minds.michel"],
            patch_operations=[{"operation": "replace_clause"}],
            created_at="2026-04-13T00:00:00Z",
        )
        result = apply_revision_bundle_to_draft(bundle=bundle, requested_by="system")
        assert result["applied"] is True


def test_apply_to_draft_blocks_unresolved_conflicts(app):
    with app.app_context():
        db.session.add(_seed_revision("rev_conflict", "approved", "actor_minds.annette"))
        db.session.add(
            NarrativeRevisionConflict(
                conflict_id="conf_pending_1",
                module_id="god_of_carnage",
                candidate_ids_json=["rev_conflict"],
                conflict_type="target_overlap",
                target_kind="actor_mind",
                target_ref="actor_minds.annette",
                resolution_status="pending",
            )
        )
        db.session.commit()
        bundle = DraftPatchBundle(
            patch_bundle_id="patch_bundle_2",
            module_id="god_of_carnage",
            draft_workspace_id="draft_goc_001",
            revision_ids=["rev_conflict"],
            target_refs=["actor_minds.annette"],
            patch_operations=[{"operation": "replace_clause"}],
            created_at="2026-04-13T00:00:00Z",
        )
        with pytest.raises(NarrativeGovernanceError) as exc:
            apply_revision_bundle_to_draft(bundle=bundle, requested_by="system")
        assert exc.value.code == "revision_conflicts_unresolved"


def test_transition_revision_blocks_role_not_allowed(app):
    with app.app_context():
        db.session.add(_seed_revision("rev_role_guard", "pending", "actor_minds.veronique"))
        db.session.commit()
        with pytest.raises(NarrativeGovernanceError) as exc:
            transition_revision(
                revision_id="rev_role_guard",
                to_status="in_review",
                actor_id="system_actor",
                actor_role="system",
                notes="role guard test",
            )
        assert exc.value.code == "transition_role_not_allowed"


def test_emit_narrative_event_executes_notification_rule(app):
    with app.app_context():
        db.session.add(
            NarrativeNotificationRule(
                rule_id="rule_eval_1",
                event_type="evaluation_failed",
                condition_json={"module_id": "god_of_carnage"},
                channels_json=["admin_ui", "slack"],
                recipients_json=["ops-team"],
                enabled=True,
            )
        )
        db.session.commit()
        emit_narrative_event(
            event_type="evaluation_failed",
            severity="critical",
            module_id="god_of_carnage",
            related_ref="eval_1",
            payload={"message": "Evaluation failed", "count": 2},
        )
        row = NarrativeNotification.query.order_by(NarrativeNotification.id.desc()).first()
        assert row is not None
        assert row.event_type == "evaluation_failed"
        assert row.payload_json.get("rule_id") == "rule_eval_1"
        assert row.payload_json.get("channels") == ["admin_ui", "slack"]


def test_promote_preview_to_active_updates_history_and_package(app, tmp_path, monkeypatch):
    with app.app_context():
        module_root = tmp_path / "god_of_carnage"
        preview_root = module_root / "previews" / "preview_001"
        preview_root.mkdir(parents=True, exist_ok=True)
        (preview_root / "manifest.json").write_text(
            '{"package_version":"2.1.5-preview.1","source_revision":"git:test"}',
            encoding="utf-8",
        )
        (preview_root / "package.json").write_text("{}", encoding="utf-8")
        (preview_root / "validation_report.json").write_text('{"validation_status":"passing"}', encoding="utf-8")
        monkeypatch.setattr(governance_service, "_compiled_module_root", lambda module_id: tmp_path / module_id)
        monkeypatch.setattr(
            governance_service,
            "_request_world_engine_active_reload",
            lambda module_id, target_version: {"reload_status": "accepted", "loaded_version": target_version},
        )
        db.session.add(
            NarrativePreview(
                preview_id="preview_001",
                module_id="god_of_carnage",
                package_version="2.1.5-preview.1",
                draft_workspace_id="draft_1",
                build_status="built",
                validation_status="passing",
                evaluation_status="completed",
                promotion_readiness_json={"is_promotable": True, "blocking_reasons": []},
                artifact_root_path=str(preview_root),
                created_by="operator",
            )
        )
        db.session.commit()
        result = promote_preview_to_active(
            module_id="god_of_carnage",
            preview_id="preview_001",
            approved_by="operator",
            notes="promotion test",
        )
        assert result["new_active_version"] == "2.1.5"
        pkg = NarrativePackage.query.filter_by(module_id="god_of_carnage").first()
        assert pkg is not None
        assert pkg.active_package_version == "2.1.5"
        history = NarrativePackageHistoryEvent.query.filter_by(module_id="god_of_carnage", event_type="promote").all()
        assert len(history) == 1


def test_rollback_to_version_raises_when_reload_refused(app, tmp_path, monkeypatch):
    with app.app_context():
        version_root = tmp_path / "god_of_carnage" / "versions" / "2.1.3"
        version_root.mkdir(parents=True, exist_ok=True)
        (version_root / "manifest.json").write_text('{"package_version":"2.1.3"}', encoding="utf-8")
        (version_root / "package.json").write_text("{}", encoding="utf-8")
        (version_root / "validation_report.json").write_text('{"validation_status":"passing"}', encoding="utf-8")
        monkeypatch.setattr(governance_service, "_compiled_module_root", lambda module_id: tmp_path / module_id)

        def _raise_reload(module_id: str, target_version: str):
            raise NarrativeGovernanceError("reload refused", code="world_engine_reload_refused")

        monkeypatch.setattr(governance_service, "_request_world_engine_active_reload", _raise_reload)
        db.session.add(
            NarrativePackage(
                module_id="god_of_carnage",
                active_package_version="2.1.4",
                active_manifest_path="x",
                active_package_path="y",
                active_source_revision="git:old",
                validation_status="passing",
            )
        )
        db.session.commit()
        with pytest.raises(NarrativeGovernanceError) as exc:
            rollback_to_version(
                module_id="god_of_carnage",
                target_version="2.1.3",
                requested_by="operator",
                reason="rollback test",
            )
        assert exc.value.code == "world_engine_reload_refused"


def test_ingest_runtime_health_emits_threshold_event(app):
    with app.app_context():
        db.session.add(
            SiteSetting(
                key="narrative_runtime_config",
                value='{"fallback":{"alert_on_frequent_fallbacks":true,"fallback_alert_threshold":1}}',
            )
        )
        db.session.commit()
        ingest_runtime_health_event(
            module_id="god_of_carnage",
            event_type="safe_fallback_used",
            severity="critical",
            scene_id="scene_01",
            turn_number=1,
            failure_types=["policy_violation"],
            payload={},
        )
        threshold_row = (
            NarrativeNotification.query.filter_by(event_type="fallback_threshold_exceeded")
            .order_by(NarrativeNotification.id.desc())
            .first()
        )
        assert threshold_row is not None
