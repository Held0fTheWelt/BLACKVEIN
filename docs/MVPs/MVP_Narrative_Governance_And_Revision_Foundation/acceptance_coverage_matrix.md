# Narrative Governance MVP Acceptance Coverage Matrix

This matrix maps each acceptance criterion from `10_acceptance_criteria_and_open_risks.md` to implementation touchpoints and tests.

## Runtime

| Criterion | Implementation | Tests |
|---|---|---|
| Runtime loads only approved compiled package versions | `world-engine/app/narrative/package_loader.py`, `backend/app/services/narrative_governance_service.py` | `world-engine/tests/test_narrative_governance_api.py` |
| Typed scene packet built for turn execution | `world-engine/app/narrative/package_models.py`, `world-engine/app/narrative/scene_packet_builder.py` | `world-engine/tests/test_narrative_governance_api.py` |
| Validator strategy inspectable/configurable | `world-engine/app/narrative/validator_strategies.py`, `backend/app/api/v1/narrative_governance_routes.py` (`/runtime/config`) | `backend/tests/test_narrative_governance_routes.py`, `world-engine/tests/test_narrative_governance_api.py` |
| Invalid triggers/responders blocked before commit | `world-engine/app/narrative/output_validator.py` | `world-engine/tests/test_narrative_governance_api.py` |
| Actionable validation feedback on rejected outputs | `world-engine/app/narrative/validation_feedback.py`, `world-engine/app/narrative/output_validator.py` | `world-engine/tests/test_narrative_governance_api.py` |
| No player-visible raw validation failure/hung turn | `world-engine/app/narrative/corrective_retry.py`, `world-engine/app/narrative/fallback_generator.py` | `world-engine/tests/test_narrative_governance_api.py` |
| Every playable scene has fallback content path | `world-engine/app/narrative/fallback_generator.py`, `world-engine/app/narrative/package_models.py` (`SceneFallbackBundle`) | `world-engine/tests/test_narrative_governance_api.py` |
| Preview sessions isolated from active sessions | `world-engine/app/narrative/preview_isolation.py`, `world-engine/app/api/http.py` internal narrative preview endpoints | `world-engine/tests/test_narrative_governance_api.py::test_internal_narrative_preview_load_unload_and_session_endpoints` |

## Package lifecycle

| Criterion | Implementation | Tests |
|---|---|---|
| Preview build produces isolated artifact registration | `backend/app/services/narrative_governance_service.py` (`build_preview` artifact resolution by real preview id) | `backend/tests/test_narrative_governance_routes.py` (build-preview route contract), `backend/tests/test_narrative_governance_service.py` (service guard coverage) |
| Promotion/rollback history append-only | `backend/app/models/narrative_package_history_event.py`, migration `042_narrative_governance_foundation.py` | `backend/tests/test_narrative_governance_models_schema.py` |
| Rollback to older version without rebuild | `backend/app/services/narrative_governance_service.py` (`rollback_to_version`) | `backend/tests/test_narrative_governance_service.py::test_rollback_to_version_raises_when_reload_refused` |
| World-engine reload after package pointer change | `world-engine/app/api/http.py` (`/internal/narrative/packages/reload-active`), `backend/app/services/narrative_governance_service.py` (promotion/rollback orchestration) | `world-engine/tests/test_narrative_governance_api.py::test_internal_narrative_reload_active_endpoint`, `backend/tests/test_narrative_governance_routes.py::test_promote_preview_route_maps_reload_refusal` |

## Revisions

| Criterion | Implementation | Tests |
|---|---|---|
| Revision candidates store target kind/ref | `backend/app/models/narrative_revision_candidate.py` | `backend/tests/test_narrative_governance_service.py` |
| Unresolved conflicts block draft apply | `backend/app/services/narrative_governance_service.py` (`apply_revision_bundle_to_draft`) | `backend/tests/test_narrative_governance_service.py` |
| Workflow transitions enforced | `backend/app/services/narrative_governance_service.py` (`transition_revision` with role guards) | `backend/tests/test_narrative_governance_service.py::test_transition_revision_blocks_invalid_edges`, `backend/tests/test_narrative_governance_service.py::test_transition_revision_blocks_role_not_allowed`, `backend/tests/test_narrative_governance_routes.py::test_revision_transition_role_violation_returns_403` |
| Group/filter availability in admin | `backend/app/api/v1/narrative_governance_routes.py` revisions/conflicts list endpoints | `backend/tests/test_narrative_governance_routes.py` |

## Evaluation

| Criterion | Implementation | Tests |
|---|---|---|
| Preview evaluation persisted against baseline | `backend/app/models/narrative_evaluation_run.py`, `backend/app/services/narrative_governance_service.py` (`record_evaluation_run`, `complete_evaluation_run`) | `backend/tests/test_narrative_governance_routes.py::test_complete_evaluation_route_updates_run` |
| Promotion readiness derived from validation/evaluation/workflow | `backend/app/services/narrative_governance_service.py` (preview readiness + conflict/readiness gating in `promote_preview_to_active`) | `backend/tests/test_narrative_governance_service.py::test_promote_preview_to_active_updates_history_and_package`, `backend/tests/test_narrative_governance_routes.py::test_promote_preview_route_maps_reload_refusal` |
| Coverage report available per run | `backend/app/models/narrative_evaluation_coverage.py`, evaluation coverage APIs | `backend/tests/test_narrative_governance_routes.py` |
| Live quality metrics exposed (first-pass/retry/fallback) | `world-engine/app/narrative/runtime_health.py`, backend runtime health ingestion and sync | `world-engine/tests/test_narrative_governance_api.py::test_internal_narrative_runtime_health_endpoint`, `backend/tests/test_narrative_governance_service.py::test_ingest_runtime_health_emits_threshold_event`, `backend/tests/test_narrative_governance_routes.py::test_runtime_health_sync_route_success` |

## Persistence and migrations

| Criterion | Implementation | Tests |
|---|---|---|
| Governance tables + indexes created | `backend/migrations/versions/042_narrative_governance_foundation.py` | `backend/tests/test_narrative_governance_models_schema.py` |
| Additive migration posture | migration `042` only adds tables/indexes | `backend/tests/test_narrative_governance_models_schema.py` |
| Backfill-compatible compiled package linkage | `backend/app/services/narrative_governance_service.py` artifact path checks | `backend/tests/test_narrative_governance_routes.py` |
| Admin UI tolerates empty tables | `administration-tool/static/narrative_governance.js` and narrative templates render empty payloads safely | manual smoke + API contract tests |

## Administration-tool

| Criterion | Implementation | Tests |
|---|---|---|
| Rollback reachable from overview/packages journey | `administration-tool/static/narrative_governance.js` actionable package controls + rollback API | manual smoke (button-driven rollback), API covered by backend route/service tests |
| Revisions page shows conflicts inline | `administration-tool/static/narrative_governance.js` (`loadRevisions` + `Resolve Conflict` action) | manual smoke + API tests |
| Package comparison readiness context available | `administration-tool/static/narrative_governance.js` combined package/preview/evaluation payloads + promote action | manual smoke |
| Runtime health highlights spikes | `runtime_health.html` + runtime sync/health APIs | manual smoke + `backend/tests/test_narrative_governance_routes.py::test_runtime_health_sync_route_success` |
| Critical notifications visible without polling logs | `administration-tool/static/narrative_governance.js` notification feed + ack/rule actions | manual smoke + API tests |
