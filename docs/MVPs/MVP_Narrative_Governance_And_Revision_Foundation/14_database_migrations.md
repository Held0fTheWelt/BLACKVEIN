# Database Migrations Strategy

## Purpose

This document makes the governance foundation implementable in a repository that already has live backend, administration-tool, world-engine, and content flows.
It defines the database migration posture for the new narrative governance objects, the order in which schema changes should land, and the minimum backward-compatibility rules.

## Migration posture

Use an **expand → backfill → switch reads/writes → contract** strategy.
Do not introduce schema changes that require same-deployment hard cutovers between backend and administration-tool.
World-engine should remain largely stateless for package artifacts; the persistent schema changes belong primarily in backend storage.

## Recommended storage ownership

### Persistent database tables in backend
- `narrative_packages`
- `narrative_package_history_events`
- `narrative_previews`
- `narrative_revision_candidates`
- `narrative_revision_conflicts`
- `narrative_revision_status_history`
- `narrative_evaluation_runs`
- `narrative_evaluation_coverage`
- `narrative_notification_rules`
- `narrative_notifications`
- `narrative_runtime_health_events`
- `narrative_runtime_health_rollups`

### File-system artifacts outside the database
- compiled package versions under `content/compiled_packages/...`
- preview package artifacts under `content/compiled_packages/.../previews/...`
- package manifests and validation reports
- package history mirror file `history.json`

The file-system artifact remains operational truth for package bytes.
The database records remain governance and query truth for admin workflows, filters, history screens, and joins.

## Table-by-table schema additions

### `narrative_packages`
Represents known active package identity per module.

Suggested columns:
- `id` primary key
- `module_id` string, unique per logical active pointer row
- `active_package_version` string
- `active_manifest_path` string
- `active_package_path` string
- `active_source_revision` string
- `validation_status` string
- `created_at` timestamp
- `updated_at` timestamp

Indexes:
- unique index on `module_id`
- index on `active_package_version`

### `narrative_package_history_events`
Append-only promotion, rollback, preview-retirement, and build history.

Suggested columns:
- `id` primary key
- `module_id` string
- `event_type` string
- `package_version` string nullable
- `from_version` string nullable
- `to_version` string nullable
- `preview_id` string nullable
- `actor_id` string nullable
- `reason` text nullable
- `metadata_json` json/jsonb
- `occurred_at` timestamp

Indexes:
- composite index on `(module_id, occurred_at desc)`
- index on `(module_id, event_type)`
- index on `preview_id`

### `narrative_previews`
Tracks isolated preview package lifecycle.

Suggested columns:
- `id` primary key
- `preview_id` string unique
- `module_id` string
- `package_version` string
- `draft_workspace_id` string nullable
- `build_status` string
- `validation_status` string
- `evaluation_status` string
- `promotion_readiness_json` json/jsonb
- `artifact_root_path` string
- `created_by` string nullable
- `created_at` timestamp
- `updated_at` timestamp

Indexes:
- unique index on `preview_id`
- composite index on `(module_id, created_at desc)`
- index on `(module_id, build_status)`
- index on `(module_id, evaluation_status)`

### `narrative_revision_candidates`
Stores revision candidates produced by research or manual review.

Suggested columns:
- `id` primary key
- `revision_id` string unique
- `module_id` string
- `source_finding_id` string nullable
- `target_kind` string
- `target_ref` string
- `operation` string
- `structured_delta_json` json/jsonb
- `expected_effects_json` json/jsonb
- `risk_flags_json` json/jsonb
- `review_status` string
- `requires_review` boolean
- `mutation_allowed` boolean default false
- `created_by` string nullable
- `created_at` timestamp
- `updated_at` timestamp

Indexes:
- unique index on `revision_id`
- composite index on `(module_id, review_status)`
- composite index on `(module_id, target_kind, target_ref)`
- index on `source_finding_id`

### `narrative_revision_conflicts`
First-class conflict records across revision candidates.

Suggested columns:
- `id` primary key
- `conflict_id` string unique
- `module_id` string
- `conflict_type` string
- `target_kind` string
- `target_ref` string
- `resolution_status` string
- `resolution_strategy` string nullable
- `winner_revision_id` string nullable
- `resolved_by` string nullable
- `resolved_at` timestamp nullable
- `notes` text nullable
- `created_at` timestamp

Indexes:
- unique index on `conflict_id`
- composite index on `(module_id, resolution_status)`
- composite index on `(module_id, target_kind, target_ref)`

### `narrative_revision_status_history`
Append-only workflow transition history for revisions.

Suggested columns:
- `id` primary key
- `revision_id` string
- `from_status` string nullable
- `to_status` string
- `actor_id` string nullable
- `actor_role` string nullable
- `notes` text nullable
- `occurred_at` timestamp

Indexes:
- composite index on `(revision_id, occurred_at desc)`
- index on `(to_status, occurred_at desc)`

### `narrative_evaluation_runs`
Stores evaluation run metadata and headline scores.

Suggested columns:
- `id` primary key
- `run_id` string unique
- `module_id` string
- `preview_id` string nullable
- `package_version` string nullable
- `run_type` string
- `status` string
- `scores_json` json/jsonb
- `promotion_readiness_json` json/jsonb nullable
- `created_at` timestamp
- `completed_at` timestamp nullable

Indexes:
- unique index on `run_id`
- composite index on `(module_id, created_at desc)`
- composite index on `(preview_id, created_at desc)`
- index on `(module_id, status)`

### `narrative_evaluation_coverage`
Stores normalized coverage summaries per evaluation run.

Suggested columns:
- `id` primary key
- `run_id` string
- `coverage_kind` string
- `covered_count` integer
- `total_count` integer
- `coverage_percentage` numeric
- `missing_refs_json` json/jsonb
- `created_at` timestamp

Indexes:
- composite index on `(run_id, coverage_kind)`

### `narrative_notification_rules`
Stores event-driven notification rules.

Suggested columns:
- `id` primary key
- `rule_id` string unique
- `event_type` string
- `condition_json` json/jsonb
- `channels_json` json/jsonb
- `recipients_json` json/jsonb
- `enabled` boolean
- `created_at` timestamp
- `updated_at` timestamp

Indexes:
- unique index on `rule_id`
- composite index on `(event_type, enabled)`

### `narrative_notifications`
Stores emitted notification feed items and acknowledgment state.

Suggested columns:
- `id` primary key
- `notification_id` string unique
- `event_type` string
- `severity` string
- `title` string
- `body` text nullable
- `payload_json` json/jsonb
- `acknowledged` boolean default false
- `acknowledged_by` string nullable
- `acknowledged_at` timestamp nullable
- `created_at` timestamp

Indexes:
- unique index on `notification_id`
- composite index on `(acknowledged, created_at desc)`
- composite index on `(severity, created_at desc)`

### `narrative_runtime_health_events`
Stores raw runtime health events, fallback events, and retry diagnostics.

Suggested columns:
- `id` primary key
- `event_id` string unique
- `module_id` string
- `scene_id` string nullable
- `turn_number` integer nullable
- `event_type` string
- `severity` string
- `failure_types_json` json/jsonb nullable
- `payload_json` json/jsonb
- `occurred_at` timestamp

Indexes:
- unique index on `event_id`
- composite index on `(module_id, occurred_at desc)`
- composite index on `(module_id, scene_id, occurred_at desc)`
- index on `(event_type, occurred_at desc)`

### `narrative_runtime_health_rollups`
Stores periodic aggregates for admin dashboards.

Suggested columns:
- `id` primary key
- `module_id` string
- `window_key` string
- `window_start` timestamp
- `window_end` timestamp
- `total_turns` integer
- `first_pass_success_rate` numeric
- `corrective_retry_rate` numeric
- `safe_fallback_rate` numeric
- `top_failure_types_json` json/jsonb
- `created_at` timestamp

Indexes:
- composite index on `(module_id, window_start desc)`
- composite index on `(module_id, window_key, window_start desc)`

## Suggested migration ordering

### Migration group A: package governance foundation
Create:
- `narrative_packages`
- `narrative_package_history_events`
- `narrative_previews`

This unlocks package history, promotion readiness, and rollback orchestration.

### Migration group B: revision governance foundation
Create:
- `narrative_revision_candidates`
- `narrative_revision_conflicts`
- `narrative_revision_status_history`

This unlocks review state machine, conflict detection, and auditability.

### Migration group C: evaluation foundation
Create:
- `narrative_evaluation_runs`
- `narrative_evaluation_coverage`

This unlocks readiness computation and coverage views.

### Migration group D: notifications and live health
Create:
- `narrative_notification_rules`
- `narrative_notifications`
- `narrative_runtime_health_events`
- `narrative_runtime_health_rollups`

This unlocks runtime dashboards, alerts, and event-driven governance.

## Backfill strategy

### Packages and history
If compiled packages already exist on disk, run a one-time backfill job:
- scan `content/compiled_packages/<module_id>/versions`
- identify current active symlink target
- insert one `narrative_packages` row per module
- create history events for discovered promotes where metadata exists
- create a `bootstrap_import` history event when historical attribution is incomplete

### Existing previews
If old preview artifacts exist but do not have DB rows:
- import preview metadata as `build_status = imported_legacy`
- do not assume promotable state until fresh evaluation exists

### Existing revisions or proposal previews
If previous research outputs exist only as files:
- import as `review_status = pending`
- set `mutation_allowed = false`
- mark `created_by = legacy_import`

### Existing evaluation reports
If older markdown or json evaluation reports exist:
- import summary metadata into `narrative_evaluation_runs`
- keep original files as evidence artifacts
- use `status = imported_legacy` when fine-grained scores are missing

## Backward compatibility rules

### Rule 1: additive first
Initial migrations must be additive. Existing admin pages and backend flows must continue to function even before the new governance UI reads the new tables.

### Rule 2: no destructive contract switch in one deploy
Do not remove or rename old fields in the same deployment where code first starts writing new governance records.

### Rule 3: dual-read where needed
For transitional periods:
- package history may be read from DB first, file mirror second
- evaluation summaries may be read from DB first, legacy report file fallback second

### Rule 4: feature flags for new admin surfaces
New routes and UI sections should remain behind feature flags until required migrations are present and backfill is complete.

### Rule 5: idempotent import jobs
Backfill jobs must be rerunnable without duplicating rows. Use natural keys such as `module_id + package_version + event_type + occurred_at` where possible.

## Performance and indexing notes

### High-frequency queries to optimize
- package history by module ordered newest first
- revisions by module and review status
- conflicts by module and resolution status
- evaluation runs by preview or module
- notification feed by acknowledged/severity/newest first
- runtime health by module and recent time window

### JSON field guidance
Use normalized columns for frequently filtered attributes such as:
- `review_status`
- `event_type`
- `severity`
- `module_id`
- `target_kind`
- `target_ref`

Use json/jsonb only for flexible payloads, score maps, and condition trees.

## Migration implementation notes

### Migration framework
Use the repository's existing backend migration system. If Alembic is already present, place new revisions in that chain and keep each migration group reviewable.

### Transaction guidance
- create tables and indexes in schema transactions
- perform large file-system backfills in resumable jobs, not in schema migration transactions
- mark import progress in a dedicated lock or checkpoint file if imports may take time

### Rollout order
1. deploy additive schema migrations
2. deploy backend code that can write new rows but still tolerate empty tables
3. run backfill/import jobs
4. enable admin read paths for new tables
5. enable mutation paths and workflow transitions
6. later, deprecate legacy-only reads when evidence shows parity

## Minimum acceptance for migration readiness
- all new tables exist and are queryable
- all required indexes exist
- at least one module can be imported from compiled package storage into DB records
- rollback can read package history from DB without consulting legacy code paths
- revision conflict lookup is performant on module-scoped queries
- runtime health rollup queries are bounded by indexed time windows
- admin UI can operate when tables are empty without throwing errors
