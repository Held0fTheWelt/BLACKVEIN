# Delagecy Active Surface After Semantic Audit

## Summary

- Gate status: **FAIL**
- Scanned files: 7242
- Legacy hits: 1013
- Registered findings: 1103
- Unregistered findings: 723
- Removed residue still visible: 0
- Canonicalized residue still visible: 0
- Approved UI removals still pending: 0
- Discussion-required findings: 0

## Artifacts

- Scan JSON: `'fy'-suites/delagecy/reports/active_surface_scan_after_semantic_audit.json`
- New-findings JSON: `'fy'-suites/delagecy/reports/active_surface_new_after_semantic_audit.json`
- Machine registry: `delagecy_registry.json`
- Human tracker: `legacy_removal_tracker.md`

## Required Rules

1. New legacy findings must be registered and reported before removal.
2. Removal requires explicit approval.
3. Code, routes, tests, docs, data, and UI residue are removed together.
4. Integrity risks, ownership conflicts, or ambiguous removals must be discussed before work continues.
5. Compatibility with earlier repo/product versions is removed; it is not retained as active behavior.
6. Compatibility for active alternative usage, such as provider or adapter variation, may be preserved and canonicalized.
7. A finding is only marked removed after true removal, a clean scan, and targeted verification.

## Counts By Surface

| Surface | Hits |
| --- | --- |
| docs | 412 |
| code | 383 |
| test | 156 |
| config | 46 |
| ui | 10 |
| unknown | 6 |

## Counts By Pattern

| Pattern | Hits |
| --- | --- |
| \blegacy\b | 531 |
| \bcompatibility\b | 307 |
| \blegacy_ | 120 |
| \bdeprecated\b | 49 |
| _legacy\b | 6 |

## Registry Status

| Status | Findings |
| --- | --- |
| approved_for_removal | 1024 |
| canonicalized_active_behavior | 50 |
| removed | 29 |

## Top Hit Files

| Path | Hits |
| --- | --- |
| tests/gates/test_table_b_anti_hardcoding_gate.py | 29 |
| 'fy'-suites/docs/platform/fy_v2_surface_aliases.json | 18 |
| 'fy'-suites/docs/platform/fy_v2_packaging_preparation_bundle.md | 15 |
| 'fy'-suites/contractify/adapter/service.py | 14 |
| 'fy'-suites/delagecy/README.md | 14 |
| 'fy'-suites/docs/platform/fy_v2_packaging_preparation_bundle.json | 14 |
| 'fy'-suites/contractify/adapter/tests/test_contractify_imports.py | 13 |
| 'fy'-suites/delagecy/tools/tests/test_delagecy.py | 13 |
| 'fy'-suites/contractify/tools/importer.py | 11 |
| 'fy'-suites/delagecy/tools/hub_cli.py | 11 |
| docs/technical/ai/llm-slm-role-stratification.md | 11 |
| docs/technical/architecture/ai_story_contract.md | 11 |
| 'fy'-suites/docs/platform/fy_v2_compatibility_impact_matrix.md | 10 |
| writers-room/app/templates/index.html | 10 |
| 'fy'-suites/contractify/tools/adr_governance.py | 9 |
| 'fy'-suites/fy_platform/ai/workspace_layout.py | 8 |
| 'fy'-suites/fy_platform/runtime/packaging_preparation.py | 8 |
| 'fy'-suites/fy_platform/surfaces/alias_map.py | 8 |
| docs/ADR/adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md | 8 |
| docs/ADR/adr-0053-bounded-semantic-scene-planner.md | 8 |
| docs/backend/backend_in_world_of_shadows.md | 8 |
| docs/technical/architecture/backend-runtime-classification.md | 8 |
| world-engine/tests/test_trace_middleware.py | 8 |
| 'fy'-suites/observifyfy/tools/repo_paths.py | 7 |
| docs/ADR/adr-0003-scene-identity-canonical-surface.md | 7 |
| docs/ADR/adr-0054-session-input-language-english-internal-resolution.md | 7 |
| prompts/world_engine/story_runtime_prompts.json | 7 |
| 'fy'-suites/contractify/README.md | 6 |
| 'fy'-suites/delagecy/tools/registry.py | 6 |
| 'fy'-suites/delagecy/tools/reporting.py | 6 |

## Scope Warnings

| Marker | Files | Meaning |
| --- | --- | --- |
| No scope warnings |  |  |

## First Unregistered Findings

| Fingerprint | Surface | Location | Text |
| --- | --- | --- | --- |
| b8ace99e247bebee | docs | CLAUDE.md:219 | - Auditing old patterns or legacy content |
| 0cd91a12883220e9 | docs | CLAUDE.md:238 | \| Audit legacy \| "old_pattern instances" \| |
| 6fe60fa716de7742 | code | docker-up.py:596 | legacy = shutil.which("docker-compose") |
| e469aa463af2443c | code | docker-up.py:597 | if legacy: |
| d6ba660ce0687569 | code | docker-up.py:598 | return [legacy] |
| 7ee594137b779d74 | code | docker-up.py:1288 | p_down.add_argument("services", nargs="*", help="Ignored for down (compatibility).") |
| 2f9bce4675548cb5 | docs | DOCKER_UP_COMPLETE_AUDIT.md:51 | - Auto-detects docker compose v2 or legacy docker-compose |
| cb74fb783cac3916 | docs | live_runtime_empty_session_audit.md:210 | \| D-011 \| `VISITOR_LEGACY_LEAK` \| `LOW` \| Residual local world-engine web UI \| `world-engine/app/web/static/app.js` 2... |
| ad3c076733cd75ec | docs | live_runtime_empty_session_audit.md:211 | \| D-012 \| `DOC_STALE` \| `MEDIUM` \| Docs/reports/tests comments \| `backend/tests/test_e2e_god_of_carnage_full_lifecycl... |
| 3706d81834bd81db | docs | live_runtime_empty_session_audit.md:240 | No live profile-path evidence shows `visitor` being mapped as a story actor. The `/api/runs` profile response sets `v... |
| 0b6868f47e058f8f | docs | live_runtime_empty_session_audit.md:324 | The most important drift found in source-adjacent docs/test docstrings is that tests claim to prove real/full/live be... |
| 9144a1a85b6c79d8 | docs | README.md:75 | - **Runtime authority** for live play lives in **`world-engine`** (not the backend’s legacy web layer). |
| e2c7be98df14d644 | docs | README.md:108 | **Representative tests** (current filenames; legacy “phase*” modules were renamed or folded into these surfaces) |
| 5a8e56a9613bb949 | docs | README.md:183 | - Legacy `backend/app/web/*` paths (except `/` and `/health`) remain compatibility redirects to `FRONTEND_URL`, not c... |
| 2a2bcf5d5e2791a5 | docs | README.md:267 | - `FRONTEND_URL` — backend legacy redirects; optional `ADMINISTRATION_TOOL_URL` for `/backend` links |
| c9a4f2ffe9057d66 | docs | README.md:309 | \| `tests/run_tests.py` \| Legacy multi-suite runner (`backend`, `administration`, `engine`, …) \| |
| 765dbd44a96b627e | docs | 'fy'-suites/README.md:17 | \| [**`delagecy/`](delagecy/README.md)** \| Governed legacy discovery, register-first reporting, approval tracking, UI ... |
| bb686172e8712ef7 | docs | 'fy'-suites/README.md:91 | Compatibility and mirrored internal product docs now live under `internal/`. Legacy nested documentation layouts are ... |
| 8131c1a66ef35c7d | config | 'fy'-suites/brokenify/suite_ownership.json:3 | "truth_domain": "compatibility placeholder for bounded breakage and recovery follow-up", |
| 2917769f5cca6ae2 | docs | 'fy'-suites/contractify/contract_governance_input.md:15 | \| **CG-011** \| Normalize ADR home to `docs/ADR` and stop leaving active architecture decisions in legacy folders once... |
| 2f23b9fd1e67b8b8 | docs | 'fy'-suites/contractify/contract_governance_input.md:16 | \| **CG-012** \| Prevent duplicate ADR truth by removing or redirecting legacy ADR copies after canonical migration. \| ... |
| 26bbef27297c4783 | docs | 'fy'-suites/contractify/CONTRACT_GOVERNANCE_SCOPE.md:45 | \| **`supersession_gap`** \| ADR header **`Status:`** is **`Deprecated`** / **`Superseded`** but navigation cues to the... |
| 109e50e3bdb51e8d | docs | 'fy'-suites/contractify/CONTRACT_GOVERNANCE_SCOPE.md:46 | \| **`superseded_still_referenced_as_current`** \| A normative index table row is labelled **Active** / **Binding** but... |
| cd254f2c1582405a | docs | 'fy'-suites/contractify/CONTRACT_GOVERNANCE_SCOPE.md:47 | \| **`lifecycle_projection_vs_retired_anchor`** \| A projection’s **`source_contract_id`** resolves to a discovered con... |
| 7827eac2cfb584a8 | docs | 'fy'-suites/contractify/CONTRACT_GOVERNANCE_SCOPE.md:74 | 4. Legacy or unverified intent. |

## UI Residue Examples

| Fingerprint | Location | Text |
| --- | --- | --- |
| 868d42a0e7529624 | writers-room/app/templates/index.html:22 | Legacy direct chat remains transitional only: |
| 2745720a4892884b | writers-room/app/templates/index.html:23 | <a href="{{ url_for('legacy_oracle') }}">open legacy oracle</a>. |
| ae1f51ae280d71fa | writers-room/app/templates/index.html:68 | {% if legacy_mode %} |
| 9fd604ea6e51f82b | writers-room/app/templates/index.html:70 | <h2>Legacy Oracle (Transitional)</h2> |
| bc5c3e282a29c3c7 | writers-room/app/templates/index.html:71 | <form method="post" action="{{ url_for('legacy_oracle') }}" class="manage-login-form"> |
| f9b53c2285d0961b | writers-room/app/templates/index.html:74 | <input class="form-input" type="text" name="question" id="question" placeholder="Ask legacy oracle..." required> |
| 3adccbb5809938cf | writers-room/app/templates/index.html:76 | <button type="submit" class="btn btn-primary">Ask Legacy Oracle</button> |
| 5805ab9eec2a70d1 | writers-room/app/templates/index.html:78 | {% if legacy_answer is not none %} |
| c2821495e3f34e40 | writers-room/app/templates/index.html:80 | <h3>Legacy Answer</h3> |
| d1fef3301cc8d1e6 | writers-room/app/templates/index.html:81 | <p>{{ legacy_answer }}</p> |

## Next Actions

- Register and report the 723 unregistered finding(s) before any removal work starts.
