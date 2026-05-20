# PR-0 — NPC Interactivity Runtime Contracts + PIV Baseline (PIV Artifact)

**PR title:** PR-0 — NPC Interactivity Runtime Contracts + PIV Baseline
**Status:** Draft (this commit)
**Date:** 2026-05-19
**Roadmap section:** Phase 1 §3.0 (pre-PR-A contract spec) and §3.5 (`runtime_diagnostic_snapshot.v1`) of [`NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md`](../../NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md)
**Roadmap index entry:** [`docs/MVPs/npc_interactivity_piv_log.md`](../MVPs/npc_interactivity_piv_log.md)

**Reviewer rule (binding):** Every `file:line` reference in this document was verified against repository HEAD on 2026-05-19. False or invented `file:line` references are reject-worthy. Where the roadmap plan differs from current truth, the discrepancy is captured in §6 explicitly.

---

## 1. Scope (in one paragraph)

PR-0 establishes the contract and verification baseline that PR-A, PR-B, and PR-C will build against. It adds (a) this PIV artifact, (b) the roadmap PIV index, (c) the ADR-0057 Phase-1 amendment that names the four runtime contracts, (d) the ADR-0061 Draft that defines the Director-Pause mode, (e) a `runtime_diagnostic_snapshot.v1` envelope stub (no UI page beyond an optional smoke link if needed), and (f) acceptance tests that prove no runtime behavior changed. PR-0 does **not** implement any of the four contracts, does **not** modify the resolver or director, does **not** add a runtime aspect ledger row, and does **not** ship a diagnostic UI page.

## 2. Consumer scan — files that today consume the contract surfaces PR-A/B/C will extend

| Surface today | File:line (verified) | What it does today | What PR-A/B/C will change |
|---|---|---|---|
| Player-action resolution entry point | [`ai_stack/player_action_resolution.py:502`](../../ai_stack/player_action_resolution.py) `resolve_player_action()` | Builds `PlayerActionFrameContract` + `AffordanceResolutionContract`; returns frame, affordance, scene affordance model. Today does **not** guarantee `resolved_target_type: "location"` for paraphrased movement inputs in every register. | PR-A closes the resolver contract so movement paraphrases reliably produce `resolved_target_type: "location"` + `resolved_target_id`. |
| Canonical-path-control policy projection | [`ai_stack/module_runtime_policy.py:413`](../../ai_stack/module_runtime_policy.py) | Projects `runtime_governance_policy.player_freedom.canonical_path_control` from module YAML. | No change in PR-0; PR-B may extend to expose hold-effect provenance. |
| Canonical-path-control policy consumer | [`ai_stack/player_action_resolution.py:336`](../../ai_stack/player_action_resolution.py) `policy.get("canonical_path_control")` | Reads the module's default hold mode. | PR-B will propagate `canonical_path_hold_effect.v1` source (`ai_semantic_plausible_inference`, `gathering_paused`, `social_wait_policy`) alongside the existing literal. |
| Hold-effect read at commit | [`world-engine/app/story_runtime/manager.py:8683-8687`](../../world-engine/app/story_runtime/manager.py) `_turn_holds_canonical_path_for_free_player_action()` | Returns `True` iff `player_action_frame.canonical_path_effect == "hold_current_step"`. | PR-B will ensure the effect string lands consistently in `graph_state` after every mundane inference; the read site stays. |
| Hold-effect gate against pointer advance | [`world-engine/app/story_runtime/manager.py:8746`](../../world-engine/app/story_runtime/manager.py) | Gates `session.canonical_step_id` advance when the hold returns `True`. | No change in PR-0; PR-B uses this gate as the acceptance probe. |
| Canonical-path control block in graph state | [`ai_stack/langgraph/langgraph_runtime_executor.py:4703`](../../ai_stack/langgraph/langgraph_runtime_executor.py) | Constructs the `canonical_path_control` projection block in graph_state from policy. | PR-B will extend the block with `until_condition` and `source` fields from `canonical_path_hold_effect.v1`. |
| NPC agency / responder selection | [`ai_stack/director/scene_director_goc.py:655`](../../ai_stack/director/scene_director_goc.py) `_build_responder_set()` definition; call site at [`:911`](../../ai_stack/director/scene_director_goc.py) | Selects NPC responders for the current beat. | PR-C wraps this with a `gathering_paused` gate: when paused, mandatory-beat consumption is suppressed (no responder selection drives a step advance). |
| NPC agency plan projection | [`ai_stack/langgraph/langgraph_runtime_executor.py:3996`](../../ai_stack/langgraph/langgraph_runtime_executor.py) `_build_npc_agency_plan_projection()` definition; call site at [`:4279`](../../ai_stack/langgraph/langgraph_runtime_executor.py) | Builds the NPC agency plan that the LDSS consumes. | PR-C consults `director_gathering_state.v1` here so paused gatherings short-circuit mandatory-beat consumption without removing NPC mundane-action freedom. |
| Named-characters predicate (content) | [`content/modules/god_of_carnage/canonical_path/005_statement_reading.yaml:36`](../../content/modules/god_of_carnage/canonical_path/005_statement_reading.yaml) `named_characters: [...]` | Declares which actors must be co-present for the step to consume mandatory beats. | PR-C reads this as the source of `presence_required_for_step` in `director_gathering_state.v1`. |
| Runtime aspect ledger keys | [`ai_stack/runtime_aspect_ledger.py:128-163`](../../ai_stack/runtime_aspect_ledger.py) `ASPECT_KEYS` | Enumerates the persisted runtime-aspect rows. No Director-Pause row exists today. | PR-C will either reuse an existing aspect (e.g. `npc_agency` companion field) or, if a new aspect row is required, that addition is scoped in PR-C with its own ADR-0061 evidence — **not** in PR-0. |

**Cross-cutting consumer note.** The four PR-A/B/C contracts are **runtime data contracts**, not new node names. They flow through existing graph state keys (`player_action_frame`, `affordance_resolution`, `canonical_path_control`, `narrator_consequence_packet`) plus a new graph-state key for `director_gathering_state` (PR-C). PR-0 introduces only the **names and field lists**; no consumer is added.

## 3. Existing-path probe — what runs today for the action classes Phase 1 targets

Phase 1 illustrates four action classes (§3.4 of the plan). For each, the existing-path probe records what runtime code executes today **before** PR-A/B/C land.

- **Mundane local action ("look out the window", "take off coat") today.** Input → `resolve_player_action()` → semantic AI resolution path → `affordance_resolution.status="allowed"` → `canonical_path_effect="hold_current_step"` (via policy projection) → manager `_turn_holds_canonical_path_for_free_player_action()` returns `True` → canonical step pointer holds. Observed gaps (per plan §2.2): live narrator block emission for `requires_model_realization=true` is not reliable end-to-end; hold-effect propagation has paths where the effect is missing from `graph_state` and the pointer drifts. **PR-0 records only the gap; PR-B closes it.**
- **Local mundane movement to a non-gathering room ("go to the kitchen") today.** Input → resolver attempts location target inference. Observation (per plan §1.d.0): paraphrased movement inputs do not yet **reliably** produce `resolved_target_type: "location"` + `resolved_target_id` across registers. **PR-0 records only the gap; PR-A closes it.**
- **Leaving the gathering ("I leave the apartment") today.** Input → resolver may classify as ambiguous or as location movement; no Director-Pause exists today. The hold remains on the player, not on the gathering — which is exactly the inversion the plan calls out. **PR-0 records only the gap; PR-C closes it.**
- **Return to the gathering ("I come back to the living room") today.** No `gathering_paused` state to clear; behavior is identical to any other movement. **PR-0 records only the gap; PR-C closes it.**

## 4. Live-smoke feasibility probe — what evidence exists, what is still missing

| Evidence channel | Today | After PR-A/B/C |
|---|---|---|
| Langfuse spans for `resolve_player_action` | Yes (via existing thin-path summary in ADR-0062). | PR-A adds `resolved_target_type`, `resolved_target_id`, `presence_breaks_gathering`, `affordance_status`, `canon_safety`, `canonical_risk`, `action_commit_policy` as structured span fields. |
| Operator endpoint exposing per-turn evidence | `GET /api/story/sessions/{session_id}/thin-path-summary` (per [ADR-0062](../ADR/adr-0062-director-realization-thin-path.md)). | PR-A/B/C add the same fields to the existing endpoint's payload — no new endpoint family for PR-0. |
| Runtime aspect ledger row for Director-Pause | None. Aspect keys today (`ai_stack/runtime_aspect_ledger.py:128-163`) do not include a Director-Pause row. | PR-C decides whether to add a row or attach `gathering_paused` to an existing aspect; ADR-0061 records that decision. |
| Diagnostic UI surface | `world-engine/app/web/templates/ui/narrative_systems.html` is the natural home per plan §3.5; today it shows thin-path evidence only. | PR-A/B/C add structured fields to the existing page through the operator endpoint above. PR-0 introduces **no** UI page; the snapshot envelope stub is contract-only. |
| Live-smoke session ("smoke link") | `WOS_THIN_PATH_LIVE_SMOKE=1 python -m pytest tests/smoke/test_thin_path_pr_a_live_smoke.py` (per ADR-0062). | PR-A extends this smoke; PR-B/PR-C add their own live smokes against the same model. |

**Feasibility verdict.** PR-A/B/C can be observed via existing operator/Langfuse channels. PR-0 does **not** need to add a new surface — only the envelope shape that PR-A/B/C will populate.

## 5. Anti-dead-end checkpoints

Each checkpoint names a failure mode that PR-A/B/C must surface as observable runtime evidence rather than as a silent degradation.

1. **Resolver returns `null` target on a clearly-bounded movement input.** Must surface as `affordance_status: unknown_target` with a `classification_reason` field — not as a silent generic `interact` fallback. PR-A is responsible; PR-0 names the field in ADR-0057 amendment.
2. **`canonical_path_effect: hold_current_step` not propagated after a mundane inference.** Must surface as a missing/non-`hold_current_step` value in the per-turn snapshot, observable at `manager.py:8683-8687` (the read site). PR-B is responsible; PR-0 names `canonical_path_hold_effect.v1` so PR-B has a contract to fail against.
3. **`narrator_consequence_packet` with `requires_model_realization: true` produces no visible block.** Must surface as `narrator_consequence_realization.v1.realized_block_id == null` with a `non_realization_reason` field — not as a silent missing block. PR-B is responsible; PR-0 names the contract.
4. **Director-Pause transition `false → true` without a narrator reaction block.** Must surface as an explicit `transition_reaction_emitted: false` field in `director_gathering_state.v1` so absence is observable. PR-C is responsible; PR-0 names the contract.
5. **Off-stage NPC mundane action conflated with mandatory-beat consumption while paused.** Must surface in the runtime evidence as `mandatory_beat_consumed_during_pause: false` so a regression that consumes a beat under pause fails an assertable invariant. PR-C is responsible; PR-0 records the invariant only.

## 6. Plan-file reference reconciliation (verified differences)

The plan file cites several `file:line` anchors. The following were verified against repository HEAD on 2026-05-19. Where the plan and current truth disagree, the truth column wins and is what PR-A/B/C must build against.

| Plan claim | Verified truth | Note |
|---|---|---|
| `manager.py:8703-8717` for `_turn_holds_canonical_path_for_free_player_action()` | `world-engine/app/story_runtime/manager.py:8683-8687` (def) and `:8746` (call site) | Function moved up by ~20 lines since plan was written. |
| `langgraph_runtime_executor.py:4276-4335` for `_build_npc_agency_plan_projection()` | `ai_stack/langgraph/langgraph_runtime_executor.py:3996` (def) and `:4279` (call site at the cited block) | Definition lives ~280 lines above the cited range; call site is at the lower bound. |
| `langgraph_runtime_executor.py:4681-4718` for `canonical_path_control` block | `ai_stack/langgraph/langgraph_runtime_executor.py:4703` (block opens at this line) | Block exists; opening line ~22 lines later than plan's lower bound. |
| `scene_director_goc.py:911-943` for `_build_responder_set()` | `ai_stack/director/scene_director_goc.py:655` (def) and `:911` (call site) | Plan's range was the call site; the function definition is much earlier. |
| `005_statement_reading.yaml:36` `named_characters: [veronique, michel, annette, alain]` | Verified at line 36. | Matches. |

These corrections must propagate into PR-A/B/C PIV artifacts when those PRs are opened.

## 7. What existing paths will be extended later (not in PR-0)

- `ai_stack/player_action_resolution.py:502` — PR-A adds the contract fields enumerated in `free_player_action_resolution.v1`.
- `ai_stack/langgraph/langgraph_runtime_executor.py:4703` — PR-B extends the `canonical_path_control` block with `canonical_path_hold_effect.v1` fields.
- `ai_stack/narrator_consequence_contracts.py` — PR-B adds `narrator_consequence_realization.v1` realization-evidence fields.
- `ai_stack/director/scene_director_goc.py:655` / `ai_stack/langgraph/langgraph_runtime_executor.py:3996` — PR-C introduces the `gathering_paused` gate around mandatory-beat consumption.
- `world-engine/app/story_runtime/manager.py:8683-8687` — PR-B uses this read site as its acceptance probe (no signature change).
- `world-engine/app/web/templates/ui/narrative_systems.html` and the `thin-path-summary` operator endpoint — PR-A/B/C extend the existing surface with the snapshot fields PR-0 envelopes. No new page family.

## 8. What must not be touched in PR-0

- `ai_stack/player_action_resolution.py` — no change. Resolver behavior is unchanged.
- `ai_stack/narrator_consequence_contracts.py` — no change. Narrator consequence logic is unchanged.
- `ai_stack/canonical_path_resolver.py` — no change. Canonical path loading is unchanged.
- `ai_stack/director/scene_director_goc.py` — no change. Director / responder selection is unchanged.
- `ai_stack/langgraph/langgraph_runtime_executor.py` — no change. Graph nodes, routing, and `canonical_path_control` block are unchanged.
- `ai_stack/live_dramatic_scene_simulator.py` — no change. LDSS / mandatory-beat consumption is unchanged.
- `ai_stack/module_runtime_policy.py` — no change. Policy projection is unchanged.
- `world-engine/app/story_runtime/manager.py` — no change. The hold-read site (`_turn_holds_canonical_path_for_free_player_action`) and all commit / readiness paths are unchanged.
- `world-engine/app/web/templates/ui/**` — no change. No diagnostic UI page is introduced.
- `world-engine/app/api/**` — no change. No operator endpoint is added.
- `ai_stack/runtime_aspect_ledger.py` — no change. `ASPECT_KEYS` is unchanged; no Director-Pause aspect row is added.
- `ai_stack/goc_narrator_path.py` — no change. Narrator path (Turn 0) is unchanged.
- `ai_stack/goc_souffleuse.py` — no change. Souffleuse production is unchanged.
- `frontend/static/play_typewriter_engine.js` — no change. Block streaming and cut-in semantics are unchanged.
- Any schema/database migration — none introduced.
- Any Commit / Readiness gate — none changed.
- Any prompt or story generation template — none changed.
- Any NPC pulse logic — none introduced.

## 9. Pre-existing baseline observation (out of PR-0 scope)

Independent of this PR, the following baseline test fails at HEAD on 2026-05-19:

```
tests/test_capability_matrix_documentation_readiness.py::test_capability_matrix_doc_links_resolve
```

Reason: `docs/MVPs/capability_matrix_status_and_adr_relations.md` contains a markdown link to `../../content/modules/god_of_carnage/direction/character_voice.yaml`, and that file moved to `content/modules/god_of_carnage/characters/voices/character_voice_*.yaml` (per-actor). The link target no longer exists.

PR-0 **does not fix this**. The cleanup belongs to a separate doc-hygiene change, not to the NPC interactivity roadmap. The failure is recorded here so it is not confused with a side-effect of PR-0.

## 10. Acceptance evidence for PR-0 itself

PR-0 must satisfy:

1. `docs/MVPs/npc_interactivity_piv_log.md` exists and lists PR-0 with a link to this PIV artifact.
2. This PIV artifact exists at `docs/implementation_logs/pr_0_npc_interactivity_contracts_piv.md` and contains every required section (1 through 8).
3. [ADR-0057](../ADR/adr-0057-canon-safe-player-freedom-and-affordance-inference.md) has a Phase-1 contracts amendment naming exactly four contracts: `free_player_action_resolution.v1`, `director_gathering_state.v1`, `canonical_path_hold_effect.v1`, `narrator_consequence_realization.v1`.
4. [ADR-0061](../ADR/adr-0061-director-pause-mode-for-gathering-interruption.md) exists with `Status: Draft` and defines `director_gathering_state.v1`, `compute_gathering_state`, the named-character presence predicate, the beat-consumption pause, the player-freedom invariant, the return-clears-pause condition, the optional narrator transition reaction, and the explicit non-goals (no Phase-2 pulse, no pointer repair, no `step.mode` switch).
5. The `runtime_diagnostic_snapshot.v1` envelope stub exists as a contract definition with the placeholder fields enumerated in §3.5 of the plan.
6. The acceptance tests in `tests/test_npc_interactivity_piv_baseline.py` pass and verify that no PR-A/B/C runtime symbols were introduced.

## 11. Footer

- Verification date: 2026-05-19
- Repository SHA at verification time: see git log (HEAD prior to this commit)
- Author handoff: PR-A may begin once this PIV is merged and the four-contract surface in ADR-0057's Phase-1 amendment is reviewed.
