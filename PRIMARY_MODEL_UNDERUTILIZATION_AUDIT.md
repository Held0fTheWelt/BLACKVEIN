# Primary Model Underutilization Audit Report

**Date:** 2026-04-22  
**Status:** FINDINGS COMPLETE - CRITICAL GAPS IDENTIFIED

---

## EXECUTIVE SUMMARY

The World of Shadows runtime is **materially underusing the primary model** as a runtime intelligence component. The system computes rich scene, character, social, and dramatic intelligence but delivers only **5 data points** to the model, constraining it to **prose generation only**.

**Severity:** CRITICAL  
**Impact:** High-agency model behaviors, social intelligence, character perspective, and dramatic adaptation are all unavailable because the model never receives the relevant state.

---

## PHASE 1: INTENDED CAPABILITY TARGET

### What the System Appears to Expect

From code analysis (manager.py, langgraph_runtime_executor.py), the system passes rich state to `turn_graph.run()`:

- `active_narrative_threads` - story threads with pressure
- `thread_pressure_summary` - narrative continuity state
- `host_experience_template` - character/scene intent
- `prior_continuity_impacts` - historical constraints
- `turn_number`, `turn_initiator_type`, `live_player_truth_surface`

From the graph structure, the system **builds**:
- Scene assessments
- Pacing and silence parameters
- Responder and function selections
- Social state records
- Character mind modeling
- Dramatic effect parameters
- Continuity impact tracking

From documentation and operator surfaces, the system language implies:
- "AI-driven gameplay"
- "Live runtime intelligence"
- "Scene-aware narration"
- "Character-driven responses"
- "Social dynamics modeling"

### What Actually Happens

The primary model receives **exactly 5 pieces of information**:

1. `player_input` - raw player text
2. `interpreted_input` - structured interpretation (kind, confidence, ambiguity, intent, handling_path, delivery_hint)
3. `retrieval_context` - retrieved knowledge from memory
4. `correction_block` - (only in retry/rewrite passes)
5. `format_instructions` - JSON schema instruction

The model can produce **exactly 3 outputs**:

1. `narrative_response` - prose narration
2. `proposed_scene_id` - optional scene ID
3. `intent_summary` - optional intent paraphrase

---

## PHASE 2: ACTUAL ACTIVE FOOTPRINT

### Canonical Prompt Catalog

The catalog contains **4 generic prompts**:
- `decision_context` - "analyze game state and player action, generate 3-5 possible outcomes"
- `action_selection` - "select the best outcome from analysis"
- `narrative_response` - "generate 2-3 sentences describing action outcome"
- `failure_explanation` - "explain in narrative terms why action failed"

**Status:** These 4 prompts are **DEFINED BUT NEVER INVOKED** in the active path. They exist in `canonical_prompt_catalog.py` but no code calls them.

### Runtime Invocation Chain

**File: `ai_stack/langgraph_runtime_executor.py`**

1. `_retrieve_context()` (line 323-393)
   - Builds `context_text` from retrieval
   - Builds `model_prompt` = player_input + context + interpretation_block + narrative_threads
   - **MISSING:** Scene assessment, pacing info, social state, character info, dramatic params

2. `_invoke_model()` (line 696-771)
   - Calls `_invoke_runtime_adapter_with_langchain()`
   - Passes only: player_input, interpreted_input, retrieval_context, timeout
   - **MISSING:** All computed scene/character/dramatic state

3. **LangChain Bridge** (file: `ai_stack/langchain_integration/bridges.py`)
   - Prompt template (line 92-104):
   ```
   "Player input:\n{player_input}\n\n"
   "Interpreted input:\n{interpreted_input}\n\n"
   "Runtime retrieval context:\n{retrieval_context}\n\n"
   "{correction_block}"
   "Format instructions:\n{format_instructions}"
   ```
   - Output schema: `RuntimeTurnStructuredOutput` (narrative_response, proposed_scene_id, intent_summary)

---

## PHASE 3: COMPUTED BUT UNDELIVERED STATE

### Scene Intelligence (computed but not delivered)

**Code:** `_director_assess_scene()` (langgraph_runtime_executor.py ~line 470)
```python
def _director_assess_scene(self, state: RuntimeTurnState) -> RuntimeTurnState:
    # Computes:
    # - scene_assessment (dict with assessment details)
    # - scene_assessment_narrative (prose summary)
    # State includes: current_scene_id, module context, character profiles
    # RESULT: Stored in state but NEVER reaches model prompt
```

**What the model SHOULD know:** 
- What scene is active
- Who is present
- What the scene constraints are
- What dramatic/emotional tone is appropriate

**What the model ACTUALLY knows:** Nothing about the scene

---

### Pacing & Silence Parameters (computed but not delivered)

**Code:** `_director_select_dramatic_parameters()` (langgraph_runtime_executor.py ~line 550)
```python
def _director_select_dramatic_parameters(self, state: RuntimeTurnState) -> RuntimeTurnState:
    # Computes:
    # - pacing_directive (fast, normal, slow)
    # - silence_expectation (whether response is needed now)
    # - dramatic_pressure (escalation level)
    # RESULT: Stored in state but NEVER reaches model prompt
```

**What the model SHOULD know:**
- Current pacing (should response be brief or detailed?)
- Whether silence is expected
- Dramatic pressure level (escalate tension or defuse?)

**What the model ACTUALLY knows:** Nothing about pacing or dramatics

---

### Responder & Function Selection (computed but not delivered)

**Code:** `build_responder_and_function()` (ai_stack/scene_director_goc.py)
```python
# Computes:
# - responder_id: Who should respond (NPC1, NPC2, environment, etc.)
# - function_type: What action type (dialogue, action, reaction, etc.)
# RESULT: Computed but NEVER reaches model, so model generates prose without knowing
#         who should speak or what action to take
```

**What the model SHOULD know:**
- Who should be the active responder
- What type of function/action is appropriate
- Whether this is a dialogue response, environmental description, character action, etc.

**What the model ACTUALLY knows:** Nothing about responder or function type

---

### Social State (computed but not delivered)

**Code:** `build_social_state_record()` (ai_stack/social_state_goc.py)
```python
# Computes:
# - relationship_states (dict of relationship shifts)
# - emotional_state (dict of emotional positions)
# - social_pressure (social dynamics and pressure)
# - group_state (if multi-participant scene)
# RESULT: Computed for diagnostics but NEVER reaches model prompt
```

**What the model SHOULD know:**
- Relationship changes between characters
- Emotional states of participants
- Social pressure and dynamics
- Group emotional state

**What the model ACTUALLY knows:** Nothing about social state

---

### Character Mind Records (computed but not delivered)

**Code:** `build_character_mind_records_for_goc()` (ai_stack/character_mind_goc.py)
```python
# Computes:
# - character_knowledge (what each character knows)
# - character_perspective (each character's view of situation)
# - character_memory (recent interactions relevant to character)
# RESULT: Computed for scene context but NEVER reaches model
```

**What the model SHOULD know:**
- The active character's knowledge/perspective
- What they remember
- Their relationship to current situation

**What the model ACTUALLY knows:** Generic player input, nothing perspective-specific

---

### Continuity Impacts (computed but not delivered)

**Code:** `goc_prior_continuity_for_graph()` (world-engine/app/story_runtime/module_turn_hooks.py)
```python
# Computes continuity constraints from prior turns
# Delivered to graph as prior_continuity_impacts
# RESULT: In state but NEVER delivered to model prompt
```

**What the model SHOULD know:**
- What continuity constraints apply
- What must be preserved from prior context
- What dramatic threads need continuity

**What the model ACTUALLY knows:** Current retrieval context only (no continuity framing)

---

## PHASE 4: ROOT CAUSES OF UNDERUTILIZATION

### Root Cause #1: Prompt Design is Minimal

**Symptom:** Model receives 5 inputs, produces 3 outputs  
**Mechanical Cause:** `_RUNTIME_PROMPT_TEMPLATE` in `bridges.py` line 92-104 includes only player_input, interpreted_input, retrieval_context  
**Deeper Cause:** Prompt was designed for narrow prose generation, not scene-aware intelligence  
**Impact:** Model has no structural path to use scene, character, or social knowledge

### Root Cause #2: Output Schema is Restrictive

**Symptom:** Model can only output prose, optional scene_id, optional intent_summary  
**Mechanical Cause:** `RuntimeTurnStructuredOutput` defines only 3 fields, all strings/IDs  
**Deeper Cause:** Schema was designed for narrative summary, not structured behavior guidance  
**Impact:** Model cannot express responder selection, function type, social state updates, dramatic decisions

### Root Cause #3: Computed State is Not Integrated

**Symptom:** Scene assessment, pacing, responder, social state are all computed but unused  
**Mechanical Cause:** States are computed in separate graph nodes but not merged into model_prompt  
**Deeper Cause:** System treats model invocation as isolated prose generation, not integrated behavior oracle  
**Impact:** Rich intelligence is computed but discarded, model is starved of context

### Root Cause #4: Canonical Prompt Catalog is Not Used

**Symptom:** 4 prompts exist but are never invoked  
**Mechanical Cause:** No code path calls `CanonicalPromptCatalog.get_prompt()`  
**Deeper Cause:** Prompt template is hardcoded in LangChain bridge instead of using catalog  
**Impact:** Prompt catalog system exists but is inert; prompts are not managed through governance

### Root Cause #5: Retrieval is Context-Only

**Symptom:** Retrieval provides narrative facts but not behavioral context  
**Mechanical Cause:** `ContextRetriever` and `ContextPackAssembler` fetch story content, not behavioral guidance  
**Deeper Cause:** Retrieval was designed for grounding prose, not for social/scene reasoning  
**Impact:** Model lacks historical behavioral patterns, character precedents, scene dynamics from memory

---

## PHASE 5: CAPABILITY USAGE GAP MAP

| Capability Class | Current Usage | Should Be | Gap Type | Severity |
|---|---|---|---|---|
| **Scene Understanding** | None - not delivered | High - model should understand active scene | Prompt/Context | CRITICAL |
| **Character Perspective** | Generic only | High - model should see through active character's eyes | Prompt/Context | CRITICAL |
| **Social Intelligence** | None - computed but discarded | High - model should reason about relationships/emotion | Prompt/Schema | CRITICAL |
| **Responder Selection** | Model generates prose unaware | High - model should decide who responds | Schema/Orchestration | CRITICAL |
| **Function/Action Type** | None - computed separately, model writes prose | High - model should select action type | Schema/Orchestration | CRITICAL |
| **Pacing & Rhythm** | None - computed but not delivered | Medium - model should adapt pace | Prompt/Context | HIGH |
| **Dramatic Adaptation** | Generic prose only | High - model should respond to dramatic pressure | Prompt/Context | CRITICAL |
| **Continuity Reasoning** | Implicit in retrieval only | High - model should see continuity constraints | Prompt/Context | HIGH |
| **Player Intent Interpretation** | Good - interpreted_input is delivered | Good | None | N/A |
| **Narrative Prose Generation** | Good - primary purpose | Good | None | N/A |
| **Memory/Retrieval Integration** | Adequate - context delivered | Good | None | N/A |

---

## PHASE 6: IMPLEMENTATION REPAIR PRIORITIES

### Wave 1: Expand Prompt Context (HIGH IMPACT, MEDIUM EFFORT)

Deliver the computed state to the model prompt:
1. Scene assessment (who, where, what constraints)
2. Active character perspective
3. Social state summary (relationships, emotions)
4. Pacing directive
5. Continuity constraints
6. Prior dramatic thread status

**Expected Effect:** Model goes from 5 inputs to 11+ inputs, can now reason about scene and character context

### Wave 2: Expand Output Schema (CRITICAL IMPACT, LOW EFFORT)

Extend output to capture structured behavior:
```python
class RuntimeTurnStructuredOutput(BaseModel):
    narrative_response: str  # Keep existing
    proposed_scene_id: str | None = None  # Keep existing
    intent_summary: str | None = None  # Keep existing
    
    # NEW:
    responder_id: str | None = None  # Who should respond
    function_type: str | None = None  # Type of action (dialogue, description, action, reaction)
    emotional_shift: dict | None = None  # Emotional change
    social_outcome: str | None = None  # Social/relationship effect
    dramatic_direction: str | None = None  # Escalate/defuse/sustain
```

**Expected Effect:** Model can now express structured behavioral intent, not just prose

### Wave 3: Integrate Computed State into Delivery (MEDIUM IMPACT, HIGH EFFORT)

Merge scene assessment, responder selection, social state into model_prompt assembly

### Wave 4: Align Validation & Commit with Richer Behavior (MEDIUM IMPACT, MEDIUM EFFORT)

Update validation to accept richer outputs; update rendering to preserve structured contributions

### Wave 5: Activate Canonical Prompt Catalog (LOW IMPACT, MEDIUM EFFORT)

Move prompt template from hardcoded LangChain to governed catalog system

---

## CONCLUSION

The World of Shadows runtime is **using the primary model as a bounded prose generator** when it should be using it as a **scene-aware, character-aware, socially-intelligent behavior oracle**.

The infrastructure for rich reasoning exists (scene assessment, character modeling, social state, pacing) but is disconnected from model invocation.

**Recommended immediate action:** Implement Waves 1-2 to deliver computed state to model and allow structured behavior expression. This will unlock the model's ability to adapt to scene, character, and social context.

---

**Generated:** 2026-04-22 01:30 UTC  
**Auditor:** Claude Code (Primary Model Utilization Analysis)
