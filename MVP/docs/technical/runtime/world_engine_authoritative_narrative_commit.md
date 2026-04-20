# World-Engine Authoritative Narrative Commit Semantics

Status: active runtime behavior (A2 repair, A2-next hardening).

## Purpose

Define how story turns transition from AI/runtime proposals to authoritative committed narrative state inside the World-Engine story host.

## Authoritative commit model

1. A turn is executed through `StoryRuntimeManager.execute_turn(...)`.
2. Runtime graph output provides interpreted input, generation metadata (including structured output when parsing succeeds), and diagnostics.
3. The manager builds **scene progression candidates** from, in strict priority order:
   1. **Explicit travel command** arguments (`interpreted_input` `explicit_command` with `move` / `goto` / `go` / `scene` / `travel` and a known scene id).
   2. **Model structured output** — `generation.metadata.structured_output.proposed_scene_id` when `generation.success` is true and the id is in the known scene set.
   3. **Player input token scan** — first token matching a known scene id (legacy NL hint path).
4. The manager evaluates the **selected** proposal against runtime projection legality rules:
   - known scene ids from `runtime_projection.scenes` (plus current scene)
   - legal edges from `runtime_projection.transition_hints`
5. Only legal transitions are committed to authoritative session state (`current_scene_id`).
6. Every turn emits a bounded **`narrative_commit`** (`StoryNarrativeCommitRecord`) in diagnostics (for correlation) and in session history as authoritative truth. Fields include:
   - `prior_scene_id`, `proposed_scene_id`, `committed_scene_id`
   - `situation_status` (`continue` | `transitioned` | `blocked` | `terminal`)
   - `allowed`, `authoritative_reason`, `commit_reason_code`
   - `candidate_sources` — audit list of discovered candidates (command / model / token scan), including model ids that are **not** selectable because they are unknown to the projection
   - `selected_candidate_source` — which branch supplied the selected proposal (`explicit_command` | `model_structured_output` | `player_input_token_scan` | null)
   - `model_structured_proposed_scene_id` — raw model `proposed_scene_id` when present (even if not selected or unknown)
   - `committed_interpretation_summary` — bounded linkage from interpretation to progression (not a full world-state delta)
   - `committed_consequences`, `open_pressures`, `resolved_pressures`, `is_terminal`
7. Committed history entries omit full `interpreted_input` and graph blobs; orchestration detail stays in `diagnostics[]` envelopes only.

## Safety semantics

- Illegal or unknown transitions are rejected without mutating committed scene state.
- Missing transition rules do not permit implicit scene mutation.
- Model proposals are **never** authoritative on their own: they pass the same legality checks as other candidates, and explicit travel commands override them.
- Diagnostic envelopes still carry full graph/retrieval orchestration data; committed history entries intentionally omit those blobs.

## Observable authoritative state

`GET /api/story/sessions/{session_id}/state` exposes:

- authoritative `current_scene_id`
- `turn_counter`
- `committed_state` snapshot including `last_narrative_commit`, summary fields, and recent consequence tokens
- `last_committed_turn` including `narrative_commit` (bounded) and `committed_state_after`

`GET /api/story/sessions/{session_id}/diagnostics` exposes:

- recent turn diagnostics (full envelopes, including `graph` / `retrieval`)
- `authoritative_history_tail` without graph blobs, aligned with committed truth

## Scope boundary (intentionally conservative)

- This commit model governs **scene id progression** only, not full simulation of physical actions, social outcomes, or inventory.
- Structured model output that fails JSON parsing does not contribute a model candidate (same as before; no fabricated proposals).
- Richer canonical state deltas beyond scene progression can be layered on the same audit pattern in later milestones.
