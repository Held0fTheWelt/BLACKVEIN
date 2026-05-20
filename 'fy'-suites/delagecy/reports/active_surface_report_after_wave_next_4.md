# Delagecy Legacy Scan Report

## Summary

- Gate status: **PASS**
- Scanned files: 5454
- Legacy hits: 358
- Registered findings: 1103
- Unregistered findings: 0
- Removed residue still visible: 0
- Approved UI removals still pending: 0
- Discussion-required findings: 0

## Artifacts

- Scan JSON: `'fy'-suites/delagecy/reports/active_surface_scan_after_wave_next_4.json`
- New-findings JSON: `'fy'-suites/delagecy/reports/active_surface_new_after_wave_next_4.json`
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
| code | 110 |
| test | 59 |
| config | 5 |

## Counts By Pattern

| Pattern | Hits |
| --- | --- |
| \blegacy\b | 187 |
| \bcompatibility\b | 101 |
| \blegacy_ | 39 |
| \bdeprecated\b | 23 |
| _legacy\b | 8 |

## Registry Status

| Status | Findings |
| --- | --- |
| approved_for_removal | 1034 |
| removed | 69 |

## Top Hit Files

| Path | Hits |
| --- | --- |
| docs/technical/ai/llm-slm-role-stratification.md | 11 |
| docs/technical/architecture/ai_story_contract.md | 11 |
| world-engine/tests/test_trace_middleware.py | 8 |
| docs/ADR/adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md | 8 |
| docs/ADR/adr-0053-bounded-semantic-scene-planner.md | 8 |
| docs/technical/architecture/backend-runtime-classification.md | 8 |
| docs/ADR/adr-0003-scene-identity-canonical-surface.md | 7 |
| docs/ADR/adr-0054-session-input-language-english-internal-resolution.md | 7 |
| ai_stack/live_dramatic_scene_simulator.py | 6 |
| ai_stack/story_runtime/god_of_carnage/god_of_carnage_opening_transition.py | 5 |
| frontend/package-lock.json | 5 |
| docs/ADR/adr-0034-player-facing-narrative-shell-contract.md | 5 |
| docs/ADR/README.md | 5 |
| docs/technical/architecture/canonical_runtime_contract.md | 5 |
| docs/testing/LEGACY_TEST_QUARANTINE_POLICY.md | 5 |
| ai_stack/tests/test_w5_actor_tracking_projection.py | 4 |
| world-engine/tests/test_backend_bridge_contract.py | 4 |
| docs/ADR/adr-0029-residue-removal-policy.md | 4 |
| docs/ADR/adr-0031-env-configuration-governance.md | 4 |
| backend/app/runtime/narrative_threads.py | 3 |
| backend/app/runtime/runtime_ai_stages.py | 3 |
| backend/app/services/governance/governance_runtime_service.py | 3 |
| backend/tests/test_narrow_followup.py | 3 |
| backend/tests/test_world_engine_backend_api_contracts.py | 3 |
| ai_stack/actor_tracking/projection.py | 3 |
| ai_stack/story_runtime/turn/validation_authority_bridge.py | 3 |
| ai_stack/telemetry/actor_survival_telemetry.py | 3 |
| ai_stack/telemetry/diagnostics_envelope.py | 3 |
| world-engine/tests/test_story_runtime_w5_narrator_projection.py | 3 |
| world-engine/tests/test_story_session_w5_round_trip.py | 3 |

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
