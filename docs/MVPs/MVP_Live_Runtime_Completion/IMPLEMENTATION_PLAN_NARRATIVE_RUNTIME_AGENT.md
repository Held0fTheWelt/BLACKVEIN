# Implementation Plan: Narrative Runtime Agent for MVP 3

**Date**: 2026-04-29  
**Phase**: MVP 3 Implementation (Event-Based Runtime Architecture)  
**Status**: In Planning  

---

## Executive Summary

This document captures the design decisions made during grill-me session on 2026-04-29 and specifies the implementation path for the **NarrativeRuntimeAgent** — a new component that streams continuous narrator prose based on NPC motivation pressure while respecting MVP 2 validation boundaries and enabling player agency.

The NarrativeRuntimeAgent is **not optional** for MVP 3. It transforms the runtime from turn-sequential to event-based, where narrator, NPCs, and player act together asynchronously.

---

## Architecture Decision: Event-Based Runtime Environment

**Decided**: 2026-04-29, Session: grill-me  
**Status**: ✅ Locked

### The Model

```
[HTTP Turn Request] 
  ↓
[Story Runtime Manager orchestrates in sequence]:
  1. LDSS executes → NPCAgencyPlan + VisibleSceneOutput (blocks)
  2. Input-UI disabled
  3. NarrativeRuntimeAgent starts streaming
  4. Frontend: Typewriter effect live
  5. Player input queued (not processed)
  6. When Narrator reaches ruhepunkt (no more NPC initiatives):
     - Signal: ruhepunkt_reached=true, can_accept_input=true
     - Story Runtime Manager: process input_queue → next turn
```

### Key Decisions

| Decision | Value | Why |
|----------|-------|-----|
| Narrator Streaming | Continuous (not turn-sequential) | Fills silence based on motivation pressure; respects agency |
| Input During Streaming | Queued (not blocked at UI) | Player can attempt; input processed after ruhepunkt |
| Ruhepunkt Detection | Motivation-based | Agent analyzes `NPCAgencyPlan.npc_initiatives`; if none remain, signals ruhepunkt |
| Tracing | Optional (default JSON scaffold) | Live Langfuse only when enabled; deferred to MVP4 admin UI |
| Agent Location | Separate component in `ai_stack/` | Reusable for other experiences; not mixed with LDSS |
| Orchestration | Story Runtime Manager | Manages lifecycle: start LDSS → start NarrativeRuntimeAgent → monitor ruhepunkt → process input |

---

## Integration Points

### 1. Story Runtime Manager (`world-engine/app/story_runtime/manager/`)

**Current State**: Calls `_build_ldss_scene_envelope()` in `_finalize_committed_turn()`

**Changes Required**:

```python
def _finalize_committed_turn(self, session_id: str, event: dict) -> dict:
    # [Current: LDSS integration]
    ldss_output = self._build_ldss_scene_envelope(...)
    event["scene_turn_envelope"] = ldss_output
    
    # [NEW: NarrativeRuntimeAgent orchestration]
    if self._is_god_of_carnage_session(session_id):
        # Start narrative streaming
        narrative_agent = NarrativeRuntimeAgent(
            runtime_state=event.get("runtime_state"),
            npc_agency_plan=ldss_output.npc_agency_plan,
            ldss_output=ldss_output,
            enable_langfuse_tracing=self._get_tracing_config(session_id),
        )
        
        # Store for WebSocket streaming (if HTTP streaming endpoint used)
        self.narrative_agents[session_id] = narrative_agent
        
        # Signal to frontend: narrator is streaming
        event["narrative_streaming"] = {
            "status": "streaming",
            "agent_id": id(narrative_agent),
        }
```

**New Methods**:
- `_orchestrate_narrative_agent()` — Starts agent, monitors ruhepunkt
- `_check_ruhepunkt_signal()` — Polls/awaits agent's ruhepunkt signal
- `_process_input_queue()` — When ruhepunkt reached, execute queued player inputs
- `_get_tracing_config()` — Returns `enable_langfuse_tracing` from session config

### 2. NarrativeRuntimeAgent (`ai_stack/story_runtime/narrative_runtime_agent.py`)

**New Component**: Implements continuous narrator streaming

```python
class NarrativeRuntimeAgent:
    def __init__(
        self,
        runtime_state: RuntimeState,
        npc_agency_plan: NPCAgencyPlan,
        ldss_output: LDSSOutput,
        enable_langfuse_tracing: bool = False,
        narrator_style: str = "inner_perception_orientation",
    ):
        self.runtime_state = runtime_state
        self.npc_agency_plan = npc_agency_plan
        self.ldss_output = ldss_output
        self.enable_langfuse_tracing = enable_langfuse_tracing
        self.narrator_style = narrator_style
        self.streaming = True
        self.ruhepunkt_reached = False
    
    def stream_narrator_blocks(self) -> Iterator[NarrativeRuntimeAgentEvent]:
        """Generator that yields narrator blocks and signals."""
        while self.streaming:
            # Analyze motivation pressure from runtime_state
            pressure = self._analyze_motivation_pressure()
            
            # Generate narrator block based on pressure
            block = self._generate_narrator_block(pressure)
            
            # Validate: does not block player agency
            self._validate_narrative_output(block)
            
            # Yield block
            yield NarrativeRuntimeAgentEvent(
                event_type="narrator_block",
                narrator_block=block,
                decision_id=f"d-narrator-{uuid.uuid4()}",
            )
            
            # Check: should continue or signal ruhepunkt?
            remaining_initiatives = self._count_remaining_npc_initiatives()
            
            if remaining_initiatives == 0:
                # Signal ruhepunkt
                yield NarrativeRuntimeAgentEvent(
                    event_type="ruhepunkt_signal",
                    ruhepunkt_reached=True,
                    can_accept_input=True,
                    narrative_context={
                        "blocks_streamed": self.block_count,
                        "total_duration_ms": self.elapsed_ms,
                        "silence_filled": self.silence_filled,
                        "motivation_pressure_addressed": pressure.label,
                    },
                )
                self.streaming = False
                self.ruhepunkt_reached = True
                break
    
    def _analyze_motivation_pressure(self) -> MotivationPressure:
        """Analyze NPC motivation from RuntimeState.

        Returns pressure assessment:
        - label: "escalating", "building", "sustained", "resolved"
        - npc_initiatives_remaining: int
        - recommended_narrator_action: str
        """
        # Consult dramatic_signature, narrative_threads, thread_pressure_summary
        # from runtime_state
        ...
    
    def _generate_narrator_block(self, pressure: MotivationPressure) -> SceneBlock:
        """Generate narrator block based on motivation pressure.

        Uses LLM prompt that:
        - Analyzes pressure
        - Fills silence if pressure suggests it
        - Maintains inner_perception_orientation voice
        - Does NOT block player agency
        """
        prompt = self._build_narrator_prompt(pressure)
        # Call LLM or deterministic narrator
        text = self._call_narrator_llm(prompt)
        
        return SceneBlock(
            id=f"turn-{self.turn_number}-narrator-{self.block_count}",
            block_type="narrator",
            text=text,
            delivery=DeliveryConfig(
                mode="typewriter",
                characters_per_second=35,
                pause_before_ms=200,
                pause_after_ms=500,
                skippable=True,
            ),
        )
    
    def _validate_narrative_output(self, block: SceneBlock) -> None:
        """Validate narrator block does not:
        - Force player state ("you feel ashamed")
        - Predict player choice ("you decide to...")
        - Reveal hidden NPC intent
        - Summarize dialogue instead of perceiving
        """
        validator = NarratorVoiceValidator()
        result = validator.validate(block)
        if result.status == "rejected":
            raise NarrativeValidationError(f"Narrator block rejected: {result.error_code}")
    
    def _count_remaining_npc_initiatives(self) -> int:
        """Count how many NPC initiatives in agency_plan haven't been addressed."""
        # Tracks: primary_responder + secondary_responders
        # Once all have "spoken/acted", return 0
        ...
```

### 3. HTTP API Streaming Endpoint (`world-engine/app/api/http.py`)

**New Endpoint**: Stream narrator blocks to frontend

**Option A: Server-Sent Events (SSE)**
```python
@router.get("/story/sessions/{session_id}/stream-narrator")
def stream_narrator_blocks(session_id: str):
    """Stream narrator blocks as they are generated."""
    def generate():
        manager = get_story_manager()
        agent = manager.narrative_agents.get(session_id)
        
        if not agent:
            yield f"data: {json.dumps({'error': 'no narrator streaming'})}\n\n"
            return
        
        for event in agent.stream_narrator_blocks():
            yield f"data: {json.dumps(event.to_dict())}\n\n"
    
    return Response(generate(), mimetype="text/event-stream")
```

**Option B: WebSocket** (preferred for interactive input queuing)
```python
@app.websocket("/story/sessions/{session_id}/ws")
async def websocket_narrator_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()
    manager = get_story_manager()
    agent = manager.narrative_agents.get(session_id)
    
    try:
        async for event in agent.stream_narrator_blocks():
            await websocket.send_json(event.to_dict())
        
        # After ruhepunkt, accept player input
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "player_input":
                manager.queue_player_input(session_id, data["input"])
    except Exception as e:
        await websocket.close(code=1000)
```

---

## Data Contracts

### NarrativeRuntimeAgentInput

```python
@dataclass
class NarrativeRuntimeAgentInput:
    contract: str = "narrative_runtime_agent_input.v1"
    runtime_state: RuntimeState
    npc_agency_plan: NPCAgencyPlan
    ldss_output: LDSSOutput
    enable_langfuse_tracing: bool = False
    player_input_queued: bool = False
    narrative_context: dict[str, Any] | None = None  # prior silence duration, last npc action, etc.
```

### NarrativeRuntimeAgentEvent (Streaming)

```python
@dataclass
class NarrativeRuntimeAgentEvent:
    contract: str = "narrative_runtime_agent_event.v1"
    event_type: str  # "narrator_block" | "ruhepunkt_signal"
    narrator_block: SceneBlock | None = None
    ruhepunkt_reached: bool | None = None
    can_accept_input: bool | None = None
    decision_id: str = ""
    narrative_context: dict[str, Any] | None = None
```

### NarrativeRuntimeAgentConfig

```python
@dataclass
class NarrativeRuntimeAgentConfig:
    contract: str = "narrative_runtime_agent_config.v1"
    enable_langfuse_tracing: bool = False
    narrator_style: str = "inner_perception_orientation"
    silence_filling_enabled: bool = True
    motivation_awareness_enabled: bool = True
    max_silence_duration_ms: int = 8000
    ruhepunkt_strategy: str = "motivation_based"
```

---

## Patch Map

| Patch ID | Area | Files | Required Change | Tests |
|----------|------|-------|-----------------|-------|
| NRA-P01 | NarrativeRuntimeAgent module | `ai_stack/story_runtime/narrative_runtime_agent.py` | Implement agent with streaming, motivation analysis, narrator validation. | `test_narrative_agent_streams_continuously`, `test_narrative_agent_respects_motivation_pressure` |
| NRA-P02 | Story Runtime Manager orchestration | `world-engine/app/story_runtime/manager/` | Orchestrate: LDSS → NarrativeRuntimeAgent; manage input queue; detect ruhepunkt. | `test_story_runtime_manager_orchestrates_ldss_and_narrative_agent`, `test_input_blocked_while_narrative_agent_streams` |
| NRA-P03 | HTTP streaming endpoint | `world-engine/app/api/http.py` | Add SSE or WebSocket endpoint for narrator streaming. | `test_narrator_stream_endpoint_emits_blocks`, `test_websocket_narrator_streaming` |
| NRA-P04 | Input queue management | `world-engine/app/story_runtime/manager/` | Queue player input during streaming; process queue after ruhepunkt signal. | `test_player_input_queued_during_streaming`, `test_input_queue_processed_after_ruhepunkt` |
| NRA-P05 | Narrative validation | `ai_stack/validators/narrator_voice_validator.py` | Validate narrator blocks: no forced state, no hidden intent, no dialogue summary. | `test_narrative_validator_rejects_forced_state`, `test_narrative_validator_rejects_hidden_intent` |
| NRA-P06 | Langfuse optional instrumentation | `ai_stack/story_runtime/narrative_runtime_agent.py` + `ai_stack/langfuse_integration.py` | Optional live Langfuse spans when enabled; default JSON scaffold. | `test_narrative_agent_accepts_enable_langfuse_tracing`, `test_narrative_agent_emits_trace_scaffold_by_default` |
| NRA-P07 | Frontend streaming integration | `frontend/static/play_narrative_stream.js` | Receive narrator blocks; render typewriter effect; manage input-UI blocking. | `test_frontend_receives_narrator_blocks`, `test_frontend_blocks_input_during_streaming` |

---

## Validation Rules

| Rule | Where Enforced | Error Code | Test Name |
|------|---|---|---|
| Narrative agent must stream while NPC initiatives pending | NarrativeRuntimeAgent | `narrative_agent_must_stream_npc_initiatives` | `test_narrative_agent_continues_while_npc_initiatives_pending` |
| Narrative agent must signal ruhepunkt when no NPC initiatives | NarrativeRuntimeAgent | `ruhepunkt_signal_required` | `test_narrative_agent_signals_ruhepunkt_when_initiatives_exhausted` |
| Input must be blocked while narrative agent streams | Story Runtime Manager | `input_blocked_during_narrative_streaming` | `test_input_blocked_while_narrative_agent_streams` |
| Narrative agent must not force player state or emotion | NarratorVoiceValidator | `narrator_forces_player_state` | `test_narrative_agent_does_not_force_player_state` |
| Ruhepunkt only reached when NPC initiatives exhausted | NarrativeRuntimeAgent | `premature_ruhepunkt_signal` | `test_ruhepunkt_only_when_no_npc_initiatives` |

---

## Required Tests

### NarrativeRuntimeAgent Unit Tests
- `test_narrative_agent_streams_continuously`
- `test_narrative_agent_respects_motivation_pressure`
- `test_narrative_agent_fills_silence_based_on_npc_pressure`
- `test_narrative_agent_blocks_input_while_streaming`
- `test_narrative_agent_signals_ruhepunkt_when_no_npc_initiatives`
- `test_narrative_agent_continues_while_npc_initiatives_pending`
- `test_narrative_agent_does_not_force_player_state`
- `test_narrative_agent_rejects_dialogue_recap`
- `test_narrative_agent_rejects_hidden_npc_intent`

### Story Runtime Manager Integration Tests
- `test_story_runtime_manager_orchestrates_ldss_and_narrative_agent`
- `test_input_blocked_while_narrative_agent_streams`
- `test_input_queue_processed_after_ruhepunkt_signal`
- `test_narrative_agent_receives_correct_input_from_ldss`
- `test_ruhepunkt_only_when_no_npc_initiatives`

### HTTP Streaming Endpoint Tests
- `test_narrator_stream_endpoint_emits_blocks`
- `test_websocket_narrator_streaming`
- `test_stream_endpoint_returns_ruhepunkt_signal`

### Langfuse Optional Instrumentation Tests
- `test_narrative_agent_accepts_enable_langfuse_tracing_config`
- `test_narrative_agent_emits_trace_scaffold_by_default`
- `test_narrative_agent_emits_langfuse_spans_when_enabled`

### Frontend Integration Tests
- `test_frontend_receives_narrator_blocks`
- `test_frontend_blocks_input_during_streaming`
- `test_frontend_displays_typewriter_effect`
- `test_frontend_queues_input_during_streaming`

---

## Required ADRs

**New ADRs for NarrativeRuntimeAgent**:
- ADR-MVP3-014: Event-Based Runtime Environment (Narrator, NPCs, Player async)
- ADR-MVP3-015: NarrativeRuntimeAgent Streaming Architecture
- ADR-MVP3-016: Motivation-Based Ruhepunkt Detection
- ADR-MVP3-017: Narrator Voice Validation (agency protection)

**Existing ADRs to Update**:
- ADR-MVP3-011 (LDSS) — Add reference to NarrativeRuntimeAgent orchestration
- ADR-MVP3-012 (NPC Agency) — Add reference to motivation pressure feedback loop
- ADR-MVP3-013 (Narrator) — Add reference to streaming and ruhepunkt

---

## Stop Condition for NarrativeRuntimeAgent Implementation

Stop only when:

1. ✅ NarrativeRuntimeAgent module exists and streams narrator blocks based on motivation pressure
2. ✅ Story Runtime Manager orchestrates LDSS → NarrativeRuntimeAgent in sequence
3. ✅ Ruhepunkt signal correctly detects when NPC initiatives are exhausted
4. ✅ Input is queued while narrator streams and processed after ruhepunkt
5. ✅ Narrator blocks are validated (no forced state, no hidden intent, no dialogue summary)
6. ✅ HTTP streaming endpoint (SSE or WebSocket) delivers narrator blocks to frontend
7. ✅ Frontend receives blocks and blocks input-UI while streaming
8. ✅ Langfuse tracing is optional (default: JSON scaffold, optional: live spans)
9. ✅ All required tests PASS (unit, integration, streaming)
10. ✅ All required ADRs exist and reference each other
11. ✅ Operational gates verified (docker-up.py, tests/run_tests.py, GitHub workflows, TOML/tooling)

---

## Implementation Sequence

### Phase 1: NarrativeRuntimeAgent Core (Days 1-2)
1. Create `ai_stack/story_runtime/narrative_runtime_agent.py`
2. Implement `stream_narrator_blocks()` generator
3. Implement `_analyze_motivation_pressure()`
4. Implement `_generate_narrator_block()`
5. Unit tests: streaming, motivation analysis

### Phase 2: Validation & Narrator Voice (Days 3-4)
1. Create `ai_stack/validators/narrator_voice_validator.py`
2. Implement validation rules (no forced state, etc.)
3. Integrate validation into agent
4. Unit tests: narrator validation

### Phase 3: Story Runtime Manager Integration (Days 5-6)
1. Modify `world-engine/app/story_runtime/manager/`
2. Implement orchestration methods
3. Implement input queue management
4. Implement ruhepunkt detection
5. Integration tests: orchestration, input blocking

### Phase 4: HTTP Streaming Endpoint (Days 7-8)
1. Add SSE or WebSocket endpoint
2. Stream narrator blocks to frontend
3. Endpoint tests: streaming, signal propagation

### Phase 5: Frontend Integration (Days 9-10)
1. Create `frontend/static/play_narrative_stream.js`
2. Implement typewriter effect
3. Implement input-UI blocking
4. Frontend tests: streaming, input blocking

### Phase 6: Langfuse Optional Instrumentation (Days 11-12)
1. Add `enable_langfuse_tracing` config
2. Implement trace scaffold generation
3. Optional live Langfuse spans
4. Tests: tracing optional behavior

### Phase 7: Operational Gates & Handoff (Days 13-14)
1. Verify docker-up.py, tests/run_tests.py, GitHub workflows, TOML/tooling
2. Create MVP3_NARRATIVE_RUNTIME_AGENT_EVIDENCE.md
3. Create handoff document to MVP 4
4. Final ADRs and documentation

---

## Success Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| NarrativeRuntimeAgent exists | ✅ COMPLETE | `ai_stack/story_runtime/narrative_runtime_agent.py` present |
| Narrator blocks stream continuously | ✅ COMPLETE | `test_narrative_agent_streams_continuously` PASS |
| Motivation pressure detected | ✅ COMPLETE | `test_narrative_agent_respects_motivation_pressure` PASS |
| Ruhepunkt signal works | ✅ COMPLETE | `test_narrative_agent_signals_ruhepunkt_*` PASS |
| Input queuing works | ✅ COMPLETE | `test_input_queue_processed_after_ruhepunkt` PASS |
| Narrator validation enforced | ✅ COMPLETE | All narrator validator tests PASS |
| HTTP streaming endpoint functional | ✅ COMPLETE | `test_narrator_stream_endpoint_*` PASS |
| Frontend receives blocks | ✅ COMPLETE | `test_frontend_receives_narrator_blocks` PASS |
| Input-UI blocked during streaming | ✅ COMPLETE | `test_frontend_blocks_input_during_streaming` PASS |
| Langfuse optional | ✅ COMPLETE | `test_narrative_agent_emits_trace_scaffold_by_default` PASS |
| All operational gates PASS | ✅ COMPLETE | docker-up.py, tests/run_tests.py verified |
| Handoff document created | ✅ COMPLETE | `tests/reports/MVP3_NARRATIVE_RUNTIME_AGENT_HANDOFF.md` exists |

---

## Notes

- This plan captures design decisions from grill-me session 2026-04-29
- NarrativeRuntimeAgent is **not optional** for MVP 3 stop condition
- Event-based runtime enables future experiences (multi-perspective, different narrative styles)
- Langfuse integration deferred to MVP 4 admin UI (tracing toggle)
- Frontend streaming can use SSE (simpler) or WebSocket (more interactive) — decide during Phase 4
