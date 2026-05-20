# PR-D — Phase-1 closure (aggregator + operator UI + ADR-0061 Accept)

**Date:** 2026-05-20  
**Roadmap:** NPC Interactivity — Sub-Plan 1 closure  
**Classification:** Genuine gap (operator aggregation + governance), not plan drift.

## 1. Consumer scan

| Consumer | Location | Reads |
|----------|----------|-------|
| `GET .../runtime-diagnostic-snapshot` | `world-engine/app/api/http.py` | `StoryRuntimeManager.get_runtime_diagnostic_snapshot` |
| Narrative Systems UI | `world-engine/app/web/static/ui_narrative_systems.js` | snapshot + thin-path-summary |
| Tests | `world-engine/tests/test_runtime_diagnostic_snapshot_api.py` | envelope shape |

Production graph / `langgraph_runtime_executor` — **no** import of `ai_stack.runtime_diagnostic_snapshot_contracts`.

## 2. Existing-path probe

| Surface | Already exists |
|---------|----------------|
| Per-turn Phase-1 fields | `observability_path_summary` → `get_thin_path_summary` (`diagnostics_api.py:6-78`) |
| Pulse | `diagnostics.director_pulse` on turn events (`ai_stack/tests/test_phase2_dual_mode.py`) |
| Parity | `diagnostics.director_pulse.parity` or `bundle_vs_event_stream_parity` |

PR-D **aggregates** these; it does not re-emit graph state.

## 3. Live-smoke feasibility

Operator can open Narrative Systems → session → structured snapshot sections + raw JSON. HTTP route returns 200 with `runtime_diagnostic_snapshot.v1` without executing a turn.

## 4. Anti-dead-end checkpoints

| Checkpoint | Result |
|------------|--------|
| Second graph path for diagnostics | **Stopped** — aggregator only |
| Import PR-0 stub in manager | **Stopped** — dict envelope built inline |
| Force `presence_breaks_gathering` on resolver | **Out of scope** — ADR-0061 director_final |

## 5. Hold-path audit (`canonical_step_id` writers)

Verified grep in `world-engine/app/story_runtime/manager/`:

| Writer | File | Notes |
|--------|------|-------|
| LDSS fallback advance | `ldss_narrative_queue.py:30,65` | Advances when hold false |
| Opening continuation | `opening_execution.py:145-147` | Opening only |
| Turn execution projection | `turn_execution.py:93` | Passes context; not a direct advance |

Primary thin player path does not list a separate `canonical_step_id` increment outside LDSS/opening. **Conclusion:** `_turn_holds_canonical_path_for_free_player_action` in LDSS fallback (`manager` mixin ~9148–9215) is the active gate; **no second caller required** unless a future path advances the pointer on free action (none found 2026-05-20).

## 6. File:line references (delivery)

- `world-engine/app/story_runtime/manager/diagnostics_api.py` — `get_runtime_diagnostic_snapshot`
- `world-engine/app/api/http.py` — route
- `world-engine/app/web/static/ui_narrative_systems.js` — structured sections
- `docs/ADR/adr-0061-director-pause-mode-for-gathering-interruption.md` — Status → Accepted

## 7. What this PR does not touch

- Resolver / `compute_gathering_state` semantics
- Phase-2 pulse implementation
- `deferred_capability` routing (ADR-0062 scope)
