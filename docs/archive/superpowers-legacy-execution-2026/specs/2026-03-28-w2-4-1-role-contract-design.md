# W2.4.1: Canonical Internal AI Role Contract Design

**Goal:** Define a canonical structured output contract for three internal logical roles (interpreter, director, responder) operating inside a single AI call, ensuring clear role separation, preventing scope blur, and maintaining authority of the existing validated runtime path.

**Architecture:** Single top-level `AIRoleContract` Pydantic model with three explicitly typed nested sections. Responder output is pre-normalized and fed into the existing canonical proposal/delta path.

**Tech Stack:** Python 3.10+, Pydantic v2, existing runtime structures (ProposedStateDelta, SessionState, GuardOutcome).

---

## 1. Role Definitions and Responsibilities

### 1.1 Interpreter (Diagnostic / Scene Reading)

**Purpose:** Interpret the current scene, identify tensions, detect potential triggers. Non-executive; remains diagnostic.

**Responsibilities:**
- Scene reading and narrative interpretation
- Identification of interpersonal/situational tensions
- Detection of trigger candidates from the scene
- Marking uncertainty where interpretation is ambiguous

**What it is NOT:**
- Does not propose state mutations
- Does not decide which triggers are active
- Does not frame conflict direction
- Does not emit executable proposals

**Example output:**
```
scene_reading: "Alice and Bob face off in the courtyard. Alice's jaw is clenched,
               suggesting suppressed anger. Bob stands closer than usual,
               signaling escalated confidence."
detected_tensions: ["power_imbalance_shifting", "suppressed_anger", "boundary_violation"]
trigger_candidates: ["jealousy_spike", "power_reversal", "intimate_distance_violation"]
uncertainty_markers: ["unclear_if_alice_noticed_bobs_advance", "ambiguous_backstory_reference"]
```

---

### 1.2 Director (Diagnostic / Conflict Steering)

**Purpose:** Frame the intended narrative direction and conflict movement. Non-executive; remains diagnostic and steering.

**Responsibilities:**
- Narrative rationale for conflict direction
- Recommend escalation, stabilization, alliance shifts, or new factors
- Describe pressure movement (where conflict pressure should shift)
- Provide dramaturgic intent

**What it is NOT:**
- Does not emit executable proposals
- Does not decide state mutations
- Does not generate dialogue or actions
- Does not collapse into generic narration

**Example output:**
```
conflict_steering: "Alice's suppressed anger needs release. A direct confrontation
                   would clarify the power dynamic, but could destabilize the group."
escalation_level: 6  # moderate escalation
recommended_direction: "escalate"
pressure_movement: "shift pressure from Bob (who's gaining ground) to Alice (who's losing composure)"
```

---

### 1.3 Responder (Runtime-Relevant / Feeds Normalization)

**Purpose:** Emit concrete response impulses and structured proposals that will be normalized into canonical runtime mutations. The only role allowed to propose state changes.

**Responsibilities:**
- Emit response impulses (behavioral/emotional urges)
- Propose state changes in pre-delta format (not yet ProposedStateDelta)
- Assert which triggers should be active
- Suggest dialogue or scene transitions
- Provide rationale for each proposal

**What it is NOT:**
- Does not emit final ProposedStateDelta objects
- Does not directly execute state mutations
- Does not bypass the existing guard/validation path
- Does not assert triggers without normalization

**Example output:**
```
response_impulses:
  - character_id: "alice"
    impulse_type: "emotional_reaction"
    intensity: 8
    rationale: "Alice's suppressed anger reaches critical level"

  - character_id: "bob"
    impulse_type: "action_urge"
    intensity: 5
    rationale: "Bob senses escalation and prepares retreat"

state_change_candidates:
  - target_path: "characters.alice.emotional_state"
    proposed_value: "angry"
    rationale: "Suppressed anger can no longer be contained"

  - target_path: "characters.bob.confidence_level"
    proposed_value: -3
    rationale: "Bob's confidence erodes as Alice's intensity increases"

trigger_assertions: ["jealousy_spike", "power_reversal"]

scene_transition_candidate: null  # Scene continues; no transition needed

dialogue_impulses:
  - "Alice: You think you can just dismiss me?"
  - "Bob: Alice, I didn't mean—"
```

---

## 2. Data Model: AIRoleContract

### 2.1 InterpreterSection

```python
class InterpreterSection(BaseModel):
    """Scene reading and interpretation (diagnostic only)."""

    scene_reading: str
        # Narrative description of what's happening in the scene.
        # Includes observed tensions, body language, spatial context.

    detected_tensions: list[str]
        # List of interpersonal/situational tensions identified.
        # Examples: "power_imbalance", "unspoken_resentment", "boundary_violation"

    trigger_candidates: list[str]
        # List of potential triggers the scene could activate.
        # Examples: "memory_of_betrayal", "jealousy_spike", "alliance_shift"

    uncertainty_markers: list[str] | None = Field(default=None)
        # Optional: Places where interpretation is ambiguous.
        # Helps runtime understand interpreter confidence.
        # Examples: "unclear_motivation", "ambiguous_backstory", "unknown_emotional_state"
```

---

### 2.2 DirectorSection

```python
class DirectorSection(BaseModel):
    """Conflict steering and narrative direction (diagnostic only)."""

    conflict_steering: str
        # Narrative rationale for the chosen direction.
        # Plain text explanation of why conflict should move this way.

    escalation_level: int = Field(ge=0, le=10)
        # 0-10 scale: how much should conflict intensity change?
        # 0 = de-escalate, 5 = neutral, 10 = maximum escalation.

    recommended_direction: Literal["escalate", "stabilize", "shift_alliance", "redirect", "hold"]
        # Enum: type of narrative movement (bounded set, not free text).

    pressure_movement: str | None = Field(default=None)
        # Optional: specific description of where conflict pressure shifts.
        # Examples: "shift from A→B", "relieve pressure on C", "distribute evenly"
```

---

### 2.3 ResponderSection and Supporting Models

```python
class ResponseImpulse(BaseModel):
    """A concrete behavioral or emotional impulse from responder."""

    character_id: str
        # Character experiencing the impulse

    impulse_type: Literal["emotional_reaction", "dialogue_urge", "action_urge"]
        # Category of impulse (enumerated, not free text)

    intensity: int = Field(ge=0, le=10)
        # 0-10 scale: how strong is the impulse?

    rationale: str
        # Why this character has this impulse in this moment


class StateChangeCandidate(BaseModel):
    """A pre-delta proposal for state mutation from responder."""

    target_path: str
        # Path to the state field (e.g., "characters.alice.emotional_state")
        # NOT yet ProposedStateDelta; will be normalized

    proposed_value: Any
        # New value for the target (any type allowed at this stage)

    rationale: str
        # Why this state change is proposed


class ResponderSection(BaseModel):
    """Runtime-relevant proposals (feeds normalization)."""

    response_impulses: list[ResponseImpulse] = Field(default_factory=list)
        # Concrete behavioral/emotional impulses before execution.
        # Typed as ResponseImpulse, not dict.

    state_change_candidates: list[StateChangeCandidate] = Field(default_factory=list)
        # Pre-delta format proposals for state mutations.
        # Typed as StateChangeCandidate, not dict.
        # Will be normalized to ProposedStateDelta in W2.4.2.

    dialogue_impulses: list[str] | None = Field(default=None)
        # Suggested dialogue lines or dialogue directions.
        # Diagnostic; not directly executed; helps narrative logging.

    trigger_assertions: list[str] = Field(default_factory=list)
        # Triggers the responder asserts should be activated.
        # Will be normalized and validated before runtime assertion.

    scene_transition_candidate: str | None = Field(default=None)
        # If responder proposes scene change, candidate scene_id.
        # Will be validated against legal transitions before execution.
```

---

### 2.4 AIRoleContract (Top Level)

```python
class AIRoleContract(BaseModel):
    """Canonical structured output contract for AI roles.

    All three roles are required; prevents silent failures or role omission.
    Interpreter and Director remain non-executive (diagnostic).
    Only Responder emits runtime-relevant candidates (pre-normalized).
    """

    interpreter: InterpreterSection
    director: DirectorSection
    responder: ResponderSection

    class Config:
        json_schema_extra = {
            "example": {
                "interpreter": {...},
                "director": {...},
                "responder": {...}
            }
        }
```

---

## 3. Integration with Existing Runtime

### 3.1 AdapterResponse Integration

The AIRoleContract lives inside `AdapterResponse.structured_payload`:

```python
# In ai_adapter.py (existing)
class AdapterResponse(BaseModel):
    raw_output: str
    structured_payload: dict[str, Any] | None = None  # Can contain serialized AIRoleContract
    backend_metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    is_error: bool = False
```

**W2.4.2 work** (not this phase): Add parsing logic to deserialize `structured_payload` into AIRoleContract.

### 3.2 Normalization Path (W2.4.2)

After parsing, the runtime normalizes responder output into existing canonical structures:

```python
# Pseudocode (W2.4.2 implementation)
def normalize_responder_to_proposals(role_contract: AIRoleContract) -> dict:
    """Convert responder impulses (typed objects) into canonical runtime proposal structures."""

    normalized = {
        "detected_triggers": role_contract.responder.trigger_assertions,
        "proposed_deltas": [
            ProposedStateDelta(
                target=candidate.target_path,
                next_value=candidate.proposed_value
            )
            for candidate in role_contract.responder.state_change_candidates
            # Note: candidate is StateChangeCandidate (typed object), not dict
        ],
        "proposed_scene_id": role_contract.responder.scene_transition_candidate,
        # narrative_text built from dialogue_impulses (if needed)
    }

    # Pass to existing guard → validation → mutation path
    return normalized
```

**Critical principle:** Role contract is **input to** the canonical runtime path, not a replacement. All proposals go through existing guards.

### 3.3 Diagnostics and Logging

Both Interpreter and Director output remains available for:
- Runtime diagnostics and debugging
- Replay/audit logging
- Future decision tracing
- Conflict analysis without executing proposals

---

## 4. Responsibility Boundaries (Preventing Role Blur)

### 4.0 Canonical Contract Rules (Enforceable)

These are hard boundaries, not guidelines. Enforced at type-system level and in tests.

**Interpreter Rule:**
```
interpreter = diagnostic only

Interpreter output must NOT contain:
- state mutations or proposals
- trigger assertions (only candidates)
- executable proposals
- role collapse into raw observations
```

**Director Rule:**
```
director = diagnostic/steering only

Director output must NOT contain:
- state mutations or proposals
- dialogue generation or action frames
- trigger assertions
- role collapse into generic narration
```

**Responder Rule:**
```
responder = may emit runtime-relevant candidates

Responder output must:
- use pre-delta format (StateChangeCandidate), not ProposedStateDelta
- emit ResponseImpulse objects (typed, not dict)
- propose triggers as plain strings (trigger_assertions)
- propose scene transitions as candidate IDs
- remain pre-normalized (normalization happens in W2.4.2)

Responder output must NOT:
- directly mutate state (proposals must be normalized first)
- bypass guard/validation (all go through existing path)
- assert triggers without normalization
- emit ProposedStateDelta directly
- ignore existing mutation authorization
```

**Runtime Rule:**
```
only normalized responder-derived proposals may enter the canonical guarded runtime path

- Interpreter and Director outputs are diagnostic only
- They do not authorize state mutations
- All responder candidates must undergo normalization before guard evaluation
- Existing guard/validation path remains authoritative
```

---

### 4.1 Interpreter Cannot

- ✗ Decide state mutations
- ✗ Assert final triggers (only candidates)
- ✗ Frame conflict direction
- ✗ Emit executable proposals
- ✗ Collapse into raw observations

### 4.2 Director Cannot

- ✗ Emit executable proposals
- ✗ Generate dialogue or actions
- ✗ Decide state mutations
- ✗ Assert trigger activation
- ✗ Collapse into generic narration

### 4.3 Responder Cannot

- ✗ Directly mutate state (proposals must be normalized first)
- ✗ Bypass guard/validation (all proposals go through existing path)
- ✗ Assert triggers without normalization
- ✗ Emit ProposedStateDelta directly (must use pre-delta format)
- ✗ Ignore existing mutation authorization

---

## 5. Files to Create/Modify

### 5.1 New Files

- **`backend/app/runtime/role_contract.py`** (new)
  - ResponseImpulse and StateChangeCandidate (typed candidate models)
  - InterpreterSection, DirectorSection, ResponderSection (role models)
  - AIRoleContract (top-level contract)
  - Example instances for documentation

- **`backend/tests/runtime/test_w2_4_1_role_contract.py`** (new)
  - Validation tests for each role section
  - Contract integrity tests
  - Serialization/deserialization tests
  - Role distinctness verification
  - Scope boundaries verification

### 5.2 Modified Files

- **`backend/app/runtime/ai_adapter.py`** (minimal change)
  - Add comment linking AdapterResponse.structured_payload to AIRoleContract
  - No code changes (normalization happens in W2.4.2)

---

## 6. Testing Strategy

### 6.1 Unit Tests (test_w2_4_1_role_contract.py)

**Test Group 1: Role Contract Validation**
- Valid AIRoleContract with all three roles deserializes correctly
- Missing interpreter raises validation error
- Missing director raises validation error
- Missing responder raises validation error
- Invalid escalation_level (outside 0-10) raises error
- Invalid recommended_direction (not in enum) raises error

**Test Group 2: Role Distinctness**
- Interpreter and Director fields are never empty/None (required)
- Responder state_change_candidates are pre-delta format (no ProposedStateDelta objects)
- Responder trigger_assertions are plain strings (not Trigger objects)
- Director output contains no executable proposals
- Interpreter output contains no state mutations

**Test Group 3: Serialization/Deserialization**
- AIRoleContract → JSON → AIRoleContract (round-trip)
- Nested models serialize correctly
- Type validation on deserialization

**Test Group 4: Role Boundaries**
- Interpreter uncertainty_markers is optional (allows None)
- Director pressure_movement is optional (allows None)
- Responder dialogue_impulses is optional (allows None)
- Responder scene_transition_candidate is optional (allows None)
- All required fields present in deserialized contract

**Test Group 5: No Scope Jump**
- Role contract does NOT require existing runtime changes
- Role contract does NOT depend on W2.4.2 normalization (can be tested independently)
- Role contract does NOT modify ProposedStateDelta or guard logic

---

## 7. Acceptance Criteria

- ✅ AIRoleContract model exists with three typed nested sections
- ✅ Interpreter, Director, Responder are explicitly distinct in schema
- ✅ Interpreter and Director remain non-executable (diagnostic only)
- ✅ Responder emits pre-delta, pre-normalized proposals
- ✅ All tests pass (validation, distinctness, boundaries, serialization)
- ✅ No W2 scope jump (existing runtime unchanged)
- ✅ Role contract ready for W2.4.2 (adapter integration)

---

## 8. What's Deferred (W2.4.2 and Beyond)

- **Responder normalization logic** — Converting pre-delta to ProposedStateDelta
- **AI prompt integration** — Teaching the AI to emit role-structured output
- **Guard/validator updates** — Handling normalized proposals (uses existing guards)
- **UI/diagnostics** — Displaying roles in response traces
- **Multi-call orchestration** — This is single-call, single-AI only

---

## 9. Files Structure

```
backend/app/runtime/
  role_contract.py          # NEW: ResponseImpulse, StateChangeCandidate,
                            #      InterpreterSection, DirectorSection, ResponderSection,
                            #      AIRoleContract
  ai_adapter.py             # MODIFIED: Comment only (no code change)

backend/tests/runtime/
  test_w2_4_1_role_contract.py  # NEW: Validation, distinctness, boundary tests
```

---

## 10. Commit Message

```
feat(w2): define canonical internal AI role contract

Introduces AIRoleContract with three explicitly typed nested roles:
- Interpreter (diagnostic scene reading)
- Director (diagnostic conflict steering)
- Responder (runtime-relevant pre-normalized proposals)

Role contract preserves responsibility boundaries and prevents scope blur.
Responder output will be normalized in W2.4.2.
All three roles required; supports role diagnostics and runtime transparency.
```

