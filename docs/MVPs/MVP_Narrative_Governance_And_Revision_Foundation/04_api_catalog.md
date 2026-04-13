# API Catalog

## API conventions

### Success envelope

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "request_id": "req_01HZY...",
    "timestamp": "2026-04-13T15:42:00Z"
  }
}
```

### Error envelope

```json
{
  "ok": false,
  "error": {
    "code": "package_version_not_found",
    "message": "Requested package version does not exist.",
    "details": {
      "module_id": "god_of_carnage",
      "package_version": "2.1.3"
    }
  },
  "meta": {
    "request_id": "req_01HZY...",
    "timestamp": "2026-04-13T15:42:00Z"
  }
}
```

### Error code guidance
- `400` malformed request payload or invalid enum
- `401` unauthenticated
- `403` authenticated but not authorized for requested transition or action
- `404` target resource missing
- `409` action blocked by workflow, conflicts, incomplete artifacts, or non-ready state
- `422` payload parses but violates business rules
- `500` unexpected internal error
- `502` or `503` dependent internal service unavailable or refused action

---

## Backend admin APIs

### Runtime configuration

#### `GET /api/admin/narrative/runtime/config`
Returns the effective runtime configuration visible to operators.

Example response:

```json
{
  "ok": true,
  "data": {
    "narrative_director_enabled": true,
    "policy_profile": "canonical_strict",
    "output_validator": {
      "strategy": "schema_plus_semantic",
      "semantic_policy_check": true,
      "enable_corrective_feedback": true,
      "max_retry_attempts": 1,
      "fast_feedback_mode": true
    },
    "fallback": {
      "safe_fallback_enabled": true,
      "alert_on_frequent_fallbacks": true,
      "fallback_alert_threshold": 5
    }
  }
}
```

Errors:
- `401` `auth_required`
- `403` `admin_permission_required`

#### `POST /api/admin/narrative/runtime/config`
Updates inspectable runtime configuration. Must append an audit event.

Example request:

```json
{
  "policy_profile": "canonical_strict",
  "output_validator": {
    "strategy": "strict_rule_engine",
    "semantic_policy_check": false,
    "enable_corrective_feedback": true,
    "max_retry_attempts": 2,
    "fast_feedback_mode": true
  }
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "updated": true,
    "audit_event_id": "audit_00031"
  }
}
```

Errors:
- `400` `invalid_validation_strategy`
- `422` `runtime_config_invalid`
- `503` `world_engine_config_sync_failed`

### Runtime health

#### `GET /api/admin/narrative/runtime/health`
Returns aggregate live runtime health metrics.

Example response:

```json
{
  "ok": true,
  "data": {
    "module_id": "god_of_carnage",
    "window": "last_hour",
    "total_turns": 487,
    "first_pass_success_rate": 0.949,
    "corrective_retry_rate": 0.037,
    "safe_fallback_rate": 0.014,
    "top_failure_types": ["policy_violation", "invalid_trigger"],
    "top_scenes": ["scene_02_confrontation"]
  }
}
```

Errors:
- `404` `module_not_found`

#### `GET /api/admin/narrative/runtime/health/fallbacks`
Returns recent fallback events.

Example response:

```json
{
  "ok": true,
  "data": {
    "events": [
      {
        "event_id": "rt_evt_001",
        "scene_id": "scene_02_confrontation",
        "turn_number": 8,
        "failure_types": ["policy_violation"],
        "recovery_mode": "safe_fallback",
        "occurred_at": "2026-04-13T15:31:12Z"
      }
    ]
  }
}
```

Errors:
- `404` `module_not_found`

#### `GET /api/admin/narrative/runtime/health/events`
Returns low-level runtime health events for operator inspection.

Example response:

```json
{
  "ok": true,
  "data": {
    "events": [
      {
        "event_type": "corrective_retry_used",
        "severity": "warning",
        "scene_id": "scene_03",
        "count": 3
      }
    ]
  }
}
```

Errors:
- `404` `module_not_found`

### Packages

#### `GET /api/admin/narrative/packages`
Lists modules with active and latest preview package information.

Example response:

```json
{
  "ok": true,
  "data": {
    "packages": [
      {
        "module_id": "god_of_carnage",
        "active_version": "2.1.4",
        "latest_preview_id": "preview_0007",
        "promotion_ready": false
      }
    ]
  }
}
```

Errors:
- `401` `auth_required`

#### `GET /api/admin/narrative/packages/<module_id>/active`
Returns manifest, readiness, and pointers for the active package.

Example response:

```json
{
  "ok": true,
  "data": {
    "module_id": "god_of_carnage",
    "active_version": "2.1.4",
    "manifest": {
      "package_version": "2.1.4",
      "source_revision": "git:abc123",
      "validation_status": "passing"
    }
  }
}
```

Errors:
- `404` `module_not_found`

#### `GET /api/admin/narrative/packages/<module_id>/history`
Returns append-only package history entries.

Example response:

```json
{
  "ok": true,
  "data": {
    "module_id": "god_of_carnage",
    "events": [
      {
        "event_type": "promote",
        "package_version": "2.1.4",
        "actor_id": "operator_bob",
        "occurred_at": "2026-04-13T09:15:00Z"
      },
      {
        "event_type": "rollback",
        "from_version": "2.1.4",
        "to_version": "2.1.3",
        "actor_id": "operator_alice",
        "occurred_at": "2026-04-13T15:38:00Z"
      }
    ]
  }
}
```

Errors:
- `404` `module_not_found`

#### `GET /api/admin/narrative/packages/<module_id>/previews`
Returns isolated previews and their readiness state.

Example response:

```json
{
  "ok": true,
  "data": {
    "previews": [
      {
        "preview_id": "preview_0007",
        "package_version": "2.1.5-preview.7",
        "build_status": "built",
        "evaluation_status": "failed",
        "is_promotable": false
      }
    ]
  }
}
```

Errors:
- `404` `module_not_found`

#### `POST /api/admin/narrative/packages/<module_id>/build-preview`
Builds a preview package from the current draft workspace.

Example request:

```json
{
  "draft_workspace_id": "draft_goc_0003",
  "source_revision": "git:def456",
  "reason": "review approved revisions batch 14"
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "preview_id": "preview_0008",
    "package_version": "2.1.5-preview.8",
    "build_status": "built",
    "validation_status": "passing"
  }
}
```

Errors:
- `404` `draft_workspace_not_found`
- `409` `preview_build_blocked`
- `422` `package_validation_failed`

#### `POST /api/admin/narrative/packages/<module_id>/promote-preview`
Promotes a preview package to active when readiness gates pass.

Example request:

```json
{
  "preview_id": "preview_0008",
  "approved_by": "operator_bob",
  "notes": "Coverage and regression gates passed."
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "promotion_id": "prom_0009",
    "new_active_version": "2.1.5",
    "history_event_id": "pkg_evt_00091"
  }
}
```

Errors:
- `404` `preview_not_found`
- `409` `promotion_blocked_not_ready`
- `409` `unresolved_revision_conflicts`
- `503` `world_engine_reload_refused`

#### `POST /api/admin/narrative/packages/<module_id>/rollback-to/<package_version>`
Rolls active runtime back to a previously promoted immutable version.

Example request:

```json
{
  "module_id": "god_of_carnage",
  "target_version": "2.1.3",
  "requested_by": "operator_alice",
  "reason": "Preview promotion caused repeated safe fallbacks in scene_02"
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "rollback_id": "rb_00017",
    "previous_active_version": "2.1.4",
    "new_active_version": "2.1.3",
    "history_event_id": "pkg_evt_00092",
    "reload_status": "accepted"
  }
}
```

Errors:
- `404` `package_version_not_found`
- `409` `rollback_blocked_incomplete_artifacts`
- `409` `rollback_blocked_same_version`
- `503` `world_engine_reload_refused`

### Policies

#### `GET /api/admin/narrative/policies/<module_id>/effective`
Returns the resolved effective policy currently used by runtime.

Example response:

```json
{
  "ok": true,
  "data": {
    "module_id": "god_of_carnage",
    "effective_policy": {
      "violence_threshold": "verbal_only",
      "max_emotional_intensity": 0.9,
      "fallback_mode": "safe_response"
    }
  }
}
```

Errors:
- `404` `module_not_found`

#### `GET /api/admin/narrative/policies/<module_id>/layers`
Returns policy layers before resolution.

Example response:

```json
{
  "ok": true,
  "data": {
    "global_policy": {},
    "module_policy": {},
    "scene_policy": {},
    "actor_policy": {},
    "turn_override_policy": {},
    "fallback_policy": {}
  }
}
```

Errors:
- `404` `module_not_found`

#### `POST /api/admin/narrative/policies/<module_id>/resolve-preview`
Resolves policy for a preview package or draft context.

Example request:

```json
{
  "preview_id": "preview_0008",
  "scene_id": "scene_02_confrontation",
  "actor_id": "veronique"
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "resolved_policy": {
      "violence_threshold": "verbal_only",
      "character_honesty": "guarded"
    }
  }
}
```

Errors:
- `404` `preview_not_found`
- `422` `policy_resolution_failed`

### Findings and research

#### `GET /api/admin/narrative/findings`
Lists findings produced by research and runtime-health ingestion.

Example response:

```json
{
  "ok": true,
  "data": {
    "findings": [
      {
        "finding_id": "finding_0042",
        "module_id": "god_of_carnage",
        "severity": "high",
        "finding_type": "runtime_health_pattern",
        "title": "Repeated policy violations in scene_02"
      }
    ]
  }
}
```

Errors:
- `401` `auth_required`

#### `GET /api/admin/narrative/findings/<finding_id>`
Returns a single finding, evidence, and linked revision candidates.

Example response:

```json
{
  "ok": true,
  "data": {
    "finding_id": "finding_0042",
    "linked_revision_ids": ["rev_0091", "rev_0092"],
    "evidence": ["runtime_health_event:rt_evt_001"]
  }
}
```

Errors:
- `404` `finding_not_found`

#### `POST /api/admin/narrative/research/runs`
Starts a research run over selected sources.

Example request:

```json
{
  "module_id": "god_of_carnage",
  "sources": ["runtime_health", "evaluation_history", "active_package"],
  "mode": "revision_candidate_generation"
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "run_id": "research_0017",
    "status": "started"
  }
}
```

Errors:
- `404` `module_not_found`
- `422` `research_mode_invalid`

#### `GET /api/admin/narrative/research/runs/<run_id>`
Returns run status, created findings, and candidate counts.

Example response:

```json
{
  "ok": true,
  "data": {
    "run_id": "research_0017",
    "status": "completed",
    "finding_count": 5,
    "revision_candidate_count": 3
  }
}
```

Errors:
- `404` `research_run_not_found`

### Revisions

#### `GET /api/admin/narrative/revisions`
Returns revision candidates with filters and batch metadata.

Example response:

```json
{
  "ok": true,
  "data": {
    "revisions": [
      {
        "revision_id": "rev_0091",
        "target_kind": "actor_mind",
        "target_ref": "veronique",
        "review_status": "pending",
        "has_conflicts": true
      }
    ]
  }
}
```

Errors:
- `401` `auth_required`

#### `GET /api/admin/narrative/revisions/<revision_id>`
Returns a single revision candidate and linked evidence.

Example response:

```json
{
  "ok": true,
  "data": {
    "revision_id": "rev_0091",
    "structured_delta": {
      "operation": "replace_clause",
      "path": "actor_minds.veronique.current_pressure",
      "value": "social exposure fear"
    }
  }
}
```

Errors:
- `404` `revision_not_found`

#### `POST /api/admin/narrative/revisions/<revision_id>/transition`
Moves revision state when workflow rules allow it.

Example request:

```json
{
  "to_status": "approved",
  "by_role": "operator",
  "notes": "Aligned with evaluation evidence and conflict check."
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "revision_id": "rev_0091",
    "from_status": "in_review",
    "to_status": "approved"
  }
}
```

Errors:
- `404` `revision_not_found`
- `403` `transition_role_not_allowed`
- `409` `invalid_revision_transition`

#### `POST /api/admin/narrative/revisions/<revision_id>/apply-to-draft`
Applies an approved revision to a draft workspace when no unresolved conflicts exist.

Example request:

```json
{
  "draft_workspace_id": "draft_goc_0003",
  "requested_by": "system"
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "revision_id": "rev_0091",
    "draft_workspace_id": "draft_goc_0003",
    "applied": true,
    "new_status": "applied_to_draft"
  }
}
```

Errors:
- `404` `revision_not_found`
- `409` `revision_conflicts_unresolved`
- `409` `revision_not_approved`
- `422` `draft_target_ref_not_resolved`

#### `GET /api/admin/narrative/revision-conflicts`
Lists open or resolved conflicts.

Example response:

```json
{
  "ok": true,
  "data": {
    "conflicts": [
      {
        "conflict_id": "conf_0012",
        "target_ref": "actor_minds.veronique",
        "conflict_type": "target_overlap",
        "candidate_ids": ["rev_0091", "rev_0092"],
        "resolution_status": "open"
      }
    ]
  }
}
```

Errors:
- `401` `auth_required`

#### `POST /api/admin/narrative/revision-conflicts/<conflict_id>/resolve`
Resolves a conflict with an explicit strategy.

Example request:

```json
{
  "resolution_strategy": "manual_select_winner",
  "winner_revision_id": "rev_0091",
  "resolved_by": "operator_bob",
  "notes": "Higher evidence quality and lower regression risk."
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "conflict_id": "conf_0012",
    "resolution_status": "resolved",
    "winner_revision_id": "rev_0091"
  }
}
```

Errors:
- `404` `revision_conflict_not_found`
- `409` `invalid_conflict_resolution_strategy`
- `422` `winner_revision_not_in_conflict`

### Draft and preview

#### `GET /api/admin/narrative/drafts/<module_id>`
Returns draft workspace metadata for a module.

Example response:

```json
{
  "ok": true,
  "data": {
    "module_id": "god_of_carnage",
    "draft_workspace_id": "draft_goc_0003",
    "last_updated_at": "2026-04-13T14:12:00Z"
  }
}
```

Errors:
- `404` `draft_workspace_not_found`

#### `POST /api/admin/narrative/drafts/<module_id>/build-preview`
Creates a preview package directly from the draft workspace.

Example request:

```json
{
  "draft_workspace_id": "draft_goc_0003"
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "preview_id": "preview_0008",
    "build_status": "built"
  }
}
```

Errors:
- `404` `draft_workspace_not_found`
- `422` `package_validation_failed`

#### `GET /api/admin/narrative/previews/<preview_id>/diff`
Returns source, package, and policy diff summary.

Example response:

```json
{
  "ok": true,
  "data": {
    "preview_id": "preview_0008",
    "diff": {
      "manifest_changed": true,
      "policy_changed": true,
      "affected_targets": ["actor_minds.veronique"]
    }
  }
}
```

Errors:
- `404` `preview_not_found`

#### `POST /api/admin/narrative/previews/<preview_id>/simulate-branch`
Runs branch simulation against a preview package.

Example request:

```json
{
  "starting_scene_id": "scene_02_confrontation",
  "player_actions": [
    "Ich frage nach dem Handy",
    "Ich bestehe darauf",
    "Ich verlange die Wahrheit"
  ]
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "simulation_run_id": "sim_0003",
    "overall_coherence": 0.92,
    "emotional_arc_quality": 0.89
  }
}
```

Errors:
- `404` `preview_not_found`
- `409` `preview_session_isolation_unavailable`
- `422` `simulation_request_invalid`

### Evaluation

#### `POST /api/admin/narrative/evaluations/run-preview`
Runs evaluation against a preview package and active baseline.

Example request:

```json
{
  "module_id": "god_of_carnage",
  "preview_id": "preview_0008",
  "run_types": ["preview_comparison", "coverage", "rollback_verification"]
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "run_id": "eval_0094",
    "status": "started"
  }
}
```

Errors:
- `404` `preview_not_found`
- `422` `evaluation_run_type_invalid`

#### `GET /api/admin/narrative/evaluations/<run_id>`
Returns evaluation results and promotion readiness.

Example response:

```json
{
  "ok": true,
  "data": {
    "run_id": "eval_0094",
    "status": "completed",
    "scores": {
      "policy_compliance": 0.97,
      "actor_consistency": 0.91,
      "regression_risk": 0.11
    },
    "promotion_readiness": {
      "is_promotable": true,
      "blocking_reasons": []
    }
  }
}
```

Errors:
- `404` `evaluation_run_not_found`

#### `GET /api/admin/narrative/evaluations/<run_id>/coverage`
Returns scenario coverage details.

Example response:

```json
{
  "ok": true,
  "data": {
    "covered_scenes": ["scene_01", "scene_02"],
    "missing_scenes": ["scene_04_confrontation"],
    "coverage_percentage": 0.66
  }
}
```

Errors:
- `404` `evaluation_run_not_found`

#### `GET /api/admin/narrative/evaluations?module_id=<module_id>`
Lists evaluation runs for a module.

Example response:

```json
{
  "ok": true,
  "data": {
    "runs": [
      {
        "run_id": "eval_0094",
        "status": "completed",
        "is_promotable": true
      }
    ]
  }
}
```

Errors:
- `404` `module_not_found`

### Notifications

#### `GET /api/admin/narrative/notifications/rules`
Returns notification rules.

Example response:

```json
{
  "ok": true,
  "data": {
    "rules": [
      {
        "rule_id": "notif_rule_001",
        "event_type": "evaluation_failed",
        "channels": ["admin_ui", "slack"],
        "enabled": true
      }
    ]
  }
}
```

Errors:
- `401` `auth_required`

#### `POST /api/admin/narrative/notifications/rules`
Creates or updates notification rules.

Example request:

```json
{
  "rule_id": "notif_rule_001",
  "event_type": "frequent_fallbacks_detected",
  "condition": {
    "count": {"$gte": 5},
    "window_minutes": 10
  },
  "channels": ["admin_ui", "slack"],
  "recipients": ["ops-team"],
  "enabled": true
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "rule_id": "notif_rule_001",
    "updated": true
  }
}
```

Errors:
- `400` `notification_channel_invalid`
- `422` `notification_rule_invalid`

#### `GET /api/admin/narrative/notifications/feed`
Returns operator-visible notification feed.

Example response:

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "notification_id": "notif_090",
        "severity": "critical",
        "title": "Evaluation failed for preview_0008",
        "acknowledged": false
      }
    ]
  }
}
```

Errors:
- `401` `auth_required`

---

## World-engine internal APIs

### Package lifecycle

#### `POST /internal/narrative/packages/reload-active`
Requests that world-engine reload the active immutable package.

Example request:

```json
{
  "module_id": "god_of_carnage",
  "expected_active_version": "2.1.3"
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "reload_status": "accepted",
    "loaded_version": "2.1.3"
  }
}
```

Errors:
- `404` `module_not_found`
- `409` `active_package_mismatch`
- `503` `package_loader_unavailable`

#### `POST /internal/narrative/packages/load-preview`
Loads preview package into isolated preview runtime space.

Example request:

```json
{
  "module_id": "god_of_carnage",
  "preview_id": "preview_0008",
  "isolation_mode": "session_namespace"
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "preview_id": "preview_0008",
    "load_status": "loaded"
  }
}
```

Errors:
- `404` `preview_not_found`
- `409` `preview_already_loaded`
- `503` `preview_isolation_unavailable`

#### `POST /internal/narrative/packages/unload-preview`
Unloads preview package from isolated preview runtime space.

Example request:

```json
{
  "module_id": "god_of_carnage",
  "preview_id": "preview_0008"
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "preview_id": "preview_0008",
    "unload_status": "accepted"
  }
}
```

Errors:
- `404` `preview_not_loaded`

### Preview execution support

#### `POST /internal/narrative/preview/start-session`
Starts an isolated preview session.

Example request:

```json
{
  "module_id": "god_of_carnage",
  "preview_id": "preview_0008",
  "isolation_mode": "session_namespace",
  "session_seed": "sim_0003"
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "preview_session_id": "prev_sess_0031",
    "namespace": "preview:god_of_carnage:preview_0008:sim_0003"
  }
}
```

Errors:
- `404` `preview_not_loaded`
- `409` `preview_session_collision`
- `503` `preview_isolation_unavailable`

#### `POST /internal/narrative/preview/end-session`
Ends an isolated preview session and releases resources.

Example request:

```json
{
  "preview_session_id": "prev_sess_0031"
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "preview_session_id": "prev_sess_0031",
    "ended": true
  }
}
```

Errors:
- `404` `preview_session_not_found`

### Diagnostics

#### `GET /internal/narrative/runtime/state`
Returns runtime state needed by backend diagnostics.

Example response:

```json
{
  "ok": true,
  "data": {
    "module_id": "god_of_carnage",
    "active_version": "2.1.3",
    "loaded_previews": ["preview_0008"]
  }
}
```

Errors:
- `503` `runtime_state_unavailable`

#### `GET /internal/narrative/runtime/validator-config`
Returns currently active validator strategy and fallback settings.

Example response:

```json
{
  "ok": true,
  "data": {
    "strategy": "strict_rule_engine",
    "enable_corrective_feedback": true,
    "max_retry_attempts": 2
  }
}
```

Errors:
- `503` `validator_config_unavailable`

#### `GET /internal/narrative/runtime/health`
Returns world-engine side runtime health metrics.

Example response:

```json
{
  "ok": true,
  "data": {
    "safe_fallback_rate": 0.014,
    "corrective_retry_rate": 0.037,
    "preview_session_count": 1
  }
}
```

Errors:
- `503` `runtime_health_unavailable`

---

## API behavior rules

### Promotion
Promotion must fail when any of the following is true:
- preview evaluation missing
- hard policy failure present
- unresolved revision conflicts exist for included changes
- package validation report is not passing
- approval transition not completed

### Rollback
Rollback must:
- validate the target package version exists
- append a history event
- repoint active version
- request active reload from world-engine
- return failure if reload is refused or target artifacts are incomplete

### Apply to draft
Apply-to-draft must reject candidates when:
- unresolved conflicts exist
- revision state is not approved
- target references no longer resolve in draft workspace

### Live-turn recovery
The runtime must expose enough diagnostics for backend/admin visibility when:
- corrective retry was used
- safe fallback was used
- repeated validation failures occur in the same scene
- contradiction or semantic-validation failures spike

### Preview isolation
Preview session start must fail when:
- preview package not loaded or mismatched
- isolation mode unavailable
- requested preview session would collide with active session namespace
