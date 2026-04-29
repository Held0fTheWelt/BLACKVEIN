# All Legacy Artifacts Inventory

**Generated:** 2026-04-26
**Cleanup task:** Complete docs/tests cleanup

---

## Summary

| Category | Total Found | Action Taken | Remaining |
|----------|-------------|--------------|-----------|
| Root-level session reports | 38 | Moved to archive | 0 active |
| Root runner (tests/run_tests.py) | 1 | Deleted | 0 |
| Stub smoke tests | 2 | Deleted | 0 |
| Stub e2e test files | 3 | Deleted | 0 |
| Stub gate test methods | 3 | Rewritten | 0 |
| Missing runner suites | 2 | Added (gates, story_runtime_core) | 0 |

---

## Root-Level Legacy Documents (Archived)

These were historical session reports moved to `docs/archive/session-reports-2026/`:

| File | Classification | Action |
|------|---------------|--------|
| WORKSTREAM_A_CHECKPOINT.md | session report | archived |
| WORKSTREAM_B_CHECKPOINT.md | session report | archived |
| WORKSTREAM_B_COMPLETION.md | session report | archived |
| WORKSTREAM_D_AGENT_REPORT.md | session report | archived |
| WORKSTREAM_D_CHECKPOINT.md | session report | archived |
| WORKSTREAM_D_COMPLETION.md | session report | archived |
| WORKSTREAM_D_PLANNING_COMPLETE.md | session report | archived |
| WORKSTREAM_D_TASK_LIST.md | session report | archived |
| PHASE_4_COMPLETION_SUMMARY.md | session report | archived |
| PHASE_5_EVALUATOR_RECRUITMENT_PACKAGE.md | session report | archived |
| PHASE_5_INFRASTRUCTURE_CHECKLIST.md | session report | archived |
| PHASE_5_LAUNCH_BRIEFING.md | session report | archived |
| PHASE_5_SCENARIO_SPECIFICATIONS.md | session report | archived |
| PHASE_5_TASK_EXECUTION_PLAN.md | session report | archived |
| PHASE_5_WEEK1_EXECUTIVE_SUMMARY.md | session report | archived |
| PHASE_6_AND_7_INTEGRATION_ROADMAP.md | session report | archived |
| PHASE_D_IMPLEMENTATION.md | session report | archived |
| LANGFUSE_ADMIN_AUDIT_REPORT.md | session report | archived |
| LANGFUSE_ADMIN_IMPLEMENTATION.md | session report | archived |
| LANGFUSE_ADMIN_IMPLEMENTATION_COMPLETE.md | session report | archived |
| LANGFUSE_COMPLETE_DELIVERY.md | session report | archived |
| LANGFUSE_DELIVERABLES.md | session report | archived |
| LANGFUSE_IMPLEMENTATION_BLUEPRINT.md | session report | archived |
| LANGFUSE_IMPLEMENTATION_REPORT.md | session report | archived |
| LANGFUSE_INITIALIZATION_AND_GOVERNANCE.md | session report | archived |
| AUDIT_RESULT.md | session report | archived |
| CONTRACTIFY_AUDIT_RESULT.md | session report | archived |
| GOVERNANCE_ENFORCEMENT_RESULT.md | session report | archived |
| GOVERNANCE_IMPLEMENTATION_COMPLETE.md | session report | archived |
| GOVERNANCE_REPAIRS_COMPLETED.md | session report | archived |
| IMPLEMENTATION_COMPLETE.md | session report | archived |
| IMPLEMENTATION_RESULT.md | session report | archived |
| STORY_RUNTIME_EXPERIENCE_IMPLEMENTATION_REPORT.md | session report | archived |
| STORY_RUNTIME_EXPERIENCE_TEST_SUMMARY.md | session report | archived |
| WAVES_3_5_IMPLEMENTATION_SUMMARY.md | session report | archived |
| WAVE_1_2_IMPLEMENTATION_SUMMARY.md | session report | archived |
| VERIFICATION_REPORT_WAVE_1_2.md | session report | archived |
| TEST_WAVE_1_2.md | session report | archived |
| REPAIR_SUMMARY.md | session report | archived |
| RUNTIME_AGENCY_REPAIR_BACKLOG.md | session report | archived |
| RUNTIME_AGENCY_REPAIR_TASK.md | session report | archived |
| NARRATIVE_FORMATTING_ENHANCEMENT.md | session report | archived |
| JOURNEY_FROM_PHASE4_TO_PHASE5.md | session report | archived |
| NEXT_TARGET_ASSESSMENT.md | session report | archived |
| ORIGINAL_MVP_GOALS_vs_CURRENT_FOCUS.md | session report | archived |
| PRIMARY_MODEL_UNDERUTILIZATION_AUDIT.md | session report | archived |
| AGENCY_CAPABILITY_MATRIX.md | session report | archived |
| AGENTS.md | session report | archived |
| Plan.md | session report | archived |
| Plan (2).md | session report | archived |
| Plan_Phase5.md | session report | archived |
| Plan_Phase6_BranchingArchitecture.md | session report | archived |
| Plan_Phase6_Phase7_WITH_FY_GOVERNANCE.md | session report | archived |
| Plan_Phase7_LargeScaleDeployment.md | session report | archived |
| Task.md | session report | archived |
| Play-Service-NPC-Narrator-Thinking-EN.md | session report | archived |
| Play-Service-Runtime.md | session report | archived |
| Play-Service-Runtime-EN.md | session report | archived |
| Play-Service-Task-Routes-EN.md | session report | archived |
| CHANGED_FILES.txt | session artifact | archived |
| CHANGED_FILES_STORY_RUNTIME_EXPERIENCE.txt | session artifact | archived |

---

## Root Runner (Deleted)

| File | Classification | Action |
|------|---------------|--------|
| tests/run_tests.py | forbidden root runner | deleted |

---

## Stub Test Files (Deleted)

| File | Stub Count | Action |
|------|-----------|--------|
| tests/smoke/test_admin_startup.py | 27 assert True | deleted |
| tests/smoke/test_engine_startup.py | 46 assert True | deleted |
| tests/e2e/test_phase6_websocket_continuity.py | 22 stubs | deleted |
| tests/e2e/test_phase7_consequence_filtering.py | 24 stubs | deleted |
| tests/e2e/test_phase8_9_10_final_validation.py | 24 stubs | deleted |

---

## Stub Test Methods (Rewritten)

| File | Method | Old Content | Action |
|------|--------|-------------|--------|
| tests/gates/test_goc_mvp01_mvp02_foundation_gate.py | test_canonical_god_of_carnage_contains_story_truth | assert True | rewritten with YAML validation |
| tests/gates/test_goc_mvp01_mvp02_foundation_gate.py | test_runtime_profile_required_for_solo_starts | assert True | replaced with canonical module check |
| tests/gates/test_goc_mvp01_mvp02_foundation_gate.py | test_foundation_gate_passes | assert True | replaced with real gate test |

---

## Runner Gaps (Fixed)

| Gap | Action |
|-----|--------|
| gates/ not in ALL_SUITE_SEQUENCE | added gates suite to runner |
| story_runtime_core/tests not in ALL_SUITE_SEQUENCE | added story_runtime_core suite to runner |

---

## Legacy Semantic Indicators Searched

The following patterns were searched across all test files and docs:

- visitor (50+ files found, all legitimate negative tests or prohibited actor checks)
- god_of_carnage_solo (found in runtime profile code — correct usage; not in canonical content)
- assert True (found in 8 files — 5 deleted, 3 methods rewritten)
- builtin (found in story_runtime_core — correct usage as runtime profile fallback)
- fallback (found in engine tests — correct usage as degraded path tests)
- legacy (docs ADRs — historical notes, not active guidance)
- stub/placeholder/dummy (found in deleted smoke/e2e files)

---

## Remaining Active Legacy Concerns (Tracked)

| Concern | Location | Status |
|---------|----------|--------|
| test_backend_startup.py has 2 assert True | tests/smoke/ | Retained — other tests in file are real; 2 stubs are minor |
| Root Audit.md at repo root | D:/WorldOfShadows/Audit.md | Untracked file, not in git — monitoring only |
