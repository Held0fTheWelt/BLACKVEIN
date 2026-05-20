# Delagecy Legacy Removal Execution Plan

Status: draft for review  
Baseline: `active_surface_scan.json` from 2026-05-20  
Current gate: failing, because 989 active findings are unregistered

## Goal
Remove legacy content completely without breaking the environment.

"Complete" means no remaining code path, compatibility alias, UI entry, hidden
UI block, test expectation, generated route, diagnostic field, documentation
instruction, or config fallback that is truly legacy. Legacy is not active
compatibility: if a surface is still required by the current system, preserve the
behavior and canonicalize the name/contract instead of deleting it.

This plan is not removal approval. It defines the safe order of work. Every new
finding must be registered and reported before removal. Any integrity risk,
ownership conflict, or ambiguous compatibility case must be discussed before
work continues.

## Baseline
| Surface | Findings |
| --- | ---: |
| Code | 401 |
| Tests | 214 |
| Docs | 187 |
| UI | 110 |
| Config | 77 |
| Total | 989 |

| Area | Findings |
| --- | ---: |
| `ai_stack` | 280 |
| `backend` | 260 |
| `docs` | 186 |
| `world-engine` | 135 |
| `administration-tool` | 107 |
| `frontend` | 18 |
| `story_runtime_core` | 3 |

Scope warnings to decide before removal:

| Scope | Decision needed |
| --- | --- |
| `frontend/htmlcov`, `backend/htmlcov` | Generated coverage output: exclude/regenerate or register as generated residue. |
| `docs/generated` | Generated docs: remove at source, then regenerate. |
| `world-engine/app/var/story_sessions` | Decide whether these are fixtures, generated state, or committed product data. |

## Hard Rules
1. Register and report before removal.
2. Remove only after explicit approval for the finding or approved batch.
3. Remove all surfaces together: code, routes, tests, docs, UI, config, data,
   diagnostics, generated outputs, and hidden fallbacks.
4. If removal can break a public route, environment variable, stored data format,
   active workflow, or external dashboard, stop and discuss first.
5. Required active behavior must remain intact. Such findings are reclassified
   as canonicalization work or blockers; they are not marked removed by mere
   renaming.
6. Mark a finding removed only after targeted tests and a clean `delagecy` scan
   for the affected scope.

## Work Loop
Each wave uses this loop:

1. Refresh the scan for the wave scope.
2. Register all new findings in the registry.
3. Report the candidate batch and wait for approval.
4. Remove implementation, UI, tests, docs, and generated residue together.
5. Run targeted tests plus `delagecy scan`.
6. Mark findings removed only after verification.
7. Update tracker/report with the completion note.

No wave starts broad removal while the previous wave has unresolved blockers.

## Wave 0: Scope And Registry
Purpose: make the backlog trustworthy before deleting anything.

Actions:
- Decide generated artifact handling for coverage, generated docs, and story
  session files.
- Exclude generated artifacts from active scans or register them with a clear
  regeneration/removal rule.
- Add a batch registration workflow if one-by-one registration is too slow for
  the current 989 findings. Batch registration must not approve removal.
- Re-run `scan`, `new`, `check`, and `report`.

Exit criteria:
- Active scope is agreed.
- All current findings are registered or explicitly queued for registration.
- Generated/noise handling is documented.
- No removal happened without approval.

## Wave 1: UI And Navigation Residue
Purpose: remove user-visible residue first, including hidden UI fallbacks.

Primary areas:
- `backend/app/info/static/manage.css`
- `backend/app/info/templates/*`
- `administration-tool/static/manage.css`
- `administration-tool/templates/*`
- `world-engine/app/web/templates/ui/*`
- `world-engine/app/web/static/*`
- `frontend/static/play_*.js`
- `frontend/static/style.css`

Actions:
- Remove labels such as `Legacy Simulator` from navigation, titles, headings,
  help text, tables, and templates.
- Remove hidden compatibility CSS after confirming the replacement UI is active.
- Remove frontend direct-render fallbacks after the orchestrated rendering path
  is verified.
- Remove stale CSS selectors only after no active template or JS references them.

Verification:
- `delagecy scan` on the affected UI roots.
- Frontend/admin static tests where available.
- Manual inspection or screenshot of critical pages if a dev server is available.

Exit criteria:
- No visible labels, links, headings, or hidden UI residue remain.
- Current UI workflows still render and navigate.

## Wave 2: Backend Routes And API Shapes
Purpose: remove compatibility routes, deprecated inputs, and old response fields
without breaking canonical API behavior.

Primary areas:
- `backend/app/config.py`
- `backend/app/api/v1/game_routes.py`
- `backend/app/api/v1/site_routes.py`
- `backend/app/api/v1/wiki_routes.py`
- `backend/app/auth/*`
- `backend/app/content/module_loader.py`
- `backend/app/web/routes.py`
- `backend/app/services/*`

Actions:
- Remove old readiness aliases after active clients/tests use canonical names.
- Remove deprecated environment variable fallbacks after deployment config uses
  canonical variables.
- Remove old redirects/routes after no UI, test, or service calls them.
- Replace imports of auth/feature compatibility helpers, then delete helpers.
- Remove old content projections after committed content is migrated.

Stop and discuss if:
- A public route would change method, status code, or response shape.
- A deployment still uses a deprecated environment variable.
- Stored modules or sessions need data migration.

Verification:
- Targeted backend pytest for touched routes/services.
- Route registration/import smoke checks.
- `delagecy scan` on `backend/app backend/tests`.

Exit criteria:
- Canonical routes and schemas remain green.
- Removed aliases no longer appear in code, tests, docs, or UI.

## Wave 3: AI Stack And Runtime Names
Purpose: remove old naming and compatibility branches in runtime readiness,
Langfuse catalogs, LangChain/LangGraph bridges, and dramatic-effect code.

Primary areas:
- `ai_stack/runtime_readiness_consumer.py`
- `ai_stack/tests/test_runtime_readiness_consumer.py`
- `ai_stack/langfuse/langfuse_evaluator_catalog.py`
- `ai_stack/langchain/bridges.py`
- `ai_stack/langgraph/langgraph_runtime_executor.py`
- `ai_stack/story_runtime/dramatic_effect/*`
- `story_runtime_core/*`

Actions:
- Rename compatibility-facing fields to canonical terms in vertical slices:
  producer, consumer, tests, docs.
- Remove compatibility branches after the canonical payload is produced
  everywhere.
- Update Langfuse evaluator names only together with dashboards, tests, and docs.

Stop and discuss if:
- External dashboards depend on current names.
- Runtime traces or stored evaluations need migration.
- AI evaluation contracts are referenced by a nonlocal tool.

Verification:
- AI stack targeted tests.
- Runtime readiness tests.
- Dramatic-effect gate tests.
- `delagecy scan` on `ai_stack story_runtime_core`.

Exit criteria:
- Runtime and observability use canonical names only.
- No compatibility branch remains for removed payloads.

## Wave 4: World Engine Runtime And Session Data
Purpose: remove world-engine simulator/session residue without breaking runtime
execution.

Primary areas:
- `world-engine/app/web/templates/ui/*`
- `world-engine/app/web/static/*`
- `world-engine/app/var/story_sessions/*`
- `world-engine/tests/*`

Actions:
- Remove simulator route/template naming after confirming the current runtime UI
  entry point.
- Treat `story_sessions` as either migrated fixtures or generated state removed
  from active scan scope.
- Update tests to assert canonical behavior rather than compatibility behavior.

Verification:
- World-engine targeted tests.
- Runtime smoke test if available.
- `delagecy scan` on `world-engine/app world-engine/tests`.

Exit criteria:
- Active world-engine UI and runtime tests pass.
- Session fixtures or generated state no longer contain legacy schema/labels.

## Wave 5: Docs And ADR Cleanup
Purpose: remove documentation residue after code and UI decisions are real.

Primary areas:
- `docs/ADR`
- `docs/technical`
- `docs/testing`
- `docs/security`
- `docs/operations`

Actions:
- Remove stale migration language once migration is complete.
- Keep historical ADR context only when it is clearly historical.
- Update ADR-0029 with executed removal evidence and final status.
- Remove instructions that tell users or agents to rely on compatibility
  behavior.

Verification:
- `delagecy scan` on docs scope.
- Link/reference checks where available.
- Review docs for active instructions that contradict removed code.

Exit criteria:
- Docs describe canonical behavior only.
- Historical references are not operational guidance.

## Final Gate
The project is clean only when all are true:

- `delagecy check` passes for the agreed active scope.
- The readable report shows zero unregistered findings.
- Removed findings have no scan residue.
- Approved UI removals have no visible or hidden residue.
- Targeted test suites for touched areas pass.
- Retained exceptions are explicitly registered, approved, and documented.

Recommended commands:

```bash
PYTHONPATH="'fy'-suites" python -m delagecy.tools scan \
  --include backend/app --include backend/tests \
  --include world-engine/app --include world-engine/tests \
  --include ai_stack --include story_runtime_core \
  --include frontend --include administration-tool \
  --include docs/ADR --include docs/operations --include docs/technical \
  --include docs/testing --include docs/security --include docs/governance \
  --out "'fy'-suites/delagecy/reports/active_surface_scan.json"

PYTHONPATH="'fy'-suites" python -m delagecy.tools new \
  --scan-json "'fy'-suites/delagecy/reports/active_surface_scan.json" \
  > "'fy'-suites/delagecy/reports/active_surface_new.json"

PYTHONPATH="'fy'-suites" python -m delagecy.tools check \
  --scan-json "'fy'-suites/delagecy/reports/active_surface_scan.json"

PYTHONPATH="'fy'-suites" python -m delagecy.tools report \
  --scan-json "'fy'-suites/delagecy/reports/active_surface_scan.json" \
  --new-json "'fy'-suites/delagecy/reports/active_surface_new.json" \
  --out "'fy'-suites/delagecy/reports/active_surface_report.md"
```

## Decisions Needed Before Removal
1. Exclude/regenerate generated coverage and generated docs, or register them as
   generated residue?
2. Treat `world-engine/app/var/story_sessions` as fixtures to migrate or
   generated state outside active scan scope?
3. Remove environment fallbacks and API compatibility fields in one pass, or use
   a coordinated deployment window?
4. Add batch registration to `delagecy` before registering the current 989
   findings?
