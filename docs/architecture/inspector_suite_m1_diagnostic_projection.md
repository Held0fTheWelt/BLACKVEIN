# Inspector Suite M1 — Canonical Diagnostic Projection (Single Turn)

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

## Administration-tool posture

- Route: `/manage/inspector-suite` (alias: `/manage/inspector-suite/turn`)
- Template: `administration-tool/templates/manage/inspector_suite.html`
- Script: `administration-tool/static/manage_inspector_suite.js`

M1 implemented section:
- `Turn Inspector` (functional)

M1 reserved, explicitly non-implemented sections:
- `Timeline`
- `Comparison`
- `Coverage / Health`
- `Provenance / Raw Inspector`

These reserved sections are intentionally visible placeholders to avoid fake completeness.

## Non-goals for M1

M1 does not implement:
- multi-turn timeline analytics,
- cross-run comparison engine,
- fleet-wide semantic coverage analytics,
- runtime/planner/gate redesign,
- authority or commit semantic changes.
