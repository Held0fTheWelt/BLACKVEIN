# Phase 2 — Director Pulse, Block-Stream-Bus & Live Cut-In: Status

**Status:** Phase 2 runtime/player-experience chain — **complete**.
Documentation last refreshed 2026-05-20 (post Stage-M finalization and narrated-speech boundary update).
**Last verified:** 2026-05-20
**Roadmap source:** [`NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md`](../../NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md)
**Primary governance:** [ADR-0058](../ADR/adr-0058-director-driven-pulse-block-stream-bus.md), [ADR-0059](../ADR/adr-0059-semantic-npc-motivation-score.md), [ADR-0060](../ADR/adr-0060-souffleuse-inner-voice-composition.md)
**Vocabulary discipline:** [ADR-0039](../ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md) (no Pi/Π runtime keys)

---

## 1. Scope of this document

This is the authoritative "what is shipped, what is wired, what is deferred"
record for Phase 2 of the NPC Interactivity roadmap. It documents:

1. The stage map (A–M) actually present in code, with the module that owns each
   stage and the flag that activates it.
2. ADR governance status (which ADRs are accepted, which sections of ADR-0058
   currently lag behind the implementation).
3. The Phase-2 verification log (which test suites prove which stages today).
4. Capability-matrix / ADR-0039 surface governance for Phase 2 modules.
5. A clean separation of **complete** stages from **deliberate Future Work**
   (no Phase-2 overrun by quietly relabeling missing work as "done").

It does **not** re-narrate `NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md` or
duplicate ADR-0058 §"Decision" — it indexes them and points at the code and
tests that actually realize each stage.

---

## 2. Stage map (A–M) — implementation truth

| Stage | Theme | Module(s) | Activation flag | Status |
|---|---|---|---|---|
| **A** | Director Pulse shadow (per-turn `director_tick_decision.v1`) | `ai_stack/director/director_pulse_shadow.py`, `ai_stack/director/director_pulse_contracts.py` | always on (shadow, `shadow_only=True`) | **complete** |
| **B** | Dual mode block stream (parallel `block_stream_events` channel) | `ai_stack/block_stream_dual_mode.py` | `PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED` | **complete** |
| **B→C** | Stream readiness diagnostics (`phase2_event_stream_readiness`) | `ai_stack/stream_readiness.py` | inherits Stage B | **complete** |
| **C** | Primary event stream (event stream promoted over bundle on the frontend) | `ai_stack/stream_readiness.py` + `frontend/static/play_blocks_orchestrator.js` | server `PHASE2_BLOCK_STREAM_PRIMARY_ENABLED`, client `window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED` | **complete** |
| **D** | WebSocket session loop + live cut-in protocol | `ai_stack/ws_session_loop.py`, `world-engine/app/api/story_ws.py`, `frontend/static/play_blocks_orchestrator.js` | server `PHASE2_WS_SESSION_LOOP_ENABLED`, pacing `PHASE2_WS_BLOCK_PACING_SECONDS`, client `window.WOS_PHASE2_WS_SESSION_LOOP_ENABLED` | **complete** |
| **E** | Autonomous Director tick (event-driven; at-most-one block per tick) | `ai_stack/autonomous_tick.py` | `PHASE2_AUTONOMOUS_TICK_ENABLED` | **complete** |
| **F** | Capability-fed ticks + off-stage update *candidate* preview | `ai_stack/autonomous_tick.py`, `ai_stack/off_stage_updates.py` | inherits Stage E (off-stage path is preview-only without Stage G) | **complete** |
| **G** | Off-stage safe-commit policy (opt-in; preview→commit) | `ai_stack/off_stage_updates.py` (`commit_off_stage_update_candidates`) | inherits Stage F; commit requires per-call `OffStageCommitInputs` policy + targets (preview-only when omitted) | **complete (scaffold)** — see §5.3 |
| **H** | Multi-tick pause loop (bounded explicit pause iteration) | `ai_stack/autonomous_tick.py` (`evaluate_autonomous_pause_loop`) | `PHASE2_AUTONOMOUS_PAUSE_LOOP_ENABLED` (inherits Stage E) | **complete** |
| **I** | Replanning readiness (Stage-I replanning decision: cancel future events only, never mutate history) | `ai_stack/ws_session_loop.py` (`build_replanning_decision`) | inherits Stage D | **complete** |
| **K** | Player cut-in handoff (promotes queued input into the next turn trigger) | `ai_stack/ws_session_loop.py` (`build_player_cut_in_handoff`) | inherits Stage D | **complete** |
| **L** | Post-cut-in replanning + follow-up execution (template render) | `ai_stack/ws_session_loop.py` (`build_post_cut_in_replanning_decision`, `build_post_cut_in_follow_up_event`) | inherits Stage D | **complete** |
| **M** | Semantic NPC follow-up composition (template ↔ semantic dispatcher, closed-enum safety gates) | `ai_stack/ws_session_loop.py` (`_compose_npc_follow_up`, `_run_safety_gates`) | `PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED` **and** an injected `FollowUpSemanticProvider` (both required) | **complete (template + dispatcher); semantic provider wiring is Future Work — see §5.2** |

All flags are **fail-closed**. Off or unparseable values disable the stage.
Stage-A shadow output and Stage-B→C readiness diagnostics ride on every turn
that traverses dual mode, regardless of the primary-rendering flag.

### 2.1 Stage activation order for live smoke

Minimum env vars to drive the full Stage-A→M chain in a live smoke session:

```
PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED=true
PHASE2_BLOCK_STREAM_PRIMARY_ENABLED=true
PHASE2_WS_SESSION_LOOP_ENABLED=true
PHASE2_AUTONOMOUS_TICK_ENABLED=true
PHASE2_AUTONOMOUS_PAUSE_LOOP_ENABLED=true       # optional; Stage H loop
PHASE2_WS_BLOCK_PACING_SECONDS=0.3              # gives the client a real cut-in window
PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED=false  # leave off until provider wired (see §5.2)
```

Frontend window flags (set on `window` before the orchestrator boots):

```
window.WOS_PHASE2_BLOCK_STREAM_ENABLED = true;
window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED = true;
window.WOS_PHASE2_WS_SESSION_LOOP_ENABLED = true;
```

Operator-readable activation surface:
`GET /api/story/runtime/ws-session-loop-support` reports `ws_session_loop_supported`,
`autonomous_tick_enabled`, `autonomous_pause_loop_enabled`, the supported
cut-kind semantics, and the `fallback_path`.

---

## 3. ADR governance status

| ADR | Title | Status | Implementation coverage |
|---|---|---|---|
| [ADR-0039](../ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md) | Gate tests: no hardcoded oracles; no Pi/Π runtime keys | **Accepted** | Enforced by `tests/gates/test_table_b_anti_hardcoding_gate.py` (18/18 passing, incl. Pi-scope and runtime-surface inventory tests). Stage-M additions to `SCENE_ENERGY_CANONICAL_SURFACES` and `INFORMATION_DISCLOSURE_CANONICAL_SURFACES` are scoped to `ai_stack/ws_session_loop.py` only and are commented as Stage M usage. |
| [ADR-0058](../ADR/adr-0058-director-driven-pulse-block-stream-bus.md) | Director-Driven Pulse and Block-Stream-Bus | **Accepted** | Stages A–M plus a Completion Pass documented in the ADR body (refreshed 2026-05-20). Companion short conceptual ADR ([`adr-0058-director-driven-pulse-and-block-stream-bus.md`](../ADR/adr-0058-director-driven-pulse-and-block-stream-bus.md)) carries a Phase-2 completion banner that defers to the long file for the stage map. |
| [ADR-0059](../ADR/adr-0059-semantic-npc-motivation-score.md) | Semantic NPC Motivation Score | **Accepted** | `ai_stack/npc_agency/npc_motivation_score_engine.py` + Stage-F three-tier source classification (`real_runtime_signal` / `module_policy_default` / `missing_signal`) surface via `stream_readiness.classify_motivation_component_sources` (now documented in ADR-0059 §9). |
| [ADR-0060](../ADR/adr-0060-souffleuse-inner-voice-composition.md) | Souffleuse inner-voice composition | **Accepted** | Souffleuse block-type registered in `director_pulse_contracts.BLOCK_TYPE_SOUFFLEUSE` and the WS cut-kind map (`souffleuse → skip_to_end`). Stage-M NPC follow-up composition (template + safety-gated semantic dispatcher) documented in ADR-0060 §9–§12; live Director-composed Souffleuse pressure-escalation blocks remain explicit Future Work (§5.2). |
| [ADR-0061](../ADR/adr-0061-director-pause-mode-for-gathering-interruption.md) | Director-Pause mode | Draft | Phase-1 contract; surfaced to Phase 2 via `gathering_paused` plumbing in the autonomous-tick coordinator. |
| [ADR-0062](../ADR/adr-0062-director-realization-thin-path.md) | Resolver → Director → Narrator thin path | Accepted | Phase-1 thin path that Phase-2 Pulse rides on. |

### 3.1 ADR-0058 documentation refresh (2026-05-20)

Two files exist under `docs/ADR/` for ADR-0058:

- [`adr-0058-director-driven-pulse-and-block-stream-bus.md`](../ADR/adr-0058-director-driven-pulse-and-block-stream-bus.md) — short conceptual ADR; the file other ADRs cross-link to.
- [`adr-0058-director-driven-pulse-block-stream-bus.md`](../ADR/adr-0058-director-driven-pulse-block-stream-bus.md) — long implementation ADR with stage-by-stage detail.

The 2026-05-20 documentation pass folded Stages G, H, I, K, L, and M
plus a Completion Pass into the long file (added stage sections,
flag-table additions, governance/anti-hardcoding entries for every
new stage). The short conceptual ADR carries a Phase-2 completion
banner that points to the long file for the stage map; the two files
agree on every hard boundary.

The duplication itself is left in place rather than collapsed in this
pass — collapsing it is its own ADR-0023 change and is *not* a Phase-2
closure blocker.

The hard guarantees that ADR-0058 asserts (no commit/readiness mutation, no
`validation_outcome` change, no Pi/Π keys, no hardcoded actor/room IDs, cut
semantics block-type-driven) are enforced by Stages G–M:

- `ai_stack/ws_session_loop.py` records `"validation_outcome_changed": False`
  on 5 contract surfaces (Stage K handoff, Stage L replanning decision, Stage L
  follow-up event, Stage M dispatcher results).
- `"graph_state_mutated_mid_turn": False` and `"historical_events_mutated": False`
  recorded on every follow-up artifact.
- No `Pi*` / `Π*` / `pi_*` literals in the modified Phase-2 surfaces (verified
  by the Table-B gate suite).

---

## 4. Verification log

All numbers below were obtained on 2026-05-19 against the current working tree.

### 4.1 Phase-2 module tests (canonical: `tests/run_tests.py`)

| Suite | Command | Result |
|---|---|---|
| ai_stack — WS session loop pure helpers (Stages D, I, K, L, M) | `python -m pytest ai_stack/tests/test_ws_session_loop.py` | **98 passed** (verified 2026-05-19) |
| ai_stack — Director Pulse + autonomous tick + off-stage + readiness + Stages F/G + dual-mode | `python -m pytest ai_stack/tests/test_phase2_director_pulse.py test_autonomous_tick.py test_off_stage_updates.py test_stream_readiness.py test_phase2_stage_f_capability_feeding.py test_phase2_stage_g_off_stage_commits.py test_phase2_dual_mode.py` | **314 passed** (verified 2026-05-19) |
| world-engine — WS session-loop endpoint (Stage D/K/L/M end-to-end at the transport layer) | `python -m pytest world-engine/tests/test_ws_session_loop_endpoint.py` | **49 passed** (verified 2026-05-19) |
| world-engine — MVP3 LDSS integration (committed-state envelope) | `PYTHONPATH=world-engine python -m pytest world-engine/tests/test_mvp3_ldss_integration.py` | **10 passed** (verified 2026-05-19) |
| ai_stack — LDSS canonical-step integration | `python -m pytest ai_stack/tests/test_canonical_step_ldss_output.py ai_stack/tests/test_ldss_canonical_step_integration.py` | **10 passed** (verified 2026-05-19) |
| tests/gates — full architecture-enforcement suite (incl. ADR-0039 Pi-scope, Table-B anti-hardcoding) | `python tests/run_tests.py --suite gates --quick` | **156 passed** (incl. 18 Table-B gate tests, all 14 Table-B aspect surface tests; verified 2026-05-19) |
| frontend — blocks orchestrator (Stage B/C/D client) | `cd frontend; npx jest tests/test_blocks_orchestrator.js` | **95 passed** (verified 2026-05-19) |
| Whitespace gate | `git diff --check` | **clean** |

**Aggregate: 732 Python + 95 JS test cases proving Phase-2 stages A–M, plus
the gate suite proving Table-B / ADR-0039 surface governance. The
2026-05-20 documentation pass touches docs only (ADR-0058 long/short,
ADR-0059, ADR-0060, this status doc, the PIV log); the test counts
above are unchanged by doc-only edits.**

### 4.2 Out-of-scope, pre-existing failures (not Phase-2 regressions)

The repository carries two pre-existing failure buckets that are unrelated to
Phase 2. These are intentionally tracked in the working-tree file
`failing-tests.txt` and confirmed not to touch any `phase2_*` module or any
WS-session-loop surface:

- `tests/test_goc_player_input_greeting_imperative.py` (3 tests) — greeting
  imperative classification regression.
- `tests/test_mvp2_runtime_state_actor_lanes.py`, `test_mvp4_runtime_profile_handoff.py`,
  `test_story_window_projection.py` (5 tests) — pre-existing actor-id
  canonicalization mismatch (`annette_reille` vs `annette`).
- `tests/test_mvp4_contract_opening_truthfulness.py`, `test_story_runtime_*.py`,
  `test_trace_middleware.py` (28 tests) — pre-existing
  `narrator_path_synthesis_module_unavailable` env condition, plus
  `test_story_runtime_aspect_ledger.py` env-tag mismatch (`local` vs `staging`).
- 57 `ai_stack/tests/test_goc_*` / `test_semantic_planner_*` failures in the
  broader ai_stack suite (god_of_carnage long-run breadth, semantic planner
  golden cases, sensory context, etc.) — all unrelated to `phase2_*` modules.

None of these block Phase-2 closure. They are owned by separate workstreams
(narrator path synthesis, actor-id canonicalization, GoC long-run breadth) and
must not be silently rolled into the Phase-2 status.

### 4.3 Diagnostics chain (proof of end-to-end playable Phase-2 chain)

The Stage A–M chain is observable via the WS protocol and per-turn diagnostics:

```
Player Turn                                  ← REST or WS `start_turn`
  ↓ block_stream_event.v1 (Stage D, sequenced over WS)
  ↓ autonomous_tick_evaluated  (Stage E/H, only after a clean delivery)
  ↓ block_stream_event.v1 (autonomous NPC block, originator=autonomous_tick)
  ↓ block_cut + player_cut_in_event.v1 (Stage D cut-in semantics)
  ↓ replanning_decision.v1  (Stage I: cancel future events only)
  ↓ player_cut_in_handoff.v1  (Stage K: promote queued input to next trigger)
  ↓ post_cut_in_replanning_decision.v1  (Stage L: select next-action source)
  ↓ post_cut_in_follow_up_event.v1  (Stage L+M: composition_result with
        composition_mode ∈ {template_render, semantic_generation,
        template_fallback_after_semantic_failure, not_applicable},
        safety_gate_decisions per closed-enum gate, voice_profile metadata)
  ↓ silence path: stream_idle + post_cut_in_follow_up_event.silence_reason
```

Visible follow-up or autonomous blocks may be ordinary `actor_line` blocks or a
single `narrator` block with `composition_kind="narrated_actor_speech"` and
`embedded_speech_spans[]`. The latter is still one stream event; its embedded
span supplies speaker authority for diagnostics and prevents NPC speech from
being misattributed to the player.

Server diagnostics that prove the chain on the WS transport:

- `diagnostics.phase2_event_stream_readiness.{event_stream_present, can_be_primary_candidate, blockers, motivation_score_sources}`
- `diagnostics.phase2_primary_selection.{event_stream_primary_used, event_stream_fallback_reason}`
- `diagnostics.director_pulse.{capability_outputs, capability_outputs_used, capability_outputs_missing, parity}`
- `composition_result.{composition_mode, source_contexts, safety_gate_decisions, rejected_reason, voice_profile_actor_id}`
  on every `post_cut_in_follow_up_event.v1`
- `GET /api/story/runtime/ws-session-loop-support` operator endpoint (reports the active flags)
- Frontend `BlocksOrchestrator.getState()` exposes
  `{active_block_id, live_interruption_supported, last_player_cut_in_event,
  cut_in_count, stream_fallback_reason, proof_level,
  last_primary_selection, last_autonomous_tick_summary}`.

---

## 5. Future work (deliberately deferred — NOT silently rolled into "done")

### 5.1 Full mid-turn graph mutation

**Current state.** Stage I replanning is intentionally "future-events only":
the Director may cancel not-yet-started events and queue the player's input
into the next turn trigger, but it never mutates already-emitted blocks or
the in-flight graph state. `historical_events_mutated: False` and
`graph_state_mutated_mid_turn: False` are recorded on every replanning and
follow-up artifact precisely to make that boundary auditable.

**Why deferred.** Mid-turn graph mutation requires a re-entrancy contract on
the runtime turn graph (proposal → validation → commit) and a rewind story for
the committed canonical-turn lifecycle (ADR-0038). Mixing that into Phase 2
would either weaken ADR-0058's hard guarantees or block Phase-2 closure.

**What "done" looks like later.** A `mid_turn_graph_mutation_decision.v1`
contract that re-runs validation/commit against a delta, with the same
fail-closed flag pattern as Stages D/E. Not in Phase 2 scope.

### 5.2 Stronger semantic generation provider wiring

**Current state.** Stage M ships:

- The `FollowUpSemanticProvider` callable contract.
- The `PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED` opt-in flag.
- The dispatcher that prefers semantic generation when both the flag is on
  **and** a provider is injected, and falls back to the deterministic
  template path otherwise.
- All seven closed-enum safety gates (`length`, `actor_lane`,
  `voice_forbidden_markers`, `no_new_people`, `no_new_rooms`,
  `no_forbidden_plot_facts`, `information_disclosure`) running on **both**
  template and semantic output before any block is emitted.
- A fully structured `follow_up_composition_request.v1` projection (voice
  profile, motivation score, relationship/scene-energy/social-pressure
  outputs, recent visible context, information-disclosure target,
  voice-forbidden markers, max-text cap) that the provider sees.

**Not wired in this commit.** No production semantic provider is registered
on the WS endpoint. The current call sites for `build_post_cut_in_follow_up_event`
do not pass a `composition_provider`, so the dispatcher uniformly takes the
deterministic template path even when the flag is on.

**Why deferred.** Production provider wiring requires:
- A choice of provider lane (Souffleuse semantic provider vs. the cheap
  follow-up provider; ADR-0060 implications).
- Latency budget agreement against `PHASE2_WS_BLOCK_PACING_SECONDS`.
- Langfuse span shape for the semantic call (ADR-mvp4-002 / ADR-0049 evidence
  policy).

**What "done" looks like later.** A registered `composition_provider`
implementation passed through `world-engine/app/api/story_ws.py` into
`build_post_cut_in_follow_up_event`, with the existing `composition_result.provider_metadata`
surface populated and a Langfuse span around the provider call. The gates and
flag scaffolding are already in place; this is wiring, not new contract design.

### 5.3 Richer off-stage memory commit policy

**Current state.** Stage F builds *candidate* off-stage relationship and
hierarchical-memory updates with a hard safety gate. Stage G adds an opt-in
commit path (`commit_off_stage_update_candidates`) that requires explicit
`OffStageCommitInputs` policy + targets per call. When the policy is omitted,
the path stays preview-only.

**Why deferred (full enrichment).** A "rich" off-stage memory commit policy
needs:
- Per-module commit budgets (writes per pause, writes per turn).
- Memory-index target contracts beyond relationship + hierarchical memory
  (e.g. ADR-0045 retrieval-write contracts).
- A retraction / rollback story tied into the canonical-turn lifecycle.

**What "done" looks like later.** A module-policy schema for off-stage write
budgets, plus a documented matrix of which Π27 / Π1 surfaces are write
targets. Not in Phase 2 scope.

### 5.4 Production rollout flags + ADR-0058 file consolidation

**Current state.** All Phase-2 server flags default off. The frontend flags
default off. There is no per-environment rollout policy beyond
`is_*_enabled()` helpers.

**ADR maintenance status (2026-05-20).**

- ADR-0058 (long file) now documents **Stages A–M** plus a **Completion
  Pass** in its Decision body, with closed-enum vocabulary and
  anti-hardcoding postures recorded per stage. ADR-0059 §9 documents
  the Stage F three-tier source classification. ADR-0060 §9–§12
  document the Stage M dispatcher, safety-gate suite, and the
  Souffleuse / NPC follow-up boundary.
- ADR-0058 still exists in two on-disk variants
  (`adr-0058-director-driven-pulse-and-block-stream-bus.md` short /
  `adr-0058-director-driven-pulse-block-stream-bus.md` long). The
  short file now carries a Phase-2 completion banner that defers to
  the long file for the stage map. Collapsing the two files into one
  is **not** a Phase-2 closure blocker — it is its own ADR-0023
  governance change.

**Production rollout flags.** Per-environment policy for the seven
Phase-2 feature flags (server + frontend window flags) remains a
future-work item; the flags themselves all fail closed today.

---

## 6. Closure judgment

**Is Phase 2 a complete end-to-end playable chain?**
Yes for the player-experience chain (player turn → block stream → autonomous
NPC tick → player cut-in → handoff → promoted player input → post-cut-in
replanning → follow-up block or silence → diagnostics) at the WS-transport
+ `ai_stack` pure-helper level, with all closed-enum safety gates and
source-classification diagnostics in place. The Completion Pass in
ADR-0058 records the same chain as the canonical reference.

**Can Phase 2 be marked complete in the roadmap?**
**Yes.** Stages A–M as listed in §2 are complete, the ADR refresh of
2026-05-20 brings ADR-0058/0059/0060 into agreement with the
implemented surfaces, and §5 explicitly separates **deliberate Future
Work** (Stage J full mid-turn graph mutation, Stage M production
provider wiring, richer Stage G off-stage commit policy, per-env
flag rollout, optional ADR-0058 file consolidation) from Phase-2
closure. None of the Future-Work items are required for the Phase-2
completion target defined by `NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md` §4.

**Live-smoke prerequisites:** §2.1 flag set must be active; provider for §5.2
intentionally omitted so the dispatcher exercises the deterministic template
path during smoke runs. Local/live smoke evidence is runtime verification
only — no staging or live-environment claim is recorded here unless the
underlying turn carries explicit environment metadata.

**Diagnostics that prove the chain are live:** §4.3 enumerates the
server-side + client-side surfaces an operator can inspect to confirm
end-to-end Phase-2 behavior on a real session.

**Out-of-scope pre-existing failures:** §4.2 lists the known
pre-existing failure buckets (greeting imperative classification,
actor-id canonicalization, narrator-path synthesis env condition,
GoC long-run breadth, semantic planner golden cases). None touch
`phase2_*` modules, none block Phase-2 closure, and none were
introduced by the 2026-05-20 documentation pass.
