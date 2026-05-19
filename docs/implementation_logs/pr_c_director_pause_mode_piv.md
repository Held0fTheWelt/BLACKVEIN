# PR-C — Director Pause Mode — PIV Artifact

**Status:** Draft
**Created:** 2026-05-19
**Roadmap source:** [`NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md`](../../NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md) §3.4
**ADR:** [`adr-0061-director-pause-mode-for-gathering-interruption.md`](../ADR/adr-0061-director-pause-mode-for-gathering-interruption.md)

---

## 1. Consumer Scan

### 1.1 Consumers of `free_player_action_resolution.v1`

| File | Line | Consumer description |
|------|------|---------------------|
| `ai_stack/free_player_action_resolution_contracts.py` | 44 | SCHEMA_VERSION constant; contract builder |
| `ai_stack/player_action_resolution.py` | 32 | Imports `build_free_player_action_resolution` |
| `ai_stack/canonical_path_hold_effect_contracts.py` | 170 | Reads the `.v1` dict as input to build hold-effect |
| `ai_stack/langgraph_runtime_executor.py` | 6308–6315 | Lifts `canonical_path_hold_effect` into graph state |
| `ai_stack/runtime_diagnostic_snapshot_contracts.py` | 63–67 | `ResolverOutputPlaceholder` — reserves payload slot |
| `ai_stack/tests/test_free_player_action_resolution_contract.py` | passim | Contract tests |

### 1.2 Consumers of `canonical_path_hold_effect.v1`

| File | Line | Consumer description |
|------|------|---------------------|
| `ai_stack/canonical_path_hold_effect_contracts.py` | 48 | SCHEMA_VERSION constant; contract builder |
| `ai_stack/player_action_resolution.py` | 29–31 | Imports builder |
| `ai_stack/langgraph_runtime_executor.py` | 6308–6315 | Lifts into graph state as top-level key |
| `world-engine/app/story_runtime/manager.py` | 8706–8710 | `_turn_holds_canonical_path_for_free_player_action` reads frame literal |
| `world-engine/app/story_runtime/manager.py` | 8769 | Gate against step advance uses the hold |
| `ai_stack/runtime_diagnostic_snapshot_contracts.py` | 80–88 | `CanonicalPathHoldEffectPlaceholder` |

### 1.3 Current place where mandatory beats / NPC responder sets are chosen

| File | Line | Description |
|------|------|-------------|
| `ai_stack/langgraph_runtime_executor.py` | 7324–7337 | `phase_beat_candidates` + `select_beat_candidate` |
| `ai_stack/langgraph_runtime_executor.py` | 3999–4029 | `_build_npc_agency_plan_projection` — responder ids |
| `ai_stack/scene_director_goc.py` | 655–741 | `_build_responder_set` — primary + secondary + interrupter |
| `ai_stack/scene_director_goc.py` | 744–943 | `build_responder_and_function` — full director resolution |
| `ai_stack/beat_lifecycle_contracts.py` | 1–165 | Beat lifecycle schema, `phase_beat_candidates`, `select_beat_candidate` |

### 1.4 Current diagnostic exposure path

| File | Line | Description |
|------|------|-------------|
| `ai_stack/runtime_diagnostic_snapshot_contracts.py` | 107–148 | `RuntimeDiagnosticSnapshotEnvelope` — PR-0 stub; has `director_gathering_state` slot |
| `ai_stack/langgraph_runtime_executor.py` | 6309 | "thin-path summary" comment; graph state keys readable by manager |

---

## 2. Existing-Path Probe

### 2.1 What happens today when the player leaves the gathering?

1. `resolve_player_action` (ai_stack/player_action_resolution.py) classifies the action.
2. `build_free_player_action_resolution` emits `presence_breaks_gathering: False` (preliminary, line 460).
3. `build_canonical_path_hold_effect` may return a hold if `canonical_path_effect == "hold_current_step"`.
4. The executor (langgraph_runtime_executor.py:6313–6315) lifts hold-effect into graph state.
5. The manager (manager.py:8769) checks `_turn_holds_canonical_path_for_free_player_action` — if frame says `hold_current_step`, step does NOT advance.
6. Beat consumption at executor:7324–7337 proceeds normally even when the player is absent from the gathering — **this is the gap PR-C fixes**.

### 2.2 Missing piece

No code path today suppresses mandatory-beat consumption when `named_characters` are not co-present. The hold only prevents step advance; it does not prevent beat selection/consumption within the current step.

---

## 3. Live-Smoke Feasibility Probe

- `director_gathering_state.v1` slot already reserved in `RuntimeDiagnosticSnapshotEnvelope` (runtime_diagnostic_snapshot_contracts.py:136).
- The existing graph state mechanism (dict keys on `state`) already propagates `canonical_path_hold_effect`; the same mechanism will propagate `director_gathering_state`.
- The existing `presence_breaks_gathering_evidence` triple (target_location, participation_relevance, visibility_audibility) is emitted by PR-A (free_player_action_resolution_contracts.py:445–449).
- Canonical path steps (e.g. 005_statement_reading.yaml:36) declare `named_characters: [veronique, michel, annette, alain]` — the data source for required presence.

---

## 4. Anti-Dead-End Checkpoints

| Failure mode | Mitigation |
|---|---|
| `compute_gathering_state` returns paused=True incorrectly → game stalls | Pure function unit tests with all actor-topology combinations |
| Pause never clears → gathering permanently stuck | Return-clears-pause test; assert `paused=False` when actors restored |
| Beat consumption still happens during pause | Test asserts beat selection gated by `director_gathering_state.paused` |
| Narrator reaction emits hardcoded text | Safety triple assertion: no_new_people, no_new_rooms, no_plot_facts |
| Canonical step advances during pause | Existing hold gate + new gathering_paused gate; tested |

---

## 5. File:Line References (verified 2026-05-19)

| Reference | Verified |
|---|---|
| `ai_stack/free_player_action_resolution_contracts.py:44` — SCHEMA_VERSION | ✓ |
| `ai_stack/free_player_action_resolution_contracts.py:445–449` — presence_evidence triple | ✓ |
| `ai_stack/free_player_action_resolution_contracts.py:460` — `presence_breaks_gathering: False` | ✓ |
| `ai_stack/canonical_path_hold_effect_contracts.py:48` — SCHEMA_VERSION | ✓ |
| `ai_stack/canonical_path_hold_effect_contracts.py:78–90` — UNTIL_CONDITIONS including `presence_restored` | ✓ |
| `ai_stack/narrator_consequence_realization_contracts.py:181–269` — builder | ✓ |
| `ai_stack/runtime_diagnostic_snapshot_contracts.py:70–77` — DirectorGatheringStatePlaceholder | ✓ |
| `ai_stack/runtime_diagnostic_snapshot_contracts.py:136` — envelope slot | ✓ |
| `ai_stack/scene_director_goc.py:655–741` — `_build_responder_set` | ✓ |
| `ai_stack/scene_director_goc.py:744–943` — `build_responder_and_function` | ✓ |
| `ai_stack/langgraph_runtime_executor.py:7324–7337` — beat selection | ✓ |
| `ai_stack/langgraph_runtime_executor.py:3999–4029` — `_build_npc_agency_plan_projection` | ✓ |
| `ai_stack/langgraph_runtime_executor.py:6308–6315` — hold-effect lift to graph state | ✓ |
| `world-engine/app/story_runtime/manager.py:8706–8710` — `_turn_holds_canonical_path_for_free_player_action` | ✓ |
| `world-engine/app/story_runtime/manager.py:8764–8773` — step advance gate | ✓ |
| `content/modules/god_of_carnage/canonical_path/005_statement_reading.yaml:36` — `named_characters` | ✓ |
| `ai_stack/beat_lifecycle_contracts.py:125` — `phase_beat_candidates` import | ✓ (executor import) |

---

## 6. What Existing Paths Will Be Extended Later

| Path | Future PR |
|---|---|
| `_build_npc_agency_plan_projection` — per-NPC pulse logic | Phase 2 (ADR-0058) |
| `_build_responder_set` — motivation-score ranked NPC reactions | Phase 2 (ADR-0059) |
| Souffleuse inner voice during pause | Phase 2 (ADR-0060) |
| `RuntimeDiagnosticSnapshotEnvelope` — full UI page rendering | Phase 2 |

---

## 7. What PR-C Must NOT Touch

| Path | Reason |
|---|---|
| Opening/narrator path (`_execute_opening_locked`, Turn-0 handling) | ADR-0061 non-goal |
| Pointer repair logic | ADR-0061 non-goal |
| Prompt/story generation (outside transition reaction) | Scope boundary |
| Frontend/player UI | Scope boundary |
| Full Pulse/Event-Stream architecture | Phase 2 |
| Souffleuse Phase-2 behavior | Phase 2 |
| `step.mode` enum switching | ADR-0061 explicitly prohibited |
| Verb/room/action whitelists | ADR-0039 + ADR-0061 prohibited |
| Active Pi/Π runtime keys | ADR-0039 prohibited |
