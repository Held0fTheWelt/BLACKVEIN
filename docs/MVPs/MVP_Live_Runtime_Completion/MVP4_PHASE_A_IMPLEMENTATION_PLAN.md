# MVP4 Phase A Implementation Plan

## Context

MVP4 Phase A ("Foundation & Data Collection") erweitert die bereits existierende `DiagnosticsEnvelope` Infrastruktur um drei neue Fähigkeiten aus dem grill-me Architectural Audit:

1. **Degradation Timeline** — Statt nur `degradation_signals: list[str]` brauchen wir eine strukturierte Timeline mit Severity-Levels, Timestamps und Recovery-Info
2. **Tiered Visibility** — `to_response(context=...)` Methode für Operator/Langfuse/Super-Admin
3. **Cost Summary** — `cost_summary` Feld (Nullen in Phase A, echte Werte in Phase B)

**Was bereits existiert (nicht neu bauen):**
- `ai_stack/diagnostics_envelope.py` — `DiagnosticsEnvelope` dataclass + `build_diagnostics_envelope()` ✅
- `world-engine/app/story_runtime/manager.py` — ruft bereits `build_diagnostics_envelope()` auf ✅
- `world-engine/app/api/http.py` — `/story/sessions/{session_id}/diagnostics-envelope` endpoint ✅
- `ai_stack/runtime_quality_semantics.py` — `canonical_quality_summary()`, `canonical_quality_class()` ✅
- `backend/app/observability/langfuse_adapter.py` — v4 SDK adapter, flush(), record_validation() ✅
- `tests/gates/test_goc_mvp04_observability_diagnostics_gate.py` — bestehende MVP4 gate tests ✅
- `world-engine/tests/test_mvp4_diagnostics_integration.py` — integration tests ✅

---

## Kritische Dateien

| Datei | Aktion | Zweck |
|---|---|---|
| `ai_stack/diagnostics_envelope.py` | ERWEITERN | DegradationEvent Dataclass + neue Felder + to_response() |
| `ai_stack/runtime_quality_semantics.py` | ERWEITERN | DegradationEvent Sammlung während Turn |
| `world-engine/app/story_runtime/manager.py` | ERWEITERN | DegradationEvents während Turn sammeln |
| `world-engine/app/api/http.py` | ERWEITERN | to_response(context=...) aufrufen vor Response |
| `tests/gates/test_goc_mvp04_observability_diagnostics_gate.py` | ERWEITERN | Tests für neue Felder |

---

## Implementierungsreihenfolge

### Schritt 1: `DegradationEvent` Dataclass + Erweiterung `DiagnosticsEnvelope`
**Datei**: `ai_stack/diagnostics_envelope.py`

**Hinzufügen:**
```python
@dataclass
class DegradationEvent:
    marker: str                          # "RETRY_ACTIVE", "FALLBACK_ACTIVE"
    severity: str                        # "minor", "moderate", "critical"
    timestamp: str                       # ISO8601
    recovery_successful: bool
    recovery_latency_ms: int | None = None
    context_snapshot: dict = field(default_factory=dict)  # z.B. {"ldss_turn": 42}
    span_ids: list[str] = field(default_factory=list)     # leer Phase A, Phase B füllt

    def to_dict(self) -> dict:
        return {
            "marker": self.marker,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "recovery_successful": self.recovery_successful,
            "recovery_latency_ms": self.recovery_latency_ms,
            "context_snapshot": self.context_snapshot,
            "span_ids": self.span_ids,
        }
```

**Erweitern `DiagnosticsEnvelope`:**
```python
# Neue Felder (nach bestehenden):
degradation_timeline: list[DegradationEvent] = field(default_factory=list)
cost_summary: dict = field(default_factory=lambda: {
    "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0
})
debug_payload: dict | None = None  # Super-Admin only, nie in Operator/Langfuse Response

# Neue Methode:
def to_response(self, context: str = "operator") -> dict:
    """Build response dict based on consumer context.
    
    context="operator"    → tiered visibility (hashes + costs redacted)
    context="langfuse"    → full technical data (debug_payload excluded)
    context="super_admin" → everything unredacted
    """
    base = self.to_dict()
    if context == "super_admin":
        return base
    # debug_payload NIEMALS in Langfuse oder Operator
    base.pop("debug_payload", None)
    if context == "langfuse":
        return base
    # Operator: hashes und costs redacten
    if "live_dramatic_scene_simulator" in base:
        base["live_dramatic_scene_simulator"]["input_hash"] = "[REDACTED]"
        base["live_dramatic_scene_simulator"]["output_hash"] = "[REDACTED]"
    base["player_input_hash"] = "[REDACTED]"
    base["cost_summary"] = "[REDACTED]"
    # degradation_timeline: span_ids redacten
    for event in base.get("degradation_timeline", []):
        event["span_ids"] = "[REDACTED]"
    return base
```

**Erweitern `to_dict()`** um neue Felder:
```python
"degradation_timeline": [e.to_dict() for e in self.degradation_timeline],
"cost_summary": dict(self.cost_summary),
"debug_payload": self.debug_payload,
```

**Erweitern `build_diagnostics_envelope()`** Signatur:
```python
def build_diagnostics_envelope(
    *,
    ...  # bestehende Parameter
    degradation_events: list[DegradationEvent] | None = None,  # NEU
) -> DiagnosticsEnvelope:
```
Und im Body: `degradation_timeline=degradation_events or []`

---

### Schritt 2: Degradation Events während Turn sammeln
**Datei**: `world-engine/app/story_runtime/manager.py`

In `_finalize_committed_turn()` (Zeile ~1960 wo `build_diagnostics_envelope` aufgerufen wird):

```python
# Vor dem build_diagnostics_envelope Aufruf:
from ai_stack.diagnostics_envelope import DegradationEvent
from datetime import datetime, timezone

degradation_events = []
# degradation_signals bereits vorhanden — aus quality_class/degradation_signals in graph_state
signals = graph_state.get("runtime_governance_surface", {}).get("degradation_signals", []) \
       or graph_state.get("quality", {}).get("degradation_signals", [])

for signal in signals:
    severity = "critical" if signal in ("execution_error", "graph_error") \
               else "moderate" if "fallback" in signal \
               else "minor"
    degradation_events.append(DegradationEvent(
        marker=signal.upper(),
        severity=severity,
        timestamp=datetime.now(timezone.utc).isoformat(),
        recovery_successful=graph_state.get("committed_result", {}).get("commit_applied", False),
        context_snapshot={"turn_number": commit_turn_number},
    ))

diag_envelope = build_diagnostics_envelope(
    ...  # bestehende Args
    degradation_events=degradation_events,  # NEU
)
```

---

### Schritt 3: HTTP Handler — to_response() aufrufen
**Datei**: `world-engine/app/api/http.py`

In `get_story_diagnostics_envelope()` und in der Turn-Execute Response:

```python
# Statt envelope (raw dict):
envelope_dict = envelope.to_response(context="operator")  # NEU
return {"session_id": session_id, "diagnostics_envelope": envelope_dict}
```

Für Langfuse (Phase B vorbereiten — jetzt nur Placeholder):
```python
# In execute_turn handler:
# Langfuse erhält in Phase B: envelope.to_response(context="langfuse")
# Phase A: nur Logging
```

---

### Schritt 4: Tests erweitern
**Datei**: `tests/gates/test_goc_mvp04_observability_diagnostics_gate.py`

Neue Tests hinzufügen (bestehende nicht brechen):

```python
@pytest.mark.mvp4
def test_mvp04_degradation_timeline_has_severity_and_timestamp():
    """degradation_timeline events include marker, severity, timestamp, recovery."""
    env = _build_test_envelope("annette")
    d = env.to_dict()
    # Even with no degradation, field must exist
    assert "degradation_timeline" in d
    assert isinstance(d["degradation_timeline"], list)

@pytest.mark.mvp4
def test_mvp04_cost_summary_present_with_zeros_in_phase_a():
    """cost_summary field exists (zeros in Phase A, real values in Phase B)."""
    env = _build_test_envelope("annette")
    d = env.to_dict()
    assert "cost_summary" in d
    assert d["cost_summary"]["input_tokens"] == 0
    assert d["cost_summary"]["output_tokens"] == 0
    assert d["cost_summary"]["cost_usd"] == 0.0

@pytest.mark.mvp4
def test_mvp04_to_response_operator_redacts_hashes_and_costs():
    """to_response('operator') hides input_hash, output_hash, cost_summary."""
    env = _build_test_envelope("annette")
    op = env.to_response(context="operator")
    # Hashes redacted
    ldss = op.get("live_dramatic_scene_simulator", {})
    assert ldss.get("input_hash") == "[REDACTED]"
    assert ldss.get("output_hash") == "[REDACTED]"
    # Cost redacted
    assert op.get("cost_summary") == "[REDACTED]"
    # debug_payload not present
    assert "debug_payload" not in op

@pytest.mark.mvp4
def test_mvp04_to_response_langfuse_has_full_technical_data():
    """to_response('langfuse') shows hashes + costs, excludes debug_payload."""
    env = _build_test_envelope("annette")
    lf = env.to_response(context="langfuse")
    # Hashes visible
    ldss = lf.get("live_dramatic_scene_simulator", {})
    assert ldss.get("input_hash") != "[REDACTED]"
    # debug_payload excluded
    assert "debug_payload" not in lf

@pytest.mark.mvp4
def test_mvp04_to_response_super_admin_has_everything():
    """to_response('super_admin') returns complete unredacted envelope."""
    env = _build_test_envelope("annette")
    env.debug_payload = {"raw_data": "sensitive"}
    sa = env.to_response(context="super_admin")
    assert sa.get("debug_payload") == {"raw_data": "sensitive"}
```

---

## Abhängigkeiten

```
Schritt 1 (DiagnosticsEnvelope erweitern)
    ↓
Schritt 2 (Manager sammelt DegradationEvents)
    ↓
Schritt 3 (HTTP Handler verwendet to_response())
    ↓
Schritt 4 (Tests)
```

**Phase B braucht von Phase A:**
- `DegradationEvent.span_ids` bereit für Phase B Span-IDs
- `cost_summary` Feld bereit für Phase B echte Werte
- `to_response(context="langfuse")` bereit für Phase B Langfuse SDK Aufrufe
- Bestehende Gate Tests weiterhin grün

---

## Stop Gate (Phase A)

Phase A ist abgeschlossen wenn:
1. `python tests/run_tests.py --mvp4` — alle MVP4 Tests grün (bestehende + neue)
2. `env.to_response("operator")` → hashes/costs redacted ✅
3. `env.to_response("langfuse")` → hashes sichtbar, debug_payload absent ✅
4. `env.to_response("super_admin")` → vollständig unredacted ✅
5. `env.degradation_timeline` — Feld vorhanden (leer wenn keine Degradation)
6. `env.cost_summary` — Feld vorhanden mit Nullen
7. Kein bestehender Test bricht

---

## Nicht in Phase A

- Echte Langfuse SDK Spans (Phase B)
- Echte Cost-Werte (Phase B)
- span_ids in DegradationEvent befüllen (Phase B)
- Admin UIs (Phase C)
- Token Budget Enforcement (Phase C)
- Evaluation Pipeline (Phase C)
