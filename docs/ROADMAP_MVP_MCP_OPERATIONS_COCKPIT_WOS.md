# MVP_MCP_OPERATIONS_COCKPIT_WOS

## 1. Executive Summary

**MVP Name:** MCP Operations Cockpit  
**Project Context:** World of Shadows  
**Purpose:** A minimal but operational MCP control and observability surface inside the `administration-tool`

This MVP exists to make MCP in World of Shadows **visible, diagnosable, and controllable in a bounded way**.

It is **not** a full MCP platform.  
It is **not** a generic admin dashboard for everything.  
It is **not** a replacement for runtime authority.

It is a focused operations cockpit that allows an operator to answer six core questions without inspecting code:

1. Which MCP suites are active?
2. What MCP activity happened recently?
3. What is currently failing?
4. Which suite is affected?
5. What is the likely diagnosis?
6. Which safe action can be taken now?

---

## 2. Problem Statement

MCP is already becoming architecturally important inside World of Shadows, but without a dedicated operational surface it is too easy for it to remain:

- technically present but operationally opaque
- spread across logs and code paths instead of visible in one place
- hard to diagnose when something fails
- hard to audit when responsibilities across suites are unclear
- difficult to act on safely from the administration layer

This MVP solves that by establishing the `administration-tool` as the first real **MCP operations surface**.

---

## 3. MVP Goal

> Build a minimal MCP Operations Cockpit in the `administration-tool` that provides overview, activity visibility, diagnostics, structured logs, and a small set of safe actions for bounded MCP operations.

This MVP should create enough visibility and operability that MCP in WoS becomes a manageable system concern rather than a hidden implementation detail.

---

## 4. Target Users

### Primary Users
- admin
- operator
- technical author
- AI / runtime maintainer

### Secondary Users
- internal reviewers
- governance / QA stakeholders

### Explicitly Not Targeted
- end users / players
- broad external self-service users
- open-ended authoring users
- unrestricted runtime operators

---

## 5. In Scope

This MVP includes exactly five operational areas.

## 5.1 Overview
A start page with a compact situation view.

It should show:
- active MCP suites
- number of resources / prompts / tools per suite
- recent activity
- recent warnings and errors
- open diagnostic cases
- currently running operations

## 5.2 Activity
A filterable timeline of MCP operations.

Each activity item should expose:
- timestamp
- suite
- actor
- operation type
- target
- duration
- outcome

## 5.3 Diagnostics
A case-based diagnostic area for MCP problems.

The MVP should support cases such as:
- failed tool call
- policy rejection
- resource read failure
- suite misrouting
- progress timeout or stalled operation

Each case should include:
- severity
- status
- affected suite
- short summary
- recommended next action

## 5.4 Logs
A structured log explorer with filters for:
- log level
- suite
- actor
- correlation id
- session id
- date range
- errors only / all logs

## 5.5 Actions
A narrow action area for safe admin measures.

The MVP action set should include:
- refresh catalog / inventory
- retry bounded failed job
- generate audit bundle
- reclassify diagnostic case

### Optional only if a safe seam already exists
The following actions are **not required for MVP closure** and may only be exposed if an already existing safe seam is present:

- disable suite exposure
- enable suite exposure

If they are exposed in the MVP, the implementation must guarantee all of the following:
- they affect only new eligible exposure or new requests
- they do not terminate active runtime sessions
- they are explicitly audited
- they require confirmation
- they are limited to authorized operators

If those guarantees do not already exist or cannot be implemented cheaply and safely, these actions remain out of scope for the MVP.

---

## 6. Out of Scope

The following are explicitly out of scope for this MVP:

- full policy workbench
- full authoring through MCP
- unrestricted runtime mutation
- direct narrative truth changes
- broad report platform
- complex live subscriptions
- roots integration
- sampling integration
- large write-tool collections
- broad self-service automation
- suite exposure toggling without the safety guarantees defined in Section 5.5

This is an operations MVP, not a full MCP product.

---

## 7. Supported Suite Model

The MVP recognizes and surfaces the following WoS MCP suites:

- `wos-admin`
- `wos-author`
- `wos-ai`
- `wos-runtime-read`
- `wos-runtime-control`

Important:

The MVP does **not** need every suite to be functionally complete.  
It needs them to be:
- visible
- distinguishable
- diagnosable
- attributable
- operable within the cockpit

---

## 8. Core MVP Principles

1. The cockpit must improve **visibility** before it adds control.
2. The cockpit must improve **diagnosis** before it adds more actions.
3. Actions must remain **narrow, explicit, and safe**.
4. MCP suite responsibility must be operationally visible.
5. The cockpit must not become a second runtime.
6. The cockpit must not hide failures behind generic status summaries.
7. The first MVP should prefer **existing data seams** over inventing a new event platform.

---

## 9. Data Sources

The MVP is only realistic if data origin is explicit.

## 9.1 Suite Registry data source
**Initial source:** static configuration or server-side suite registry already available in the WoS MCP layer.  
**Fallback if needed:** a maintained admin-side projection file or configuration object.

The MVP does **not** require dynamic discovery as a prerequisite.  
It only requires that the suite list used by the cockpit be real, stable, and attributable.

## 9.2 Activity Events data source
**Initial source:** existing backend / MCP / bridge logs and runtime-side event emissions, normalized into a common admin-facing event shape.

The MVP assumes activity events are created from:
- existing MCP request handling logs
- backend or bridge-side structured logging where available
- runtime- or admin-side correlation metadata where available

The MVP does **not** assume a new dedicated event bus must be built first.

If multiple existing sources exist, the MVP should normalize them into one activity projection instead of introducing a new transport layer.

## 9.3 Diagnostic Cases data source
**Initial source:** hybrid generation.

Diagnostic cases should be created by:
1. **rule-based derivation** from activity/log events for obvious cases
2. **manual operator classification** where automatic case generation is not yet reliable

This means the first MVP is **not** a full autonomous diagnosis engine.
It is a hybrid operational layer:
- automatic where cheap and obvious
- manual where judgment is still required

## 9.4 Logs data source
**Initial source:** existing structured application logs, MCP-adjacent logs, and admin-observable error outputs.

The MVP should prefer:
- already available structured logs
- parsable existing log sinks
- correlation-id-compatible sources

It should avoid introducing a brand new logging architecture unless the current repo truly lacks any usable structured source.

---

## 10. Minimal Data Model

The MVP needs three core object types.

## 10.1 Suite Registry
Represents which suite exists and what it is responsible for.

Suggested fields:
- `suite_name`
- `display_name`
- `purpose`
- `status`
- `owner`

## 10.2 Activity Events
Represents normalized MCP activity.

Suggested fields:
- `timestamp`
- `suite_name`
- `actor_type`
- `actor_id`
- `operation_type`
- `target_type`
- `target_name`
- `correlation_id`
- `session_id`
- `duration_ms`
- `outcome_status`
- `error_code`
- `error_message`

## 10.3 Diagnostic Cases
Represents clustered or classified MCP problems.

Suggested fields:
- `case_id`
- `case_type`
- `severity`
- `status`
- `suite_name`
- `summary`
- `first_seen_at`
- `last_seen_at`
- `occurrence_count`
- `case_origin`              # auto_rule | manual | mixed

### Optional Early Fields
These may be included early but are not required for MVP closure:
- `policy_decision`
- `progress_token`
- `payload_summary`

---

## 11. Diagnostic Case Generation

This MVP must make case generation explicit.

## 11.1 Automatic case generation
The cockpit should automatically open or update cases for clearly detectable failures, such as:
- failed tool call
- policy rejection
- resource read failure
- repeated timeout / stalled progress event
- repeated suite mismatch according to configured suite responsibility

These cases are generated by simple rules over normalized activity/log events.

## 11.2 Manual case generation
The operator must be able to create or reclassify a case when:
- the failure is visible but not yet covered by rules
- multiple events require human grouping
- the failure type is ambiguous
- a manual operational note is needed

## 11.3 MVP implementation posture
The MVP is successful with a **hybrid model**:
- rule-based automatic cases for obvious patterns
- manual creation/reclassification for the rest

It does **not** require a sophisticated autonomous classification engine.

---

## 12. Minimal API Surface

The MVP only needs a compact admin API surface.

### Read Endpoints
```text
GET  /api/v1/admin/mcp/overview
GET  /api/v1/admin/mcp/suites
GET  /api/v1/admin/mcp/activity
GET  /api/v1/admin/mcp/diagnostics
GET  /api/v1/admin/mcp/logs
```

### Action Endpoints
```text
POST /api/v1/admin/mcp/actions/refresh-catalog
POST /api/v1/admin/mcp/actions/retry-job
POST /api/v1/admin/mcp/actions/generate-audit-bundle
POST /api/v1/admin/mcp/actions/reclassify-diagnostic
```

### Optional only if the safety seam already exists
```text
POST /api/v1/admin/mcp/actions/disable-suite
POST /api/v1/admin/mcp/actions/enable-suite
```

This is intentionally small:
- enough to be useful
- small enough to build
- narrow enough to keep safe

---

## 13. UI Structure in the Administration Tool

Add a new primary navigation entry:

**MCP Operations**

The MVP version should contain these pages:

- Overview
- Activity
- Diagnostics
- Logs
- Actions

### Not Required for MVP Completion
These may be prepared or stubbed, but do not need full implementation for MVP:
- Suites detail page
- Policies page
- Audit / Reports page

---

## 14. User Experience Expectations

An operator using this MVP should be able to do the following without opening code:

1. See whether MCP suites are active
2. View recent MCP activity
3. Find current MCP failures
4. Identify the affected suite
5. Open a diagnostic case
6. Understand the likely failure type
7. Trigger a bounded corrective action
8. See whether that action succeeded or failed

That is the real success bar for this MVP.

---

## 15. MVP Success Criteria

This MVP is successful if all of the following are true:

### Functional Success
- MCP Operations exists as a distinct area in the `administration-tool`
- Overview, Activity, Diagnostics, Logs, and Actions are all present
- the system shows **real MCP-backed data** rather than placeholder-only views
- at least one safe corrective action can be triggered end-to-end

### Operational Success
- an operator can identify a failing MCP-related case
- the operator can see which suite is involved
- the operator can inspect supporting activity/log context
- the operator can trigger a bounded action
- the result of that action is observable

### Architectural Success
- the cockpit improves MCP observability without becoming a second runtime
- it does not introduce broad uncontrolled write paths
- suite responsibility becomes more visible, not less

## 15.1 Minimum standard for “real MCP-backed data”
“Real MCP-backed data” means all of the following:

1. **Overview** is populated from the real suite registry and real aggregated counts, not hardcoded demo numbers.
2. **Activity** shows at least 20 real normalized MCP activity events from actual runtime/admin/backend sources.
3. **Logs** shows real log entries from at least one actual structured source.
4. **Diagnostics** shows at least 3 non-placeholder cases derived from real events or manually classified from real events.
5. At least one **Action** reads or updates real backend/admin state and returns an observable outcome.

A page populated only with mock rows, hardcoded fixtures, or empty placeholder cards does not satisfy MVP closure.

---

## 16. MVP Phasing

This MVP should be built in three implementation phases.

## Phase 1 — Visibility
Build:
- Overview
- Activity

Goal:
- immediate operational visibility

## Phase 2 — Diagnose
Build:
- Diagnostics
- Logs

Goal:
- understand failures instead of merely seeing that something broke

## Phase 3 — Act
Build:
- Actions

Goal:
- allow bounded safe intervention after visibility and diagnosis already exist

---

## 17. Implementation Priorities

### Highest Priority
- real data sourcing from existing seams
- normalized MCP event visibility
- suite-aware overview
- diagnostic case surfacing
- safe admin action execution
- observable outcomes of actions

### Medium Priority
- richer filtering
- better severity grouping
- improved operator drilldown
- stronger ownership visibility per suite

### Defer
- broad reporting system
- live subscriptions
- roots
- sampling
- broad write automation
- policy authoring workbench
- suite enable/disable unless the safety seam already exists

---

## 18. Risks

## Risk 1 — Dashboard without real value
The cockpit could become a passive status page with no diagnostic usefulness.

**Mitigation:** prioritize Diagnostics and Actions, not cosmetics.

## Risk 2 — Too many actions too early
The action area could become a dangerous write surface.

**Mitigation:** keep actions narrow and explicitly bounded; treat suite enable/disable as optional only if an existing safe seam is available.

## Risk 3 — Suite confusion remains hidden
The UI could aggregate everything so strongly that suite distinctions disappear.

**Mitigation:** show suite identity and ownership clearly in all relevant views.

## Risk 4 — Log volume without signal
Raw logs could overwhelm operators.

**Mitigation:** use Diagnostics as the primary problem view and Logs as supporting detail.

## Risk 5 — Scope inflation
The cockpit could drift into a full MCP platform.

**Mitigation:** keep MVP closure tied to the five in-scope pages only.

## Risk 6 — Data source sprawl
The MVP could accidentally become a new event-platform project.

**Mitigation:** start from existing logs, bridge events, and backend/runtime seams; normalize before inventing new infrastructure.

---

## 19. Final Recommendation

The correct MVP is **not** “build everything MCP-related into the administration tool.”

The correct MVP is:

> Build a focused MCP Operations Cockpit that gives WoS real operational visibility, case-based diagnosis, structured logs, and a narrow set of safe actions.

That is small enough to be realistic.  
That is large enough to produce immediate operational value.  
That is the right MVP cut.
