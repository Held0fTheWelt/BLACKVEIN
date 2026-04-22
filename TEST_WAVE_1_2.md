# Test Plan: Wave 1-2 Implementation Verification

**Goal:** Verify that the model now receives expanded context and can output structured behavior.

---

## Pre-Test Checklist

- [ ] Docker containers are all healthy (backend, play-service, frontend)
- [ ] Backend API is responding (http://localhost:8000/health or similar)
- [ ] Play service is responding (http://localhost:8001)
- [ ] Frontend loads (http://localhost:5002)

---

## Test 1: Context Delivery Verification

**Objective:** Confirm that scene assessment, social state, pacing, responders, and continuity are delivered to the model.

### Steps:

1. Open browser to http://localhost:5002
2. Create a new story session with a module that has:
   - Multiple NPCs
   - Defined scenes
   - Relationships
3. Start gameplay and play the opening turn
4. Check Docker logs for the play-service container:
   ```bash
   docker logs worldofshadows-play-service-1 --tail=100 | grep -A 50 "Scene Assessment"
   ```
5. Look for evidence that these blocks are in the prompt delivered to the model:
   - "Scene Assessment:" (from state.scene_assessment)
   - "Current Relationship State:" (from state.social_state_record)
   - "Emotional State:" (from state.social_state_record)
   - "Pacing Directive:" (from state.pacing_mode)
   - "Eligible Responders:" (from state.selected_responder_set)
   - "Continuity Constraints:" (from state.prior_continuity_impacts)

### Expected Result:
✓ Logs show all 6 context blocks being delivered to the model
✓ No errors in prompt assembly

---

## Test 2: Output Schema Expansion

**Objective:** Verify that the model output can include the new structured behavior fields.

### Steps:

1. During gameplay, examine the model's response in:
   - Browser developer console (Network tab → WebSocket messages)
   - OR Docker logs for play-service with JSON parsing

2. Look for the new fields in model output:
   - `responder_id` (should contain NPC name or environment)
   - `function_type` (should contain dialogue/action/description/reaction)
   - `emotional_shift` (should contain dict of character emotion changes)
   - `social_outcome` (should contain relationship effect)
   - `dramatic_direction` (should contain escalate/defuse/sustain)

3. Verify parsing doesn't fail (no PydanticOutputParser errors)

### Expected Result:
✓ At least some of the new fields are populated in model response
✓ No parser errors (new fields are optional, so model might not always populate them)
✓ Narrative response still generated (backwards compatibility)

---

## Test 3: Backwards Compatibility

**Objective:** Ensure existing features still work.

### Steps:

1. Play multiple turns in the story
2. Verify no regressions:
   - Narrative still generates
   - Scene transitions work
   - Player input still processed correctly
   - Retrieval context still delivered
   - No timeout increases in response time

### Expected Result:
✓ Story gameplay is smooth
✓ Response times are reasonable (not significantly slower than before)
✓ No new error messages in logs

---

## Test 4: Model Behavior Change

**Objective:** Qualitative assessment that model has richer context.

### Steps:

1. Play the same scenario with and without context (if possible via mock vs AI mode)
2. Compare response quality:
   - Does model response better match scene context?
   - Are emotional states reflected in prose?
   - Are pacing directives followed (brief vs detailed)?
   - Does model acknowledge relationship states?

### Expected Result:
✓ Model responses show greater scene awareness
✓ Emotional tone matches social state
✓ Responses adapt to pacing directive
✓ Relationship context is reflected in dialogue/action

---

## Debug Checklist (if issues arise)

### If context is not delivered:
- [ ] Check _retrieve_context() was actually modified (log the model_prompt)
- [ ] Check _invoke_model() is passing model_prompt to LangChain
- [ ] Check bridges.py is receiving model_prompt parameter
- [ ] Verify no exception in state assembly

### If output schema fails to parse:
- [ ] Check PydanticOutputParser error in logs
- [ ] Look for "langchain_parser_error" in generation metadata
- [ ] Verify model is producing valid JSON
- [ ] Check if new fields are optional (they should be)

### If tests fail:
- [ ] Clear browser cache (Ctrl+Shift+Del)
- [ ] Restart containers: `python docker-up.py restart`
- [ ] Check Docker build logs: `docker logs worldofshadows-backend-1`
- [ ] Verify no syntax errors: `python -m py_compile ai_stack/langgraph_runtime_executor.py`

---

## Success Criteria

**Minimum Success:**
- [ ] Docker builds without errors
- [ ] All containers start successfully
- [ ] Story session can be created and played
- [ ] No new errors in logs related to model invocation

**Expected Success:**
- [ ] Context blocks are visible in logs (Test 1)
- [ ] Model can output new fields without parse errors (Test 2)
- [ ] Existing features work (Test 3)

**Excellent Success:**
- [ ] All of the above, PLUS
- [ ] Model responses show improved scene awareness (Test 4)
- [ ] Response quality is noticeably better with context

---

## Logging for Detailed Investigation

To enable detailed logging of model prompt and response:

1. Find the log call in _invoke_model():
   ```python
   _log.warning("Primary model invocation failed: provider=%s error=%s", provider or "unknown", generation.get("error") or "unknown")
   ```

2. Add before _invoke_runtime_adapter_with_langchain():
   ```python
   _log.info("Model prompt (first 500 chars): %s", state.get("model_prompt", "")[:500])
   ```

3. Check logs after test:
   ```bash
   docker logs worldofshadows-play-service-1 | grep "Model prompt"
   ```

---

*Test Plan for Wave 1-2 Implementation Verification*  
*Generated: 2026-04-22*
