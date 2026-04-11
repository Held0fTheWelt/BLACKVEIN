# DS-007 / DS-006 / DS-008: Service Control Flow Hardening

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement these 3 waves task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize runtime narrative and service control flows through DTO/protocol extraction (DS-007), large function decomposition (DS-006), and recommendation logic flattening (DS-008).

**Architecture:** 
- **DS-007** (Phase 1, Foundation): Extract DTO/protocol edges in `turn_executor_validated_pipeline.py` and `narrative_threads_update_from_commit.py` before larger service moves. Stabilize seams with smaller units and deferred imports.
- **DS-006** (Phase 2, Orchestration): Shrink largest backend functions: Writers Room packaging/generation stages (~319/160 LOC), inspector assembly (~167 LOC), closure bundles (~155-160 LOC).
- **DS-008** (Phase 3, Business Logic): Flatten improvement recommendation decision path (~158 LOC) by extracting guard/policy evaluators.

**Tech Stack:** Python, pytest, dataclasses (DTO patterns), AST analysis

**Waves Sequence:** DS-007 → DS-006 → DS-008

---

## Wave 1: DS-007 (Runtime Narrative + Validated Pipeline Blocks)

### Phase 1 Overview

**Locations:**
- `backend/app/runtime/turn_executor_validated_pipeline.py` — `run_validated_turn_pipeline` (~155 LOC)
- `backend/app/runtime/narrative_threads_update_from_commit.py` — (~164 LOC)
- Runtime files with deferred-import comments: `turn_executor.py`, `ai_decision.py`, `ai_failure_recovery.py`

**Goal:** Extract DTO/protocol edges and smaller units to stabilize runtime narrative flow and validated pipeline seams before deep service refactors.

**Key Metrics (Current):**
- `turn_executor_validated_pipeline.py:run_validated_turn_pipeline` ~155 LOC
- `narrative_threads_update_from_commit.py` ~164 LOC
- Circular imports mitigated by deferred imports; goal: explicit DTOs to replace deferred-import pattern

### Task Breakdown for DS-007

#### Task 1: Analyze Runtime Narrative Patterns

- [ ] Read `turn_executor_validated_pipeline.py` and identify DTO/protocol boundaries
- [ ] Identify `narrative_threads_update_from_commit.py` control flow and state handoffs
- [ ] Document current deferred-import workarounds (lines with local imports)
- [ ] Create pre-artifact: scope snapshot of narrative flow and current workarounds
- [ ] Commit: `docs: DS-007 pre-artifact scope snapshot for runtime narrative`

#### Task 2: Extract Narrative DTO Module

- [ ] Create `backend/app/runtime/narrative_state_transfer_dto.py` with dataclasses for:
  - `NarrativeCommitEvent` (represents commit update payload)
  - `ThreadUpdateResult` (represents narrative thread update result)
  - Related validation and type-safe interfaces
- [ ] Write tests verifying DTO immutability and field validation
- [ ] Replace direct dict passing in `narrative_threads_update_from_commit.py` with DTO references
- [ ] Run tests; all passing
- [ ] Commit: `feat(DS-007): extract narrative state transfer DTOs`

#### Task 3: Refactor `run_validated_turn_pipeline` Function

- [ ] Extract pipeline decision gates to `pipeline_decision_guards.py` module
  - Extract `_check_decision_validity` → standalone function
  - Extract `_validate_decision_context` → standalone function
- [ ] Reduce `run_validated_turn_pipeline` from ~155 LOC to ~100 LOC
- [ ] Update imports: replace deferred imports with explicit DTO references where possible
- [ ] Run `pytest backend/tests/runtime/test_turn_executor_validated_pipeline.py`; all passing
- [ ] Commit: `refactor(DS-007): extract pipeline decision guards, reduce run_validated_turn_pipeline`

#### Task 4: Stabilize Runtime Narrative Seams

- [ ] Review deferred imports in `turn_executor.py`, `ai_decision.py`, `ai_failure_recovery.py`
- [ ] Replace deferred imports where DTOs now provide clean boundaries
- [ ] Add type hints to narrative functions
- [ ] Document narrative protocol in README or docstring
- [ ] Run full runtime test suite
- [ ] Commit: `refactor(DS-007): stabilize runtime narrative seams with DTOs`

#### Task 5: DS-007 Closure

- [ ] Create post-artifacts: `session_20260412_DS-007_post.md` and `.json`
- [ ] Update `WORKSTREAM_BACKEND_RUNTIME_AND_SERVICES_STATE.md`
- [ ] Update `despaghettification_implementation_input.md`: mark DS-007 closed, update open hotspots
- [ ] Commit: `docs(DS-007): closure artifacts and state update`

**Expected Outcome:** DS-007 complete with narrative DTO module + smaller pipeline guards. ~100 LOC reduction. Runtime seams stabilized for DS-006 orchestration work.

---

## Wave 2: DS-006 (Long Multi-Step Service Orchestration)

### Phase 2 Overview

**Locations:**
- `backend/app/services/writers_room_pipeline_packaging_stage.py` (~319 LOC)
- `backend/app/services/writers_room_pipeline_generation_stage.py` (~160 LOC)
- `backend/app/services/inspector_turn_projection_sections_assembly_filled.py` (~167 LOC)
- `backend/app/services/ai_stack_closure_cockpit_report_assembly.py` / `ai_stack_evidence_session_bundle.py` (~155–160 LOC)

**Goal:** Further stage-sized extractions and helper modules. Keep public seams stable. Shrink largest functions through coherent sub-stage extraction.

**Key Metrics (Current):**
- `writers_room_pipeline_packaging_stage.py` ~319 LOC (largest target)
- `inspector_turn_projection_sections_assembly_filled.py` ~167 LOC
- `writers_room_pipeline_generation_stage.py` ~160 LOC

### Task Breakdown for DS-006

#### Task 1: Analyze Writers Room Packaging Stage

- [ ] Read `writers_room_pipeline_packaging_stage.py` (~319 LOC) and identify natural sub-stages
  - Likely stages: issue extraction → recommendation bundling → review packaging → proposal finalization
- [ ] Create pre-artifact: AST breakdown of packaging stage showing LOC per logical section
- [ ] Identify helper extraction candidates (functions that could move to separate module)
- [ ] Commit: `docs: DS-006 pre-artifact Writers Room packaging analysis`

#### Task 2: Extract Writers Room Packaging Sub-Stages

- [ ] Create `backend/app/services/writers_room_pipeline_packaging_issue_extraction.py`
  - Move issue extraction logic from main packaging stage
- [ ] Create `backend/app/services/writers_room_pipeline_packaging_recommendation_bundling.py`
  - Move recommendation bundling logic
- [ ] Reduce main `writers_room_pipeline_packaging_stage.py` from ~319 to ~150 LOC
- [ ] Update imports and function calls to use sub-stage modules
- [ ] Run `pytest tests/writers_room/ -v`; all passing (expect 64+ tests)
- [ ] Commit: `refactor(DS-006): extract Writers Room packaging sub-stages`

#### Task 3: Extract Inspector Assembly Helpers

- [ ] Analyze `inspector_turn_projection_sections_assembly_filled.py` (~167 LOC)
- [ ] Extract helper module: `backend/app/services/inspector_turn_projection_assembly_helpers.py`
  - Common assembly utilities, validation functions
- [ ] Reduce main file from ~167 to ~120 LOC
- [ ] Run inspector tests; all passing
- [ ] Commit: `refactor(DS-006): extract inspector assembly helpers`

#### Task 4: Analyze Closure Bundle Functions

- [ ] Review `ai_stack_closure_cockpit_report_assembly.py` and `ai_stack_evidence_session_bundle.py` (~155–160 LOC each)
- [ ] Identify extraction opportunities (if time permits in this wave)
- [ ] Document for future DS-009 work
- [ ] Commit: `docs: DS-006 closure bundle analysis for future waves`

#### Task 5: DS-006 Closure

- [ ] Create post-artifacts: `session_20260412_DS-006_post.md` and `.json`
- [ ] Update state documents: mark DS-006 closed, update Writers Room metrics
- [ ] Commit: `docs(DS-006): closure artifacts and state update`

**Expected Outcome:** DS-006 complete. Writers Room packaging reduced from ~319 to ~150 LOC through sub-stage extraction. Inspector assembly reduced ~167 to ~120 LOC. Public API stable; tests green (64+).

---

## Wave 3: DS-008 (Improvement Recommendation Decision Flattening)

### Phase 3 Overview

**Locations:**
- `backend/app/services/improvement_service_recommendation_decision.py` (~158 LOC)
- `backend/app/api/v1/improvement_routes.py` (calling sites)

**Goal:** Flatten improvement recommendation decision path by extracting policy/guard evaluators. Preserve API contracts. Reduce branch complexity.

**Key Metrics (Current):**
- `improvement_service_recommendation_decision.py` ~158 LOC
- High branch count / nested control flow
- Multiple decision gates in single function

### Task Breakdown for DS-008

#### Task 1: Analyze Improvement Decision Logic

- [ ] Read `improvement_service_recommendation_decision.py` (~158 LOC)
- [ ] Identify decision gates and policy checks (e.g., user permission checks, context validation, scoring logic)
- [ ] Create pre-artifact: decision flow diagram + LOC breakdown by gate
- [ ] Estimate extraction target: goal ~100 LOC main function
- [ ] Commit: `docs: DS-008 pre-artifact improvement decision analysis`

#### Task 2: Extract Improvement Policy Evaluators

- [ ] Create `backend/app/services/improvement_service_policy_evaluators.py`
  - `evaluate_user_recommendation_permission(user, improvement)` → bool
  - `evaluate_improvement_context_validity(improvement, commit)` → bool
  - `evaluate_recommendation_eligibility(recommendation, filters)` → bool
- [ ] Add dataclass for `ImprovementRecommendationPolicy` (configurable evaluation rules)
- [ ] Write tests for policy evaluators
- [ ] Commit: `feat(DS-008): extract improvement policy evaluators`

#### Task 3: Refactor Main Decision Function

- [ ] In `improvement_service_recommendation_decision.py`, replace nested policy checks with guard function calls
- [ ] Reduce function LOC from ~158 to ~110 LOC (target: 30% reduction)
- [ ] Improve readability: main flow becomes guard checks + decision application
- [ ] Run improvement service tests; all passing
- [ ] Commit: `refactor(DS-008): flatten improvement decision with policy guards`

#### Task 4: Verify Backwards Compatibility

- [ ] Check all call sites in `improvement_routes.py` and related services
- [ ] Verify API contract unchanged (function signature, return types, behavior)
- [ ] Run full improvement test suite (estimate 30+ tests)
- [ ] Commit: `test(DS-008): verify backwards compatibility and API contracts`

#### Task 5: DS-008 Closure

- [ ] Create post-artifacts: `session_20260412_DS-008_post.md` and `.json`
- [ ] Update state documents: mark DS-008 closed
- [ ] Commit: `docs(DS-008): closure artifacts and state update`

**Expected Outcome:** DS-008 complete. Improvement decision reduced from ~158 to ~110 LOC. Policy logic extracted to reusable module. Branch complexity flattened. All 30+ tests passing.

---

## Summary: DS-007 / DS-006 / DS-008

| Wave | Primary Target | Current LOC | Target LOC | Reduction | Status |
|------|---|---|---|---|---|
| DS-007 | Runtime narrative + validated pipeline | 155 + 164 = 319 | ~250 | ~21% | 5 tasks |
| DS-006 | Writers Room + inspector orchestration | 319 + 160 + 167 = 646 | ~400 | ~38% | 5 tasks |
| DS-008 | Improvement recommendation decision | 158 | ~110 | ~30% | 5 tasks |
| **Total** | **Service control flow hardening** | **~1123** | **~760** | **~32%** | **15 tasks** |

---

## Execution Notes

- **Subagent-driven recommended**: 3 waves × 5 tasks = 15 independent implementation tasks. Fresh subagent per task with 2-stage reviews (spec → quality) ensures quality at scale.
- **Test gates per wave**: Each wave runs full service/route test suite before closure (expect 60+ tests passing per wave).
- **Backwards compatibility critical**: DS-008 and DS-006 are public service APIs; verify no signature changes.
- **DTO pattern for DS-007**: Extract data transfer objects to replace deferred-import workarounds; explicit over implicit.

---

## Execution Choice

Plan complete. **Two execution options:**

1. **Subagent-Driven (recommended)** — Fresh subagent per task, spec + code quality reviews, fast parallel iteration
2. **Inline Execution** — Execute tasks in this session with checkpoints

Which approach?
