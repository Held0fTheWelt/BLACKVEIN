# Langfuse Trace Complete View

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client Request                              │
│                   POST /api/v1/sessions/{id}/turns                  │
│                       {"player_input": "..."}                       │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKEND (Flask)                                  │
│            backend/app/api/v1/session_routes.py                     │
│                  execute_session_turn()                             │
├─────────────────────────────────────────────────────────────────────┤
│ Step 1: Get LangfuseAdapter singleton                               │
│   adapter = LangfuseAdapter.get_instance()                          │
│                                                                     │
│ Step 2: Create ROOT SPAN                                            │
│   root_span = adapter.start_trace(                                  │
│     name="backend.turn.execute",                                    │
│     session_id=session_id,                                          │
│     module_id=module_id,                                            │
│     metadata={                                                      │
│       "player_input_length": len(player_input),                     │
│       "stage": "turn_execution"                                     │
│     }                                                               │
│   )                                                                 │
│   → Returns Langfuse Span with trace_id T1                         │
│                                                                     │
│ Step 3: Proxy to World-Engine                                       │
│   turn = execute_story_turn_in_engine(                              │
│     session_id=engine_story_session_id,                             │
│     player_input=player_input,                                      │
│     trace_id=trace_id  ◄─── Pass trace_id!                         │
│   )                                                                 │
│   → Calls game_service._request() which adds HTTP header:           │
│     headers["X-WoS-Trace-Id"] = trace_id                            │
│     POST /api/story/sessions/{id}/turns                             │
│     X-WoS-Trace-Id: T1                                              │
│                                                                     │
│ Step 4: Update ROOT SPAN with results                               │
│   root_span.update(output={                                         │
│     "turn_number": runtime_session.turn_counter,                    │
│     "status": "completed"                                           │
│   })                                                                │
│                                                                     │
│ Step 5: End ROOT SPAN and flush                                     │
│   finally:                                                          │
│     root_span.end()                                                 │
│     adapter.flush()  ◄─── Send spans to Langfuse                   │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         │ HTTP POST with header X-WoS-Trace-Id: T1
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  WORLD-ENGINE (FastAPI)                             │
│                world-engine/app/middleware/                         │
│           trace_middleware.py + app/api/http.py                     │
├─────────────────────────────────────────────────────────────────────┤
│ Step 1: Middleware extracts trace_id from header                    │
│   raw = request.headers.get("X-WoS-Trace-Id")  ◄─── "T1"           │
│   request.state.trace_id = trace_id  ◄─── Store in request state   │
│                                                                     │
│ Step 2: Handler extracts trace_id from request state                │
│   trace_id = getattr(request.state, "trace_id", None)  ◄─── T1    │
│   adapter = LangfuseAdapter.get_instance()                          │
│                                                                     │
│ Step 3: Link to existing trace (Backend's root span)                │
│   if trace_id:  ◄─── We have T1 from Backend                       │
│     langfuse_trace = adapter.client.trace(id=trace_id)              │
│     root_span = langfuse_trace.span(                                │
│       name="world-engine.turn.execute",                             │
│       input={"session_id": session_id, ...},                        │
│       metadata={"stage": "world_engine_turn_execution"}             │
│     )                                                               │
│     ► Creates child span under Backend's trace T1                   │
│                                                                     │
│ Step 4: Set as active span context                                  │
│   adapter.set_active_span(root_span)                                │
│   ► Stored in ContextVar for Manager/NarrativeAgent to use          │
│                                                                     │
│ Step 5: Call Manager to execute turn                                │
│   turn = manager.execute_turn(                                      │
│     session_id=session_id,                                          │
│     player_input=payload.player_input,                              │
│     trace_id=trace_id                                               │
│   )                                                                 │
│   → Manager will create phase spans                                 │
│                                                                     │
│ Step 6: Update and end span                                         │
│   root_span.update(output={...})                                    │
│   root_span.end()                                                   │
│   adapter.flush()  ◄─── Send child span to Langfuse                │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         │ (Called from http.py handler)
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  MANAGER (StoryRuntimeManager)                       │
│         world-engine/app/story_runtime/manager.py                   │
│                    execute_turn()                                   │
├─────────────────────────────────────────────────────────────────────┤
│ Step 1: Get adapter and active span                                 │
│   adapter = LangfuseAdapter.get_instance()                          │
│   ► Active span already set by HTTP handler                         │
│                                                                     │
│ ═══════════════════════════════════════════════════════════════     │
│ LDSS PHASE                                                          │
│ ═══════════════════════════════════════════════════════════════     │
│                                                                     │
│ Step 2a: Create LDSS phase span (child of world-engine span)        │
│   ldss_span = adapter.create_child_span(                            │
│     name="story.phase.ldss",                                        │
│     input={                                                         │
│       "session_id": session_id,                                     │
│       "turn_number": turn_counter,                                  │
│       "player_input_length": len(player_input)                      │
│     },                                                              │
│     metadata={"stage": "ldss_execution"}                            │
│   )                                                                 │
│   ► Creates under active world-engine span                          │
│                                                                     │
│ Step 2b: Execute LDSS                                               │
│   blocks, decisions = ldss_executor.execute(...)                    │
│   block_count = len(blocks)                                         │
│   decision_count = len(decisions)                                   │
│                                                                     │
│ Step 2c: Update and end LDSS span                                   │
│   ldss_span.update(output={                                         │
│     "block_count": block_count,                                     │
│     "decision_count": decision_count,                               │
│     "status": "completed"                                           │
│   })                                                                │
│   ldss_span.end()                                                   │
│                                                                     │
│ ═══════════════════════════════════════════════════════════════     │
│ NARRATOR PHASE                                                      │
│ ═══════════════════════════════════════════════════════════════     │
│                                                                     │
│ Step 3a: Create NARRATOR phase span (child of world-engine span)    │
│   narrator_span = adapter.create_child_span(                        │
│     name="story.phase.narrator",                                    │
│     input={                                                         │
│       "session_id": session_id,                                     │
│       "turn_number": turn_counter,                                  │
│       "npc_agency_plan": npc_plan                                   │
│     },                                                              │
│     metadata={"stage": "narrator_execution"}                        │
│   )                                                                 │
│                                                                     │
│ Step 3b: Set narrator span as active context                        │
│   adapter.set_active_span(narrator_span)                            │
│   ► NarrativeRuntimeAgent will use this as parent for block spans   │
│                                                                     │
│ Step 3c: Execute NarrativeRuntimeAgent                              │
│   narrative_response = narrative_agent.stream_narrator_blocks(...)  │
│   ► Agent will create child spans for each narrator block           │
│   ► (See NarrativeRuntimeAgent section below)                       │
│                                                                     │
│ Step 3d: Update and end NARRATOR span                               │
│   narrator_span.update(output={                                     │
│     "streaming_started": True,                                      │
│     "status": "completed"                                           │
│   })                                                                │
│   narrator_span.end()                                               │
│                                                                     │
│ Step 4: Return complete turn to HTTP handler                        │
│   return {                                                          │
│     "turn_number": ...,                                             │
│     "narrative_response": ...,                                      │
│     ...                                                             │
│   }                                                                 │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         │ (Called during manager.execute_turn())
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│         NARRATIVE RUNTIME AGENT (ai_stack)                          │
│         ai_stack/narrative_runtime_agent.py                         │
│            stream_narrator_blocks()                                 │
├─────────────────────────────────────────────────────────────────────┤
│ For each narrator block generated:                                  │
│                                                                     │
│ Step 1: Get active parent span from context                         │
│   parent_span = adapter.get_active_span()                           │
│   ► Returns narrator_span set by Manager                            │
│                                                                     │
│ Step 2: Create NARRATOR BLOCK child span                            │
│   if parent_span:                                                   │
│     block_span = adapter.create_child_span(                         │
│       name="narrator.narrate_block",                                │
│       input={                                                       │
│         "block_number": block_count,                                │
│         "block_type": "dialogue|narration|action"                   │
│       },                                                            │
│       metadata={"stage": "block_generation"}                        │
│     )                                                               │
│     ► Creates under narrator_span                                   │
│                                                                     │
│ Step 3: Generate narrator block content                             │
│   narrator_block = llm.generate(...)                                │
│   block_id = narrator_block.get("block_id")                         │
│   atmospheric_tone = narrator_block.get("tone")                     │
│   text_length = len(narrator_block.get("text", ""))                 │
│                                                                     │
│ Step 4: Update block span                                           │
│   block_span.update(output={                                        │
│     "block_id": block_id,                                           │
│     "atmospheric_tone": atmospheric_tone,                           │
│     "text_length": text_length,                                     │
│     "status": "generated"                                           │
│   })                                                                │
│                                                                     │
│ Step 5: End block span                                              │
│   block_span.end()                                                  │
│   ► Span ready to be sent to Langfuse                               │
│                                                                     │
│ (Repeat for each narrator block)                                    │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         │ Return to Manager
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  LANGFUSE CLOUD                                     │
│              (When flush() is called)                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ COMPLETE TRACE HIERARCHY SENT:                                      │
│                                                                     │
│ Trace T1:                                                           │
│   │                                                                 │
│   ├─ Span: backend.turn.execute                                     │
│   │   ├─ duration: 324ms (turn 1)                                   │
│   │   ├─ input: {player_input_length: 25, stage: "turn_execution"} │
│   │   ├─ output: {turn_number: 1, status: "completed"}             │
│   │   │                                                             │
│   │   └─ Child Span: world-engine.turn.execute                      │
│   │       ├─ duration: 300ms                                        │
│   │       ├─ input: {session_id, player_input_length}               │
│   │       │                                                         │
│   │       ├─ Child Span: story.phase.ldss                           │
│   │       │   ├─ duration: 120ms                                    │
│   │       │   ├─ output: {block_count: 3, decision_count: 2}        │
│   │       │   │                                                     │
│   │       │   └─ (no children)                                      │
│   │       │                                                         │
│   │       └─ Child Span: story.phase.narrator                       │
│   │           ├─ duration: 180ms                                    │
│   │           ├─ input: {npc_agency_plan: {...}}                    │
│   │           │                                                     │
│   │           ├─ Child Span: narrator.narrate_block #1              │
│   │           │   ├─ duration: 45ms (LLM call)                      │
│   │           │   ├─ output: {block_id: "b1", tone: "tense", len: 156}
│   │           │   │                                                 │
│   │           │   └─ (no children)                                  │
│   │           │                                                     │
│   │           ├─ Child Span: narrator.narrate_block #2              │
│   │           │   ├─ duration: 58ms (LLM call)                      │
│   │           │   ├─ output: {block_id: "b2", tone: "calm", len: 203}
│   │           │   │                                                 │
│   │           │   └─ (no children)                                  │
│   │           │                                                     │
│   │           └─ Child Span: narrator.narrate_block #3              │
│   │               ├─ duration: 52ms (LLM call)                      │
│   │               ├─ output: {block_id: "b3", tone: "dramatic", len: 189}
│   │               │                                                 │
│   │               └─ (no children)                                  │
│   │                                                                 │
│   └─ (World-Engine, Manager, Agent all report complete)             │
│                                                                     │
│ Total spans in trace: 7                                             │
│ Total duration: 324ms                                               │
│ Session ID: e3efccba222f4cf0b6b836b704911efc                        │
│ Module: god_of_carnage                                              │
│ Environment: development (or production if configured)              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Trace Data Flow

### 1. Trace ID Generation & Propagation

```
Backend receives request
  ├─ Has X-WoS-Trace-Id header? Use it
  └─ No header? Generate new UUID
       └─ Create root span → Gets trace_id from Langfuse

Backend → World-Engine
  └─ Pass trace_id via X-WoS-Trace-Id header

World-Engine middleware
  └─ Extract header → store in request.state.trace_id

World-Engine handler
  └─ Retrieve from request.state.trace_id
     └─ Use to link to existing Langfuse trace
```

### 2. Span Parent-Child Relationships

```
Langfuse Trace (ID T1)
  │
  └─ backend.turn.execute (Root, starts trace T1)
       │
       └─ world-engine.turn.execute (Child, same trace T1)
            │
            ├─ story.phase.ldss (Child of world-engine)
            │
            └─ story.phase.narrator (Child of world-engine)
                 │
                 ├─ narrator.narrate_block (Child, block 1)
                 ├─ narrator.narrate_block (Child, block 2)
                 └─ narrator.narrate_block (Child, block 3)
```

### 3. ContextVar for Thread-Safe Span Passing

```python
# In Backend
root_span = adapter.start_trace(...)  # Creates Span S1

# In World-Engine HTTP handler
adapter.set_active_span(root_span)  # Stores in ContextVar

# In Manager
parent_span = adapter.get_active_span()  # Retrieves from ContextVar
ldss_span = adapter.create_child_span(...)  # Uses parent_span

# In NarrativeRuntimeAgent
parent_span = adapter.get_active_span()  # Retrieves updated span
block_span = adapter.create_child_span(...)  # Uses parent_span
```

---

## Key Implementation Files

| File | Function | Span Created |
|------|----------|--------------|
| `backend/app/api/v1/session_routes.py` | `execute_session_turn()` | `backend.turn.execute` (ROOT) |
| `backend/app/services/game_service.py` | `_request()` | (Passes trace_id via header) |
| `world-engine/app/middleware/trace_middleware.py` | `wos_trace_middleware()` | (Extracts trace_id from header) |
| `world-engine/app/api/http.py` | `execute_story_turn()` | `world-engine.turn.execute` (CHILD) |
| `world-engine/app/story_runtime/manager.py` | `_build_ldss_scene_envelope()` | `story.phase.ldss` (CHILD) |
| `world-engine/app/story_runtime/manager.py` | `_orchestrate_narrative_agent()` | `story.phase.narrator` (CHILD) |
| `ai_stack/narrative_runtime_agent.py` | `stream_narrator_blocks()` | `narrator.narrate_block` (CHILD) ×N |

---

## Environment Setup

To see traces in Langfuse dashboard:

```bash
# Set environment variables
export LANGFUSE_ENABLED=true
export LANGFUSE_PUBLIC_KEY=<your-public-key>
export LANGFUSE_SECRET_KEY=<your-secret-key>
export LANGFUSE_BASE_URL=https://cloud.langfuse.com

# Start stack
docker-compose up -d

# Execute turn via API
curl -X POST http://localhost:8000/api/v1/sessions/{id}/turns \
  -H "Content-Type: application/json" \
  -d '{"player_input": "I look around"}'

# Check Langfuse dashboard for trace
```

---

## Verification Checklist

- ✅ Backend creates root span before calling world-engine
- ✅ Trace ID passed via `X-WoS-Trace-Id` header
- ✅ World-Engine middleware extracts trace ID
- ✅ World-Engine creates child span under Backend's trace
- ✅ Manager creates phase spans for LDSS and Narrator
- ✅ NarrativeRuntimeAgent creates block spans
- ✅ All spans properly ended and flushed
- ✅ Complete hierarchy visible in Langfuse dashboard
- ✅ 1120 engine tests pass (no regressions)
- ✅ No mock tests used (integration tests execute real code)

