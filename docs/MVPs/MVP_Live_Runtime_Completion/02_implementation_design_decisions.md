# MVP 2 — Implementation Design Decisions

**Date**: 2026-04-29  
**Status**: LOCKED (Grilling session complete, ready for implementation)  
**From**: MVP 2 Grill-Me Session  
**Ref**: `02_runtime_state_actor_lanes_content_boundary.md`

---

## 1. MVP 1 Handoff — Input Contract Verification

**Decision**: MVP 1 handoff is complete and ready for MVP 2 consumption.

**Evidence**:
- ✅ `tests/reports/MVP_Live_Runtime_Completion/MVP1_HANDOFF_RUNTIME_PROFILE.md` exists (dated 2026-04-29)
- ✅ All 6 required ADRs exist and are ACCEPTED
- ✅ All MVP 1 operational gates PASS
- ✅ CreateRunResponse includes: `human_actor_id`, `npc_actor_ids`, `actor_lanes` (seeded), `visitor_present=false`

**Input guarantees MVP 2 can rely on**:
- Normalized RuntimeProfile with no story truth
- RoleSlugActorIdMap resolving canonical actor IDs
- CreateRunResponse seeding actor lanes before MVP 2 bootstrap
- `visitor` proven absent from all outputs

**Implication**: MVP 2 bootstrap can consume `build_actor_ownership()` output directly without rediscovery.

---

## 2. Actor-Lane Validator Seams — Defense in Depth

**Decision**: Implement actor-lane validation at **both seams** (early + late rejection).

**Seam 1: Early Validation (Langgraph node level)**
- `ActorLaneContext` threaded through Langgraph nodes
- Validation fires **before** output is written to turn memory
- Human-actor lines/actions rejected before memory pollution
- Requires: Langgraph node signature changes to accept `actor_lane_context` parameter

**Seam 2: Late Validation (Response packaging seam)**
- `run_validation_seam()` in `ai_stack/story_runtime/turn/god_of_carnage_turn_seams.py` scans structured output
- Validation fires **before** response packaging and **before** commit
- Catches any violations that escape early seam
- Requires: `actor_lane_context` dict parameter to `run_validation_seam()`

**Enforcement Order**:
```
RuntimeBootstrap 
  → ActorLaneContext assembly (from MVP1 CreateRunResponse)
  → AI candidate generation
  → Early Seam: Actor-lane validation in langgraph node
  → AI generation completes
  → Late Seam: run_validation_seam() scans output
  → Response packaging
  → Commit seam
```

**Error Code**: `ai_controlled_human_actor` (human actor in any forbidden block type)

**Rationale**: Defense in depth reduces risk of forbidden output polluting turn history or reaching render layer.

---

## 3. Object Admission Override Strategy

**Decision**: **Default A (Code-Based Rules) + Admin-Switch for Operator Override (Option B)**

### Default Behavior (Always Active)
- Validator uses hardcoded `VALID_SOURCE_KINDS` rules in code
- `canonical_content` → always admitted, commit_allowed=True
- `typical_minor_implied` → admitted as temporary, commit_allowed=False
- `similar_allowed` → admitted as temporary, requires similarity_reason, commit_allowed=False
- Dangerous/major objects without canonical backing → always rejected

### Operator Override (Admin-Switch in Runtime Settings)
- **When**: Operator encounters a legitimate admission edge case
- **How**: Runtime Settings Panel → Object Admission Overrides section → enable single-object override
- **Scope**: Per-turn, per-object, with audit trail (operator ID + timestamp + reason)
- **Validation**: Override still requires source_kind + admission_reason; cannot bypass structure

### Implementation
- Backend: Extend `ObjectAdmissionRecord` with `override_applied` and `override_reason` fields
- API: `PATCH /api/v1/admin/ai/object-admission-overrides` stores operator decision
- Turn-Seam: Check `object_admission_overrides` dict before rejecting
- Admin UI: Toggle switch for each problematic object (populated from turn diagnostics)

---

## 4. State Delta Boundary Granularity + Configurability

**Decision**: **Option B (Granular Paths) + Admin-Tool Configuration**

### Protected Paths (Always Enforced)
```python
protected_paths = [
    "canonical_scene_order",
    "canonical_characters",
    "canonical_relationships",
    "canonical_content_truth",
    "canonical_props",
    "canonical_endings",
    "content_module_id",
    "selected_player_role",
    "human_actor_id",
    "actor_lanes",
]
```

### Allowed Runtime Paths (Granular, with Sub-Path Precision)
```python
allowed_runtime_paths = [
    "runtime_flags",
    "turn_memory",
    "scene_pressure",
    "admitted_objects",
    "relationship_runtime_pressure",
]
```

### Granular Enforcement Example
- ✅ `relationship_runtime_pressure.annette_alain = 0.7` (subpath allowed)
- ✅ `relationship_runtime_pressure.annette_alain += 0.1` (increment within bounds)
- ❌ `relationship_runtime_pressure.annette_alain = 1.5` (exceeds max)
- ❌ `canonical_scene_order` mutation (protected root)

### Admin Configuration (in Runtime Settings)
- **Operator can adjust allowed_runtime_paths** for specific sessions
- **Operator can set bounds** on numeric fields (e.g., max +0.1 per turn for pressure)
- **Operator can set reject_unknown_paths behavior** (default: True, can disable for debug)
- **All changes logged** with operator ID + reason

### Implementation
- Backend: Extend `StateDeltaBoundary` with operator overrides
- API: `PATCH /api/v1/admin/ai/state-delta-boundary` updates boundary config
- Commit-Seam: `run_commit_seam(..., state_delta_boundary=boundary_dict)` uses configured boundary
- Admin UI: Bounded controls (sliders for numeric limits, toggle for reject_unknown_paths)

---

## 5. MVP 3 Handoff Gate — Integration Testing During MVP 2

**Decision**: **Option B — MVP 3 writes integration tests against MVP 2 output *while MVP 2 is being implemented***

### Timeline Coordination
- **MVP 2 Weeks 1–2**: Core patches P01–P06 reach "testable" state (handoff contracts defined)
- **MVP 3 Week 1**: Starts writing integration tests against MVP 2 output contract
  - Reads `RuntimeState`, `ActorLaneContext`, `ObjectAdmissionRecord`, `StateDeltaBoundary` from MVP 2
  - Validates that these inputs enable LDSS behavior
  - Reports feedback to MVP 2 team if contracts are insufficient
- **MVP 2 Weeks 3–4**: Operational wiring, admin UI refinement
- **MVP 3 Weeks 2–4**: Full LDSS implementation
- **Handoff Gate**: MVP 2 is "ready for MVP 3" when **both**:
  1. All MVP 2 tests pass (P01–P07)
  2. MVP 3 integration tests pass (reads MVP 2 output, proves it works for LDSS)

### Failure Handling
- If MVP 3 finds a problem with MVP 2 output structure:
  - Report as bug in MVP 2
  - MVP 2 fixes and re-releases
  - MVP 3 waits
- No rollback — MVP 2 commitment is final once merged

---

## 6. Test Coverage Reporting — Patch-Level Transparency

**Decision**: **Option C (Explicit Patch-Coverage Report) + tests/run_tests.py as Canonical**

### Patch Coverage Report Format
```
# MVP 2 Patch Coverage Report

| Patch | Required Tests | Status | Test Count | All Pass |
|-------|---|---|---|---|
| P01: Runtime State Provenance | test_runtime_state_contains_source_provenance, test_story_session_state_persists_role_ownership | PASS | 2 | ✅ |
| P02: Actor-Lane Validator | test_ai_cannot_speak_for_human_actor, test_ai_cannot_act_for_human_actor, test_human_actor_cannot_be_primary_responder, test_actor_lane_validation_runs_before_response_packaging | PASS | 4 | ✅ |
| P03: NPC Coercion Classifier | test_npc_action_cannot_force_human_response | PASS | 1 | ✅ |
| P04: Runtime/Content Boundary | test_profile_contains_no_story_truth, test_runtime_module_contains_no_goc_story_truth | PASS | 2 | ✅ |
| P05: Object Admission | test_environment_object_admission_requires_source_kind, test_rejects_unadmitted_plausible_object | PASS | 2 | ✅ |
| P06: State Delta Boundary | test_environment_delta_cannot_mutate_protected_truth, test_commit_seam_rejects_protected_state_mutation | PASS | 2 | ✅ |
| P07: Operational Wiring | tests/run_tests.py --suite mvp2 includes all above | PASS | operational check | ✅ |

**Total**: 15 required tests, all PASS

**Canonical Runner**: `python tests/run_tests.py --suite mvp2`
```

### Registration in tests/run_tests.py
- All MVP 2 tests must be registered in `--suite mvp2`
- `--mvp2` preset must include `--suite mvp2`
- No alternate test runners; `tests/run_tests.py` is canonical

### Gate Failure Condition
- If any required test fails → MVP 2 is incomplete
- If any patch has zero tests → MVP 2 is incomplete (code without proof)
- If tests not in `tests/run_tests.py` → MVP 2 is incomplete (tooling gate)

---

## 7. Patch Implementation Sequencing — Parallelization Strategy

**Decision**: **Option B with 4-phase sequencing (respect dependencies, maximize parallel execution)**

### Phase 1: Parallel (Weeks 1–1.5)
- **P01: Runtime State Provenance** (models.py, manager.py)
  - Define `RuntimeState`, `StorySessionState` dataclasses
  - Implement `_bootstrap_instance()` with source hashes
  - Tests: 2 (source provenance, role ownership)
- **P04: Runtime/Content Boundary** (profiles.py)
  - Validate profile contains no story truth
  - Validate runtime module contains no story truth
  - Tests: 2 (independent of P01–P03)

**Rationale**: P04 is completely independent. P01 is the foundation for P02 and P06.

### Phase 2: Sequential (after P01, Week 1.5–2)
- **P02: Actor-Lane Validator** (actor_lane.py, models.py, god_of_carnage_turn_seams.py)
  - Define `ActorLaneContext`, `ActorLaneValidationResult`
  - Implement `validate_actor_lane_output()`, `validate_responder_plan()`
  - Thread `actor_lane_context` through `run_validation_seam()`
  - Both seams (early + late)
  - Tests: 4

**Rationale**: Depends on P01 (RuntimeState structure and human_actor_id field).

### Phase 3: Parallel (after P02, Week 2–3)
- **P03: NPC Coercion Classifier** (actor_lane.py)
  - Implement `validate_npc_action_coercion()`
  - Define `_COERCIVE_ACTION_TYPES`, `_ALLOWED_PRESSURE_VERBS`
  - Tests: 1 (main), plus integration tests
- **P05: Object Admission** (object_admission.py, models.py)
  - Implement `admit_object()`, `validate_object_admission()`
  - Define `ObjectAdmissionRecord`, `VALID_SOURCE_KINDS`
  - Tests: 2+
- **P06: State Delta Boundary** (state_delta.py, models.py, god_of_carnage_turn_seams.py)
  - Implement `validate_state_delta()`, `validate_state_deltas()`
  - Define `StateDeltaBoundary`, granular path enforcement
  - Thread boundary through `run_commit_seam()`
  - Tests: 2+

**Rationale**: P03 and P05 depend on P02 (actor lane infrastructure). P06 depends on P01 (state model). P03, P05, P06 are independent of each other.

### Phase 4: Sequential (after Phase 3, Week 3–4)
- **P07: Operational Wiring** (tests/run_tests.py, CI, TOML, docker-up.py)
  - Register all MVP 2 tests in `--suite mvp2` and `--mvp2` preset
  - Update GitHub workflows to include MVP 2 suites
  - Update pyproject.toml testpaths
  - Verify docker-up.py still works
  - Tests: operational checks (no new behavior tests)

**Rationale**: P07 depends on all code being written. It cannot run before.

---

## 8. Narrative Gov Admin UI — Location and Design Pattern

**Decision**: **Full UI in MVP 2, integrated into Runtime Settings Panel (Option A)**

### Location
- **Template**: `administration-tool/templates/manage/runtime_settings.html`
- **JS**: `administration-tool/static/manage_runtime_settings.js`
- **CSS**: Existing `manage.css` (no new stylesheet)
- **API Endpoints**:
  - `PATCH /api/v1/admin/ai/object-admission-overrides`
  - `PATCH /api/v1/admin/ai/state-delta-boundary`

### Design Pattern (Follow Existing manage_runtime_settings.js)
```javascript
// Pattern from existing code:
function loadModes() {
  return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/runtime/modes")
    .then(function (res) {
      setValue("manage-rs-generation-mode", res.generation_execution_mode);
      // ...
    });
}

function saveAdvancedSettings() {
  var payload = collectAdvancedPayload();
  return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/advanced-settings", {
    method: "PATCH",
    body: JSON.stringify(payload)
  }).then(refreshAll);
}
```

### New Sections in Runtime Settings
#### Section 1: Object Admission Overrides
```html
<div id="manage-rs-object-admission-panel">
  <h3>Object Admission Overrides</h3>
  <p>Default: Admit canonical, typical-minor, similar_allowed only</p>
  <button id="manage-rs-oa-refresh">Load Recent Rejections</button>
  <table>
    <tr><th>Object ID</th><th>Rejection Reason</th><th>Override</th></tr>
    <!-- Populated by JS from turn diagnostics -->
  </table>
  <button id="manage-rs-oa-save">Save Overrides</button>
</div>
```

#### Section 2: State Delta Boundary Configuration
```html
<div id="manage-rs-state-delta-panel">
  <h3>State Delta Boundary Configuration</h3>
  <p>Protected paths: canonical_* always enforced</p>
  <label>Reject unknown paths: <input type="checkbox" id="manage-rs-sdb-reject-unknown"></label>
  <label>Max pressure change per turn: <input type="number" id="manage-rs-sdb-max-pressure" min="0" max="1" step="0.1"></label>
  <button id="manage-rs-sdb-save">Save Configuration</button>
  <button id="manage-rs-sdb-reset">Reset to Defaults</button>
</div>
```

### JS Functions (Add to manage_runtime_settings.js)
```javascript
function loadObjectAdmissionOverrides() {
  // Fetch recent rejections from turn diagnostics
  // Populate table with toggles for override
}

function saveObjectAdmissionOverrides() {
  var overrides = {};
  // Collect checked objects
  return apiFetch("/api/v1/admin/ai/object-admission-overrides", {
    method: "PATCH",
    body: JSON.stringify(overrides)
  }).then(refreshAll);
}

function loadStateDeltaBoundary() {
  // Fetch current boundary config
  // Populate form fields
}

function saveStateDeltaBoundary() {
  var config = {
    reject_unknown_paths: document.getElementById("manage-rs-sdb-reject-unknown").checked,
    max_pressure_delta: parseFloat(document.getElementById("manage-rs-sdb-max-pressure").value)
  };
  return apiFetch("/api/v1/admin/ai/state-delta-boundary", {
    method: "PATCH",
    body: JSON.stringify(config)
  }).then(refreshAll);
}
```

### Backend API Implementation
- Extend existing `/api/v1/admin/ai/advanced-settings` infrastructure
- Store overrides in session-scoped config (not persisted across sessions by default)
- Include override_applied + override_reason in diagnostics envelope for audit
- Operators can view override history in inspector workbench

---

## 9. Implementation Readiness Checklist

**Pre-Implementation Verification**:

- [ ] MVP 1 handoff verified (MVP1_HANDOFF_RUNTIME_PROFILE.md readable, contracts match)
- [ ] Source Locator Matrix filled for all 7 patches
- [ ] All required ADR files created in `docs/ADR/MVP_Live_Runtime_Completion/`
- [ ] Langgraph node signatures surveyed (understand where to thread actor_lane_context)
- [ ] `run_validation_seam()` and `run_commit_seam()` signatures understood
- [ ] Object admission danger list defined (`_is_dangerous_or_major()` rules)
- [ ] State delta protected path list finalized with team
- [ ] Runtime Settings template and JS patterns reviewed
- [ ] Team has admin auth / feature gate (`FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE`) access

**Critical File Dependencies**:
- `world-engine/app/runtime/models.py` — must update to add P01–P06 dataclasses
- `world-engine/app/runtime/actor_lane.py` — must create or update for P02/P03
- `world-engine/app/runtime/object_admission.py` — must create or update for P05
- `world-engine/app/runtime/state_delta.py` — must create or update for P06
- `ai_stack/story_runtime/turn/god_of_carnage_turn_seams.py` — must update P02 and P06 seams
- `administration-tool/templates/manage/runtime_settings.html` — new sections for P05/P06 admin
- `administration-tool/static/manage_runtime_settings.js` — new functions for P05/P06 admin
- `tests/run_tests.py` — must register all MVP 2 tests under `--suite mvp2`

---

## References

- **MVP 2 Spec**: `02_runtime_state_actor_lanes_content_boundary.md`
- **MVP 1 Handoff**: `tests/reports/MVP_Live_Runtime_Completion/MVP1_HANDOFF_RUNTIME_PROFILE.md`
- **ADR-004 (Actor-Lane)**: `docs/ADR/MVP_Live_Runtime_Completion/adr-mvp2-004-actor-lane-enforcement.md`
- **ADR-003 (NPC Coercion)**: `docs/ADR/MVP_Live_Runtime_Completion/adr-mvp2-003-npc-coercion-state-delta.md`
- **Admin Tool Patterns**: `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/05_admin_tool_governance_surface.md`

---

**Status**: LOCKED — ready for implementation
