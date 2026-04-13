# Administration-Tool Governance Surface

## Design intent

The administration-tool is not only a runtime control page.
It is the main governance surface for package lifecycle, revision review, evaluation visibility, and live runtime health.

The first release can remain form-driven and read-heavy, but it must optimize the most important journeys and show critical status without deep navigation.

## Navigation

- Overview
- Runtime
- Runtime Health
- Packages
- Policies
- Findings
- Revisions
- Evaluations
- Notifications

## Overview page

Display:
- active package per module
- latest preview package state
- unresolved revision conflicts
- latest failing evaluation
- high-confidence findings awaiting review
- coverage gaps
- live runtime health summary

Actions:
- open active package history
- open failing evaluation
- open conflict queue
- open runtime health details
- start research run
- start preview build

### Wireframe sketch

```text
+---------------------------------------------------------------+
| Overview                                                      |
+---------------------------------------------------------------+
| Active Package | Latest Preview | Runtime Health | Alerts     |
| GoC 2.1.4      | preview_0007   | Fallback 1.4%  | 2 critical |
+---------------------------------------------------------------+
| Promotion Readiness | Conflicts Queue | Findings Awaiting Review|
+---------------------------------------------------------------+
| [Open Packages] [Open Runtime Health] [Open Revisions]        |
+---------------------------------------------------------------+
```

## Runtime page

Display:
- narrative director enabled
- active policy profile
- validator strategy
- corrective feedback enabled
- active package version
- currently loaded preview package, if any

Actions:
- enable/disable narrative director
- switch validator strategy
- switch corrective feedback mode
- force reload active package
- load/unload preview package for preview sessions only

## Runtime Health page

Display:
- first-pass success rate
- corrective retry rate
- safe fallback rate
- top validation failure types
- top fallback-heavy scenes
- recent runtime recovery events

Actions:
- filter by module / scene / timeframe
- inspect event details
- open affected policy or package
- open suggested revision candidate or finding if linked

### Wireframe sketch

```text
+----------------------------------------------------------------+
| Runtime Health                                                 |
+----------------------------------------------------------------+
| Success 94.9% | Corrective Retry 3.7% | Safe Fallback 1.4%     |
+----------------------------------------------------------------+
| Top Failure Types: policy_violation, invalid_trigger           |
| Top Scenes: scene_02_confrontation, scene_03_reveal            |
+----------------------------------------------------------------+
| Recent Events                                                  |
| [warn] corrective retry   scene_02 turn 12                     |
| [crit] safe fallback      scene_02 turn 13                     |
| [warn] fallback spike     scene_02 threshold exceeded          |
+----------------------------------------------------------------+
```

## Packages page

Display:
- active package manifest
- preview packages
- version history timeline
- validation reports
- promotion readiness banner

Actions:
- build preview from draft
- compare preview vs active
- promote preview
- rollback to version

## Policies page

Display:
- policy layers
- resolved effective policy for selected module/scene/actor
- fallback policy
- preview policy diff

Actions:
- inspect effective policy for selected scene
- resolve preview policy
- export policy view for debugging

## Findings page

Display:
- findings grouped by module and severity
- evidence summary
- linked scenes, actors, triggers, policies
- confidence and contradiction flags

Actions:
- open supporting research run
- create or inspect revision candidates
- send finding to writers-room task queue

## Revisions page

Display:
- revision candidate list
- workflow status
- grouped conflicts
- target overlap warnings
- expected effects and risk flags
- draft apply history

Actions:
- transition revision state
- resolve conflict
- apply approved revision to draft
- batch reject or archive low-value revisions
- group by target kind or source finding

### Wireframe sketch

```text
+----------------------------------------------------------------+
| Revisions                                                      |
+----------------------------------------------------------------+
| Filters: [module] [status] [target_kind] [has_conflict]        |
+----------------------------------------------------------------+
| rev_103 | approved | actor_mind/veronique | CONFLICT with 109  |
| rev_109 | pending  | actor_mind/veronique | CONFLICT with 103  |
+----------------------------------------------------------------+
| [Resolve Conflict] [Apply to Draft] [Batch Reject]             |
+----------------------------------------------------------------+
```

## Evaluations page

Display:
- latest runs
- score columns
- delta against active baseline
- hard gate failures
- coverage report
- regression risk warnings
- branching simulation results when available

Actions:
- run preview evaluation
- inspect run details
- inspect scenario coverage gaps
- run preview branch simulation
- mark run as reviewed

## Notifications page

Display:
- active notification rules
- recent event feed
- alert severity
- channel delivery status

Actions:
- enable/disable rules
- configure thresholds
- test notification delivery
- acknowledge or bulk acknowledge items

## Top MVP UX priorities

1. **Emergency rollback must be reachable in two clicks from Overview or Packages.**
2. **Revision conflict visibility must appear inline on the Revisions page without requiring drill-down first.**
3. **Critical runtime degradation must be visible from Overview and Runtime Health without manual log inspection.**
4. **Preview vs active comparison must combine manifest, effective policy diff, evaluation delta, and readiness in one place.**
