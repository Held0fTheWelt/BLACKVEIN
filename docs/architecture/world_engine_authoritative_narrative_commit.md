# World-Engine Authoritative Narrative Commit Semantics

Status: active runtime behavior (A2 repair).

## Purpose

Define how story turns transition from AI/runtime proposals to authoritative committed narrative state inside the World-Engine story host.

## Authoritative commit model

1. A turn is executed through `StoryRuntimeManager.execute_turn(...)`.
2. Runtime graph output provides interpreted input and diagnostics.
3. The manager evaluates scene progression proposals against runtime projection legality rules:
   - known scene ids from `runtime_projection.scenes`
   - legal edges from `runtime_projection.transition_hints`
4. Only legal transitions are committed to authoritative session state (`current_scene_id`).
5. Every turn emits a `progression_commit` record in turn history and diagnostics:
   - `from_scene_id`
   - `proposed_scene_id`
   - `committed_scene_id`
   - `allowed`
   - `reason`
   - `rule_source`

## Safety semantics

- Illegal or unknown transitions are rejected without mutating committed scene state.
- Missing transition rules do not permit implicit scene mutation.
- Diagnostic output reports proposal and verdict, but does not replace state mutation.

## Observable authoritative state

`GET /api/story/sessions/{session_id}/state` now exposes:

- authoritative `current_scene_id`
- `turn_counter`
- `committed_state` snapshot including `last_progression_commit`

`GET /api/story/sessions/{session_id}/diagnostics` exposes:

- recent turn diagnostics
- committed state snapshot to keep diagnostics coherent with runtime authority

## Scope boundary

- This commit model currently governs scene progression authority.
- Richer canonical state deltas beyond scene progression can be layered on top of the same pattern in later milestones.
