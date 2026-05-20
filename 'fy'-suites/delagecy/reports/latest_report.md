# Delagecy Legacy Scan Report

## Summary

- Gate status: **FAIL**
- Scanned files: 23515
- Legacy hits: 29642
- Registered findings: 0
- Unregistered findings: 29642
- Removed residue still visible: 0
- Approved UI removals still pending: 0
- Discussion-required findings: 0

## Artifacts

- Scan JSON: `'fy'-suites/delagecy/reports/latest_scan.json`
- New-findings JSON: `not provided`
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
| config | 27179 |
| code | 1416 |
| docs | 627 |
| test | 219 |
| ui | 197 |
| unknown | 4 |

## Counts By Pattern

| Pattern | Hits |
| --- | --- |
| \blegacy_ | 14041 |
| \bcompatibility\b | 8774 |
| \blegacy\b | 5940 |
| \bdeprecated\b | 852 |
| _legacy\b | 35 |

## Registry Status

| Status | Findings |
| --- | --- |
| No registered findings |  |

## Top Hit Files

| Path | Hits |
| --- | --- |
| world-engine/source/Lib/site-packages/pip/_vendor/packaging/licenses/_spdx.py | 740 |
| docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/mvp_source_inventory.md | 108 |
| docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/source_to_destination_mapping_table.md | 108 |
| world-engine/app/var/story_sessions/043fcc396a4d4b76aff88e496970200f.json | 36 |
| world-engine/app/var/story_sessions/ec68e3494ffd461487de581d91a86002.json | 36 |
| ai_stack/langfuse/langfuse_evaluator_catalog.py | 34 |
| ai_stack/tests/test_runtime_readiness_consumer.py | 26 |
| docs/generated/langfuse/langfuse_judge_transfer.local.json | 25 |
| world-engine/source/Lib/site-packages/pip/_vendor/rich/console.py | 22 |
| world-engine/source/Lib/site-packages/pip/_vendor/pkg_resources/__init__.py | 20 |
| docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/reconciliation_report.md | 19 |
| ai_stack/runtime_readiness_consumer.py | 18 |
| docs/MVPs/MVP_Live_Runtime_Completion/05_interactive_text_adventure_frontend_e2e.md | 18 |
| backend/app/services/governance_console_service.py | 17 |
| world-engine/source/Lib/site-packages/pip/_vendor/urllib3/util/retry.py | 17 |
| ai_stack/tests/test_phase1_live_wiring.py | 17 |
| ai_stack/langchain/bridges.py | 15 |
| ai_stack/langgraph/langgraph_runtime_executor.py | 15 |
| ai_stack/story_runtime/dramatic_effect/dramatic_effect_gate_evaluate_branch_outcomes.py | 15 |
| docs/MVPs/w5_actor_situation_migration.md | 13 |
| backend/app/runtime/model_inventory_report.py | 12 |
| backend/htmlcov/z_c6970844fb9f4745_model_inventory_report_py.html | 12 |
| world-engine/tests/test_trace_middleware.py | 12 |
| administration-tool/static/manage_inspector_workbench.js | 12 |
| docs/technical/ai/llm-slm-role-stratification.md | 11 |
| docs/technical/architecture/ai_story_contract.md | 11 |
| world-engine/source/Lib/site-packages/pip/_internal/metadata/base.py | 10 |
| writers-room/app/templates/index.html | 10 |
| backend/app/services/inspector_turn_projection_assembly_helpers.py | 9 |
| backend/tests/runtime/test_ai_decision_logging.py | 8 |

## Scope Warnings

| Marker | Files | Meaning |
| --- | --- | --- |
| site-packages | 98 | Bundled dependency files are in scope. Treat these as scan noise unless ownership is explicit. |
| htmlcov | 34 | Coverage output is in scope. Generated reports should normally be excluded from removal planning. |
| /var/story_sessions/ | 2 | Runtime story-session snapshots are in scope. Decide whether these are fixtures or generated state before registration. |
| docs/generated | 1 | Generated documentation is in scope. Prefer removing the source of residue, then regenerating docs. |

## First Unregistered Findings

| Fingerprint | Surface | Location | Text |
| --- | --- | --- | --- |
| a7409c2ba08c3955 | unknown | backend/alembic.ini:57 | # Note that in order to support legacy alembic.ini files, this default does NOT |
| 9a49818e93f975b3 | unknown | backend/alembic.ini:61 | # 1. Parsing of the version_locations option falls back to using the legacy |
| 7159dbf3b61e40e2 | unknown | backend/alembic.ini:62 | #    "version_path_separator" key, which if absent then falls back to the legacy |
| 6ecf637f2d372f08 | unknown | backend/alembic.ini:64 | # 2. Parsing of the prepend_sys_path option falls back to the legacy |
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
| 62526228c0862fbb | backend/htmlcov/function_index.html:8181 | <td class="name"><a href="z_c6970844fb9f4745_adapter_registry_py.html#t126"><data value='legacy_adapter_without_model... |
| afb0ebf95b78ca22 | backend/htmlcov/z_44edb72147bcffed_feature_registry_py.html:210 | <p class="pln"><span class="n"><a id="t126" href="#t126">126</a></span><span class="t">    <span class="com"># No row... |
| ad38f2e65f96c1d4 | backend/htmlcov/z_49d90ef04657052e_routes_py.html:85 | <p class="pln"><span class="n"><a id="t1" href="#t1">1</a></span><span class="t"><span class="str">"""Legacy web comp... |
| 5e6010f02d9d9569 | backend/htmlcov/z_49d90ef04657052e_routes_py.html:89 | <p class="pln"><span class="n"><a id="t5" href="#t5">5</a></span><span class="t"><span class="str">``/backend`` info ... |
| 42e56e279e7c71f1 | backend/htmlcov/z_49d90ef04657052e_routes_py.html:90 | <p class="pln"><span class="n"><a id="t6" href="#t6">6</a></span><span class="t"><span class="str">frontend service f... |
| 705b139b4ef045cd | backend/htmlcov/z_49d90ef04657052e_routes_py.html:111 | <p class="mis mis2 show_mis"><span class="n"><a id="t27" href="#t27">27</a></span><span class="t">                <sp... |
| ff1a0a0820dd650c | backend/htmlcov/z_49d90ef04657052e_routes_py.html:112 | <p class="mis mis2 show_mis"><span class="n"><a id="t28" href="#t28">28</a></span><span class="t">                <sp... |
| 1e4883ef501a41f5 | backend/htmlcov/z_49d90ef04657052e_routes_py.html:148 | <p class="mis mis2 show_mis"><span class="n"><a id="t64" href="#t64">64</a></span><span class="t">            <span c... |
| 42fce26fc7c43fd1 | backend/htmlcov/z_49d90ef04657052e_routes_py.html:151 | <p class="mis mis2 show_mis"><span class="n"><a id="t67" href="#t67">67</a></span><span class="t">            <span c... |
| a6a9a14aaa84ee91 | backend/htmlcov/z_4c37ce8615b5aa70_ai_stack_evidence_service_py.html:569 | <p class="mis show_mis"><span class="n"><a id="t485" href="#t485">485</a></span><span class="t">        <span class="... |
| d68b6e0574b5990c | backend/htmlcov/z_4c37ce8615b5aa70_data_import_service_py.html:89 | <p class="pln"><span class="n"><a id="t5" href="#t5">5</a></span><span class="t"><span class="str">- schema/version c... |
| 05f2f86c7c239ef7 | backend/htmlcov/z_4c37ce8615b5aa70_data_import_service_py.html:166 | <p class="pln"><span class="n"><a id="t82" href="#t82">82</a></span><span class="t">    <span class="str">"""Validate... |
| ef71db311434f1df | backend/htmlcov/z_4c37ce8615b5aa70_game_service_py.html:166 | <p class="pln"><span class="n"><a id="t82" href="#t82">82</a></span><span class="t">    <span class="str">"""Validate... |
| b044f47ad011804e | backend/htmlcov/z_4c37ce8615b5aa70_session_service_py.html:104 | <p class="pln"><span class="n"><a id="t20" href="#t20">20</a></span><span class="t">    <span class="str">"""Bootstra... |
| b99540984b992a25 | backend/htmlcov/z_4c37ce8615b5aa70_user_service_py.html:118 | <p class="pln"><span class="n"><a id="t34" href="#t34">34</a></span><span class="t">        <span class="com"># Retur... |
| 19355e56cbd345bc | backend/htmlcov/z_4c37ce8615b5aa70_user_service_py.html:322 | <p class="pln"><span class="n"><a id="t238" href="#t238">238</a></span><span class="t">    <span class="com"># treat ... |

## Next Actions

- Register and report the 29642 unregistered finding(s) before any removal work starts.
