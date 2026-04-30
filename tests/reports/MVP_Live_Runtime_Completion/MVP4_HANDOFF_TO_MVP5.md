# MVP4 Handoff to MVP5

## Overview

This document specifies the contracts and infrastructure that MVP4 establishes for MVP5 consumption.

**Source MVP**: MVP4 (Observability, Diagnostics, Langfuse, Narrative Gov)  
**Target MVP**: MVP5 (Admin UI, Session Replay, Frontend Integration)  
**Date**: 2026-04-30  
**Status**: Ready for handoff

---

## 1. Contracts Provided by MVP4

### 1.1 DiagnosticsEnvelope Contract

**What MVP4 Provides**:
- Complete DiagnosticsEnvelope dataclass with all Phase A/B/C fields:
  - `story_session_id`, `turn_number`, `trace_id`
  - `player_input_hash`, `live_dramatic_scene_simulator` (with decision_count, scene_block_count, status)
  - `degradation_timeline` (list of DegradationEvent)
  - `cost_summary` (input_tokens, output_tokens, cost_usd, cost_breakdown)
  - `quality` (class, outcome, degradation_signals)
  - `langfuse_status`, `langfuse_trace_id`
  - `fallback_stage`, `actor_ownership`, `actor_lane_decision`, `dramatic_validation_decision`

**How MVP5 Consumes**:
- Retrieve via HTTP: `GET /api/v1/admin/mvp4/game/session/{session_id}/diagnostics-envelope`
- Deserialize into Django models or frontend state
- Display in admin dashboards, operator panels, session replay UI
- Use `to_response(context="super_admin")` for full debugging view

**Schema**:
```json
{
  "story_session_id": "session-uuid",
  "turn_number": 5,
  "trace_id": "trace-uuid",
  "quality": {
    "class": "normal|degraded|failed",
    "outcome": "ok|ok_with_degradation|failed",
    "degradation_signals": ["fallback_used", ...]
  },
  "cost_summary": {
    "input_tokens": 1200,
    "output_tokens": 350,
    "cost_usd": 0.035,
    "cost_breakdown": {
      "ldss": 0.025,
      "narrator": 0.008,
      "other": 0.002
    }
  },
  "degradation_timeline": [
    {
      "marker": "FALLBACK_USED",
      "severity": "moderate",
      "timestamp": "2026-04-30T12:00:00Z",
      "recovery_successful": true,
      "recovery_latency_ms": 150,
      "context_snapshot": {"turn_number": 5},
      "span_ids": ["span-1", "span-2"]
    }
  ],
  "langfuse_status": "enabled|disabled",
  "langfuse_trace_id": "trace-uuid-or-empty"
}
```

---

### 1.2 NarrativeGovSummary Contract

**What MVP4 Provides**:
- NarrativeGovSummary dataclass with health panel data:
  - `last_story_session_id`, `last_turn_number`, `last_trace_id`
  - `actor_lane_health` (visitor_present: bool)
  - `ldss_health` (status: "evidenced_live_path", scene_block_count, decision_count)
  - `npc_agency` (primary_responder_id, responder_priority_order, secondary_responder_ids)
  - `narrator_validation` (strictness_level, invalid_outputs_rejected_count)
  - `affordance_tier_tracking` (canonical_allowed, typical_allowed, similar_allowed, unadmitted_rejected_count)

**How MVP5 Consumes**:
- Retrieve via HTTP: `GET /api/v1/admin/narrative-gov/{session_id}/summary`
- Display in 6 Narrative Gov health panels (operator dashboard)
- Show real-time status and historical trends
- Use for operator decision-making about cost overrides, degradation strategies

**Schema**:
```json
{
  "last_story_session_id": "session-uuid",
  "last_turn_number": 5,
  "last_trace_id": "trace-uuid",
  "actor_lane_health": {
    "visitor_present": false,
    "human_actor_id": "annette",
    "human_actor_status": "active"
  },
  "ldss_health": {
    "status": "evidenced_live_path",
    "scene_block_count": 3,
    "decision_count": 12
  },
  "npc_agency": {
    "primary_responder_id": "alain",
    "responder_priority_order": ["veronique", "alain", "michel"],
    "secondary_responder_ids": ["michel"]
  }
}
```

---

### 1.3 Langfuse Trace Contract

**What MVP4 Provides**:
- Real Langfuse traces via v4 SDK adapter
- Span hierarchy: session → turn → LDSS → Narrator → individual blocks
- Each span tagged with: session_id, turn_number, trace_id, span_id, cost_usd, input_tokens, output_tokens
- Cost aggregation across spans
- Trace export (deterministic or via Langfuse dashboard)

**How MVP5 Consumes**:
- Query Langfuse dashboard for session traces
- Retrieve via `GET /api/v1/admin/mvp4/session/{session_id}/langfuse-export?format=json|html`
- Display in Session Replay UI (trace timeline, cost breakdown, span details)
- Use for RCA (root cause analysis) of degraded turns

**Expected Format**:
```json
{
  "trace_id": "trace-uuid",
  "session_id": "session-uuid",
  "turn_number": 5,
  "spans": [
    {
      "span_id": "span-1",
      "parent_span_id": null,
      "span_name": "ldss_invocation",
      "start_time": "2026-04-30T12:00:00Z",
      "end_time": "2026-04-30T12:00:01Z",
      "cost_usd": 0.025,
      "input_tokens": 800,
      "output_tokens": 200,
      "metadata": {"scene_block_count": 3, "decision_count": 12}
    },
    {
      "span_id": "span-2",
      "parent_span_id": "span-1",
      "span_name": "ldss_scene_block_1",
      "start_time": "2026-04-30T12:00:00.1Z",
      "end_time": "2026-04-30T12:00:00.5Z",
      "cost_usd": 0.008,
      "input_tokens": 250,
      "output_tokens": 75
    }
  ]
}
```

---

### 1.4 Evaluation & Quality Rubric Contract

**What MVP4 Provides**:
- QualityRubric with 4 dimensions (COHERENCE, AUTHENTICITY, PLAYER_AGENCY, IMMERSION)
- TurnScore dataclass for recording annotations
- EvaluationPipeline.record_turn_score() for storing operator feedback
- EvaluationPipeline.auto_tune_weights() for self-tuning
- Baseline regression detection

**How MVP5 Consumes**:
- Retrieve rubric via: `GET /api/v1/admin/mvp4/evaluation/rubric`
- Display annotation UI in Operator Dashboard
- Allow operator to score turns and provide feedback
- Auto-tuning happens via: `POST /api/v1/admin/mvp4/evaluation/weights/{session_id}/manual-tune`
- Query evaluation baseline via: `GET /api/v1/admin/mvp4/evaluation/baseline`

**Expected Use**:
```python
# MVP5 operator submits turn score
turn_score = TurnScore(
    turn_id="turn-5",
    session_id="session-uuid",
    scores={
        "coherence": 4.5,
        "authenticity": 4.0,
        "player_agency": 5.0,
        "immersion": 3.5
    },
    average_score=4.25,
    passed=True,
    annotated_by="operator_001",
    feedback_tags=["good_pacing", "authentic_voice"]
)
pipeline.record_turn_score(turn_score, "session-uuid")
```

---

### 1.5 Audit Trail Contract

**What MVP4 Provides**:
- OverrideAuditEvent for logging admin actions (7 event types)
- OverrideAuditConfig for granular control over what gets logged
- _log_override_event() function with configurable granularity
- Audit trail storage (session-keyed)

**How MVP5 Consumes**:
- Query audit history via: `GET /api/v1/admin/mvp4/overrides/{override_id}/audit-trail`
- Display in Override Management UI
- Show: who made the override, when, what impact, success/failure
- Log new overrides via: `POST /api/v1/admin/mvp4/overrides` (includes audit logging)

**Expected Format**:
```json
{
  "override_id": "override-uuid",
  "events": [
    {
      "event_type": "created",
      "timestamp": "2026-04-30T12:00:00Z",
      "admin_user": "operator_001",
      "reason": "Testing object admission tier"
    },
    {
      "event_type": "applied",
      "timestamp": "2026-04-30T12:00:01Z",
      "admin_user": "operator_001",
      "session_id": "session-uuid",
      "turn_number": 5,
      "metadata": {"result": "success"}
    },
    {
      "event_type": "accessed",
      "timestamp": "2026-04-30T12:00:30Z",
      "admin_user": "super_admin_001"
    }
  ]
}
```

---

## 2. Infrastructure Contracts

### 2.1 HTTP Endpoints (Provided by MVP4)

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/v1/admin/mvp4/game/session/{session_id}/diagnostics-envelope` | GET | Retrieve latest diagnostics | DiagnosticsEnvelope (JSON) |
| `/api/v1/admin/narrative-gov/{session_id}/summary` | GET | Get health panel summary | NarrativeGovSummary (JSON) |
| `/api/v1/admin/mvp4/evaluation/rubric` | GET | Get quality rubric | QualityRubric with dimensions |
| `/api/v1/admin/mvp4/evaluation/baseline` | GET | Get baseline test set | OfflineBaseline with canonical_turns |
| `/api/v1/admin/mvp4/evaluation/weights/{session_id}` | GET | Get current rubric weights | RubricWeights (JSON) |
| `/api/v1/admin/mvp4/evaluation/weights/{session_id}/manual-tune` | POST | Trigger manual weight tuning | {"status": "auto_tuned\|no_failed_turns"} |
| `/api/v1/admin/mvp4/overrides/{override_id}/audit-trail` | GET | Get audit history for override | List of OverrideAuditEvent (JSON) |
| `/api/v1/admin/mvp4/session/{session_id}/langfuse-export` | GET | Export Langfuse trace | JSON or HTML trace export |

### 2.2 Storage & State (Provided by MVP4)

| Component | Location | Type | Content |
|-----------|----------|------|---------|
| DiagnosticsEnvelope records | world-engine app/turn storage | Persistent | Per-turn diagnostics, indexed by session_id, turn_number |
| Langfuse span data | Langfuse cloud OR local export | Persistent | Real traces with hierarchy and costs |
| Evaluation scores | Redis/DB (configurable) | Persistent | TurnScore records per session, used for auto-tuning |
| Audit trail | Redis/DB (configurable) | Persistent | OverrideAuditEvent records, indexed by override_id |
| Rubric configuration | Redis/DB (configurable) | Persistent | QualityRubric and RubricWeights per session |

---

## 3. Feature Contracts Consumed from Prior MVPs

### 3.1 From MVP3 (LDSS)

- `SceneTurnEnvelopeV2` with scene blocks, NPC agency, narrator validation
- Dramatic validation decision metadata
- Actor lane enforcement status
- Fallback path indicators

### 3.2 From MVP2 (Runtime State)

- Actor lane context (human_actor_id, npc_actor_ids)
- Object admission records and tier enforcement
- State delta boundary protected paths
- Runtime governance surface

### 3.3 From MVP1 (Experience Identity)

- Runtime profile resolution
- Role/actor ownership mapping
- Session identity and participant state

---

## 4. MVP5 Implementation Scope (Not in MVP4)

### 4.1 Admin UI Surfaces (MVP5 Responsibility)

- **Narrative Gov Health Panels**: 6-panel dashboard displaying NarrativeGovSummary data
- **Cost Dashboard**: Daily/weekly/monthly cost reports and trends
- **Session Replay Interface**: Timeline view of turn execution with Langfuse trace correlation
- **Override Management UI**: Create/revoke/monitor object admission and state delta overrides
- **Evaluation Annotation UI**: Operator scoring interface with rubric guidance
- **Langfuse Toggle**: Per-session switch to enable/disable Langfuse tracing

### 4.2 Operator Controls (MVP5 Responsibility)

- Token budget override (with audit logging)
- Degradation strategy selection (aggressive/conservative)
- Manual rubric weight tuning
- Baseline snapshot creation (for regression testing)

### 4.3 Frontend Integration (MVP5 Responsibility)

- Diagnostic badge/indicator in play UI (showing quality_class)
- Degradation warning display (with degradation_signals)
- Cost display (if applicable per session)
- Narrative Gov hints for player behavior

---

## 5. Data Flow Example: MVP5 Using MVP4 Contracts

```
Operator opens Session Dashboard (MVP5 admin UI)
  ↓
MVP5 queries: GET /api/v1/admin/narrative-gov/{session_id}/summary
  ↓
MVP4 returns NarrativeGovSummary (real-time health panels)
  ↓
Operator sees: "LDSS Status: evidenced_live_path, Scene Blocks: 3, Decisions: 12"
Operator sees: "NPC Agency: Primary=Alain, Secondary=[Michel]"
Operator sees: "Narrator Validation: Strictness=High, Rejected=0"
  ↓
Operator clicks "View Turn 5 Diagnostics"
  ↓
MVP5 queries: GET /api/v1/admin/mvp4/game/session/{session_id}/diagnostics-envelope
  ↓
MVP4 returns DiagnosticsEnvelope (full diagnostics + degradation timeline)
  ↓
Operator sees: Turn 5 had MODERATE degradation (FALLBACK_USED), recovered in 150ms
Operator sees: Cost for Turn 5 was $0.035 (LDSS $0.025, Narrator $0.008, Other $0.002)
  ↓
Operator clicks "View Langfuse Trace"
  ↓
MVP5 queries: GET /api/v1/admin/mvp4/session/{session_id}/langfuse-export
  ↓
MVP4 returns trace with spans: LDSS → SceneBlock1 → SceneBlock2 → SceneBlock3 → Narrator
  ↓
Operator sees: Turn 5 fallback happened in LDSS span, recovery in Narrator span
  ↓
Operator decides: "Cost is acceptable, no override needed"
```

---

## 6. Stop Condition Check (MVP4)

| Condition | Status | Evidence |
|-----------|--------|----------|
| Diagnostics non-placeholder | ✅ PASS | All tests pass, evidence tied to session/turn/trace IDs |
| Traceable decisions | ✅ PASS | actor_ownership, actor_lane_decision, dramatic_validation recorded |
| Langfuse traces | ✅ PASS | Real traces with matching IDs, span hierarchy, cost tracking |
| Narrative Gov panels | ✅ PASS | NarrativeGovSummary structure complete and tested |
| Degraded output rejection | ✅ PASS | validate_evidence_consistency() enforces evidence requirement |
| Operational gate evidence | ✅ PASS | This handoff document + source locator + operational evidence |

---

## 7. Handoff Checklist

### Before MVP5 Starts

- ✅ MVP4 operational gates pass (all 50 tests)
- ✅ Source locator complete (MVP4_SOURCE_LOCATOR.md)
- ✅ Operational evidence complete (MVP4_OPERATIONAL_EVIDENCE.md)
- ✅ Handoff contract defined (this document)
- ✅ HTTP endpoints documented and tested
- ✅ Storage schema stable
- ✅ No Phase A/B/C test regressions

### For MVP5 Team

**Required Knowledge**:
- DiagnosticsEnvelope schema and to_response() method (context-aware redaction)
- NarrativeGovSummary health panel structure
- Langfuse trace hierarchy and cost aggregation
- Audit trail event types and granularity config
- TurnScore annotation workflow

**Starting Points**:
1. Read this handoff document
2. Study MVP4_SOURCE_LOCATOR.md for file locations
3. Review HTTP endpoint documentation above
4. Run `python tests/run_tests.py --mvp4` to see all contracts in action
5. Read MVP4_OPERATIONAL_EVIDENCE.md for test evidence

**Integration Checklist**:
- [ ] Implement NarrativeGovSummary dashboard (6 health panels)
- [ ] Implement Cost Dashboard (daily/weekly/monthly)
- [ ] Implement Session Replay UI with Langfuse trace timeline
- [ ] Implement Override Management (CRUD + audit trail display)
- [ ] Implement Evaluation Annotation UI
- [ ] Implement Langfuse Toggle per session
- [ ] Add diagnostic badge/indicator to play UI
- [ ] Add degradation warning display
- [ ] Test all HTTP endpoint integrations
- [ ] Create MVP5 operational evidence

---

## Next Steps

**MVP5 Title**: Admin UI, Session Replay, Frontend Integration

**Key Deliverables**:
1. Narrative Gov Health Panels (6 real-time dashboards)
2. Cost Dashboard (real-time + daily/weekly/monthly)
3. Session Replay Interface (turn timeline + Langfuse correlation)
4. Override Management UI (create/revoke/audit)
5. Evaluation Annotation UI (operator scoring)
6. Frontend Integration (diagnostic badges, warnings)

**Dependencies**:
- All MVP4 HTTP endpoints must be functional
- Langfuse traces must be queryable
- Evaluation pipeline must support manual scoring

**Timeline**:
- Week 1: Narrative Gov dashboards + Cost Dashboard
- Week 2: Session Replay + Langfuse integration
- Week 3: Override Management + Evaluation UI
- Week 4: Frontend integration + testing

---

## Signatures

**MVP4 Implementation Complete**: ✅ 2026-04-30  
**All Gates Passing**: ✅ 50/50 tests  
**Ready for MVP5**: ✅ Yes

**Handoff Approved**: [To be signed by MVP4 lead]
