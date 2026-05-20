# Delagecy Legacy Scan Report

## Summary

- Gate status: **FAIL**
- Scanned files: 5454
- Legacy hits: 427
- Registered findings: 1095
- Unregistered findings: 8
- Removed residue still visible: 0
- Approved UI removals still pending: 0
- Discussion-required findings: 0

## Artifacts

- Scan JSON: `'fy'-suites/delagecy/reports/active_surface_scan_after_wave_next_2.json`
- New-findings JSON: `'fy'-suites/delagecy/reports/active_surface_new_after_wave_next_2.json`
- Machine registry: `delagecy_registry.json`
- Human tracker: `legacy_removal_tracker.md`

## Required Rules

1. New legacy findings must be registered and reported before removal.
2. Removal requires explicit approval.
3. Code, routes, tests, docs, data, and UI residue are removed together.
4. Integrity risks, ownership conflicts, or ambiguous removals must be discussed before work continues.
5. Legacy is not active compatibility; required active behavior must be preserved and canonicalized, not deleted.
6. A finding is only marked removed after a clean scan and targeted verification.

## Counts By Surface

| Surface | Hits |
| --- | --- |
| docs | 184 |
| code | 134 |
| test | 96 |
| config | 13 |

## Counts By Pattern

| Pattern | Hits |
| --- | --- |
| \blegacy\b | 215 |
| \bcompatibility\b | 113 |
| \blegacy_ | 59 |
| \bdeprecated\b | 23 |
| _legacy\b | 17 |

## Registry Status

| Status | Findings |
| --- | --- |
| approved_for_removal | 1095 |

## Top Hit Files

| Path | Hits |
| --- | --- |
| docs/technical/ai/llm-slm-role-stratification.md | 11 |
| docs/technical/architecture/ai_story_contract.md | 11 |
| backend/tests/runtime/test_ai_decision_logging.py | 8 |
| world-engine/tests/test_trace_middleware.py | 8 |
| docs/ADR/adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md | 8 |
| docs/ADR/adr-0053-bounded-semantic-scene-planner.md | 8 |
| docs/technical/architecture/backend-runtime-classification.md | 8 |
| backend/tests/runtime/test_preview_delta.py | 7 |
| docs/ADR/adr-0003-scene-identity-canonical-surface.md | 7 |
| docs/ADR/adr-0054-session-input-language-english-internal-resolution.md | 7 |
| backend/tests/runtime/test_ai_adapter.py | 6 |
| ai_stack/live_dramatic_scene_simulator.py | 6 |
| ai_stack/tests/test_npc_agency_contracts.py | 6 |
| ai_stack/contracts/npc_agency_contracts.py | 5 |
| ai_stack/story_runtime/god_of_carnage/god_of_carnage_opening_transition.py | 5 |
| ai_stack/story_runtime/npc_agency/npc_agency_planner.py | 5 |
| ai_stack/tests/test_mcp_canonical_surface_extended.py | 5 |
| ai_stack/tests/test_narrative_runtime_agent.py | 5 |
| frontend/package-lock.json | 5 |
| docs/ADR/adr-0034-player-facing-narrative-shell-contract.md | 5 |
| docs/ADR/README.md | 5 |
| docs/technical/architecture/canonical_runtime_contract.md | 5 |
| docs/testing/LEGACY_TEST_QUARANTINE_POLICY.md | 5 |
| backend/app/runtime/ai_adapter.py | 4 |
| backend/app/runtime/area2_routing_authority.py | 4 |
| ai_stack/tests/test_w5_actor_tracking_projection.py | 4 |
| world-engine/tests/test_backend_bridge_contract.py | 4 |
| docs/ADR/adr-0029-residue-removal-policy.md | 4 |
| docs/ADR/adr-0031-env-configuration-governance.md | 4 |
| backend/app/runtime/narrative_threads.py | 3 |

## Scope Warnings

| Marker | Files | Meaning |
| --- | --- | --- |
| No scope warnings |  |  |

## First Unregistered Findings

| Fingerprint | Surface | Location | Text |
| --- | --- | --- | --- |
| c31fd05e1de5c37e | config | backend/app/var/improvement/recommendations/recommendation_0c95552486884972807f381825a433c9.json:588 | "canonical_authority_summary": "Authoritative Task 2A policy: app.runtime.model_routing.route_model. Runtime uses ada... |
| 9735ae1bf6a8ecbf | config | backend/app/var/improvement/recommendations/recommendation_1bd7044d4b1f41a38821dd11c34e6ef5.json:576 | "canonical_authority_summary": "Authoritative Task 2A policy: app.runtime.model_routing.route_model. Runtime uses ada... |
| b7d5fa08a110f5a5 | config | backend/app/var/improvement/recommendations/recommendation_44eb47204006475ab31eeb119eb774b3.json:588 | "canonical_authority_summary": "Authoritative Task 2A policy: app.runtime.model_routing.route_model. Runtime uses ada... |
| 32be38057758751e | config | backend/app/var/improvement/recommendations/recommendation_691fa23760314b8c8b2797a9248c585e.json:585 | "canonical_authority_summary": "Authoritative Task 2A policy: app.runtime.model_routing.route_model. Runtime uses ada... |
| 4a092835336f365b | config | backend/app/var/improvement/recommendations/recommendation_6cf86f54a70642dab0ea4434d31cf3cb.json:588 | "canonical_authority_summary": "Authoritative Task 2A policy: app.runtime.model_routing.route_model. Runtime uses ada... |
| af1a839d38f3f662 | config | backend/app/var/improvement/recommendations/recommendation_8b1362178dc84516bc50ec352ba770e9.json:588 | "canonical_authority_summary": "Authoritative Task 2A policy: app.runtime.model_routing.route_model. Runtime uses ada... |
| 7e25214fe2bf764d | config | backend/app/var/improvement/recommendations/recommendation_9ae35c68404b4507b8dd96e8697d13e6.json:576 | "canonical_authority_summary": "Authoritative Task 2A policy: app.runtime.model_routing.route_model. Runtime uses ada... |
| a2ea04078869d4d1 | config | backend/app/var/improvement/recommendations/recommendation_d6cff5f5df024de69df3959c3342f371.json:567 | "canonical_authority_summary": "Authoritative Task 2A policy: app.runtime.model_routing.route_model. Runtime uses ada... |

## UI Residue Examples

| Fingerprint | Location | Text |
| --- | --- | --- |
| No UI residue hits |  |  |

## Next Actions

- Register and report the 8 unregistered finding(s) before any removal work starts.
