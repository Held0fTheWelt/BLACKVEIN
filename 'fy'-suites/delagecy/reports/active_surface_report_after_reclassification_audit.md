# Delagecy Legacy Scan Report

## Summary

- Gate status: **FAIL**
- Scanned files: 5396
- Legacy hits: 682
- Registered findings: 989
- Unregistered findings: 69
- Removed residue still visible: 0
- Approved UI removals still pending: 0
- Discussion-required findings: 0

## Artifacts

- Scan JSON: `'fy'-suites/delagecy/reports/active_surface_scan_after_reclassification_audit.json`
- New-findings JSON: `'fy'-suites/delagecy/reports/active_surface_new_after_reclassification_audit.json`
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
| code | 329 |
| docs | 184 |
| test | 164 |
| config | 5 |

## Counts By Pattern

| Pattern | Hits |
| --- | --- |
| \blegacy\b | 295 |
| \blegacy_ | 220 |
| \bcompatibility\b | 114 |
| _legacy\b | 30 |
| \bdeprecated\b | 23 |

## Registry Status

| Status | Findings |
| --- | --- |
| approved_for_removal | 989 |

## Top Hit Files

| Path | Hits |
| --- | --- |
| backend/app/services/governance_console_service.py | 17 |
| ai_stack/tests/test_phase1_live_wiring.py | 17 |
| ai_stack/langchain/bridges.py | 15 |
| ai_stack/langgraph/langgraph_runtime_executor.py | 15 |
| ai_stack/story_runtime/dramatic_effect/dramatic_effect_gate_evaluate_branch_outcomes.py | 15 |
| backend/app/runtime/model_inventory_report.py | 12 |
| world-engine/tests/test_trace_middleware.py | 12 |
| docs/technical/ai/llm-slm-role-stratification.md | 11 |
| docs/technical/architecture/ai_story_contract.md | 11 |
| backend/app/services/inspector_turn_projection_assembly_helpers.py | 9 |
| backend/tests/runtime/test_ai_decision_logging.py | 8 |
| ai_stack/tests/test_dramatic_effect_gate.py | 8 |
| docs/ADR/adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md | 8 |
| docs/ADR/adr-0053-bounded-semantic-scene-planner.md | 8 |
| docs/technical/architecture/backend-runtime-classification.md | 8 |
| backend/app/runtime/operator_truth.py | 7 |
| backend/app/services/ai_engineer_suite_service.py | 7 |
| backend/app/services/inspector_projection_coverage_health_distribution.py | 7 |
| backend/app/services/inspector_turn_projection_sections_gate_payload.py | 7 |
| backend/app/services/writers_room_pipeline_finalize_package_out.py | 7 |
| backend/tests/runtime/test_preview_delta.py | 7 |
| docs/ADR/adr-0003-scene-identity-canonical-surface.md | 7 |
| docs/ADR/adr-0054-session-input-language-english-internal-resolution.md | 7 |
| backend/app/runtime/operator_audit.py | 6 |
| backend/tests/runtime/test_ai_adapter.py | 6 |
| ai_stack/live_dramatic_scene_simulator.py | 6 |
| ai_stack/tests/test_npc_agency_contracts.py | 6 |
| backend/app/runtime/adapter_registry.py | 5 |
| backend/app/services/inspector_turn_projection_sections_provenance_entries.py | 5 |
| backend/tests/test_inspector_turn_projection.py | 5 |

## Scope Warnings

| Marker | Files | Meaning |
| --- | --- | --- |
| No scope warnings |  |  |

## First Unregistered Findings

| Fingerprint | Surface | Location | Text |
| --- | --- | --- | --- |
| 79c8129b72ca9b53 | code | backend/app/auth/feature_registry.py:67 | # Legacy tuple view derived from ``app.auth.feature_access_resolver.FEATURE_ACCESS_RULES`` (import lazily). |
| aebf77720a999229 | code | backend/app/auth/feature_registry.py:68 | def feature_required_roles_legacy(feature_id: str) -> tuple[str, ...]: |
| c841daf12381dcea | code | backend/app/runtime/runtime_ai_stages_sections.py:29 | """Attach runtime stage metadata to an adapter request (same contract as legacy orchestrator).""" |
| ecbd03215b8cc8c6 | code | ai_stack/god_of_carnage_dramatic_alignment.py:193 | """Bounded legacy seam: length thresholds, withhold beat, |
| 4d1c74d32c1a54fb | code | ai_stack/god_of_carnage_dramatic_alignment.py:249 | """Deprecated full surface path: legacy structural + token/boilerplate |
| 867711d1e880c33f | code | ai_stack/god_of_carnage_dramatic_alignment.py:266 | legacy = dramatic_alignment_legacy_fallback_only( |
| 8da110bf068ad38b | code | ai_stack/god_of_carnage_dramatic_alignment.py:272 | if legacy: |
| beb20a026755f6f0 | code | ai_stack/god_of_carnage_dramatic_alignment.py:273 | return legacy |
| 98cd517c98fa5232 | code | ai_stack/god_of_carnage_opening_transition.py:75 | """Compatibility API: explicit fallback only, never substitute opening prose.""" |
| daeeb2e479e03bcb | code | ai_stack/god_of_carnage_opening_transition.py:80 | """Compatibility API: explicit fallback only, never substitute room prose.""" |
| f8afa93c6c34b82d | code | ai_stack/god_of_carnage_opening_transition.py:90 | """Compatibility API: explicit fallback only, never substitute role-anchor prose.""" |
| 4c085209375e8e3c | code | ai_stack/god_of_carnage_opening_transition.py:95 | """Compatibility API: explicit fallback only, never substitute NPC dialogue.""" |
| 6f3cd31f673e8b8a | code | ai_stack/god_of_carnage_opening_transition.py:424 | """Compatibility API: no deterministic NPC-line replacement is allowed.""" |
| cc64e84bc54c547d | code | ai_stack/god_of_carnage_scene_identity.py:16 | # Runtime / slice scene identifiers → legacy-compatible phase guidance keys. |
| bc538fdc4eb44dda | code | ai_stack/god_of_carnage_souffleuse.py:165 | stance = {"legacy_stance_summary": _clean(raw)} |
| 164ba990cf565a78 | code | ai_stack/god_of_carnage_souffleuse.py:186 | return {"legacy_guidance_summary": _clean(raw)} |
| 97f8bf4762ef0d59 | code | ai_stack/god_of_carnage_yaml_authority.py:266 | """Project phase_beat_policy into the legacy scene-guidance shape. |
| 98c9daa5c6f4af96 | code | ai_stack/god_of_carnage_yaml_authority.py:330 | """Project phase_beat_policy phases into the legacy scene_phases shape.""" |
| dd6a0cfb3a8e1690 | code | ai_stack/runtime_aspect_ledger.py:773 | When disabled, final session readiness fields must match legacy/seam evaluation |
| b36d9aa981fa3390 | code | ai_stack/actor_tracking/projection.py:16 | diff against the legacy ``transition_from_previous`` block. |
| 3cd29cf8df4426d5 | code | ai_stack/actor_tracking/projection.py:659 | against the prior persisted snapshot — same semantics as the legacy |
| dfb1f3b4f58ff69a | code | ai_stack/actor_tracking/projection.py:747 | summary and a compatibility ``derived_actor_locations`` map. Raw persisted |
| 866886a5f230b17d | code | ai_stack/actor_tracking/validation.py:431 | "w5_validation_source": "legacy_fallback", |
| 62090d2659350d59 | code | ai_stack/contracts/dramatic_effect_contract.py:96 | legacy_fallback_used: bool = False |
| 389343775c55ffd4 | code | ai_stack/contracts/genre_awareness_contracts.py:4 | evidence. It does not judge generated prose and it never uses legacy Pi labels |

## UI Residue Examples

| Fingerprint | Location | Text |
| --- | --- | --- |
| No UI residue hits |  |  |

## Next Actions

- Register and report the 69 unregistered finding(s) before any removal work starts.
