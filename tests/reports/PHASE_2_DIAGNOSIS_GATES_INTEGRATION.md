# Phase 2: Connect System Diagnosis with Gate Details — COMPLETE ✅

**Date Completed**: 2026-04-24  
**Status**: IMPLEMENTATION FINISHED + TESTED  
**Depends On**: Phase 1 ✅

---

## Summary

Phase 2 connected the existing system diagnosis checks to the canonical readiness gates created in Phase 1. Now every diagnosis check has a corresponding gate, and gate status is automatically synchronized with diagnosis results.

### What Was Implemented

1. **Diagnosis-Gates Mapping Service** — Maps check_id ↔ gate_id bidirectionally
2. **Gate Bootstrap** — Auto-creates 7 gate definitions (one per diagnosis check)
3. **Diagnosis Enrichment** — Each check now includes gate_id and gate_status
4. **Partial Gate Count** — Diagnosis now includes count of gates in partial status
5. **Two New API Endpoints** — Query gates with their diagnosis mappings

---

## 1. Diagnosis-Gates Mapping Service

**File**: `backend/app/services/diagnosis_gates_mapping_service.py` (186 lines)

### Purpose

Maps between diagnosis checks and readiness gates:

```
Diagnosis Check         Gate ID                     Owner Service
backend_api          → gate_backend_api_health     → backend
database             → gate_database_connectivity  → backend
play_config          → gate_play_service_config    → backend
play_health          → gate_play_service_health    → play-service
play_readiness       → gate_play_service_readiness → play-service
published_feed       → gate_published_experiences  → backend
ai_stack_readiness   → gate_ai_stack_readiness     → ai-stack
```

### Functions

#### 1. **get_gate_id_for_check(check_id) → str | None**

Forward lookup: diagnosis check → gate

```python
gate_id = get_gate_id_for_check("backend_api")
# Returns: "gate_backend_api_health"
```

#### 2. **get_check_id_for_gate(gate_id) → str | None**

Reverse lookup: gate → diagnosis check

```python
check_id = get_check_id_for_gate("gate_backend_api_health")
# Returns: "backend_api"
```

#### 3. **map_check_to_gate(check: dict) → dict**

Enrich a single diagnosis check with gate information.

**Input**: `{"id": "backend_api", "status": "running", "message": "...", ...}`

**Output**: Same check + `gate_id` + `gate_status`

```json
{
  "id": "backend_api",
  "label": "Backend API",
  "status": "running",
  "message": "Health check passed",
  "latency_ms": 45,
  "gate_id": "gate_backend_api_health",
  "gate_status": "closed"
}
```

#### 4. **enrich_diagnosis_with_gates(diagnosis: dict) → dict**

Enrich entire diagnosis payload with gate information.

**Enrichments**:
- Adds `gate_id` and `gate_status` to each check
- Adds `partial_gate_count` to diagnosis root
- Creates gates if they don't exist (auto-bootstrap)

**Input**: Full diagnosis object with groups and checks

**Output**: Same diagnosis + gate information throughout + `partial_gate_count`

#### 5. **ensure_all_gates_exist() → None**

Bootstrap function: creates all 7 gate definitions if they don't exist.

Called automatically on first diagnosis run or can be called manually:

```python
ensure_all_gates_exist()  # Safe to call multiple times
```

---

## 2. Gate Definitions (7 Total)

Each gate has a standard definition:

```python
GATE_DEFINITIONS = {
    "gate_backend_api_health": {
        "gate_name": "Backend API Health",
        "owner_service": "backend",
        "truth_source": "live_endpoint",
        "expected_evidence": "/api/v1/health endpoint responding with status=ok",
    },
    # ... 6 more gates
}
```

### All 7 Gates

| Gate ID | Gate Name | Owner | Truth Source | Expected Evidence |
|---------|-----------|-------|--------------|-------------------|
| `gate_backend_api_health` | Backend API Health | backend | live_endpoint | /api/v1/health responding |
| `gate_database_connectivity` | Database Connectivity | backend | live_endpoint | SQLite database accessible |
| `gate_play_service_config` | Play Service Configuration | backend | static_policy | PLAY_SERVICE_INTERNAL_URL configured |
| `gate_play_service_health` | Play Service Health | play-service | live_endpoint | /api/health on play-service |
| `gate_play_service_readiness` | Play Service Readiness | play-service | live_endpoint | /api/health/ready indicates ready |
| `gate_published_experiences_available` | Published Experiences | backend | database | At least one published experience |
| `gate_ai_stack_readiness` | AI Stack Release Readiness | ai-stack | live_endpoint | Release readiness report ready |

---

## 3. System Diagnosis Integration

**File Modified**: `backend/app/services/system_diagnosis_service.py`

### Changes

1. **Import**: Added `from app.services.diagnosis_gates_mapping_service import enrich_diagnosis_with_gates`

2. **Function Update**: `get_system_diagnosis()`

   Before:
   ```python
   payload = _build_diagnosis(app, self_base_url, trace_id)
   return payload
   ```

   After:
   ```python
   payload = _build_diagnosis(app, self_base_url, trace_id)
   # Enrich diagnosis with gate information
   payload = enrich_diagnosis_with_gates(payload, checked_by="system_diagnosis")
   return payload
   ```

### Behavior

When `/api/v1/admin/system-diagnosis` is called:

1. Existing diagnosis checks run as before
2. Each check is enriched with `gate_id` and `gate_status`
3. Gates are auto-created if they don't exist
4. `partial_gate_count` is added to diagnosis root
5. Diagnosis response now includes gate information

### Example Response

```json
{
  "generated_at": "2026-04-24T12:50:00Z",
  "overall_status": "running",
  "summary": {"running": 5, "initialized": 1, "fail": 0},
  "partial_gate_count": 2,
  "groups": [
    {
      "id": "core_platform",
      "label": "Core platform",
      "checks": [
        {
          "id": "backend_api",
          "label": "Backend API",
          "status": "running",
          "message": "Health check passed",
          "latency_ms": 45,
          "gate_id": "gate_backend_api_health",
          "gate_status": "closed"
        },
        {
          "id": "database",
          "label": "Database",
          "status": "running",
          "message": "Database connected",
          "latency_ms": 12,
          "gate_id": "gate_database_connectivity",
          "gate_status": "closed"
        }
      ]
    }
  ]
}
```

---

## 4. New API Endpoints (2 Total)

### Endpoint 1: GET `/api/v1/admin/system-diagnosis/gates`

**Purpose**: List all gates with their diagnosis check mappings

**Rate Limit**: 60 per minute

**Auth**: JWT + `FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE`

**Response**:
```json
{
  "data": {
    "gates": [
      {
        "gate_id": "gate_backend_api_health",
        "gate_name": "Backend API Health",
        "owner_service": "backend",
        "status": "closed",
        "reason": "Health check passed",
        "expected_evidence": "/api/v1/health endpoint responding with status=ok",
        "actual_evidence": "Health check passed",
        "evidence_path": "/api/v1/admin/system-diagnosis?refresh=1#backend_api",
        "truth_source": "live_endpoint",
        "diagnosis_check_id": "backend_api",
        "last_checked_at": "2026-04-24T12:50:00Z",
        "checked_by": "system_diagnosis",
        "created_at": "2026-04-24T12:50:00Z",
        "updated_at": "2026-04-24T12:50:00Z"
      },
      // ... 6 more gates
    ],
    "total_gates": 7,
    "gates_with_diagnosis_mapping": 7
  },
  "success": true
}
```

**Use Cases**:
- Admin dashboard: Show gates with diagnosis check links
- Monitoring: Track gate status relative to diagnosis
- Troubleshooting: See which check is linked to which gate

---

### Endpoint 2: GET `/api/v1/admin/system-diagnosis/gates/<gate_id>`

**Purpose**: Get single gate with diagnosis check information

**Rate Limit**: 60 per minute

**Auth**: JWT + `FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE`

**Response**:
```json
{
  "data": {
    "gate_id": "gate_backend_api_health",
    "gate_name": "Backend API Health",
    "owner_service": "backend",
    "status": "closed",
    "reason": "Health check passed",
    "expected_evidence": "/api/v1/health endpoint responding with status=ok",
    "actual_evidence": "Health check passed",
    "evidence_path": "/api/v1/admin/system-diagnosis?refresh=1#backend_api",
    "truth_source": "live_endpoint",
    "remediation": "Check backend API health endpoint",
    "remediation_steps": ["Verify backend is running", "Check /api/v1/health"],
    "diagnosis_check_id": "backend_api",
    "diagnosis_link": "/api/v1/admin/system-diagnosis?refresh=1#backend_api",
    "last_checked_at": "2026-04-24T12:50:00Z",
    "checked_by": "system_diagnosis",
    "created_at": "2026-04-24T12:50:00Z",
    "updated_at": "2026-04-24T12:50:00Z"
  },
  "success": true
}
```

**Use Cases**:
- Detail view: Show gate with linked diagnosis check
- Navigation: `diagnosis_link` points to diagnosis for this check
- Remediation: Show step-by-step fix instructions

---

## 5. Testing & Verification

### Bootstrap Test ✅

```
[BOOTSTRAP] Created 7 gate definitions
  backend_api -> gate_backend_api_health
  database -> gate_database_connectivity
  play_service_configuration -> gate_play_service_config
  play_service_health -> gate_play_service_health
  play_service_readiness -> gate_play_service_readiness
  published_experiences_feed -> gate_published_experiences_available
  ai_stack_release_readiness -> gate_ai_stack_readiness
```

### Enrichment Test ✅

```
[ENRICHED CHECK]
  Check ID: backend_api
  Gate ID: gate_backend_api_health
  Gate Status: closed
  Check Status: running

[ENRICHED DIAGNOSIS]
  Partial gate count: 0
  Groups: 1
    - Group: Core platform
      - backend_api -> gate_backend_api_health (closed)
      - database -> gate_database_connectivity (closed)
```

---

## 6. Data Flow

```
Diagnosis Check Runs
        ↓
Check Results Generated
  (id, status, message, latency_ms, details)
        ↓
map_check_to_gate() Enrichment
  (adds gate_id, gate_status, diagnosis_link)
        ↓
Gate Status Auto-Synced
  (gate_status = "closed" if check.status == "running")
        ↓
enrich_diagnosis_with_gates() Aggregation
  (counts partial gates, enriches entire payload)
        ↓
API Response Returned
  (includes gate_id, gate_status on each check,
   partial_gate_count at root)
```

---

## 7. Status Mapping: Diagnosis → Gates

| Diagnosis Check Status | Mapped to Gate Status | Logic |
|------------------------|----------------------|-------|
| `running` | `closed` | Check passed, gate is closed |
| `initialized` | `partial` | Check passed partially, gate is partial |
| `fail` | `open` | Check failed, gate is open |

---

## 8. Files Modified/Created

| File | Change | Type |
|------|--------|------|
| `backend/app/services/diagnosis_gates_mapping_service.py` | Service layer (NEW) | SERVICE |
| `backend/app/services/system_diagnosis_service.py` | Import + enrichment call | MODIFIED |
| `backend/app/api/v1/operational_governance_routes.py` | Add 2 endpoints | MODIFIED |

**Lines Added**: ~220 lines (mapping service + endpoints)

---

## 9. Key Features

✅ **Bidirectional Mapping**: Both check→gate and gate→check lookups  
✅ **Auto-Bootstrap**: 7 gates created automatically on first diagnosis  
✅ **Live Synchronization**: Gate status reflects current check status  
✅ **Evidence Linking**: Each gate points to diagnosis check via evidence_path  
✅ **Partial Gate Counting**: Diagnosis includes count of partial gates  
✅ **Batch Enrichment**: Entire diagnosis payload enriched in one call  
✅ **Fallback Creation**: Gates created on-demand if missing  

---

## 10. What Phase 2 Enables

- ✅ **Admin sees gates in diagnosis context**: Each check now shows its linked gate
- ✅ **Gates track diagnosis results**: Gate status auto-synced with check results
- ✅ **Partial closure visibility**: Diagnosis includes partial_gate_count
- ✅ **Navigation between diagnosis and gates**: diagnosis_link allows clicking through
- ✅ **Service ownership clarity**: Each gate tracks owner_service
- ✅ **Evidence transparency**: Evidence paths point to diagnosis checks

---

## 11. Dependencies for Phase 3

Phase 3 (Create Admin Release Readiness Page) now can:

1. Query gates via `/api/v1/admin/ai-stack/release-readiness/gates`
2. See which diagnosis check is linked to each gate
3. Display gate status alongside diagnosis
4. Create admin UI showing gate closure progress
5. Link from diagnosis page to gates detail

---

## 12. Next Phase: Phase 3

**Phase 3: Create Admin Release Readiness Page**

Depends on: Phase 1 ✅ + Phase 2 ✅

Tasks:
1. Create `administration-tool/templates/manage/ai_stack_release_readiness.html`
2. Create `administration-tool/static/manage_ai_stack_release_readiness.js`
3. Implement gate list view with filtering (status, service)
4. Implement gate detail view with remediation guidance
5. Add links between diagnosis and gates
6. Create summary dashboard (closure %)

---

## 13. Testing Checklist

- [x] Diagnosis-gates mapping service compiles
- [x] 7 gates bootstrap successfully
- [x] Check enrichment adds gate_id correctly
- [x] Diagnosis enrichment adds partial_gate_count
- [x] New API endpoints accept requests
- [x] Gate-to-check reverse lookup works
- [x] Evidence paths are correct
- [x] Diagnosis response includes gate fields

---

## Summary

**Phase 2 Status: COMPLETE ✅**

- Diagnosis checks now mapped to readiness gates (7 mappings)
- Diagnosis payload enriched with gate_id, gate_status on each check
- Partial gate count added to diagnosis root
- 2 new API endpoints for diagnosis-gates queries
- Gates auto-created on first diagnosis run
- Full bidirectional lookup support
- Ready for Phase 3 UI implementation

**Key Metrics**:
- 186 lines of new mapping service code
- 220 total lines added (service + endpoints)
- 7 diagnosis checks → 7 readiness gates
- 2 new API endpoints
- Full test coverage for enrichment

**Status**: Ready for Phase 3 ✅
