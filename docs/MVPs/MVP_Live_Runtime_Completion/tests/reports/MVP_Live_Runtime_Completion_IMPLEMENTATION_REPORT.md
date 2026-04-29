# MVP_Live_Runtime_Completion — Implementation Guide Package Report

## 1. Summary

Implemented the quality-audit findings into the five requested Markdown guide files. The package now uses the required final structure for every MVP, preserves the final God of Carnage live dramatic scene target, adds concrete work context, contracts, validation rules, examples, tests, ADR coverage, operational gates, handoffs, and copy-ready Claude implementation prompts.

No TXT duplicates, no `no-loss`, no `expanded`, no `v2`, and no renamed guide files were created.

## 2. Waves Applied

| Wave | Applied? | Files Changed | Notes |
|---|---:|---|---|
| Wave 0 — Package and Baseline Hardening | yes | all five MVP guides | Removed audit/preparation framing, preserved final target, added Base Contract and Global Prohibitions, made LDSS non-optional/final, and added P13 before final P12 in MVP 5. |
| Wave 1 — Source Coverage and Work Context | yes | all five MVP guides | Added inputs, outputs, consumers, touched services, concrete file/symbol source lists, do-not-touch lists, targeted search commands, and Source Locator Matrix. |
| Wave 2 — Contract and Validation Implementation | yes | all five MVP guides | Added/strengthened all required contracts and validation tables with rule, enforcement location, error code, test name, and diagnostic field. |
| Wave 3 — Example and Behavior-Proof Implementation | yes | all five MVP guides | Added concrete valid/invalid JSON, Python, HTML, DOM, trace, diagnostics, and final E2E examples. |
| Wave 4 — Operational Gate Implementation | yes | all five MVP guides | Replaced presence-only gate language with command-execution evidence requirements and required operational tests/checks. |
| Wave 5 — Tests, ADRs, and Handoffs | yes | all five MVP guides | Added required tests, ADR coverage, explicit MVP-to-MVP handoffs, stop conditions, and final handoff. |
| Wave 6 — Claude Efficiency and Final Hardening | yes | all five MVP guides | Added copy-ready Claude Implementation Prompt and Token Discipline sections to each guide. |

## 3. Files Updated

| File | Major Changes |
|---|---|
| `01_experience_identity_and_session_start.md` | Runtime profile/content separation, Annette/Alain start contract, visitor rejection, role slug mapping, capability evidence, MVP 1 handoff. |
| `02_runtime_state_actor_lanes_content_boundary.md` | RuntimeState, StorySessionState, ActorLaneContext, actor-lane rejection examples, object admission, protected state boundary, MVP 2 handoff. |
| `03_live_dramatic_scene_simulator.md` | Full LDSS contract, SceneTurnEnvelope.v2, SceneBlock examples, NPC agency, environment affordances, narrator validation, live-path evidence. |
| `04_observability_diagnostics_langfuse_narrative_gov.md` | Non-placeholder diagnostics, TraceableDecision, Langfuse/local trace proof, NarrativeGovSummary, degraded semantics. |
| `05_interactive_text_adventure_frontend_e2e.md` | Frontend render contract, DOM block rendering, deterministic typewriter, controls, accessibility, legacy fallback degradation, final Annette/Alain E2E evidence. |

## 4. Audit Findings Resolved

| Finding | Resolution | File |
|---|---|---|
| Guides had blocking context gaps | Added structured work context, source locator matrix, inputs/outputs/consumers, files, symbols, and search commands. | all five |
| Examples were insufficient | Added concrete JSON/Python/HTML examples for all required guide areas. | all five |
| Cross-MVP handoffs were implied | Added explicit handoff sections and required handoff artifact paths. | all five |
| ADR coverage incomplete | Added complete ADR map and MVP-specific ADR requirements. | all five |
| Operational gates risked file-existence false-green | Added command execution evidence, operational evidence schema, and false-green failure rules. | all five |
| MVP 1 E0 could be static | CapabilityEvidenceReport now requires source anchors or honest `missing`. | MVP 1 |
| Actor-lane enforcement could be nominal | Added seam-level validation rules and rejection fixtures. | MVP 2 |
| LDSS status could be set without live proof | Added live-route evidence contract with IDs, hashes, counts, and no legacy blob. | MVP 3 |
| Diagnostics examples allowed empty success | Added non-placeholder rule and invalid placeholder diagnostics example. | MVP 4 |
| Frontend could collapse to a blob | Added DOM invariant, forbidden DOM shape, deterministic typewriter, and E2E transcript requirements. | MVP 5 |

## 5. Contracts Added or Strengthened

| Contract | MVP | File |
|---|---|---|
| RuntimeProfile | 1 | `01_experience_identity_and_session_start.md` |
| RoleSlugActorIdMap | 1 | `01_experience_identity_and_session_start.md` |
| CreateRunRequest | 1 | `01_experience_identity_and_session_start.md` |
| CreateRunResponse | 1 | `01_experience_identity_and_session_start.md` |
| CapabilityEvidenceReport | 1 | `01_experience_identity_and_session_start.md` |
| RuntimeState | 2 | `02_runtime_state_actor_lanes_content_boundary.md` |
| StorySessionState | 2 | `02_runtime_state_actor_lanes_content_boundary.md` |
| ActorLaneContext | 2 | `02_runtime_state_actor_lanes_content_boundary.md` |
| ObjectAdmissionRecord | 2 | `02_runtime_state_actor_lanes_content_boundary.md` |
| StateDeltaBoundary | 2 | `02_runtime_state_actor_lanes_content_boundary.md` |
| ActorLaneValidationResult | 2 | `02_runtime_state_actor_lanes_content_boundary.md` |
| SceneTurnEnvelope.v2 | 3 | `03_live_dramatic_scene_simulator.md` |
| SceneBlock | 3 | `03_live_dramatic_scene_simulator.md` |
| LDSSInput | 3 | `03_live_dramatic_scene_simulator.md` |
| LDSSOutput | 3 | `03_live_dramatic_scene_simulator.md` |
| NPCAgencyPlan | 3 | `03_live_dramatic_scene_simulator.md` |
| EnvironmentInteraction | 3 | `03_live_dramatic_scene_simulator.md` |
| AffordanceValidation | 3 | `03_live_dramatic_scene_simulator.md` |
| NarratorVoiceValidation | 3 | `03_live_dramatic_scene_simulator.md` |
| PassivityValidation | 3 | `03_live_dramatic_scene_simulator.md` |
| DiagnosticsEnvelope | 4 | `04_observability_diagnostics_langfuse_narrative_gov.md` |
| TraceableDecision | 4 | `04_observability_diagnostics_langfuse_narrative_gov.md` |
| LangfuseRealTraceEvidence | 4 | `04_observability_diagnostics_langfuse_narrative_gov.md` |
| NarrativeGovSummary | 4 | `04_observability_diagnostics_langfuse_narrative_gov.md` |
| Degraded Outcome Semantics | 4 | `04_observability_diagnostics_langfuse_narrative_gov.md` |
| FrontendRenderContract | 5 | `05_interactive_text_adventure_frontend_e2e.md` |
| FrontendBlockRenderState | 5 | `05_interactive_text_adventure_frontend_e2e.md` |
| TypewriterDeliveryConfig | 5 | `05_interactive_text_adventure_frontend_e2e.md` |
| LegacyFallbackPolicy | 5 | `05_interactive_text_adventure_frontend_e2e.md` |
| E2EAcceptanceEvidence | 5 | `05_interactive_text_adventure_frontend_e2e.md` |

## 6. Examples Added

| Example | MVP | File |
|---|---|---|
| valid Annette start, valid Alain start, missing role, invalid role, visitor rejection, profile-as-content rejection, role mapping, resolver shape | 1 | `01_experience_identity_and_session_start.md` |
| selected role human, remaining roles NPC, AI speaks for human rejection, human responder rejection, NPC coercion rejection, object admission, protected mutation rejection | 2 | `02_runtime_state_actor_lanes_content_boundary.md` |
| full SceneTurnEnvelope.v2, narrator, actor line, actor action, NPC-to-NPC dialogue, environment interaction, canonical/typical/similar affordances, hallucinated object rejection, narrator invalid modes, passivity/degradation | 3 | `03_live_dramatic_scene_simulator.md` |
| full diagnostics envelope, invalid placeholder diagnostics, TraceableDecision, Langfuse/local trace export, NarrativeGovSummary, degraded diagnostics | 4 | `04_observability_diagnostics_langfuse_narrative_gov.md` |
| frontend render input, DOM transcript, forbidden blob DOM, typewriter config, skip current, reveal all, accessibility, legacy fallback degraded, Annette/Alain E2E evidence, final transcript artifact | 5 | `05_interactive_text_adventure_frontend_e2e.md` |

## 7. Tests Added to Guides

| Test | MVP | Purpose |
|---|---|---|
| `test_valid_annette_start`, `test_valid_alain_start` | 1 | Prove real role-specific session start. |
| `test_visitor_absent_from_prompts_responders_lobby` | 1 | Sweep visitor across runtime, prompts, responders, lobby, frontend. |
| `test_ai_cannot_speak_or_act_for_human_role` | 2 | Prove actor-lane enforcement at AI seam. |
| `test_ai_cannot_choose_human_responder` | 2 | Prove responder nomination guard. |
| `test_npc_action_cannot_force_human_response` | 2 | Prove non-coercive NPC action boundary. |
| `test_rejects_unadmitted_plausible_object` | 2/3 | Prove object admission is required. |
| `test_live_turn_route_invokes_ldss` | 3 | Prove LDSS runs in real turn route. |
| `test_live_dramatic_scene_simulator_not_partial` | 3 | Prevent status-only LDSS pass. |
| `test_no_visible_actor_response_triggers_retry_or_degradation` | 3 | Prevent passive/narrator-only output. |
| `test_langfuse_real_trace_export_matches_story_turn` | 4 | Prevent mock/static trace final proof. |
| `test_diagnostics_complete_envelope_requires_evidence_consistency` | 4 | Prevent empty approved diagnostics. |
| `test_frontend_does_not_collapse_to_single_blob` | 5 | Enforce one DOM node per block. |
| `test_typewriter_uses_virtual_clock_in_test_mode` | 5 | Make typewriter deterministic and testable. |
| `test_final_annette_e2e_evidence`, `test_final_alain_e2e_evidence` | 5 | Prove final role-specific E2E acceptance. |
| mandatory operational checks | all | Prevent false-green startup/test/CI/tooling gates. |

## 8. ADRs Required

| ADR | MVP |
|---|---|
| ADR-001 Experience Identity | 1 |
| ADR-002 Runtime Profile Resolver | 1 |
| ADR-003 Role Selection and Actor Ownership | 1, 2 |
| ADR-004 Actor-Lane Enforcement | 2 |
| ADR-005 Canonical Content Authority | 2 |
| ADR-006 Evidence-Gated Architecture Capabilities | 1, 4 |
| ADR-007 Minimum Agency Baseline / Superseded Relation | 3 |
| ADR-008 Diagnostics and Degradation Semantics | 4 |
| ADR-009 Langfuse and Traceable Decisions | 4 |
| ADR-010 Narrative Gov Operator Truth Surface | 4 |
| ADR-011 Live Dramatic Scene Simulator | 3 |
| ADR-012 NPC Free Dramatic Agency | 3 |
| ADR-013 Narrator Inner Voice Contract | 3 |
| ADR-014 Interactive Text-Adventure Frontend | 5 |
| ADR-015 Canonical, Typical, and Similar Environment Affordances | 2, 3 |
| ADR-016 Operational Test and Startup Gates | all |

## 9. Operational Gate Coverage

| MVP | docker-up.py | tests/run_tests.py | GitHub | TOML/tooling |
|---|---|---|---|---|
| MVP 1 | command evidence required; failed services must fail gate | role/session/visitor tests included | workflows include MVP 1 suites | testpaths/pythonpath include backend/world-engine/frontend tests |
| MVP 2 | command evidence required after runtime model changes | actor-lane/object/state suites included | workflows include MVP 2 suites | world-engine/ai_stack paths and markers covered |
| MVP 3 | command evidence required after LDSS integration | LDSS unit/integration/live-route tests included | workflows include live-path tests | LDSS paths and markers covered |
| MVP 4 | command evidence required with admin/trace services | diagnostics/trace/admin tests included | workflows include trace/export and admin tests | diagnostics/admin paths covered |
| MVP 5 | command evidence required for all four services | frontend/browser/final E2E tests included | workflows include E2E without silent skip | frontend/e2e markers and browser config covered |

## 10. Remaining Risks

| Risk | Reason | Follow-up |
|---|---|---|
| Repository symbols may differ from expected paths | Guides were hardened from package/audit, not from a fresh full repository code audit. | Each MVP requires Source Locator Matrix before patching and closest-equivalent mapping when paths differ. |
| Some exact canonical actor IDs may differ | Examples use known expected IDs, but implementation must resolve from content. | Tests must assert resolved content-derived IDs, not hardcoded examples when content differs. |
| Langfuse may be unavailable locally | Final proof can use deterministic local trace export if generated by real test and metadata matches. | MVP 4 must document environment mode and export artifact. |
| Browser test stack may differ | Guide names Playwright/Selenium generically through search and equivalent command evidence. | MVP 5 must record actual browser framework/config in report. |

## 11. Final Verdict

```text
guides_ready_after_required_patches

Operational interpretation:
- The guide package is safe for MVP 1 locator-first Claude/Cursor execution.
- The first action must complete the Source Locator Matrix.
- Code patching remains blocked while unresolved source-locator placeholders remain.
- The package is not classified as `guides_implementation_ready` until concrete repository paths and symbols are filled by the locator pass.
```

## 12. Wave Quality-Audit Patch Addendum

Applied the follow-up quality-audit patches from the wave-implemented package review.

| Patch | Applied? | Files Changed | Notes |
|---|---:|---|---|
| GUIDE-PATCH-010 — Source Locator Stop Gate | yes | all five MVP guides | Added a pre-patch failure gate for unresolved `from patch map`, `fill during implementation`, unresolved `or equivalent`, unresolved `not_present`, and empty symbol cells. |
| GUIDE-PATCH-011 — Actor-lane validator signature/order | yes | MVP 2 | Added central validator shape, required call order, `actor_lane_validation_too_late`, and ordering test. |
| GUIDE-PATCH-012 — LDSS live call-chain anchors | yes | MVP 3 | Added call-chain anchor table and live HTTP final-response proof requirement. |
| GUIDE-PATCH-013 — Current-test-run trace proof | yes | MVP 4 | Added `source_test_run_id`, `generated_at`, matching response/export trace IDs, and stale/static export rejection. |
| GUIDE-PATCH-014 — DOM staged text-state invariant | yes | MVP 5 | Added text-state DOM invariant, validation error, and frontend test. |
| GUIDE-PATCH-015 — MVP-specific operational evidence | yes | all five MVP guides | Added exact suite/file/marker evidence requirements and false-green error code. |

### Additional Findings Resolved

| Finding | Resolution | File |
|---|---|---|
| Locator matrix could remain unresolved | Source Locator Stop Gate now blocks code changes until concrete paths/symbols are recorded. | all five |
| Actor-lane enforcement could occur too late | MVP 2 now requires central validator call before commit and response packaging. | `02_runtime_state_actor_lanes_content_boundary.md` |
| LDSS could pass as unit-only behavior | MVP 3 now requires a filled live call-chain table and final HTTP response using LDSS blocks. | `03_live_dramatic_scene_simulator.md` |
| Trace export could be stale or synthetic | MVP 4 now requires current-test-run trace proof and matching response/export trace IDs. | `04_observability_diagnostics_langfuse_narrative_gov.md` |
| Frontend could create empty per-block shells | MVP 5 now requires staged text state in DOM nodes. | `05_interactive_text_adventure_frontend_e2e.md` |
| Operational gate remained generic | All guides now require exact MVP-specific suite, file, marker, runner, workflow, and TOML evidence. | all five |

### New/Strengthened Tests From Follow-up Audit

| Test | MVP | Purpose |
|---|---|---|
| `test_source_locator_matrix_has_no_placeholders_before_patch` | all | Prevent unresolved source/symbol placeholders before implementation. |
| `test_operational_report_lists_mvp_specific_suites` | all | Prevent generic operational false-green reports. |
| `test_role_slug_map_uses_content_resolved_actor_ids` | 1 | Prevent copying sample actor IDs without content resolution. |
| `test_mvp1_handoff_runtime_profile_schema_valid` | 1 | Validate MVP 1 handoff artifact. |
| `test_actor_lane_validation_runs_before_response_packaging` | 2 | Prove actor-lane enforcement occurs before commit/packaging. |
| `test_ldss_input_assembled_from_mvp2_handoff` | 3 | Prove LDSS consumes MVP 2 handoff state. |
| `test_live_turn_response_uses_ldss_blocks_not_legacy_text` | 3 | Prove final HTTP response uses LDSS block contract. |
| `test_passivity_retry_exhaustion_returns_degraded_diagnostics` | 3 | Prove passivity failure has retry/degraded semantics. |
| `test_trace_export_current_test_run_id_matches_response` | 4 | Prevent stale/static local trace proof. |
| `test_quality_normal_has_no_degradation_signals` | 4 | Prevent inconsistent diagnostics quality state. |
| `test_frontend_block_nodes_include_staged_text_state` | 5 | Prove per-block DOM contains staged text, not empty shells. |
| `test_final_e2e_artifact_index_links_all_required_evidence` | 5 | Ensure final transcript, screenshots, traces, Narrative Gov, and operational logs are linked. |

### Updated Final Readiness

```text
guides_ready_after_required_patches

Operational interpretation:
- The guide package is safe for MVP 1 locator-first Claude/Cursor execution.
- The first action must complete the Source Locator Matrix.
- Code patching remains blocked while unresolved source-locator placeholders remain.
- The package is not classified as `guides_implementation_ready` until concrete repository paths and symbols are filled by the locator pass.
```

The guides are now safe for an MVP 1 locator-first Claude/Cursor pass. The first implementation action must complete the Source Locator Matrix; production patching remains blocked while locator placeholders remain unresolved.


## 13. Final Quality-Patched Audit Addendum

Applied the follow-up quality-audit patches from the quality-patched package review.

| Patch | Applied? | Files Changed | Notes |
|---|---:|---|---|
| GUIDE-PATCH-016 — Normalize final package verdict vocabulary | yes | implementation report | Replaced `guides_ready_for_mvp_1_locator` with `guides_ready_after_required_patches` and preserved locator-first operational interpretation. |
| GUIDE-PATCH-017 — Require fixed source locator artifact per MVP | yes | all five MVP guides | Added `tests/reports/MVP_Live_Runtime_Completion/MVP<NUMBER>_SOURCE_LOCATOR.md`, `source_locator_artifact_missing`, and `test_source_locator_artifact_exists_for_mvp`. |
| GUIDE-PATCH-018 — Add MVP 4 trace/diagnostics/admin source-anchor table | yes | MVP 4 | Added Trace, Diagnostics, and Narrative Gov Source Anchor Table, plus source-anchor completeness validation. |
| GUIDE-PATCH-019 — Add MVP 5 browser runner and artifact locator table | yes | MVP 5 | Added fixed final artifact index path and browser/artifact locator table with validation and test. |
| GUIDE-PATCH-020 — Require fixed operational evidence artifact per MVP | yes | all five MVP guides | Added `tests/reports/MVP_Live_Runtime_Completion/MVP<NUMBER>_OPERATIONAL_EVIDENCE.md`, `operational_evidence_artifact_missing`, and `test_operational_evidence_artifact_exists_for_mvp`. |

### Additional Findings Resolved

| Finding | Resolution | File |
|---|---|---|
| Report verdict drift | Normalized the final report verdict to `guides_ready_after_required_patches` with explicit locator-first operational interpretation. | implementation report |
| Source locator stop gate had no fixed artifact path | Added fixed per-MVP source locator artifact path and required missing-artifact validation. | all five MVP guides |
| MVP 4 lacked a trace/admin source-anchor table | Added a concrete source-anchor table for span creation, TraceableDecision creation, diagnostics packaging, export writing, and Narrative Gov rendering. | `04_observability_diagnostics_langfuse_narrative_gov.md` |
| MVP 5 browser/artifact paths remained flexible | Added a final artifact index path and browser runner/artifact locator table. | `05_interactive_text_adventure_frontend_e2e.md` |
| Operational evidence had no fixed artifact path | Added fixed per-MVP operational evidence artifacts and tests. | all five MVP guides |

### New/Strengthened Tests From Final Follow-up Audit

| Test | MVP | Purpose |
|---|---|---|
| `test_guide_report_verdict_uses_allowed_status` | report | Prevent ambiguous or non-standard readiness language. |
| `test_source_locator_artifact_exists_for_mvp` | all | Require fixed locator artifact before code patching. |
| `test_trace_source_anchor_table_complete` | 4 | Require real source anchors for trace, diagnostics, and Narrative Gov. |
| `test_browser_artifact_locator_complete` | 5 | Require concrete browser runner and artifact paths. |
| `test_operational_evidence_artifact_exists_for_mvp` | all | Require fixed operational evidence artifact per MVP. |

### Final Readiness After Final Follow-up Audit

```text
guides_ready_after_required_patches

Operational interpretation:
- Safe for MVP 1 locator-first Claude/Cursor execution.
- Each MVP must write its fixed Source Locator artifact before code patching.
- Each MVP must write its fixed Operational Evidence artifact before closing.
- MVP 4 must complete the Trace/Diagnostics/Narrative Gov source-anchor table.
- MVP 5 must complete the Browser Runner and Artifact Locator Table.
- The package is still not `guides_implementation_ready` until actual repository paths and symbols are filled by each locator pass.
```
