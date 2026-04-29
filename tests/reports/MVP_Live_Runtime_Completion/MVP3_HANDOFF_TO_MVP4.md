# MVP 3 → MVP 4 Handoff Document

**Date**: 2026-04-29  
**From**: MVP 3 — Live Dramatic Scene Simulator  
**To**: MVP 4 — Observability, Diagnostics, Langfuse, Narrative Gov  
**Status**: Ready for MVP 4 implementation

---

## Executive Summary

MVP 3 has completed the core Live Dramatic Scene Simulator (LDSS) implementation. The LDSS module generates structured scene blocks, enforces NPC agency constraints, validates narrator voice, and provides live-path diagnostics. MVP 4 consumes these outputs and adds the observability layer (Langfuse tracing), operator health panels (Narrative Gov), and administrative overrides for object admission and state delta boundaries.

---

## Contracts Produced by MVP 3

### 1. SceneTurnEnvelopeV2

**Location**: `ai_stack/live_dramatic_scene_simulator.py` (SceneTurnEnvelopeV2 dataclass)

**Contract**:
```python
@dataclass
class SceneTurnEnvelopeV2:
    contract: str  # "scene_turn_envelope.v2"
    story_session_id: str
    run_id: str
    turn_number: int
    visible_scene_output: VisibleSceneOutput  # blocks, metadata, performance hints
    diagnostics: LiveDramaticSceneSimulatorDiagnostics  # live-path proof
```

**Consumed By MVP 4**:
- `SceneTurnEnvelopeV2.diagnostics` — passed to Langfuse for trace assembly and Narrative Gov health panels
- `SceneTurnEnvelopeV2.visible_scene_output.blocks` — rendered in frontend typewriter (MVP 5 receives shape)
- `diagnostics.live_path_status` — determines operator visibility in health panels

**MVP 3 Guarantee**:
- Produced for every God of Carnage solo turn
- Non-empty blocks list (at least one scene block per turn)
- `legacy_blob_used = false` (modern structured output only)
- live-path diagnostics include session/run/turn IDs, hashes, decision counts

---

### 2. SceneBlock

**Location**: `ai_stack/live_dramatic_scene_simulator.py` (SceneBlock dataclass)

**Contract**:
```python
@dataclass
class SceneBlock:
    block_id: str  # UUID for trace reference
    block_type: str  # narrator, actor_line, actor_action, environment_interaction, system_degraded_notice
    content: str  # Rendered text output
    actor_id: str | None  # Who is speaking/acting
    target_actor_id: str | None  # Who is being addressed/acted upon (enables NPC-to-NPC)
    validation_status: str  # valid, invalid_narrator_voice, invalid_affordance, etc.
    intent_label: str | None  # NPC intent summarized for Narrative Gov
```

**Consumed By MVP 4**:
- `block_type` — Narrative Gov categorizes output by type
- `actor_id`, `target_actor_id` — Narrative Gov tracks actor lanes and NPC agency
- `validation_status` — Health panels flag blocks that barely passed validators
- `intent_label` — Narrative Gov displays NPC motivation pressure and summary

**MVP 3 Guarantee**:
- Each block has a unique block_id for trace correlation
- block_type is one of the enumerated values
- validation_status reflects actual validator outcome (not assertion)
- All blocks passed all validators before inclusion in visible_scene_output

---

### 3. LiveDramaticSceneSimulatorDiagnostics

**Location**: `ai_stack/live_dramatic_scene_simulator.py` (LiveDramaticSceneSimulatorDiagnostics dataclass)

**Contract**:
```python
@dataclass
class LiveDramaticSceneSimulatorDiagnostics:
    status: str  # "evidenced_live_path"
    story_session_id: str  # UUID for trace assembly
    run_id: str
    turn_number: int
    input_hash: str  # SHA256(LDSSInput)
    output_hash: str  # SHA256(LDSSOutput)
    decision_count: int  # Count of NPC agency decisions made
    scene_block_count: int  # Count of blocks in visible output
    legacy_blob_used: bool  # false (structured output only)
    trace_scaffold: TraceScaffold  # span names, decision IDs, validator outcomes for Langfuse
    npc_agency_metadata: dict  # Primary/secondary responders, NPC initiatives
    narrator_validation_outcome: dict  # Narrator voice checks performed
    affordance_validation_outcome: dict  # Object admission tier checks
```

**Consumed By MVP 4**:
- `status`, `input_hash`, `output_hash`, `decision_count` — Narrative Gov displays live-path proof
- `story_session_id`, `run_id`, `turn_number` — Langfuse trace parent span references
- `trace_scaffold` — Langfuse uses to assemble real traces (real SDK calls, not mock)
- `npc_agency_metadata` — Narrative Gov displays responder selection and NPC motivation
- `narrator_validation_outcome`, `affordance_validation_outcome` — Narrative Gov health severity indicators

**MVP 3 Guarantee**:
- status = "evidenced_live_path" for all God of Carnage solo turns (never "degraded" in MVP3 context)
- Hashes are deterministic SHA256(serialized input/output)
- decision_count reflects NPC agency decisions, not empty turns
- scene_block_count > 0 for all turns
- legacy_blob_used = false (no fallback to legacy text blob)
- trace_scaffold provides concrete span references (not placeholders)

---

### 4. NPCAgencyPlan

**Location**: `ai_stack/live_dramatic_scene_simulator.py` (NPCAgencyPlan dataclass)

**Contract**:
```python
@dataclass
class NPCAgencyPlan:
    primary_responder_id: str  # NPC who speaks first (or only)
    secondary_responder_ids: list[str]  # Additional NPCs who participate
    npc_initiatives: dict[str, NPCInitiative]  # Per-NPC decision metadata
```

**Consumed By MVP 4**:
- `primary_responder_id` — Narrative Gov displays as active agent
- `secondary_responder_ids` — Narrative Gov tracks multi-NPC participation
- `npc_initiatives` — Narrative Gov extracts motivation summary and intent

**MVP 3 Guarantee**:
- primary_responder_id is never the human actor
- primary_responder_id is never "visitor"
- secondary_responder_ids excludes human actor and visitor
- All responder IDs are valid NPC actor IDs in the current scene

---

### 5. TraceScaffold

**Location**: `ai_stack/live_dramatic_scene_simulator.py` (TraceScaffold dataclass)

**Contract**:
```python
@dataclass
class TraceScaffold:
    spans: list[dict]  # Span names, timestamps, status (for Langfuse real trace assembly)
    decision_ids: list[str]  # Decision references (NPC agency decisions)
    validator_outcomes: list[dict]  # Narrator voice, affordance, state delta checks
    langfuse_enabled: bool  # Configuration flag (default: false, scaffold only; true enables live traces)
```

**Consumed By MVP 4**:
- `spans` — Langfuse parent span metadata for real SDK trace assembly
- `decision_ids` — Links trace back to NPC agency decisions in scene blocks
- `validator_outcomes` — Health panels display validation strictness/edge cases
- `langfuse_enabled` — Toggle switch for live Langfuse tracing (implemented in MVP 4 admin UI)

**MVP 3 Guarantee**:
- Default behavior: JSON scaffold (no live Langfuse SDK calls)
- Scaffold structure matches Langfuse span schema (ready for real trace conversion)
- All validator outcomes recorded (narrator voice, affordance, state delta)
- decision_ids are traceable back to NPC block generation

---

## Actor Lane Context (Consumed from MVP 2)

**Location**: `world-engine/app/runtime/models.py` (ActorLaneContext dataclass)

**Contract**:
```python
@dataclass
class ActorLaneContext:
    human_actor_id: str  # Always protected from AI generation
    ai_allowed_actor_ids: list[str]  # NPCs that AI can control
    ai_forbidden_actor_ids: list[str]  # (Includes human_actor_id)
```

**Used By MVP 3 LDSS**:
- Validates responder candidate set excludes human_actor_id
- Ensures blocks speak/act only for ai_allowed_actor_ids

**MVP 4 Expectation**:
- No changes to actor lane enforcement
- Narrative Gov displays human_actor_id as "protected" (always)
- Health panels flag any block attempting to control human actor (should be zero)

---

## Object Admission Record (Consumed from MVP 2)

**Location**: `world-engine/app/runtime/models.py` (ObjectAdmissionRecord dataclass)

**Contract**:
```python
@dataclass
class ObjectAdmissionRecord:
    object_id: str
    source_kind: str  # "canonical_content", "typical_minor_implied", "similar_allowed"
    admission_reason: str  # Why this object is admitted
    commit_allowed: bool  # Whether state delta can mutate object state
```

**Used By MVP 3 LDSS**:
- Affordance validator enforces admission tier (canonical > typical > similar)
- Environment interaction blocks rejected if object is unadmitted

**MVP 4 Expectations**:
- Admin surface for Object Admission Override (change tier temporarily)
- Narrative Gov displays object provenance (canonical vs typical vs similar)
- Health panels flag "similar_allowed" objects as high-risk affordances

---

## State Delta Boundary (Consumed from MVP 2)

**Location**: `world-engine/app/runtime/models.py` (StateDeltaBoundary dataclass)

**Contract**:
```python
@dataclass
class StateDeltaBoundary:
    protected_paths: list[str]  # State mutations forbidden (e.g., character.age)
    allowed_runtime_paths: list[str]  # Runtime-only state changes allowed
    reject_unknown_paths: bool  # Default true: reject paths not in whitelist
```

**Used By MVP 3 LDSS**:
- State validator enforces protected-path rejection at commit seam
- Blocks that propose forbidden mutations are rejected

**MVP 4 Expectations**:
- Admin surface for State Delta Boundary Override (breakglass unlock)
- Narrative Gov displays protected paths as "read-only" in operator view
- Health panels flag any attempted protected-path mutation with audit trail

---

## Contracts Consumed from Previous MVPs

### MVP 1 Runtime Profile

**Used By MVP 3**:
- Profile provides canonical role set and initial scene configuration
- god_of_carnage_solo profile cannot contain story truth (enforced)
- Role selection from profile determines human_actor_id

**MVP 4 Expectation**:
- No role/profile changes needed
- Narrative Gov displays role ownership and human actor designation

### MVP 2 Actor Lanes

**Used By MVP 3**:
- Actor lane context enforces human actor protection
- Responder candidates validated against ai_allowed_actor_ids
- No AI-generated content for human actor

**MVP 4 Expectation**:
- Health panels display actor lane enforcement strictness
- Flag any blocks that nearly violated actor lane rules

---

## Infrastructure Inherited from Prior MVPs

### Runtime State Provenance

**Location**: `world-engine/app/runtime/models.py` (RuntimeState dataclass)

**Used By MVP 3**:
- Committed state includes story_session_id, run_id, turn_number for trace assembly
- Source hashes for content, profile, runtime modules provide deterministic proof

**MVP 4 Expectation**:
- Narrative Gov uses source hashes to verify scenario configuration
- Trace spans link back to session provenance

### Response Validation Seam

**Location**: `ai_stack/goc_turn_seams.py` (run_validation_seam)

**Used By MVP 3**:
- Actor lane validation before response packaging
- NPC coercion detection before block inclusion

**MVP 4 Expectation**:
- Validation outcomes fed to Narrative Gov for health panels
- Edge cases (barely-passing validators) highlighted in operator view

---

## Deferred to MVP 4 (Contracts Scaffolded)

### Langfuse Tracing Toggle

**Status**: Scaffolded in MVP3, implementation deferred to MVP4

**What MVP 3 Provides**:
- `TraceScaffold` with span structure and decision IDs
- Configuration flag `langfuse_enabled` (default: false)
- JSON scaffold output (no live Langfuse SDK calls)

**What MVP 4 Must Implement**:
- Real Langfuse SDK integration when `langfuse_enabled = true`
- Admin UI toggle to enable/disable live tracing per session
- Trace post-processing to convert scaffold to real Langfuse spans

### Object Admission Override Admin Surface

**Status**: Infrastructure present in MVP2, UI deferred to MVP4

**What MVP 3 Expects**:
- `ObjectAdmissionRecord.source_kind` can be overridden temporarily
- Override reason recorded in diagnostics for audit trail

**What MVP 4 Must Implement**:
- Admin tool UI for selecting object and new admission tier
- Audit trail of overrides with timestamp and operator ID
- Health panel indicator when override is active

### State Delta Boundary Override Admin Surface

**Status**: Infrastructure present in MVP2, UI deferred to MVP4

**What MVP 3 Expects**:
- `StateDeltaBoundary.protected_paths` can be temporarily unlocked (breakglass)
- Override tracked in scene block diagnostics

**What MVP 4 Must Implement**:
- Admin tool UI for breakglass unlock (protected reason field)
- Audit trail of breakglass activations
- Health panel severity indicator when breakglass is active

### Narrative Gov Operator Health Panels

**Status**: Contracts defined, UI fully deferred to MVP4

**What MVP 3 Produces**:
- All diagnostic metadata for health panels
- Actor lane enforcement status
- NPC agency metadata
- Narrator validation strictness indicators
- Affordance tier tracking
- State mutation audit trail

**What MVP 4 Must Implement**:
- Dashboard layout for operator monitoring
- Real-time health status (green/yellow/red)
- Block-level validation details
- NPC motivation summary and pressure visualization
- Actor lane enforcement visualization
- Historical trend views (turn-by-turn diagnostics)

---

## Test Coverage Inherited by MVP 4

### Gate Tests

**Location**: `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py`

**Coverage**:
- 26 MVP3-specific gate tests (all PASS)
- Enforce LDSS invocation, block production, NPC agency, narrator validation
- Must remain passing in MVP 4 (no breaking changes to LDSS contracts)

**MVP 4 Expectations**:
- Add tests for Langfuse trace assembly (scaffold → real traces)
- Add tests for Object Admission Override (tier change verification)
- Add tests for State Delta Boundary Override (breakglass unlock)
- Add tests for Narrative Gov admin surfaces

### Integration Tests

**Location**: `world-engine/tests/test_mvp3_ldss_integration.py`

**Coverage**:
- 6 MVP3 integration tests (all PASS)
- Verify SceneTurnEnvelopeV2 production through HTTP endpoint
- Verify diagnostics and block structure

**MVP 4 Expectations**:
- Extend with tests for Langfuse trace POST to external service
- Extend with tests for override propagation to diagnostics
- Add performance tests for Narrative Gov health panel queries

---

## Code Locations for MVP 4 Integration

### Primary Seams for MVP 4

#### 1. Langfuse Trace Assembly

**Location**: `ai_stack/live_dramatic_scene_simulator.py` (run_ldss function)

**Current Behavior**:
```python
def run_ldss(ldss_input: LDSSInput) -> LDSSOutput:
    # ...
    trace_scaffold = TraceScaffold(
        spans=[...],  # Span structure, no live SDK calls
        decision_ids=[...],
        validator_outcomes=[...],
        langfuse_enabled=False  # Default: JSON scaffold only
    )
    return LDSSOutput(..., trace_scaffold=trace_scaffold)
```

**MVP 4 Implementation Point**:
- Check `trace_scaffold.langfuse_enabled` flag
- If true: convert scaffold to real Langfuse SDK calls
- If false: return scaffold as-is (current MVP 3 behavior)

#### 2. Object Admission Override Hook

**Location**: `ai_stack/validators/affordance_validation.py` (validate_environment_interaction)

**Current Behavior**:
```python
def validate_environment_interaction(interaction, admitted_objects) -> bool:
    # Check object admission tier
    record = admitted_objects.get(interaction.object_id)
    return record.source_kind in ("canonical_content", "typical_minor_implied", "similar_allowed")
```

**MVP 4 Implementation Point**:
- Check for admin override in session context
- If override active: accept object regardless of tier
- Log override to diagnostics for audit trail

#### 3. State Delta Boundary Override Hook

**Location**: `world-engine/app/story_runtime/state_delta.py` (validate_state_delta)

**Current Behavior**:
```python
def validate_state_delta(delta, boundary) -> StateDeltaValidationResult:
    # Reject mutations on protected_paths
    if delta.path in boundary.protected_paths:
        return StateDeltaValidationResult(status="invalid", error_code="protected_path_mutation")
```

**MVP 4 Implementation Point**:
- Check for breakglass override in session context
- If override active: allow protected-path mutation
- Log breakglass activation to diagnostics

#### 4. Narrative Gov Health Query Endpoint

**Location**: To be created in administration-tool

**MVP 4 Task**:
- Create HTTP endpoint that queries `SceneTurnEnvelopeV2` and `LiveDramaticSceneSimulatorDiagnostics` from recent turns
- Assemble health panel data (actor lane status, NPC agency, narrator validation, affordance strictness)
- Return JSON suitable for health dashboard rendering

---

## File Locations Summary

| Component | File | Anchor Symbol | MVP 4 Task |
|-----------|------|---------------|-----------|
| LDSS Module | `ai_stack/live_dramatic_scene_simulator.py` | `run_ldss()` | Implement Langfuse toggle |
| Scene Block | `ai_stack/live_dramatic_scene_simulator.py` | `SceneBlock` dataclass | No changes; consume in health panels |
| Diagnostics | `ai_stack/live_dramatic_scene_simulator.py` | `LiveDramaticSceneSimulatorDiagnostics` | Consume in Narrative Gov queries |
| Trace Scaffold | `ai_stack/live_dramatic_scene_simulator.py` | `TraceScaffold` dataclass | Convert scaffold to real Langfuse traces |
| NPC Agency | `ai_stack/live_dramatic_scene_simulator.py` | `NPCAgencyPlan` dataclass | Display in Narrative Gov UI |
| Affordance Validation | `ai_stack/validators/affordance_validation.py` | `validate_environment_interaction()` | Add override hook |
| State Delta Validation | `world-engine/app/story_runtime/state_delta.py` | `validate_state_delta()` | Add breakglass override hook |
| Runtime Manager | `world-engine/app/story_runtime/manager.py` | `_build_ldss_scene_envelope()` | Pass override context to seams |
| HTTP Response | `world-engine/app/api/http.py` | `ExecuteTurnResponse.scene_turn_envelope` | No changes; verify Langfuse tracing |

---

## Non-Functional Requirements for MVP 4

### Performance

**MVP 3 Baseline**:
- LDSS execution: < 500ms per turn
- Validation (narrator, affordance, state delta): < 200ms combined

**MVP 4 Constraint**:
- Langfuse SDK calls must not block turn response (async trace posting)
- Health panel queries must return < 1s (single session last N turns)

### Logging & Observability

**MVP 3 Baseline**:
- All validator decisions logged to decision_ids in trace scaffold
- NPC agency decisions recorded in npc_agency_metadata

**MVP 4 Requirement**:
- All diagnostics fields must be queryable by session ID and turn number
- Audit trail for overrides (Object Admission, State Delta) must be immutable

### Backward Compatibility

**MVP 3 Contract**:
- `SceneTurnEnvelopeV2` structure is final (no breaking changes)
- `SceneBlock` fields are final
- Diagnostics fields are final

**MVP 4 Constraint**:
- Add fields to contracts only as optional with defaults
- Never remove or rename existing fields
- Maintain JSON schema compatibility

---

## Operational Handoff Checklist

- [x] MVP 3 operational gates PASS (docker-up.py, tests/run_tests.py, GitHub workflows, TOML/tooling)
- [x] All MVP 3 tests pass (5,600+ tests)
- [x] All MVP 3 ADRs ACCEPTED
- [x] Source locator matrix complete (no placeholders)
- [x] Live-path evidence verified (real HTTP turn route)
- [x] Scene block production verified (non-empty blocks)
- [x] NPC agency enforcement verified (responder validation)
- [x] Narrator voice validation verified (no player coercion)
- [x] Affordance and state validation verified (tier enforcement)
- [x] Diagnostics scaffold complete (ready for Langfuse conversion)
- [x] Contracts frozen (no further MVP 3 changes)
- [x] Deferred features documented (Langfuse UI, admin overrides, Narrative Gov)

---

## Next Steps for MVP 4

1. **Week 1: Langfuse Integration**
   - Implement `langfuse_enabled` toggle and real SDK trace assembly
   - Add tests for trace post-processing and external service connectivity
   - Verify trace export and search in Langfuse dashboard

2. **Week 2: Admin Override Surfaces**
   - Implement Object Admission Override UI in administration-tool
   - Implement State Delta Boundary Override (breakglass) UI
   - Add audit trail queries and verification tests

3. **Week 3: Narrative Gov Health Panels**
   - Create health query endpoint in administration-tool
   - Assemble health panel data from recent scene turns
   - Implement operator dashboard (actor lane, NPC agency, validation status)

4. **Week 4: E2E & Handoff**
   - E2E tests through full Langfuse pipeline
   - MVP 5 handoff (frontend typewriter UX consumes SceneBlock structure)
   - Operational gate verification for MVP 4

---

**Status**: ✅ **Ready for MVP 4** — All MVP 3 contracts locked, diagnostics scaffold complete, deferred features documented.
