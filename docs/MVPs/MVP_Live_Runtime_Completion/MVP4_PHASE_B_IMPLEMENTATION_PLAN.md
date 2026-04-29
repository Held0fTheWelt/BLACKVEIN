# MVP4 Phase B Implementation Plan

## Context

MVP4 Phase B ("Instrumentation & Real Langfuse Spans") implementiert echte Langfuse SDK Aufrufe und Token/Cost-Tracking. Phase A Voraussetzungen müssen erfüllt sein (DiagnosticsEnvelope mit Degradation Timeline, Cost Summary, Tiered Visibility).

**Hauptziele:**
1. Echte Langfuse Spans emittieren (HTTP root, story manager children, LDSS, Narrator)
2. Per-Span Token/Cost Attribution (input, output, model, cost_usd)
3. Session-Level Cost Aggregation
4. Hierarchical Real Costs in Langfuse (per span + rollup)
5. Trace Quality Standards (mandatory input/output, meaningful names, type clarity)
6. Span Filtering bereit stellen (all by default, multi-select für Operator)

**Was bereits existiert (nicht neu bauen):**
- `backend/app/observability/langfuse_adapter.py` — v4 SDK adapter, flush(), record_validation() ✅
- `ai_stack/diagnostics_envelope.py` — Phase A: to_response() mit tiered visibility ✅
- `world-engine/app/story_runtime/manager.py` — Phase A: DegradationEvents Sammlung ✅
- `ai_stack/runtime_quality_semantics.py` — Quality computation ✅
- Existing trace context variable infrastructure ✅

---

## Kritische Dateien

| Datei | Aktion | Zweck |
|---|---|---|
| `world-engine/app/api/http.py` | ERWEITERN | Root span `story.turn.execute` + env tags |
| `world-engine/app/story_runtime/manager.py` | ERWEITERN | Child spans für jede Phase + Langfuse toggle |
| `ai_stack/live_dramatic_scene_simulator.py` | ERWEITERN | LDSS decision spans + token tracking |
| `ai_stack/narrative_runtime_agent.py` | ERWEITERN | Narrator block spans + token tracking |
| `ai_stack/diagnostics_envelope.py` | ERWEITERN | Real cost_summary + hierarchical rollup |
| `backend/app/observability/langfuse_adapter.py` | ERWEITERN | Cost tracking methods |
| `tests/gates/test_goc_mvp04_observability_diagnostics_gate.py` | ERWEITERN | Tests für Langfuse Spans + Costs |

---

## Implementierungsreihenfolge

### Schritt 1: HTTP Handler Root Span + Environment Tags
**Datei**: `world-engine/app/api/http.py`

In `execute_turn()` handler (am Anfang):

```python
from datetime import datetime, timezone
from langfuse import Langfuse

# Root span erstellen (wenn LANGFUSE_ENABLED oder per-session toggle)
if should_enable_langfuse_tracing(session_id):
    langfuse = Langfuse()
    root_span = langfuse.span(
        name="story.turn.execute",
        input={
            "session_id": session_id,
            "turn_number": turn_number,
            "player_input": player_input[:100],  # truncate for logging
        },
        metadata={
            "player_id": player_id,
            "scene_id": scene_id,
            "turn_number": turn_number,
        },
        tags=["story-execution", environment],  # environment = LANGFUSE_ENVIRONMENT
    )
    trace_id = root_span.trace_id
    
    # Context setzen für child spans
    set_trace_context(trace_id, root_span)
else:
    trace_id = generate_json_scaffold_trace_id()
    root_span = None

try:
    # existing turn execution logic...
    graph_state = execute_story_graph(...)
    
    # Build diagnostics envelope mit echten Costs
    diag_envelope = build_diagnostics_envelope(
        ...existing args...,
        trace_id=trace_id,
    )
    
    # Response envelope.to_response(context="langfuse") wenn Langfuse aktiv
    if root_span:
        response_dict = diag_envelope.to_response(context="langfuse")
        root_span.end(output=response_dict)
    else:
        response_dict = diag_envelope.to_response(context="operator")
    
    return response_dict
    
finally:
    if root_span:
        langfuse.flush()
```

**Ergänzen `build_diagnostics_envelope()`** Signatur:
```python
def build_diagnostics_envelope(
    *,
    ...existing params...,
    trace_id: str | None = None,  # NEU
) -> DiagnosticsEnvelope:
    # Speichere trace_id in envelope
```

---

### Schritt 2: Story Manager Child Spans + Cost Tracking
**Datei**: `world-engine/app/story_runtime/manager.py`

In `_execute_story_phases()` oder `_finalize_committed_turn()`:

```python
from backend.app.observability.langfuse_adapter import get_current_span, create_child_span

# Phase spans (profile → lanes → LDSS → narrator → affordance → state delta → commit)
class StoryPhaseSpans:
    def __init__(self, root_span):
        self.root_span = root_span
        self.spans = {}
    
    def start_phase(self, phase_name: str):
        if self.root_span:
            span = create_child_span(
                parent_span=self.root_span,
                name=f"story.phase.{phase_name}",
                metadata={"phase": phase_name},
            )
            self.spans[phase_name] = span
            return span
        return None
    
    def end_phase(self, phase_name: str, metadata: dict):
        span = self.spans.get(phase_name)
        if span:
            span.end(metadata=metadata)

# In _execute_story_phases():
phase_spans = StoryPhaseSpans(get_current_span())

# Profile phase
span = phase_spans.start_phase("profile")
profile_result = execute_profile_phase(graph_state)
phase_spans.end_phase("profile", {
    "profile_tokens": profile_result.get("tokens_used", 0),
    "profile_cost": profile_result.get("cost", 0.0),
})

# Lanes phase
span = phase_spans.start_phase("lanes")
lanes_result = execute_lanes_phase(graph_state)
phase_spans.end_phase("lanes", {
    "lanes_tokens": lanes_result.get("tokens_used", 0),
    "lanes_cost": lanes_result.get("cost", 0.0),
})

# LDSS phase (separate span)
span = phase_spans.start_phase("ldss")
ldss_result = execute_ldss_phase(graph_state)
phase_spans.end_phase("ldss", {
    "ldss_tokens": ldss_result.get("tokens_used", 0),
    "ldss_cost": ldss_result.get("cost", 0.0),
})

# ... continue for narrator, affordance, state_delta, commit phases

# Aggregiere Costs für cost_summary
total_tokens_input = sum(phase["tokens_input"] for phase in [profile_result, lanes_result, ldss_result, ...])
total_tokens_output = sum(phase["tokens_output"] for phase in [profile_result, lanes_result, ldss_result, ...])
total_cost = sum(phase["cost"] for phase in [profile_result, lanes_result, ldss_result, ...])

# Überweise an DiagnosticsEnvelope
degradation_events = collect_degradation_events(graph_state)
cost_summary = {
    "input_tokens": total_tokens_input,
    "output_tokens": total_tokens_output,
    "cost_usd": total_cost,
    "cost_breakdown": {
        "profile": profile_result.get("cost", 0.0),
        "lanes": lanes_result.get("cost", 0.0),
        "ldss": ldss_result.get("cost", 0.0),
        "narrator": narrator_result.get("cost", 0.0),
        "affordance": affordance_result.get("cost", 0.0),
        "state_delta": state_delta_result.get("cost", 0.0),
        "commit": commit_result.get("cost", 0.0),
    }
}

diag_envelope = build_diagnostics_envelope(
    ...existing args...,
    degradation_events=degradation_events,
    cost_summary=cost_summary,
)
```

---

### Schritt 3: LDSS Decision Spans + Token Tracking
**Datei**: `ai_stack/live_dramatic_scene_simulator.py`

In `simulate_scene()` oder `make_decision()`:

```python
from backend.app.observability.langfuse_adapter import get_current_span, create_child_span

def make_decision(decision_context: dict) -> dict:
    """Make LDSS decision with Langfuse span tracking."""
    
    parent_span = get_current_span()
    if parent_span:
        span = create_child_span(
            parent_span=parent_span,
            name="ldss.decision",
            input={
                "context": decision_context.get("context", ""),
                "available_actions": len(decision_context.get("actions", [])),
            },
            metadata={
                "decision_type": decision_context.get("type", "unknown"),
                "turn_number": decision_context.get("turn_number", 0),
            },
        )
    else:
        span = None
    
    try:
        # Call LLM for decision
        llm_response = call_llm_for_decision(decision_context)
        
        # Track tokens
        input_tokens = llm_response.get("usage", {}).get("prompt_tokens", 0)
        output_tokens = llm_response.get("usage", {}).get("completion_tokens", 0)
        model = llm_response.get("model", "unknown")
        
        # Calculate cost (using model's pricing)
        cost = calculate_token_cost(model, input_tokens, output_tokens)
        
        decision = parse_decision(llm_response)
        
        # Log to span
        if span:
            span.end(
                output={
                    "decision": decision,
                    "confidence": decision.get("confidence", 0.0),
                },
                metadata={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "model": model,
                    "cost_usd": cost,
                    "latency_ms": llm_response.get("latency_ms", 0),
                }
            )
        
        return {
            "decision": decision,
            "tokens_input": input_tokens,
            "tokens_output": output_tokens,
            "cost": cost,
            "model": model,
        }
        
    except Exception as e:
        if span:
            span.end(
                output={"error": str(e)},
                metadata={"error": True}
            )
        raise

def simulate_scene(scene_input: dict) -> dict:
    """Simulate scene with LDSS logic and cost tracking."""
    
    parent_span = get_current_span()
    if parent_span:
        span = create_child_span(
            parent_span=parent_span,
            name="ldss.simulate_scene",
            input={
                "scene_id": scene_input.get("scene_id"),
                "scene_type": scene_input.get("scene_type"),
            },
            metadata={
                "scene_id": scene_input.get("scene_id"),
            },
        )
    else:
        span = None
    
    try:
        total_tokens_input = 0
        total_tokens_output = 0
        total_cost = 0.0
        decisions = []
        
        # Make multiple decisions (each tracked)
        for i, decision_context in enumerate(extract_decision_contexts(scene_input)):
            decision_result = make_decision(decision_context)
            decisions.append(decision_result["decision"])
            total_tokens_input += decision_result["tokens_input"]
            total_tokens_output += decision_result["tokens_output"]
            total_cost += decision_result["cost"]
        
        # Build scene response
        scene_output = {
            "scene_text": compose_scene_text(decisions),
            "decisions": decisions,
        }
        
        if span:
            span.end(
                output={
                    "scene_text": scene_output["scene_text"][:200],  # truncate
                    "decision_count": len(decisions),
                },
                metadata={
                    "input_tokens": total_tokens_input,
                    "output_tokens": total_tokens_output,
                    "cost_usd": total_cost,
                    "decision_count": len(decisions),
                }
            )
        
        return {
            "scene_output": scene_output,
            "tokens_input": total_tokens_input,
            "tokens_output": total_tokens_output,
            "cost": total_cost,
        }
        
    except Exception as e:
        if span:
            span.end(output={"error": str(e)}, metadata={"error": True})
        raise
```

---

### Schritt 4: Narrator Block Spans + Token Tracking
**Datei**: `ai_stack/narrative_runtime_agent.py`

In `narrate_block()` oder `execute_narrative()`:

```python
from backend.app.observability.langfuse_adapter import get_current_span, create_child_span

def narrate_block(block_context: dict) -> dict:
    """Narrate a narrative block with Langfuse span tracking."""
    
    parent_span = get_current_span()
    if parent_span:
        span = create_child_span(
            parent_span=parent_span,
            name="narrator.narrate_block",
            input={
                "block_type": block_context.get("type"),
                "block_id": block_context.get("id"),
            },
            metadata={
                "block_type": block_context.get("type"),
                "block_id": block_context.get("id"),
            },
        )
    else:
        span = None
    
    try:
        # Call LLM for narration
        llm_response = call_llm_for_narration(block_context)
        
        # Track tokens
        input_tokens = llm_response.get("usage", {}).get("prompt_tokens", 0)
        output_tokens = llm_response.get("usage", {}).get("completion_tokens", 0)
        model = llm_response.get("model", "unknown")
        cost = calculate_token_cost(model, input_tokens, output_tokens)
        
        narration = llm_response.get("text", "")
        
        # Log to span
        if span:
            span.end(
                output={
                    "narration": narration[:200],  # truncate for logging
                    "narration_length": len(narration),
                },
                metadata={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "model": model,
                    "cost_usd": cost,
                    "latency_ms": llm_response.get("latency_ms", 0),
                    "narration_length": len(narration),
                }
            )
        
        return {
            "narration": narration,
            "tokens_input": input_tokens,
            "tokens_output": output_tokens,
            "cost": cost,
            "model": model,
        }
        
    except Exception as e:
        if span:
            span.end(output={"error": str(e)}, metadata={"error": True})
        raise
```

---

### Schritt 5: OTEL Filtering Configuration
**Datei**: `backend/app/observability/langfuse_adapter.py` (oder neue `otel_config.py`)

```python
# Multi-Select Configuration für Span Filtering
class OTELSpanFilter:
    """Control which spans are collected."""
    
    FILTER_TYPES = {
        "HTTP": "http_client, http_server",
        "DATABASE": "db_client, db_server",
        "FRAMEWORK": "asgi, fastapi",
        "LLM": "llm_calls",
        "CUSTOM": "custom_spans",
    }
    
    def __init__(self, enabled_filters: set[str] | None = None):
        # Default: All spans enabled
        self.enabled_filters = enabled_filters or set(self.FILTER_TYPES.keys())
    
    def should_collect_span(self, span_type: str) -> bool:
        """Check if span type should be collected."""
        # Map span type to filter category
        if span_type in ["http_client", "http_server"]:
            return "HTTP" in self.enabled_filters
        elif span_type in ["db_client", "db_server"]:
            return "DATABASE" in self.enabled_filters
        # ... etc
        return True  # Default: collect all

# API to enable/disable filters per-session
def set_session_span_filters(session_id: str, enabled_filters: set[str]):
    """Admin can configure span filters per-investigation."""
    # Store in session config
    session_config = get_session_config(session_id)
    session_config["span_filters"] = enabled_filters
    save_session_config(session_id, session_config)

def get_session_span_filters(session_id: str) -> set[str]:
    """Get active filters for session (default: all enabled)."""
    session_config = get_session_config(session_id)
    return session_config.get("span_filters", set(OTELSpanFilter.FILTER_TYPES.keys()))
```

---

### Schritt 6: Tests erweitern
**Datei**: `tests/gates/test_goc_mvp04_observability_diagnostics_gate.py`

```python
@pytest.mark.mvp4
def test_mvp04_root_span_created_with_environment_tags():
    """HTTP handler creates root span with LANGFUSE_ENVIRONMENT tags."""
    with enable_langfuse_for_test():
        response = execute_turn(session_id="test_session", turn_number=1)
        
        spans = fetch_spans_from_langfuse(trace_id=response["trace_id"])
        root_span = spans[0]
        
        assert root_span["name"] == "story.turn.execute"
        assert root_span["tags"] != None
        assert "story-execution" in root_span["tags"]

@pytest.mark.mvp4
def test_mvp04_child_spans_hierarchy():
    """Story manager creates child spans with proper hierarchy."""
    with enable_langfuse_for_test():
        response = execute_turn(session_id="test_session", turn_number=1)
        
        spans = fetch_spans_from_langfuse(trace_id=response["trace_id"])
        
        # Check for expected phases
        phase_names = [s["name"] for s in spans]
        assert "story.phase.profile" in phase_names
        assert "story.phase.ldss" in phase_names
        assert "story.phase.narrator" in phase_names

@pytest.mark.mvp4
def test_mvp04_ldss_decision_spans_with_token_tracking():
    """LDSS creates decision spans with input/output token counts."""
    with enable_langfuse_for_test():
        response = execute_turn(session_id="test_session", turn_number=1)
        
        spans = fetch_spans_from_langfuse(trace_id=response["trace_id"])
        decision_spans = [s for s in spans if "ldss.decision" in s["name"]]
        
        assert len(decision_spans) > 0
        for span in decision_spans:
            metadata = span.get("metadata", {})
            assert "input_tokens" in metadata
            assert "output_tokens" in metadata
            assert "cost_usd" in metadata

@pytest.mark.mvp4
def test_mvp04_cost_summary_in_diagnostics_envelope():
    """DiagnosticsEnvelope.cost_summary has real token/cost values in Phase B."""
    with enable_langfuse_for_test():
        response = execute_turn(session_id="test_session", turn_number=1)
        
        envelope = response["diagnostics_envelope"]
        cost_summary = envelope["cost_summary"]
        
        # Phase B should have real values (not zeros)
        assert cost_summary["input_tokens"] > 0
        assert cost_summary["output_tokens"] > 0
        assert cost_summary["cost_usd"] > 0.0
        assert "cost_breakdown" in cost_summary

@pytest.mark.mvp4
def test_mvp04_langfuse_context_shows_real_costs():
    """to_response('langfuse') shows real costs for RCA."""
    with enable_langfuse_for_test():
        envelope = build_test_envelope_with_real_costs()
        langfuse_response = envelope.to_response(context="langfuse")
        
        # Langfuse should see costs (not redacted)
        assert langfuse_response["cost_summary"] != "[REDACTED]"
        assert langfuse_response["cost_summary"]["cost_usd"] > 0.0

@pytest.mark.mvp4
def test_mvp04_operator_context_redacts_costs():
    """to_response('operator') redacts costs (security)."""
    envelope = build_test_envelope_with_real_costs()
    operator_response = envelope.to_response(context="operator")
    
    # Operator should not see costs
    assert operator_response["cost_summary"] == "[REDACTED]"

@pytest.mark.mvp4
def test_mvp04_span_filtering_all_by_default():
    """OTEL collector gathers all span types by default."""
    with enable_langfuse_for_test():
        response = execute_turn(session_id="test_session", turn_number=1)
        
        spans = fetch_spans_from_langfuse(trace_id=response["trace_id"])
        span_types = set(s.get("type", "custom") for s in spans)
        
        # Should include HTTP, DB, Framework, LLM, custom
        assert len(span_types) >= 3  # At least profile, ldss, narrator phases

@pytest.mark.mvp4
def test_mvp04_narrator_spans_with_narration_length():
    """Narrator spans include narration_length in metadata."""
    with enable_langfuse_for_test():
        response = execute_turn(session_id="test_session", turn_number=1)
        
        spans = fetch_spans_from_langfuse(trace_id=response["trace_id"])
        narrator_spans = [s for s in spans if "narrator" in s["name"]]
        
        assert len(narrator_spans) > 0
        for span in narrator_spans:
            metadata = span.get("metadata", {})
            assert "narration_length" in metadata
```

---

## Abhängigkeiten

```
Schritt 1 (HTTP Root Span + Env Tags)
    ↓
Schritt 2 (Story Manager Child Spans + Cost Tracking)
    ↓
Schritt 3 (LDSS Decision Spans + Tokens)
    ↓
Schritt 4 (Narrator Spans + Tokens)
    ↓
Schritt 5 (OTEL Filtering Configuration)
    ↓
Schritt 6 (Tests)
```

**Phase C braucht von Phase B:**
- Real spans + trace_ids für Langfuse dashboard
- Hierarchical cost_summary für cost-aware degradation
- Span filtering configuration für operator multi-select UI
- Real token counts für budget enforcement
- Langfuse SDK working + flushing properly

---

## Stop Gate (Phase B)

Phase B ist abgeschlossen wenn:
1. `python tests/run_tests.py --mvp4` — alle MVP4 Tests grün (bestehende + neue Phase B)
2. Langfuse Dashboard zeigt real traces mit proper hierarchy
3. `cost_summary` hat echte Token/Cost-Werte (nicht zeros)
4. `cost_breakdown` Feld zeigt Cost per Phase
5. Alle Phase A Tests weiterhin grün
6. to_response() contexts alle funktional (operator/langfuse/super_admin)
7. Langfuse SDK flush() works + no hanging spans
8. Span filter configuration in place, can be queried per session

---

## Nicht in Phase B

- Token Budget Enforcement (Phase C)
- Cost-aware Degradation (Phase C)
- Admin UIs (Phase C)
- Evaluation Pipeline (Phase C)
- Session Replay Debugging (Phase C)
- Audit Trail Multi-Select (Phase C)
