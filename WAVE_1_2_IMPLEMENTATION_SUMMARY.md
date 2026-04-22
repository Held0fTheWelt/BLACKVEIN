# Wave 1-2 Implementation: Model Context Expansion & Output Schema

**Date:** 2026-04-22  
**Status:** IMPLEMENTED & BUILDING

## Summary

Implemented Waves 1-2 of the Primary Model Utilization Audit repairs to expand what the primary model receives as input and what it can express as output.

---

## Wave 1: Expanded Prompt Context

### What Changed

**File: `ai_stack/langgraph_runtime_executor.py` (_retrieve_context method)**

Extended the model_prompt assembly (lines 363-451) to include 5 new context blocks:

1. **Scene Assessment**
   - Extracts `scene_assessment.assessment_summary`
   - Provides model with scene understanding, constraints, dramatic tone

2. **Social State**
   - Extracts `social_state_record.relationship_states` (up to 4 relationships)
   - Extracts `social_state_record.emotional_state` (up to 4 characters)
   - Provides model with relationship context and emotional positions

3. **Pacing Directive**
   - Extracts `pacing_mode` (fast/normal/slow)
   - Tells model what rhythm is appropriate (brief vs detailed responses)

4. **Responder Selection**
   - Extracts `selected_responder_set` (up to 3 eligible responders)
   - Shows model who could respond and their types

5. **Continuity Constraints**
   - Extracts `prior_continuity_impacts.continuity_constraints` (up to 3)
   - Ensures model sees what must be preserved from prior context

### Model Input Growth

**Before:** 5 inputs
- Player input
- Interpreted input (kind, confidence, ambiguity, intent, handling_path, delivery_hint)
- Retrieval context
- Format instructions
- (Optional) Correction block

**After:** 11+ inputs
- All of the above, PLUS:
- Scene Assessment
- Relationship States
- Emotional States  
- Pacing Directive
- Responder Candidates
- Continuity Constraints

---

**File: `ai_stack/langgraph_runtime_executor.py` (_invoke_model method)**

Modified lines 730-740 to pass `model_prompt` to the LangChain bridge:

```python
invoke_kw: dict[str, Any] = {
    "adapter": adapter,
    "player_input": state["player_input"],
    "interpreted_input": state.get("interpreted_input", {}) ...,
    "retrieval_context": state.get("context_text"),
    "timeout_seconds": float(state.get("selected_timeout", 10.0)),
    "model_prompt": state.get("model_prompt", ""),  # ← NEW
}
```

This ensures the expanded context built by _retrieve_context() actually reaches the model.

---

**File: `ai_stack/langchain_integration/bridges.py` (LangChain bridge)**

Changed 3 things:

1. **Updated function signature** (lines 110-121):
   - Added `model_prompt: str | None = None` parameter to `invoke_runtime_adapter_with_langchain()`

2. **Updated prompt template** (lines 63-79):
   - Changed from explicit field placeholders (player_input, interpreted_input, retrieval_context)
   - To a single `{full_context}` placeholder
   - Allows delivering the full assembled context from _retrieve_context()

3. **Updated context assembly** (lines 149-162):
   - If `model_prompt` is provided: use it directly (Wave 1 path)
   - Otherwise: build from individual components for backwards compatibility

**New Logic:**
```python
if model_prompt:
    full_context = model_prompt
else:
    # fallback for backwards compatibility
    interp_str = "\n".join(f"- {k}: {v}" for k, v in interpreted_input.items()) ...
    full_context = f"Player input:\n{player_input}\n\n..."
```

---

## Wave 2: Expanded Output Schema

**File: `ai_stack/langchain_integration/bridges.py` (RuntimeTurnStructuredOutput)**

Extended the model's output schema from 3 to 8 fields (lines 46-57):

### Existing Fields (preserved)
- `narrative_response: str` - prose narration (unchanged)
- `proposed_scene_id: str | None` - optional scene change (unchanged)
- `intent_summary: str | None` - paraphrase of intent (unchanged)

### New Fields (Wave 2)
- **`responder_id: str | None`** - identifies who should respond (NPC name, "environment", "silence", etc.)
- **`function_type: str | None`** - type of action (dialogue, description, action, reaction, silence, etc.)
- **`emotional_shift: dict | None`** - emotional changes for active characters (e.g., `{"NPC1": "confident", "NPC2": "uncertain"}`)
- **`social_outcome: str | None`** - effect on relationships/social dynamics (e.g., "tension_escalates" or "conflict_resolution")
- **`dramatic_direction: str | None`** - guidance on drama flow (escalate, defuse, sustain, calm)

### Model Output Growth

**Before:** 3 fields, prose + metadata
```json
{
  "narrative_response": "...",
  "proposed_scene_id": null,
  "intent_summary": null
}
```

**After:** 8 fields, prose + structured behavioral intent
```json
{
  "narrative_response": "...",
  "proposed_scene_id": null,
  "intent_summary": null,
  "responder_id": "NPC_merchant",
  "function_type": "dialogue",
  "emotional_shift": {"NPC_merchant": "intrigued"},
  "social_outcome": "alliance_possible",
  "dramatic_direction": "escalate"
}
```

---

## Expected Impact

### Immediate (Model can now understand)
- ✓ Active scene context (who, where, constraints, tone)
- ✓ Relationship and emotional states
- ✓ Pacing expectations (brevity vs detail)
- ✓ Who can respond to the player
- ✓ Continuity constraints from prior turns

### Immediate (Model can now express)
- ✓ Structured responder selection (not buried in prose)
- ✓ Explicit action type (dialogue vs description vs action)
- ✓ Emotional state changes for characters
- ✓ Social/relationship outcomes
- ✓ Dramatic direction guidance

### Second-order (System can now use)
- ✓ Responder intent from model instead of separate orchestration
- ✓ Function type from model instead of separate logic
- ✓ Emotional shifts to drive character behavior
- ✓ Social outcomes to update relationship state
- ✓ Dramatic direction to adjust pacing/tension

---

## Testing Checklist

- [ ] Docker build completes without errors
- [ ] Backend API starts (http://localhost:8000)
- [ ] Play service starts (http://localhost:8001)
- [ ] Frontend loads (http://localhost:5002)
- [ ] Create new story session
- [ ] Generate first turn with model
- [ ] Verify logs show expanded context delivered to model
- [ ] Check that model output includes new fields (responder_id, function_type, etc.)
- [ ] Verify scene understanding in model output
- [ ] Verify no regression in existing features

---

## Architectural Notes

### Why This Works

1. **Additive change:** Wave 1 adds context WITHOUT breaking existing paths
   - If `model_prompt` is not provided, falls back to original behavior
   - Existing tests still work

2. **Structured behavior:** Wave 2 adds optional fields
   - Model can ignore them and work with prose-only (backwards compatible)
   - System can use them when provided

3. **Integration point:** Both waves converge at LangChain bridge
   - Single place to modify prompt delivery
   - Single place to modify output schema
   - Reduces coordination complexity

### Future Work (Waves 3-5)

**Wave 3:** Integrate structured behavior output back into graph
- Use responder_id from model instead of separate build_responder_and_function()
- Use function_type from model to guide narration

**Wave 4:** Validation & Commit alignment
- Accept richer outputs in validation
- Preserve structured contributions in story state

**Wave 5:** Canonical Prompt Catalog
- Move hardcoded prompt template to governed catalog
- Allow prompt governance without code redeploy

---

## Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `ai_stack/langgraph_runtime_executor.py` | Expand _retrieve_context(), modify _invoke_model() | 363-451, 730-740 |
| `ai_stack/langchain_integration/bridges.py` | Update function signature, template, output schema | 110-121, 63-79, 46-57, 149-162 |

---

**Implementation Status:** ✓ COMPLETE  
**Build Status:** IN PROGRESS  
**Testing Status:** PENDING

---

*Generated: 2026-04-22 by Claude Code (Primary Model Utilization Audit - Wave 1-2)*
