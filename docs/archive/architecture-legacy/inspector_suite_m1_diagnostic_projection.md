# Inspector Suite M1 — Canonical Diagnostic Projection (Single Turn)

> **Superseded for administration-tool routing and UI.** This document remains authoritative for the **backend turn-projection contract** (single-turn envelope, API path, raw-mode posture). For the **current** operator shell, use [`inspector_suite_canonical_workbench.md`](inspector_suite_canonical_workbench.md): canonical route `/manage/inspector-workbench`, template `inspector_workbench.html`, script `manage_inspector_workbench.js`. Legacy admin URLs redirect with `308` to the workbench; the old M1-only template `inspector_suite.html` and script `manage_inspector_suite.js` were **removed** from the repository as non-canonical parallel surfaces.

## Purpose

This document defines the M1 diagnostic spine for Inspector Suite as a **read-only single-turn projection**.

The architectural posture is strict:
- Backend owns diagnostic truth for this surface.
- Administration-tool renders backend projections only.
- Diagnostics are non-authoritative and cannot mutate runtime truth.
- Missing evidence remains explicit (`unsupported` / `unavailable`), never synthesized.
- Mermaid is a subordinate view, not the source of truth.

## Canonical contract location

- Contract module: `backend/app/contracts/inspector_turn_projection.py`
- Root schema version: `inspector_turn_projection_v1`

Root payload includes:
- `schema_version`
- `projection_status`
- `trace_id`
- `backend_session_id`
- `world_engine_story_session_id`
- `warnings`
- `raw_evidence_refs`
- required section envelopes:
  - `turn_identity`
  - `planner_state_projection`
  - `decision_trace_projection`
  - `gate_projection`
  - `validation_projection`
  - `authority_projection`
  - `fallback_projection`
  - `provenance_projection`
  - `comparison_ready_fields`

Each section envelope includes:
- `status`: `supported` | `unsupported` | `unavailable`
- `data`
- `unsupported_reason`
- `unavailable_reason`

## Assembly source-of-truth path

- Assembler: `backend/app/services/inspector_turn_projection_service.py`
- Evidence source: `build_session_evidence_bundle(...)`
- Bridge key: `world_engine_story_session_id`
- Turn focus: latest diagnostics row (`diagnostics[-1]`)
- Canonical basis function: `ai_stack.goc_turn_seams.build_operator_canonical_turn_record(...)`

M1 assembler behavior:
- projects available fields from the single-turn diagnostics event;
- preserves authority/fallback/rejection distinctions when present;
- marks unsupported/unavailable when evidence is absent;
- avoids browser-side semantic reconstruction requirements.

## Read model API

Route:
- `GET /api/v1/admin/ai-stack/inspector/turn/<session_id>`

Auth/gating:
- `require_jwt_moderator_or_admin`
- `require_feature(FEATURE_MANAGE_GAME_OPERATIONS)`
- rate-limited as governance read path

Modes:
- `mode=canonical` (default): canonical versioned projection
- `mode=raw`: includes serialized evidence bundle excerpts for operator inspection

Raw mode posture:
- raw evidence is inspection material;
- raw evidence is not authoritative runtime truth;
- raw mode does not imply backend write capability or semantic completeness.

## Administration-tool posture (historical note vs current repo)

At M1 write-up time, the admin shell used `/manage/inspector-suite` with `inspector_suite.html` and `manage_inspector_suite.js`, and reserved placeholder tabs avoided fake completeness.

**Current repository state:** the unified **Inspector Suite Workbench** implements read-only sections (Turn, Timeline, Comparison, Coverage / Health, Provenance / Raw) on `/manage/inspector-workbench` via `inspector_workbench.html` and `manage_inspector_workbench.js`. Legacy paths above redirect permanently to the workbench; the old standalone templates/scripts are removed.

## Non-goals for M1

M1 does not implement:
- multi-turn timeline analytics,
- cross-run comparison engine,
- fleet-wide semantic coverage analytics,
- runtime/planner/gate redesign,
- authority or commit semantic changes.
