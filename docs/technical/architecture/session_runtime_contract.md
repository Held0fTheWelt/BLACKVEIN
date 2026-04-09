# Session Runtime Contract

## Purpose

This document defines the formal structure of World Engine sessions, turn execution, event logging, state persistence, error recovery, and API contracts. It specifies what data the Engine maintains, how turns are processed, how state changes are logged, and how the system recovers from failures.

---

## Session State

Every session maintains mandatory metadata and runtime state:

### Mandatory Session Metadata

```
session_id:                  UUID or unique identifier
module_id:                   ID of the content module (e.g., "god_of_carnage")
module_version:              Semantic version of loaded module
contract_version:            Version of this contract document (for compatibility)
prompt_version:              Version of system prompt used for story LLM
ai_backend:                  Which AI system (e.g., "claude", "ollama", "gpt4")
ai_model:                    Specific model name (e.g., "claude-opus-4-6")
created_at:                  ISO 8601 timestamp
updated_at:                  ISO 8601 timestamp
seed:                        Optional random seed for reproducibility
```

### Extended Hybrid Metadata (SLM Versions)

```
context_packer_version:      SLM model version used for context compression
trigger_extractor_version:   SLM model version used for trigger detection
delta_normalizer_version:    SLM model version used for output normalization
guard_precheck_version:      SLM model version used for pre-validation
router_version:              SLM model version used for routing decisions
fallback_mode:               Boolean; whether engine is in reduced-resource mode
recovery_attempt_count:      Integer; number of recovery retries this session
```

### Runtime State (Per Session)

```
current_scene:               Scene identifier (e.g., "scene_1_opening")
turn_number:                 Integer counter (1, 2, 3, ...)
characters:                  Map of character_name → { emotional_state, escalation_level, ... }
relationships:               Map of axis_name → { stability, dominance_shift, ... }
event_log:                   List of all past turns with outcomes
session_active:              Boolean; whether session is in progress
last_error:                  String; description of last error encountered (if any)
```

---

## Turn State

Each turn represents one exchange in the narrative. A turn follows this pipeline:

### Turn Pipeline (9 Steps)

**Step 1: Input Reception**
- Receive player/operator input (dialogue, action, or system command)
- Validate input format
- Log input to event log

**Step 2: Context Packing**
- SLM `context_packer` compresses session state and recent history
- Output: ~2000-token story context
- This context is passed to the next steps

**Step 3: Routing Decision**
- SLM `router` examines session complexity, error history, last turn performance
- Output: routing decision (`full_llm_call`, `reduced_context_llm_call`, `fallback_mode`, `safe_no_op`)
- Engine follows routing recommendation

**Step 4: Story Generation** (if full_llm_call or reduced_context_llm_call)
- LLM story model processes context + module definition
- Output: structured JSON (see AI Story Contract)
- Timeout: configurable (default 30s)

**Step 5: Trigger Extraction**
- SLM `trigger_extractor` analyzes AI output
- Detects which module triggers are active
- Output: list of detected triggers

**Step 6: Output Normalization**
- SLM `delta_normalizer` cleans and validates JSON structure
- Output: normalized `proposed_state_deltas`
- If normalization fails: guard_precheck may reject

**Step 7: Guard Pre-Check**
- SLM `guard_precheck` validates proposal against module schema and constraints
- Checks for forbidden mutations, unknown references, incoherence
- Output: list of violations or warnings
- Severity: hard_reject / warning / info

**Step 8: State Validation & Application**
- Engine validates guard_precheck output
- If no hard_rejects: Engine applies state deltas to session state
- If hard_rejects: Engine triggers fallback (retry or safe_no_op)
- Engine logs all state changes to state_delta_log

**Step 9: Response Generation & Logging**
- Engine creates response (scene update, next scene, or error message)
- All logs are written (event_log, ai_decision_log, validation_log, state_delta_log, recovery_log if applicable)
- Turn is complete; turn_number increments

---

## Event Log

The event log records all player/operator actions and outcomes:

```json
{
  "turn_number": 1,
  "timestamp": "2026-03-26T10:30:45Z",
  "input": "string (player dialogue or action)",
  "input_type": "dialogue | action | system_command",
  "output_summary": "string (AI-generated response or error message)",
  "status": "success | error | fallback",
  "error_class": "optional string (error class name if status=error)",
  "applied_deltas": { /* state changes applied */ },
  "scene": "scene identifier after turn"
}
```

**Purpose**: A human-readable record of what happened each turn. Used for UI display, debugging, session replay, and diagnostics.

---

## State Delta Log

Detailed record of every state change proposed and applied:

```json
{
  "turn_number": 1,
  "timestamp": "2026-03-26T10:30:45Z",
  "proposed": { /* proposed_state_deltas from AI */ },
  "applied": { /* state deltas actually applied by Engine */ },
  "rejected_deltas": { /* any proposed changes that were rejected */ },
  "reason": "string (why some deltas were rejected, if applicable)"
}
```

**Purpose**: Fine-grained record of state mutations. Enables state reconstruction, reproducibility checks, and forensic debugging.

---

## AI Decision Log

Detailed record of AI proposals and guard outcomes:

```json
{
  "turn_number": 1,
  "timestamp": "2026-03-26T10:30:45Z",
  "ai_output": { /* full structured AI output */ },
  "confidence": "float (AI-provided confidence 0–1)",
  "uncertainty": "string (optional AI-provided uncertainty note)",
  "triggers_detected": ["array of trigger strings"],
  "guard_verdict": "accept | warning | reject",
  "guard_issues": ["array of guard_precheck issues"],
  "routing_decision": "full_llm_call | reduced_context | fallback | safe_no_op",
  "recovery_mode": "boolean (true if fallback or safe_no_op)"
}
```

**Purpose**: Record of AI proposal quality, guard performance, and routing decisions. Used for model evaluation, debugging, and decision transparency.

---

## Validation Log

Record of guard layer checks:

```json
{
  "turn_number": 1,
  "checks": [
    { "check": "schema_valid", "status": "pass" },
    { "check": "semantic_valid", "status": "pass" },
    { "check": "constraint_valid", "status": "pass" },
    { "check": "coherence_valid", "status": "pass" },
    { "check": "confidence_valid", "status": "pass" }
  ],
  "guard_verdict": "accept | warning | reject"
}
```

**Purpose**: Transparency about which checks passed and which failed. Helps debug proposal rejection reasons.

---

## State Delta Format

State changes are represented as:

```json
{
  "character_name": {
    "emotional_state": 75,
    "escalation_level": 65,
    "engagement": 90,
    "moral_defense": 40
  },
  "axis_name": {
    "stability": 45,
    "dominance_shift": 2
  }
}
```

**Constraints**:
- Character names must exist in module
- Axis names must exist in module
- Numerical values must be within defined bounds (0–100)
- No new fields may be added

---

## Reproducibility Metadata

Sessions include fields to enable deterministic replay:

```
seed:              Optional random seed (if provided, all random outcomes are deterministic)
ai_model_version:  Exact version of LLM used (e.g., "claude-opus-4-6-20260101")
ai_temperature:    Temperature setting for LLM sampling
context_length:    Effective context length used for this session
timestamp_seed:    ISO timestamp at session start (for tie-breaking reproducibility)
```

**Purpose**: Enable deterministic session replay for debugging, testing, and demonstration.

---

## W0 Error Classes

Named error classes for W0 recovery logic:

| Error Class | Cause | Recovery |
|-------------|-------|----------|
| `schema_invalid` | Output is not valid JSON or missing mandatory fields | Retry with full context |
| `forbidden_mutation` | Attempt to change read-only state | Reject proposal; safe_no_op |
| `unknown_reference` | Reference to undefined character/trigger/axis | Retry with reduced context |
| `illegal_scene_jump` | Attempt to force scene transition | Reject; safe_no_op |
| `unsupported_trigger` | Trigger not in module trigger set | Delta_normalizer cleanup; retry if recoverable |
| `canon_conflict` | Proposed state contradicts event log | Reject; safe_no_op |
| `partial_output` | Mandatory field missing or malformed | Retry with full context |
| `empty_response` | AI returned null or empty output | Retry with reduced context |
| `timeout_backend_failure` | AI call failed to complete | Retry once; fallback_mode if repeated |
| `slm_normalization_failure` | delta_normalizer could not normalize output | Reject; safe_no_op |
| `slm_routing_mismatch` | router recommendation conflicts with constraints | Log warning; Engine overrides |
| `precheck_warning_overflow` | guard_precheck identified >threshold issues | Retry with reduced context; fallback if repeated |

---

## Recovery & Fallback Behavior

When an error occurs, the Engine follows this recovery sequence:

### Recovery Level 1: Immediate Retry
- **Condition**: First error in this session; confidence was high
- **Action**: Retry AI call with same context
- **Limit**: 1 retry
- **Outcome**: If retry succeeds, proceed normally; if fails, go to Level 2

### Recovery Level 2: Reduced-Context Retry
- **Condition**: Retry failed OR original confidence was medium
- **Action**: Call context_packer again with reduced summary; retry AI with compressed context
- **Limit**: 1 attempt
- **Outcome**: If succeeds, proceed; if fails, go to Level 3

### Recovery Level 3: Fallback Mode
- **Condition**: Reduced-context retry failed OR original error was critical
- **Action**: Enter fallback_mode; use safe_no_op (see below) or pre-scripted fallback dialogue
- **Limit**: Up to 2 fallback turns per session
- **Outcome**: Preserve session state; allow player to retry action next turn

### Safe No-Op Strategy
When Engine cannot generate a valid AI proposal:
1. Acknowledge the input (echo it back)
2. Keep state unchanged (no state deltas applied)
3. Advance turn counter
4. Log the error and recovery
5. Offer player same choice on next turn

**Constraint**: Last valid state is always preserved. Sessions never corrupt or lose coherence.

---

## API Contract (W3 Minimum)

The World Engine exposes these HTTP endpoints:

### POST `/api/v1/sessions`
- **Purpose**: Start a new session
- **Input**: `{ "module_id": "god_of_carnage" }`
- **Output**: `{ "session_id": "uuid", "session_state": {...} }`
- **Status**: 201 Created

### GET `/api/v1/sessions/{session_id}`
- **Purpose**: Retrieve current session state
- **Output**: Full session state (metadata + characters + relationships + current scene)
- **Status**: 200 OK (if session exists) or 404 Not Found

### POST `/api/v1/sessions/{session_id}/turn`
- **Purpose**: Execute one turn
- **Input**: `{ "input": "string (player action or dialogue)" }`
- **Output**: `{ "turn_result": {...}, "new_scene": {...}, "error": optional }`
- **Status**: 200 OK (even if error occurred; error is in response body)

### GET `/api/v1/sessions/{session_id}/logs`
- **Purpose**: Retrieve all logs for the session
- **Query**: `?type=event&type=ai_decision&type=validation` (optional filters)
- **Output**: `{ "event_log": [...], "ai_decision_log": [...], "validation_log": [...] }`
- **Status**: 200 OK

### GET `/api/v1/sessions/{session_id}/logs/state-delta`
- **Purpose**: Retrieve state delta log
- **Output**: `{ "state_delta_log": [...] }`
- **Status**: 200 OK

### DELETE `/api/v1/sessions/{session_id}`
- **Purpose**: End session (optional)
- **Status**: 204 No Content

---

## Related Documents

- [MVP Definition](./mvp_definition.md) — Session role in the MVP
- [AI Story Contract](./ai_story_contract.md) — AI proposal format and validation
- [God of Carnage Module Contract](./god_of_carnage_module_contract.md) — Module-specific state and validation

---

**Version**: W0 (2026-03-26)
