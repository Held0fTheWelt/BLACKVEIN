# Delagecy Legacy Scan Report

## Summary

- Gate status: **PASS**
- Scanned files: 5398
- Legacy hits: 478
- Registered findings: 1084
- Unregistered findings: 0
- Removed residue still visible: 0
- Approved UI removals still pending: 0
- Discussion-required findings: 0

## Artifacts

- Scan JSON: `'fy'-suites/delagecy/reports/active_surface_scan_after_continued_removal_2.json`
- New-findings JSON: `'fy'-suites/delagecy/reports/active_surface_new_after_continued_removal_2.json`
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
| code | 184 |
| docs | 184 |
| test | 105 |
| config | 5 |

## Counts By Pattern

| Pattern | Hits |
| --- | --- |
| \blegacy\b | 229 |
| \bcompatibility\b | 113 |
| \blegacy_ | 93 |
| \bdeprecated\b | 23 |
| _legacy\b | 20 |

## Registry Status

| Status | Findings |
| --- | --- |
| approved_for_removal | 1084 |

## Top Hit Files

| Path | Hits |
| --- | --- |
| ai_stack/langchain/bridges.py | 15 |
| backend/app/runtime/model_inventory_report.py | 12 |
| docs/technical/ai/llm-slm-role-stratification.md | 11 |
| docs/technical/architecture/ai_story_contract.md | 11 |
| backend/tests/runtime/test_ai_decision_logging.py | 8 |
| world-engine/tests/test_trace_middleware.py | 8 |
| docs/ADR/adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md | 8 |
| docs/ADR/adr-0053-bounded-semantic-scene-planner.md | 8 |
| docs/technical/architecture/backend-runtime-classification.md | 8 |
| backend/app/runtime/operator_truth.py | 7 |
| backend/tests/runtime/test_preview_delta.py | 7 |
| docs/ADR/adr-0003-scene-identity-canonical-surface.md | 7 |
| docs/ADR/adr-0054-session-input-language-english-internal-resolution.md | 7 |
| backend/app/runtime/operator_audit.py | 6 |
| backend/tests/runtime/test_ai_adapter.py | 6 |
| ai_stack/live_dramatic_scene_simulator.py | 6 |
| ai_stack/tests/test_npc_agency_contracts.py | 6 |
| backend/app/runtime/adapter_registry.py | 5 |
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
| backend/app/runtime/routing_authority.py | 4 |

## Scope Warnings

| Marker | Files | Meaning |
| --- | --- | --- |
| No scope warnings |  |  |

## First Unregistered Findings

| Fingerprint | Surface | Location | Text |
| --- | --- | --- | --- |
| No unregistered findings |  |  |  |

## UI Residue Examples

| Fingerprint | Location | Text |
| --- | --- | --- |
| No UI residue hits |  |  |

## Next Actions

- Gate is clean for this scan; keep the report with the removal review evidence.
