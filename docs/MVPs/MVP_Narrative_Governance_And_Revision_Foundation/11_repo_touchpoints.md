# Repository Touchpoints

## content

Introduce immutable package storage:

```text
content/
  compiled_packages/
    <module_id>/
      active -> versions/<package_version>/
      versions/
      previews/
      history.json
```

Compiled package contents should include scene fallback bundles per scene.

## world-engine

Recommended additions:

```text
world-engine/
  app/
    narrative/
      package_models.py
      package_loader.py
      scene_packet_builder.py
      policy_resolver.py
      runtime_output_models.py
      output_validator.py
      validator_strategies.py
      validation_feedback.py
      corrective_retry.py
      fallback_generator.py
      runtime_health.py
      preview_isolation.py
    api/
      narrative_admin_routes.py
      narrative_preview_routes.py
```

Primary responsibilities:
- active/preview package load semantics
- scene packet creation
- validator strategy selection
- runtime rejection reasons
- corrective feedback generation
- safe fallback generation
- runtime health emission
- preview session isolation

## backend

Recommended additions:

```text
backend/
  app/
    models/
      narrative_package.py
      narrative_package_history.py
      narrative_preview.py
      narrative_revision_candidate.py
      narrative_revision_conflict.py
      narrative_evaluation_run.py
      narrative_notification_rule.py
      narrative_runtime_health_event.py
      narrative_runtime_health_rollup.py
      narrative_notification.py
      narrative_evaluation_coverage.py
    services/
      narrative_package_service.py
      narrative_revision_service.py
      narrative_workflow_service.py
      narrative_conflict_service.py
      narrative_evaluation_service.py
      narrative_notification_service.py
      narrative_runtime_health_service.py
    api/
      admin/
        narrative_governance_routes.py
    migrations/
      versions/
        <governance revisions>
```

Primary responsibilities:
- package history and rollback orchestration
- revision workflow and conflict records
- notification rules and event feed
- evaluation run persistence
- runtime health persistence and aggregation
- admin endpoints

## administration-tool

Recommended additions:

```text
administration-tool/
  templates/
    narrative_governance/
      overview.html
      runtime.html
      runtime_health.html
      packages.html
      policies.html
      findings.html
      revisions.html
      evaluations.html
      notifications.html
  static/
    js/
      narrative_governance.js
    css/
      narrative_governance.css
```

Primary responsibilities:
- governance UI, not direct authority
- inline conflicts and alerts
- package history and rollback access
- runtime health and fallback visibility
- preview vs active comparison

## writers-room

Recommended additions:

```text
writers-room/
  app/
    revision/
      draft_patch_models.py
      draft_patch_apply.py
      draft_workspace_service.py
```

Primary responsibilities:
- apply structured patch bundles to draft workspaces
- preserve source-level authorship boundary
- expose draft diff for preview build input

## ai_stack

Recommended additions:

```text
ai_stack/
  narrative/
    package_build/
      compiler.py
      package_manifest.py
      fallback_compiler.py
    research/
      revision_candidates.py
      conflict_hints.py
      runtime_health_findings.py
    evaluation/
      golden_runs.py
      preview_comparator.py
      delta_metrics.py
      coverage_tracker.py
      promotion_readiness.py
      live_quality_metrics.py
      preview_branching.py
    future_quality/
      affect_models.py
      emotional_state_models.py
      contradiction_models.py
```

Primary responsibilities:
- build compiled packages from source + defaults
- turn runtime health into researchable findings
- evaluate previews and live quality deltas
- host future dramatic-quality experimentation without bypassing runtime authority


## backend migration notes

Recommended migration chain groups:
- package governance foundation
- revision governance foundation
- evaluation foundation
- notifications and runtime health foundation

Migration rules:
- additive first
- backfill through resumable jobs, not giant schema transactions
- feature-flag admin reads until required migrations are present
