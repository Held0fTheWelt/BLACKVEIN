# Administration Tool — System Diagnosis Page MVP

## Goal
Create a dedicated diagnosis page in the administration tool that evaluates core system aspects and presents their operational state with a simple traffic-light model:

- **red = fail**
- **yellow = initialized**
- **green = running**

The page should give operators a fast, trustworthy overview of whether the platform, runtime integration, content surface, and AI-related operational surfaces are actually available and usable.

---

## Product intent
The diagnosis page should not duplicate or replace canonical backend or world-engine truth. It should present an **operator-facing aggregated view** derived from existing authoritative system surfaces.

This means:
- the administration tool renders the UI,
- the backend provides a single aggregated diagnosis payload,
- the backend derives that payload from existing health, readiness, configuration, and governance surfaces,
- the world-engine remains authoritative for runtime readiness.

---

## Route and navigation

### Administration tool page
- Route: `/manage/diagnosis`
- Add a dedicated navigation entry: `Diagnosis`
- Add a dashboard card or link to the diagnosis page

### Backend API endpoint
- Route: `GET /api/v1/admin/system-diagnosis`
- Protected by admin auth and feature gating

---

## Status model

### 1. Fail (red)
Use `fail` when a required capability is unavailable or invalid.

Examples:
- service unreachable
- timeout
- required config missing
- invalid response contract
- hard exception during diagnosis

### 2. Initialized (yellow)
Use `initialized` when a capability is present or configured but not yet fully operationally confirmed.

Examples:
- configuration exists, but readiness is not confirmed
- service health responds, but operational surface is not ready
- published feed exists, but there are no published experiences yet
- AI readiness aggregate returns partial rather than ready

### 3. Running (green)
Use `running` when the capability is reachable, structurally valid, and operationally usable.

Examples:
- backend health confirms okay
- world-engine readiness confirms ready
- published content is available
- governance readiness is green/ready

---

## Execution policy

### Timeout policy
The diagnosis endpoint must never hang on a slow upstream dependency.

Required MVP rule:
- each upstream network check must time out within **750 ms**,
- each internal service/self-check must complete within **250 ms** or be treated as failed,
- any timeout maps to **`fail`** with reason `timeout`,
- the backend must still return a diagnosis payload even when one or more checks time out.

Rationale:
- a degraded but returned diagnosis response is better than a blocked operator page,
- timeout must be represented as an explicit operational problem, not hidden as “still loading”.

### Parallelization policy
Checks should run in parallel by default.

Required MVP rule:
- independent checks run concurrently,
- sequencing is allowed only when dependency order is required,
- missing prerequisites should short-circuit dependent checks without making unnecessary upstream calls.

Examples:
- `Database` and `AI stack release readiness` can run in parallel,
- `Play-service configuration` can be evaluated immediately,
- if play-service configuration is missing, runtime HTTP checks may be skipped and marked from prerequisite failure rather than attempted.

### Endpoint performance target
For MVP, the diagnosis endpoint should be designed to complete within roughly **1 second typical** and **under 2 seconds degraded**.
This is an operational target, not a correctness rule, but the timeout and parallelization policies above are mandatory because they are what make that target realistic.

---

## Overall status resolution
The page should compute one overall status from all checks.

### Proposed logic
- `fail` if any **critical** check is red
- `initialized` if no critical check is red, but at least one check is yellow
- `running` if all critical checks are green and no check requires operator attention

### Critical checks
The following should be treated as critical in MVP:
- Backend API
- Database
- Play-service configuration
- Play-service health
- Play-service readiness
- Runtime bridge

Non-critical checks may still appear as yellow or red without collapsing the entire installation unless explicitly desired later.

---

## Recommended MVP check groups

## Group 1 — Core platform

### Check: Backend API
Purpose:
Confirm that the backend API is reachable and healthy.

Source:
- `GET /api/v1/health`

Status mapping:
- green: response is successful and indicates healthy/ok
- red: endpoint unreachable, invalid, timeout, or failing

### Check: Database
Purpose:
Confirm backend database access works.

Source:
- backend-side DB self-check, e.g. simple query or existing health service integration

Status mapping:
- green: DB check succeeds
- red: DB check fails or times out

Note:
The earlier idea of a top-level `Authenticated admin context` check should not be part of MVP. Since the diagnosis endpoint is already auth-protected, that check is mostly tautological at page level. If later desired, session expiry or feature posture warnings can be shown as a separate UI hint rather than as a core diagnosis check.

---

## Group 2 — Runtime integration

### Check: Play-service configuration
Purpose:
Confirm the backend has the required runtime integration configuration.

Config examples:
- `PLAY_SERVICE_PUBLIC_URL`
- `PLAY_SERVICE_INTERNAL_URL`
- `PLAY_SERVICE_SHARED_SECRET`

Status mapping:
- red: required config missing
- yellow: config exists but operational connectivity not yet confirmed
- green: config exists and integration checks confirm use

### Check: Play-service health
Purpose:
Confirm the world-engine/play-service health endpoint is reachable.

Source:
- `GET /api/health`

Status mapping:
- green: endpoint reachable and healthy
- red: unreachable, timeout, invalid response, or unhealthy

### Check: Play-service readiness
Purpose:
Confirm the world-engine is not only alive, but ready.

Source:
- `GET /api/health/ready`

Status mapping:
- green: readiness confirms ready
- yellow: base health is okay, but readiness is not fully confirmed
- red: readiness endpoint unreachable, timeout, invalid, or failing

### Check: Runtime bridge
Purpose:
Confirm that the backend can successfully talk to runtime-facing service logic through the canonical integration path.

Source:
- existing runtime bridge service
- same service path already used by game operations where possible

Status mapping:
- green: bridge call succeeds and returns structurally valid data
- yellow: bridge partially responds but is incomplete
- red: bridge call fails or times out

---

## Group 3 — Content and operations

### Check: Published experiences feed
Purpose:
Confirm published playable/admin-visible content is available through the canonical content surface.

Source:
- published content listing surface already used in the system

Status mapping:
- green: feed responds and contains usable published items
- yellow: feed responds but is empty
- red: feed fails, times out, or returns invalid data

### Check: Game operations surface
Purpose:
Confirm game operations-related read paths are structurally available.

Source:
- existing game operations endpoints or service layer

Status mapping:
- green: operations surface responds correctly
- yellow: available but limited or empty
- red: invalid, timeout, or failing

Note:
This can be included in MVP or deferred if the first version should stay very lean.

---

## Group 4 — AI and governance

### Check: AI stack release readiness
Purpose:
Show whether the AI stack governance aggregate currently reports operational readiness.

Source:
- existing AI stack governance aggregate / release readiness endpoint

Status mapping:
- green: readiness = ready
- yellow: readiness = partial / initialized / not yet fully closed
- red: endpoint unavailable, timed out, or structurally invalid

### Check: Session evidence availability
Purpose:
Optionally confirm that session evidence surfaces are wired and usable.

Source:
- existing session evidence endpoint(s)

Status mapping:
- green: evidence surface reachable and valid
- yellow: feature exists but requires a session input or has no current evidence context
- red: broken, timed out, or unavailable

Note:
This is better as an optional or detail-level check, not necessarily a top-level blocker in MVP.

---

## Refresh and caching policy

### Frontend refresh behavior
The page should not be static.

Required MVP rule:
- auto-refresh every **15 seconds**,
- include a manual **Refresh now** action,
- show `generated_at` and optionally `stale` age in the UI.

### Backend cache behavior
The backend should not ping all upstream services on every browser refresh.

Required MVP rule:
- cache the aggregated diagnosis result for **5 seconds**,
- serve the cached result to repeated requests during that TTL,
- allow a manual refresh request to bypass cache if explicitly requested,
- never cache failures longer than the normal TTL.

Suggested request option:
- `GET /api/v1/admin/system-diagnosis?refresh=1`

### Cache semantics
- cache is an optimization, not a truth layer,
- each check result should still carry its own timestamp or reuse a shared `generated_at`,
- the UI should make it clear when data is recent but not literally real-time.

---

## Recommended MVP scope
For the first implementation, keep the page focused and reliable.

### Minimum strong MVP
Implement these 7 checks:
1. Backend API
2. Database
3. Play-service configuration
4. Play-service health
5. Play-service readiness
6. Published experiences feed
7. AI stack release readiness

### Stronger MVP if bridge value is needed immediately
Add:
8. Runtime bridge

This gives a meaningful operator dashboard without over-expanding scope.

---

## Backend architecture
The browser should **not** call multiple services directly.

### Correct flow
1. Administration tool renders `/manage/diagnosis`
2. Frontend JS requests one backend endpoint: `GET /api/v1/admin/system-diagnosis`
3. Backend aggregates all diagnosis checks server-side
4. Backend returns one structured payload
5. UI renders grouped cards, badges, and details

### Why this is the right approach
- avoids secret exposure
- avoids CORS complexity
- keeps diagnosis logic centralized
- prevents the UI from inventing its own truth
- allows the backend to reuse existing service-layer logic
- allows caching, timeouts, and concurrency policy to be enforced in one place

---

## Response shape
Recommended backend payload:

```json
{
  "generated_at": "2026-04-09T15:42:00Z",
  "overall_status": "initialized",
  "summary": {
    "running": 5,
    "initialized": 2,
    "fail": 1
  },
  "groups": [
    {
      "id": "core_platform",
      "label": "Core platform",
      "checks": [
        {
          "id": "backend_api",
          "label": "Backend API",
          "status": "running",
          "message": "GET /api/v1/health returned status ok",
          "details": {
            "endpoint": "/api/v1/health",
            "latency_ms": 31
          }
        }
      ]
    }
  ]
}
```

### Recommended additional fields
Add these fields where useful:
- `latency_ms`
- `timed_out`
- `cached`
- `critical`
- `source`

### Status enum
Use a stable internal status enum:
- `fail`
- `initialized`
- `running`

The UI can map these to colors and icons.

---

## UI recommendations
Each check should show:
- name
- status badge
- one-line explanation
- last updated time
- optional latency
- optional expandable raw details

### Example visual treatment
- **Running** — Play-service readiness confirmed
- **Initialized** — Play-service configured, readiness not yet confirmed
- **Fail** — Backend API timed out after 750 ms

### Important
Do not rely on color alone.
Always show:
- explicit status word
- icon
- short text reason

That makes the page clearer and more accessible.

---

## Suggested administration-tool changes

### New route
- `administration-tool/app.py`
  - add route for `/manage/diagnosis`

### New template
- `administration-tool/templates/manage/diagnosis.html`

### New JS
- `administration-tool/static/manage_diagnosis.js`

### Styling
- `administration-tool/static/manage.css`
  - add diagnosis card, badge, summary, and detail styles

### Navigation/dashboard
- update shared navigation template
- add dashboard entry for the diagnosis page

---

## Suggested backend changes

### Feature flag / permission
Add a dedicated feature name such as:
- `manage.system_diagnosis`

### New API route
Create a backend route module such as:
- `backend/app/api/v1/system_diagnosis_routes.py`

Endpoint:
- `GET /api/v1/admin/system-diagnosis`

### New backend service
Create:
- `backend/app/services/system_diagnosis_service.py`

Responsibilities:
- run grouped checks
- apply timeout policy
- apply concurrency policy
- apply cache policy
- normalize check results
- compute summary counts
- compute overall status
- return stable payload contract

---

## Design rules

### Rule 1 — No second truth
The diagnosis page must aggregate existing canonical surfaces, not invent new authority.

### Rule 2 — Prefer existing service paths
If a backend service already knows how to validate runtime connectivity, reuse it.
Do not build parallel integration logic unless necessary.

### Rule 3 — Stable contract
The diagnosis payload should be stable, explicit, and easy to test.

### Rule 4 — Operator-legible messaging
Each failure or warning should be understandable without reading code.

### Rule 5 — Degrade gracefully
One slow or broken upstream dependency must not prevent the diagnosis endpoint from returning a usable payload.

---

## Testing expectations

### Administration-tool tests
- route renders successfully for authorized admin users
- unauthorized access is rejected correctly
- diagnosis template includes expected containers/labels
- dashboard/navigation contains diagnosis entry
- generated timestamp and refresh controls are visible

### Backend tests
- diagnosis endpoint requires auth/feature access
- grouped payload structure is stable
- status mapping logic is correct
- overall status resolution is correct
- timeout mapping is correct
- parallel execution path returns combined results
- cache hit and cache bypass behavior are correct
- service gracefully handles upstream failures/timeouts

### Suggested test cases
- all checks green => overall running
- one critical check red => overall fail
- no red, at least one yellow => overall initialized
- published feed empty => yellow, not red
- AI governance partial => yellow
- play-service config missing => red
- play-service health timeout => red with timeout reason
- second request within cache TTL => cached result served
- manual refresh bypass => fresh upstream execution occurs

---

## Future expansion after MVP
Once the first version is stable, the diagnosis page can grow carefully.

Good next additions:
- active runs count
- recent runtime connectivity success timestamp
- runtime transcript or operations sample availability
- session evidence lookup by session ID
- config posture warnings
- environment mismatch warnings
- latency snapshot for selected critical services
- session expiry or feature-posture warning banner

These should remain secondary to the core MVP and should not delay the first operational version.

---

## Final recommendation
Build the diagnosis page as a **dedicated management page** with a **single backend aggregation endpoint**, a **strict red/yellow/green operational model**, and explicit **timeout, concurrency, and cache rules**.

For MVP, keep it focused on the 7 most important checks:
- Backend API
- Database
- Play-service configuration
- Play-service health
- Play-service readiness
- Published experiences feed
- AI stack release readiness

Add `Runtime bridge` immediately if direct runtime-connectivity evidence is needed from day one.

This gives the administration tool a strong operator-facing diagnosis surface without introducing architectural drift, page hangs, or a second source of truth.
