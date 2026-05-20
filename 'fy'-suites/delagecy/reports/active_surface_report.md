# Delagecy Legacy Scan Report

## Summary

- Gate status: **FAIL**
- Scanned files: 5349
- Legacy hits: 989
- Registered findings: 0
- Unregistered findings: 989
- Removed residue still visible: 0
- Approved UI removals still pending: 0
- Discussion-required findings: 0

## Artifacts

- Scan JSON: `'fy'-suites/delagecy/reports/active_surface_scan.json`
- New-findings JSON: `'fy'-suites/delagecy/reports/active_surface_new.json`
- Machine registry: `delagecy_registry.json`
- Human tracker: `legacy_removal_tracker.md`

## Required Rules

1. New legacy findings must be registered and reported before removal.
2. Removal requires explicit approval.
3. Code, routes, tests, docs, data, and UI residue are removed together.
4. Integrity risks, ownership conflicts, or ambiguous removals must be discussed before work continues.
5. A finding is only marked removed after a clean scan and targeted verification.

## Counts By Surface

| Surface | Hits |
| --- | --- |
| code | 401 |
| test | 214 |
| docs | 187 |
| ui | 110 |
| config | 77 |

## Counts By Pattern

| Pattern | Hits |
| --- | --- |
| \blegacy\b | 431 |
| \blegacy_ | 380 |
| \bcompatibility\b | 129 |
| _legacy\b | 25 |
| \bdeprecated\b | 24 |

## Registry Status

| Status | Findings |
| --- | --- |
| No registered findings |  |

## Top Hit Files

| Path | Hits |
| --- | --- |
| world-engine/app/var/story_sessions/043fcc396a4d4b76aff88e496970200f.json | 36 |
| world-engine/app/var/story_sessions/ec68e3494ffd461487de581d91a86002.json | 36 |
| ai_stack/langfuse/langfuse_evaluator_catalog.py | 34 |
| ai_stack/tests/test_runtime_readiness_consumer.py | 26 |
| ai_stack/runtime_readiness_consumer.py | 18 |
| backend/app/services/governance_console_service.py | 17 |
| ai_stack/tests/test_phase1_live_wiring.py | 17 |
| ai_stack/langchain/bridges.py | 15 |
| ai_stack/langgraph/langgraph_runtime_executor.py | 15 |
| ai_stack/story_runtime/dramatic_effect/dramatic_effect_gate_evaluate_branch_outcomes.py | 15 |
| backend/app/runtime/model_inventory_report.py | 12 |
| world-engine/tests/test_trace_middleware.py | 12 |
| administration-tool/static/manage_inspector_workbench.js | 12 |
| docs/technical/ai/llm-slm-role-stratification.md | 11 |
| docs/technical/architecture/ai_story_contract.md | 11 |
| backend/app/services/inspector_turn_projection_assembly_helpers.py | 9 |
| backend/tests/runtime/test_ai_decision_logging.py | 8 |
| ai_stack/tests/test_dramatic_effect_gate.py | 8 |
| docs/ADR/adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md | 8 |
| docs/ADR/adr-0053-bounded-semantic-scene-planner.md | 8 |
| docs/technical/architecture/backend-runtime-classification.md | 8 |
| backend/app/runtime/area2_operator_truth.py | 7 |
| backend/app/services/ai_engineer_suite_service.py | 7 |
| backend/app/services/inspector_projection_coverage_health_distribution.py | 7 |
| backend/app/services/inspector_turn_projection_sections_gate_payload.py | 7 |
| backend/app/services/writers_room_pipeline_finalize_package_out.py | 7 |
| backend/app/web/routes.py | 7 |
| backend/tests/runtime/test_preview_delta.py | 7 |
| docs/ADR/adr-0003-scene-identity-canonical-surface.md | 7 |
| docs/ADR/adr-0054-session-input-language-english-internal-resolution.md | 7 |

## Scope Warnings

| Marker | Files | Meaning |
| --- | --- | --- |
| htmlcov | 1 | Coverage output is in scope. Generated reports should normally be excluded from removal planning. |
| /var/story_sessions/ | 2 | Runtime story-session snapshots are in scope. Decide whether these are fixtures or generated state before registration. |

## First Unregistered Findings

| Fingerprint | Surface | Location | Text |
| --- | --- | --- | --- |
| 244731efb7e92de7 | code | backend/app/config.py:112 | # Compatibility redirect target for legacy /web routes. |
| a9b7c7bc584a60f7 | code | backend/app/config.py:145 | # Prefer PLAY_SERVICE_SHARED_SECRET; PLAY_SERVICE_SECRET is deprecated but supported for migration. |
| a8f6702fa814d10f | code | backend/app/api/v1/game_routes.py:600 | legacy_runtime_session_ready=bool(opening_readiness["runtime_session_ready"]), |
| 7b6c3ab7d7a8b3c8 | code | backend/app/api/v1/game_routes.py:601 | legacy_can_execute=bool(opening_readiness["can_execute"]), |
| 07cac6746335f95c | code | backend/app/api/v1/site_routes.py:48 | # Legacy keys (same values) — keep for older clients. |
| 4fbd51b4bc0c0733 | code | backend/app/api/v1/wiki_routes.py:1 | """Wiki API: public page by slug; legacy file GET/PUT; wiki-admin in wiki_admin_routes.""" |
| 1b61c74547b9fffd | code | backend/app/auth/admin_security.py:136 | # Re-export for tests and backwards compatibility |
| eaf2a42b6df2a64c | code | backend/app/auth/feature_access_resolver.py:113 | """Same semantics as legacy ``user_can_access_feature`` area tail.""" |
| e88546a8292a83db | code | backend/app/auth/feature_access_resolver.py:235 | """Boolean convenience matching legacy ``user_can_access_feature`` call shape.""" |
| 74988eb082715019 | code | backend/app/auth/feature_registry.py:65 | # Legacy tuple view derived from ``app.auth.feature_access_resolver.FEATURE_ACCESS_RULES`` (import lazily). |
| 015957526621ffef | code | backend/app/auth/feature_registry.py:66 | def feature_required_roles_legacy(feature_id: str) -> tuple[str, ...]: |
| 27d1d55b629ee761 | code | backend/app/config/__init__.py:18 | # Re-export main configuration classes for backward compatibility |
| ad1f232d8b8d5836 | code | backend/app/content/module_loader.py:34 | """Compatibility projection from phase_beat_policy into legacy scene_phases.""" |
| 7be837af9efe8b32 | code | backend/app/content/module_loader.py:403 | #   legacy phase file: |
| a22a4b31c97eebf6 | code | backend/app/content/module_loader.py:518 | # Legacy support: old phase files -> scene_phases. New modules should use |
| 9fa7c1078f319007 | code | backend/app/content/module_service.py:168 | useful for checking module compatibility and basic information. |
| 8e9dd73abcc4fd60 | ui | backend/app/info/static/manage.css:777 | .inspector-legacy-details { |
| 8fa02ebba2224e18 | ui | backend/app/info/static/manage.css:782 | .inspector-legacy-block { |
| 546b8efc5652fdd4 | ui | backend/app/info/static/manage.css:1581 | /* Neutralise the legacy sticky top header so its leftover rules cannot bleed |
| e616f56b6914315b | ui | backend/app/info/static/manage.css:2709 | /* Hide legacy banner placeholders that ManageUI has converted to toasts. */ |
| d11ace1604311a5f | ui | backend/app/info/static/manage.css:2710 | .mui-legacy-hidden { display: none !important; } |
| 6d94840f90e4f184 | ui | backend/app/info/templates/auth.html:5 | {% block subheading %}JWT für die API, Browser-Grenzen für Legacy — und was das für Clients bedeutet.{% endblock %} |
| 5a5f58272e826a2b | ui | backend/app/info/templates/auth.html:51 | <tr><td>Server-Session-Cookie</td><td>Legacy-Web-Routen (z.&nbsp;B. Logout)</td><td>Alte Browser-Flows</td></tr> |
| c243ae49ab3fdb88 | ui | backend/app/info/templates/security_features.html:194 | <td>Backend Legacy Web Routes</td> |
| 6f30efb7a7c95f3e | ui | backend/app/info/templates/security_features.html:196 | <td><code>POST /logout</code>, Legacy-Redirect-POSTs</td> |

## UI Residue Examples

| Fingerprint | Location | Text |
| --- | --- | --- |
| 8e9dd73abcc4fd60 | backend/app/info/static/manage.css:777 | .inspector-legacy-details { |
| 8fa02ebba2224e18 | backend/app/info/static/manage.css:782 | .inspector-legacy-block { |
| 546b8efc5652fdd4 | backend/app/info/static/manage.css:1581 | /* Neutralise the legacy sticky top header so its leftover rules cannot bleed |
| e616f56b6914315b | backend/app/info/static/manage.css:2709 | /* Hide legacy banner placeholders that ManageUI has converted to toasts. */ |
| d11ace1604311a5f | backend/app/info/static/manage.css:2710 | .mui-legacy-hidden { display: none !important; } |
| 6d94840f90e4f184 | backend/app/info/templates/auth.html:5 | {% block subheading %}JWT für die API, Browser-Grenzen für Legacy — und was das für Clients bedeutet.{% endblock %} |
| 5a5f58272e826a2b | backend/app/info/templates/auth.html:51 | <tr><td>Server-Session-Cookie</td><td>Legacy-Web-Routen (z.&nbsp;B. Logout)</td><td>Alte Browser-Flows</td></tr> |
| c243ae49ab3fdb88 | backend/app/info/templates/security_features.html:194 | <td>Backend Legacy Web Routes</td> |
| 6f30efb7a7c95f3e | backend/app/info/templates/security_features.html:196 | <td><code>POST /logout</code>, Legacy-Redirect-POSTs</td> |
| a3db0ffd23c63e98 | world-engine/app/web/static/ui.css:878 | Embed (legacy simulator iframes) — match card chrome. |
| eeff15a384a09729 | world-engine/app/web/templates/ui/base.html:50 | <a class="ui-nav-link{% if active_page == 'engine' %} is-current{% endif %}" href="/engine" data-ui-cap="observe">Leg... |
| 93a248230887a1a9 | world-engine/app/web/templates/ui/engine.html:2 | {% block title %}Legacy Simulator{% endblock %} |
| c53c6a2737979b7c | world-engine/app/web/templates/ui/engine.html:6 | <h1>Legacy Simulator (Debug)</h1> |
| ae73c2a8b9423583 | frontend/htmlcov/z_5f5a17c013354698_routes_py.html:393 | <p class="pln"><span class="n"><a id="t311" href="#t311">311</a></span><span class="t">    <span class="str">"""Compa... |
| 8f7ff3674d9b952b | frontend/static/play_narrative_stream.js:177 | // Legacy: Also render directly (for compatibility with existing players without BlocksOrchestrator) |
| 7680f23108379926 | frontend/static/play_shell.js:29 | console.warn("[MVP5] One or more MVP5 modules are not loaded. Falling back to legacy rendering."); |
| be3e209cc079faf2 | frontend/static/play_typewriter_engine.js:4 | * Replaces the legacy substring writer with a per-char span model: |
| 9ea709505b9b5035 | frontend/static/play_typewriter_engine.js:426 | // compatibility with any external caller that might invoke it. |
| 963842dfb6a5c8ee | frontend/static/style.css:1311 | /* ── Legacy templates (slim markup) ───────────────── */ |
| 6cd375aa52d09a5d | frontend/static/style.css:2326 | /* Legacy cursor classes — kept for any external CSS reference. The active |
| 995828e5e2e96621 | frontend/static/style.css:2440 | Applies both to the legacy .container (still used by a few overrides) and to |
| 3df5677b19913c8b | frontend/static/style.css:2929 | Hides the legacy `.site-header` whenever the new shell is on, since the |
| 1aca7ba867978f43 | administration-tool/static/manage.css:929 | .inspector-legacy-details { |
| b71055afd067580b | administration-tool/static/manage.css:934 | .inspector-legacy-block { |
| b9d5b074f3905cec | administration-tool/static/manage.css:1803 | /* Neutralise the legacy sticky top header so its leftover rules cannot bleed |

## Next Actions

- Register and report the 989 unregistered finding(s) before any removal work starts.
