# PR-B — Live Effect Propagation (PIV Artifact)

**PR title:** PR-B — Live Effect Propagation (`canonical_path_hold_effect.v1`, `narrator_consequence_realization.v1`)
**Status:** Draft (this commit)
**Date:** 2026-05-19
**Roadmap section:** Phase 1 §3.0 / §3.1 / §3.6 of [`NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md`](../../NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md); sub-phase **1.d.1** (Live-Effekt-Propagation).
**Roadmap index entry:** [`docs/MVPs/npc_interactivity_piv_log.md`](../MVPs/npc_interactivity_piv_log.md)
**Supersedes / extends:** [PR-A PIV](pr_a_resolver_contract_closure_piv.md), [PR-0 PIV](pr_0_npc_interactivity_contracts_piv.md)
**Governance:** [ADR-0057 Phase-1 amendment](../ADR/adr-0057-canon-safe-player-freedom-and-affordance-inference.md), [ADR-0061 (Draft)](../ADR/adr-0061-director-pause-mode-for-gathering-interruption.md), [ADR-0062](../ADR/adr-0062-director-realization-thin-path.md), [ADR-0039](../ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md).

**Reviewer rule (binding):** Every `file:line` reference in this artifact was verified against repository HEAD on 2026-05-19 prior to writing code. False or invented `file:line` references are reject-worthy. Where a PR-A anchor has shifted, the discrepancy is recorded in §6 explicitly.

---

## 1. Scope (one paragraph)

PR-B closes the **live effect propagation** between the resolver contract that PR-A delivered (`free_player_action_resolution.v1`) and the two places where the live runtime needs to act on it: (a) the canonical-path pointer hold (so a mundane free action does **not** spend the next canonical step), and (b) the narrator consequence realization (so a `requires_model_realization=true` plan produces a visible `narrator` / `environment_interaction` block, or carries an explicit `non_realization_reason`). PR-B introduces two per-turn projection contracts — `canonical_path_hold_effect.v1` and `narrator_consequence_realization.v1` — both derived from semantic contract fields (`canon_safety`, `canonical_risk`, `action_commit_policy`, `affordance_status`, `requires_model_realization`, `source`). The hold contract rides into graph state alongside the existing `player_action_frame.canonical_path_effect == "hold_current_step"` literal that the manager already reads at [`world-engine/app/story_runtime/manager.py:8683-8687`](../../world-engine/app/story_runtime/manager.py); the realization contract is a projection over the `narrator_consequence_plan` ([`ai_stack/narrator_consequence_contracts.py:169-243`](../../ai_stack/narrator_consequence_contracts.py)) and the `visible_output_bundle.scene_blocks` produced by [`ai_stack/langgraph/langgraph_runtime_executor.py:10337-10381`](../../ai_stack/langgraph/langgraph_runtime_executor.py). PR-B does **not** implement Director Pause, NPC pulse, pointer repair, `step.mode` switching, verb/room/action whitelists, or active Pi / Π runtime keys. PR-B does **not** modify resolver semantics, the LDSS beat-consumption gate, the opening narrator path, commit/readiness, prompt/story generation outside the existing narrator consequence path, or UI templates.

## 2. Consumer scan — what consumes the PR-B contracts today

| Surface today | File:line (verified 2026-05-19) | What it does today | What PR-B changes |
|---|---|---|---|
| Resolver entry | [`ai_stack/player_action_resolution.py:548`](../../ai_stack/player_action_resolution.py) `resolve_player_action()` | Builds frame + affordance + `free_player_action_resolution.v1` (PR-A) and emits envelope. | PR-B adds a sibling `canonical_path_hold_effect` dict to the envelope (and embeds it inside the frame so graph-state propagation flows it through). |
| Resolver envelope composer | [`ai_stack/player_action_resolution.py:505`](../../ai_stack/player_action_resolution.py) `_finalize_resolution_envelope()` | Composes `player_action_frame`, `affordance_resolution`, `scene_affordance_model`, `kanon_break`, `free_player_action_resolution`. | PR-B extends this composer to also derive and attach the hold-effect dict. |
| Canonical-path-effect derivation | [`ai_stack/player_action_resolution.py:327-341`](../../ai_stack/player_action_resolution.py) `_canonical_path_effect_from_policy()` | Returns `"hold_current_step"` when `action_commit_policy == commit_action` and `player_freedom_policy.canonical_path_control.default_for_free_player_action == "hold_current_step"`. | Reused unchanged. PR-B's contract derives from `free_player_action_resolution.v1` fields plus this literal. |
| Frame data class | [`ai_stack/action_resolution_contracts.py:131-196`](../../ai_stack/action_resolution_contracts.py) `PlayerActionFrameContract` (carries `canonical_path_effect` at `:156` / `:194`). | Carries the per-frame canonical-path-effect literal. | Reused unchanged. The new hold-effect dict is attached as a sibling key on the frame dict in `_finalize_resolution_envelope`. |
| LangGraph resolver node | [`ai_stack/langgraph/langgraph_runtime_executor.py:6260-6456`](../../ai_stack/langgraph/langgraph_runtime_executor.py) `_resolve_player_action()` (call at `:6280`). | Calls `resolve_player_action()`, lifts `player_action_frame`, `affordance_resolution`, `scene_affordance_model`, `kanon_break*`, and (when frame+aff+model present) builds `local_context_transition` + `narrator_consequence_plan`. | PR-B lifts the new envelope keys into graph state: `update["canonical_path_hold_effect"]` and (post-render) `update["narrator_consequence_realization"]`. The resolver node body adds the hold-effect lift only; the realization lift happens after `_render_visible` (see `_package_output`). |
| Canonical-path-control prompt block | [`ai_stack/langgraph/langgraph_runtime_executor.py:4697-4719`](../../ai_stack/langgraph/langgraph_runtime_executor.py) `player_action_resolution.canonical_path_control` (in `_build_director_realization_packet`). | Already advertises "Committed player movement, perception, waiting, and object interaction may update player local context but must not advance or rewrite the canonical_path". | Untouched. PR-B's new dict is a per-turn projection, not a packet field. |
| Narrator consequence plan builder | [`ai_stack/narrator_consequence_contracts.py:169-243`](../../ai_stack/narrator_consequence_contracts.py) `build_narrator_consequence_plan()` | Returns `consequence_text`, `consequence_type`, `source`, `requires_model_realization`, `inferred_target`, `local_context_updated`, `affordances_available`, `transition_type`. | Reused unchanged. PR-B's realization contract is a downstream projection. |
| Narrator-location-transition realization | [`ai_stack/langgraph/langgraph_runtime_executor.py:6591-6614`](../../ai_stack/langgraph/langgraph_runtime_executor.py) — `_director_compose_realization()` success branch for `CAPABILITY_NARRATOR_LOCATION_TRANSITION` builds `updated_player_local_context` from `narrator_consequence_plan`. | Already applies the consequence plan and updates `player_local_context`. | Reused unchanged. The realization contract observes the outcome; PR-B does not alter the composition. |
| Visible render | [`ai_stack/langgraph/langgraph_runtime_executor.py:10289-10384`](../../ai_stack/langgraph/langgraph_runtime_executor.py) `_render_visible()` → `run_visible_render()` at [`ai_stack/goc_turn_seams.py:777`](../../ai_stack/goc_turn_seams.py). | Produces `visible_output_bundle.scene_blocks` (block_type ∈ {narrator, actor_line, actor_action, environment_interaction, souffleuse, system_degraded_notice}). | Reused unchanged. PR-B inspects scene_blocks to set `visible_block_emitted` and `realized_block_id`. |
| Hold-effect read at commit (LDSS fallback) | [`world-engine/app/story_runtime/manager.py:8683-8687`](../../world-engine/app/story_runtime/manager.py) `_turn_holds_canonical_path_for_free_player_action()` (gate at `:8746`). | Returns `True` iff `player_action_frame.canonical_path_effect == "hold_current_step"`; suppresses pointer advance in `_build_ldss_scene_envelope`. | Untouched. PR-B's contract surfaces the *same* hold decision as a structured dict for diagnostics; the live behaviour already works (see `world-engine/tests/test_mvp3_ldss_integration.py:227-249`). |
| Thin-path summary builder | [`world-engine/app/story_runtime/manager.py:2897+`](../../world-engine/app/story_runtime/manager.py) `_build_langfuse_path_summary()` and [`:14164`](../../world-engine/app/story_runtime/manager.py) `get_thin_path_summary()` (endpoint at [`world-engine/app/api/http.py:1061-1075`](../../world-engine/app/api/http.py)). | Reads `event.observability_path_summary` and exposes Resolver → Director → Narrator evidence (realization_plan, used capability, kanon_break, block counts, validation status). | PR-B threads three new keys through the path-summary: `canonical_path_hold_effect`, `narrator_consequence_realization`, `visible_block_emitted`. No new endpoint family; no UI templates touched. |
| Diagnostic snapshot envelope stub | [`ai_stack/runtime_diagnostic_snapshot_contracts.py:80-99,167-172`](../../ai_stack/runtime_diagnostic_snapshot_contracts.py) `CanonicalPathHoldEffectPlaceholder`, `NarratorConsequenceRealizationPlaceholder`. | PR-0 stub: not imported by any production module (enforced by `tests/test_npc_interactivity_piv_baseline.py::test_runtime_diagnostic_snapshot_stub_is_not_imported_by_production_code`). | Untouched. PR-B delivers the *payload* the stub reserves; production code does **not** import the stub. |
| Player-freedom policy (content) | [`content/modules/god_of_carnage/knowledge/player_freedom_policy.yaml:12-22,47-69`](../../content/modules/god_of_carnage/knowledge/player_freedom_policy.yaml) | Declares `canonical_path_control.default_for_free_player_action: hold_current_step`, plus `semantic_resolution_requirements.if_catalog_silent.{allowed_canon_safety, require_canonical_risk, require_narrator_realization}`. | Untouched. PR-B reads the contract dict produced by PR-A; the YAML stays the source of truth. |

**Cross-cutting observation.** PR-B introduces **two new closed-enum projection modules** and **one envelope composer extension**. No graph node is added. No endpoint family is added. The resolver semantics, LDSS beat consumption gate, Director-Pause runtime, NPC agency, opening/narrator path, commit/readiness, prompt/story generation outside the narrator consequence path, and UI templates are unchanged.

## 3. Existing-path probe — what runs today for the action classes PR-B targets

This probe records the live behaviour observed at HEAD on 2026-05-19 against verified anchors **before** PR-B lands.

- **Mundane movement to a known room (e.g. `kitchen`).** The resolver hits [`ai_stack/player_action_resolution.py:710-743`](../../ai_stack/player_action_resolution.py): `_row_by_id` matches; `_status_policy_for_access` returns `("allowed", "commit_action")`; `_canonical_path_effect_from_policy` returns `"hold_current_step"` because `player_freedom_policy.canonical_path_control.default_for_free_player_action == "hold_current_step"`. The frame's `canonical_path_effect` literal is therefore `"hold_current_step"`. The manager's `_turn_holds_canonical_path_for_free_player_action()` at [`world-engine/app/story_runtime/manager.py:8683-8687`](../../world-engine/app/story_runtime/manager.py) returns `True`, and the LDSS-fallback gate at [`:8741-8750`](../../world-engine/app/story_runtime/manager.py) skips the pointer advance. **The live hold already works** (see `world-engine/tests/test_mvp3_ldss_integration.py:227-249`). What is missing today is a **structured contract dict** carrying *why* the hold fired, sourced from semantic fields rather than from a literal string match.
- **Plausible inferred mundane object (e.g. local detail not in catalog).** The resolver hits [`ai_stack/player_action_resolution.py:719-731`](../../ai_stack/player_action_resolution.py): `_resolve_query` returns `unknown_target`, then `_inferred_target_from_semantics` succeeds (because `player_freedom_policy.plausible_affordance_inference.enabled = true` and the semantic payload reports `canon_safety: content_silent_mundane`, `canonical_risk: low`). The status becomes `allowed`, the policy `commit_action`, and the `semantic_inference` dict carries the inference mode. `_canonical_path_effect_from_policy` returns `"hold_current_step"`. The narrator-consequence path at [`ai_stack/narrator_consequence_contracts.py:206-227`](../../ai_stack/narrator_consequence_contracts.py) sets `source="ai_semantic_plausible_inference"` and `requires_model_realization=True` because no authored detail exists for the inferred target.
- **Authored mundane perception (e.g. `window`).** The resolver matches the catalog row; the consequence plan at [`ai_stack/narrator_consequence_contracts.py:211-220`](../../ai_stack/narrator_consequence_contracts.py) sources `consequence_text` from `obj.perception_detail[lang]` and sets `source="scene_affordance_detail"`, `requires_model_realization=False`. A visible narrator block is produced by `run_visible_render()` ([`ai_stack/goc_turn_seams.py:777`](../../ai_stack/goc_turn_seams.py)) and gets folded into `player_input_outcome` at [`world-engine/app/story_runtime/manager.py:7752-7820`](../../world-engine/app/story_runtime/manager.py) (the thin-path narrator fold).
- **Unknown / impossible target.** The resolver returns `affordance_status=unknown_target`, `action_commit_policy=needs_clarification`, `canonical_path_effect=None`. The manager's hold gate returns `False`, the LDSS pointer can advance normally if a model realization is approved. PR-B must **not** create a successful hold-effect dict for this case.
- **Criminal / impossible morality.** The resolver fails the inference gate (semantic payload reports `canon_safety: weapons_or_threat_objects` / `hidden_or_load_bearing_fact`, `canonical_risk: high`). The branch lands on `unknown_target` / `needs_clarification`. PR-B must **not** create a successful hold-effect dict for this case.
- **Meta input / `/help`.** Short-circuit at [`ai_stack/player_action_resolution.py:569-599`](../../ai_stack/player_action_resolution.py). The frame's `canonical_path_effect` is `None`; no hold dict; no narrator realization contract (or one with explicit `non_realization_reason="meta_input_control_path"`).

**Gap closed by PR-B.** PR-A delivered the resolver contract but did **not** propagate a structured hold-effect dict, did **not** project the narrator-consequence outcome into a `narrator_consequence_realization.v1` shape, and did **not** expose the diagnostic surface needed by the operator / Langfuse path. PR-B fills these three gaps.

## 4. Live-smoke feasibility probe

| Evidence channel | Today | After PR-B |
|---|---|---|
| Hold behaviour in live LDSS path | Works via the literal `frame.canonical_path_effect == "hold_current_step"` ([`world-engine/app/story_runtime/manager.py:8683`](../../world-engine/app/story_runtime/manager.py)); proved by `world-engine/tests/test_mvp3_ldss_integration.py:227-249`. | Unchanged. PR-B adds the structured dict next to the existing literal so observability surfaces can read *why* the hold fired (`source`, `canon_safety`, `canonical_risk`, `affordance_status`, `until_condition`). |
| Narrator block emission for mundane authored consequence | Works via `_render_visible` ([`ai_stack/langgraph/langgraph_runtime_executor.py:10289-10381`](../../ai_stack/langgraph/langgraph_runtime_executor.py)) and the thin-path fold ([`world-engine/app/story_runtime/manager.py:7752-7820`](../../world-engine/app/story_runtime/manager.py)). | Unchanged. PR-B's contract observes the bundle and sets `visible_block_emitted=True`, `block_type="narrator"`, `realized_block_id=<scene_block entry id>`. |
| Narrator block emission for `requires_model_realization=True` plausible inference | The realization is composed by `_director_compose_realization` at [`ai_stack/langgraph/langgraph_runtime_executor.py:6458+`](../../ai_stack/langgraph/langgraph_runtime_executor.py) and the visible bundle is produced; today this path may either emit a narrator block (visible) or — under degraded/diagnostic conditions — emit nothing. The current code does **not** carry an explicit *non-realization reason* up to the operator surface when no block is produced; the operator only sees the absence. | PR-B's realization contract carries either `visible_block_emitted=true` (with `realized_block_id` non-null) *or* `non_realization_reason` explicitly populated. The thin-path summary exposes both. |
| Langfuse spans for the new contracts | Available via the existing path-summary surface (ADR-0062); the resolver / director / narrator nodes are already traced. | The new dicts ride in `event.observability_path_summary`. No new span family is needed. |
| Operator endpoint | `GET /api/story/sessions/{session_id}/thin-path-summary` at [`world-engine/app/api/http.py:1061-1075`](../../world-engine/app/api/http.py), backed by `get_thin_path_summary` at [`world-engine/app/story_runtime/manager.py:14164`](../../world-engine/app/story_runtime/manager.py). | The two new keys appear in each row when the data is present. No new endpoint family is added. |
| Headless tests | PR-A delivered `ai_stack/tests/test_free_player_action_resolution_contract.py`. | PR-B adds new test modules for hold + realization contracts and a graph-state propagation test under `tests/`. |

**Feasibility verdict.** PR-B rides on existing surfaces; the new contracts are read-only projections plus three thin-path-summary key additions. No new endpoint family. No UI page changes. The hold behaviour already works at the literal level; PR-B only formalizes it as a structured dict.

## 5. Anti-dead-end checkpoints

Each checkpoint names a failure mode that PR-B must expose as observable evidence, not silent degradation. Tests enforce each checkpoint.

1. **Hold-effect dict on an unsafe action.** Forbidden. When `free_player_action_resolution.action_commit_policy != "commit_action"` or `affordance_status != "allowed"` or `canonical_risk == "high"`, `build_canonical_path_hold_effect()` returns `None`. Asserted in `test_hold_effect_not_emitted_for_unknown_target`, `test_hold_effect_not_emitted_for_criminal_action`, `test_hold_effect_not_emitted_for_needs_clarification`.
2. **Hold-effect dict ignoring contract fields.** Forbidden. The builder reads from `free_player_action_resolution.v1` fields, never from `raw_text` or `player_input`. Asserted in `test_hold_effect_derives_from_contract_fields_not_input_strings`.
3. **Hold-effect propagation gap.** Forbidden. Graph state must carry the hold-effect dict at `graph_state["canonical_path_hold_effect"]` (a top-level key) whenever the contract emits one, **and** the existing `frame.canonical_path_effect == "hold_current_step"` literal stays true so `_turn_holds_canonical_path_for_free_player_action(graph_state)` still returns `True`. Asserted in `test_graph_state_carries_hold_effect_for_mundane_free_action` and `test_turn_holds_canonical_path_for_free_player_action_returns_true`.
4. **Canonical pointer drift on mundane free action.** Forbidden. The LDSS fallback gate at [`world-engine/app/story_runtime/manager.py:8741-8750`](../../world-engine/app/story_runtime/manager.py) already suppresses pointer advance when the hold fires. Asserted (regression) by `world-engine/tests/test_mvp3_ldss_integration.py::test_ldss_fallback_holds_canonical_step_for_free_player_action`, which PR-B must keep green.
5. **`requires_model_realization=True` with neither block nor non-realization reason.** Forbidden. When the consequence plan asks for model realization, the contract must carry **either** `visible_block_emitted=true` with a non-null `realized_block_id` **or** an explicit `non_realization_reason` string. Asserted in `test_realization_emits_visible_block_or_non_realization_reason`.
6. **Realization block introduces new people / rooms / plot facts.** Forbidden by the contract's `safety` triple (`no_new_people`, `no_new_rooms`, `no_plot_facts`). The triple is **always** `True` for blocks produced from the narrator-consequence path because (a) the policy's `forbidden_scope` at [`content/modules/god_of_carnage/knowledge/player_freedom_policy.yaml:33-41`](../../content/modules/god_of_carnage/knowledge/player_freedom_policy.yaml) declares `new_people_or_animals`, `new_exits_or_rooms`, `decisive_plot_information` forbidden, and (b) the resolver already fails-closed on those (`canonical_risk=high`, `needs_clarification`). The contract surfaces this guarantee as a positive assertion. Asserted in `test_realization_safety_triple_is_true_for_mundane_realization`.
7. **Actor-line-only validator rejecting narrator-only realization.** Forbidden. The contract's `block_type` is `narrator` or `environment_interaction`; the `safety.no_plot_facts=True` plus the absence of `actor_line` / `actor_action` blocks means actor-lane validators must not gate the turn. Asserted by `test_actor_lane_validation_does_not_reject_narrator_only_realization` (smoke test using existing `actor_lane_validation` logic).
8. **Hardcoded text snippets.** Forbidden. The new modules contain **no** narrative prose, **no** locale literals, **no** verb / room / actor whitelists. Asserted by `test_pr_b_modules_have_no_hardcoded_locale_or_verb_whitelists` and the existing `tests/gates/test_table_b_anti_hardcoding_gate.py`.
9. **Active Pi / Π runtime keys.** Forbidden. Asserted by `tests/gates/test_adr_0039_pi_scope.py`, `tests/gates/test_adr0039_pi_scope.py`, and a sibling regex check inside the PR-B test files.
10. **Premature Director Pause / NPC Pulse / pointer repair / `step.mode` switch.** Forbidden. PR-B must not introduce `compute_gathering_state`, `gathering_paused`, `presence_breaks_gathering` as `def` / `class` symbols, must not change canonical-step pointer semantics, must not add a `step.mode` enum, must not add a NPC tick. Asserted by `test_pr_b_does_not_implement_pr_c_or_phase_2_symbols`.

## 6. Plan-file reference reconciliation (verified)

The roadmap and PR-A PIV cite several `file:line` anchors. PR-B re-verified the following on 2026-05-19 prior to writing code. Discrepancies are recorded; the verified column wins.

| Source | Cited anchor | Verified anchor (2026-05-19) | Status |
|---|---|---|---|
| PR-A §2 | `ai_stack/player_action_resolution.py:502` `resolve_player_action()` def | `def resolve_player_action(` lands at [`:548`](../../ai_stack/player_action_resolution.py) on the modified branch (PR-A added helper imports and `_finalize_resolution_envelope` between `:29` and `:546`). The PR-A PIV anchor is correct for **pre-PR-A** HEAD; on the **post-PR-A** branch the def line shifted to `:548`. **PR-B uses `:548`.** | Shifted by PR-A; recorded. |
| PR-A §2 | `ai_stack/player_action_resolution.py:430` `_semantic_payload()` | Now at [`:433`](../../ai_stack/player_action_resolution.py). | Shifted by PR-A; recorded. |
| PR-A §2 | `ai_stack/player_action_resolution.py:276` `_inferred_target_from_semantics()` | Now at [`:279`](../../ai_stack/player_action_resolution.py). | Shifted by PR-A; recorded. |
| PR-A §2 | `ai_stack/player_action_resolution.py:324` `_canonical_path_effect_from_policy()` | Now at [`:327`](../../ai_stack/player_action_resolution.py). | Shifted by PR-A; recorded. |
| PR-A §2 | `ai_stack/action_resolution_contracts.py:131` `PlayerActionFrameContract` (carries `canonical_path_effect` at the dataclass level). | Verified — class at [`:131`](../../ai_stack/action_resolution_contracts.py), field at [`:156`](../../ai_stack/action_resolution_contracts.py), `to_dict()` projection at [`:194`](../../ai_stack/action_resolution_contracts.py). | Matches. |
| PR-A §2 | `ai_stack/langgraph/langgraph_runtime_executor.py:6260` `_resolve_player_action`, call at `:6280` | Matches at HEAD. | Matches. |
| PR-A §2 | `ai_stack/langgraph/langgraph_runtime_executor.py:4703` `canonical_path_control` block | Matches at HEAD (block at [`:4697-4719`](../../ai_stack/langgraph/langgraph_runtime_executor.py)). | Matches. |
| PR-A §2 | `world-engine/app/story_runtime/manager.py:8683-8687` `_turn_holds_canonical_path_for_free_player_action` | Matches. Gate at [`:8746`](../../world-engine/app/story_runtime/manager.py). | Matches. |
| PR-A §2 | `world-engine/app/api/http.py:1061-1075` thin-path-summary endpoint | Matches. | Matches. |
| PR-A §2 | `world-engine/app/story_runtime/manager.py:14164` `get_thin_path_summary` | Matches. | Matches. |
| PR-A §2 | `world-engine/app/story_runtime/manager.py:2897` `_build_langfuse_path_summary` def | Matches. | Matches. |
| PR-0 §2 | `ai_stack/runtime_diagnostic_snapshot_contracts.py:80-99` PR-B placeholders | Verified — `CanonicalPathHoldEffectPlaceholder` at [`:81-88`](../../ai_stack/runtime_diagnostic_snapshot_contracts.py); `NarratorConsequenceRealizationPlaceholder` at [`:92-99`](../../ai_stack/runtime_diagnostic_snapshot_contracts.py); enumeration at [`:170-171`](../../ai_stack/runtime_diagnostic_snapshot_contracts.py). | Matches. |
| Newly verified for PR-B | `ai_stack/narrator_consequence_contracts.py:169-243` `build_narrator_consequence_plan()` (sets `requires_model_realization` at `:232`). | Verified. | Matches. |
| Newly verified for PR-B | `ai_stack/langgraph/langgraph_runtime_executor.py:6591-6614` post-success `narrator_consequence_plan` application for `CAPABILITY_NARRATOR_LOCATION_TRANSITION` | Verified. | Matches. |
| Newly verified for PR-B | `ai_stack/langgraph/langgraph_runtime_executor.py:10289-10381` `_render_visible()` producing `visible_output_bundle.scene_blocks`. | Verified. | Matches. |
| Newly verified for PR-B | `world-engine/app/story_runtime/manager.py:7752-7820` thin-path narrator fold | Verified. | Matches. |
| PR-A test surface | `ai_stack/tests/test_free_player_action_resolution_contract.py` | Verified — 30 tests, all assertions on contract field names and closed enums. PR-B adds sibling test files. | Matches. |
| Pre-existing failure surface | `tests/test_capability_matrix_documentation_readiness.py::test_capability_matrix_doc_links_resolve` (stale Markdown link) | Verified at HEAD — pre-existing, **not** caused by PR-B. Recorded in §10. | Pre-existing; out of scope for PR-B. |
| Pre-existing failure surface | `ai_stack/tests/test_action_resolution_interact_fallback.py::test_semantic_resolution_required_uses_full_dramatic_pipeline_not_short_path` line `:46` asserts `selected_scene_function`; today the value is `None` for the `semantic_resolution_required` short-circuit branch. | Verified at HEAD — pre-existing failure, **not** caused by PR-B. Recorded in §10. | Pre-existing; out of scope for PR-B. |

## 7. What existing paths PR-B reuses (does not own)

PR-B's discipline is **reuse, do not rebuild**.

- **Resolver contract** at [`ai_stack/free_player_action_resolution_contracts.py`](../../ai_stack/free_player_action_resolution_contracts.py) (PR-A delivery) — the per-turn dict the hold builder consumes.
- **Player-freedom policy** at [`content/modules/god_of_carnage/knowledge/player_freedom_policy.yaml:12-22`](../../content/modules/god_of_carnage/knowledge/player_freedom_policy.yaml) (`canonical_path_control.default_for_free_player_action`).
- **Canonical-path-effect derivation** at [`ai_stack/player_action_resolution.py:327-341`](../../ai_stack/player_action_resolution.py) `_canonical_path_effect_from_policy()` — unchanged.
- **Manager hold-gate** at [`world-engine/app/story_runtime/manager.py:8683-8687`](../../world-engine/app/story_runtime/manager.py) — unchanged.
- **Narrator consequence plan builder** at [`ai_stack/narrator_consequence_contracts.py:169-243`](../../ai_stack/narrator_consequence_contracts.py) — unchanged.
- **Visible render** at [`ai_stack/langgraph/langgraph_runtime_executor.py:10289-10381`](../../ai_stack/langgraph/langgraph_runtime_executor.py) `_render_visible()` and [`ai_stack/goc_turn_seams.py:777+`](../../ai_stack/goc_turn_seams.py) `run_visible_render()` — unchanged.
- **Thin-path summary builder** at [`world-engine/app/story_runtime/manager.py:2897+`](../../world-engine/app/story_runtime/manager.py) `_build_langfuse_path_summary()` — extended with three additional keys, no semantic change.
- **Thin-path summary endpoint** at [`world-engine/app/api/http.py:1061-1075`](../../world-engine/app/api/http.py) — unchanged in signature; the returned row dicts get three additional fields when present.

## 8. What PR-B must not touch

Hard constraints. PR-B's diff stays inside this guardrail; tests enforce the negatives.

- **`ai_stack/free_player_action_resolution_contracts.py`** — owned by PR-A; PR-B reads its dict, never re-defines the schema or enums.
- **`ai_stack/canonical_path_resolver.py`** — canonical-path bundle loader; unchanged.
- **`ai_stack/director/scene_director_goc.py`** — owned by PR-C (Director composition, `compute_gathering_state`, `presence_breaks_gathering`); PR-B leaves this file untouched.
- **`ai_stack/live_dramatic_scene_simulator.py`** — LDSS and mandatory-beat consumption stay unchanged.
- **`ai_stack/runtime_aspect_ledger.py`** — `ASPECT_KEYS` unchanged; no Director-Pause / Pulse aspect row added.
- **`ai_stack/goc_narrator_path.py`** — Turn 0 narrator path unchanged.
- **`ai_stack/goc_souffleuse.py`** — Souffleuse path unchanged.
- **`ai_stack/runtime_diagnostic_snapshot_contracts.py`** — PR-0 stub stays uncoupled from production; PR-B does **not** import it from `ai_stack/player_action_resolution.py`, `world-engine/app/story_runtime/manager.py`, or any other production module (enforced by `tests/test_npc_interactivity_piv_baseline.py::test_runtime_diagnostic_snapshot_stub_is_not_imported_by_production_code`).
- **`world-engine/app/story_runtime/manager.py`** — `_turn_holds_canonical_path_for_free_player_action`, `_build_ldss_scene_envelope` pointer advance, commit/readiness, `_finalize_committed_turn` continuity, all unchanged. PR-B's only edit on this file is the additive thin-path-summary projection (three extra keys read from graph state).
- **`world-engine/app/web/templates/ui/**`** — no UI page change.
- **`world-engine/app/api/**`** — no new endpoint family; signature of `/thin-path-summary` is unchanged.
- **`frontend/static/**`** — no block-streaming, no cut-in, no UI change.
- **`content/modules/**`** — no content edit; the policy YAML stays the source of truth.
- **PR-B must not introduce** any of the symbols `compute_gathering_state`, `gathering_paused`, `presence_breaks_gathering` **as a `def` or `class`** anywhere in scope. They appear only as contract field names (dict keys), constants, or test asserts.
- **PR-B must not introduce** `step.mode` switching, pointer repair, NPC pulse, Block-Stream-Bus, Cut-In handling, or Player-Hold logic.
- **PR-B must not introduce** verb / room / actor / locale literal whitelists in any scanned production file (`tests/gates/test_table_b_anti_hardcoding_gate.py`).
- **PR-B must not introduce** active Pi / Π runtime keys (`tests/gates/test_adr_0039_pi_scope.py`).

## 9. Files PR-B adds / modifies

| Path | Action | Reason |
|---|---|---|
| `ai_stack/canonical_path_hold_effect_contracts.py` | **add** | Closed-enum constants + builder for `canonical_path_hold_effect.v1`. Reads `free_player_action_resolution.v1` fields; never reads raw input strings. |
| `ai_stack/narrator_consequence_realization_contracts.py` | **add** | Closed-enum constants + builder for `narrator_consequence_realization.v1`. Projects the existing `narrator_consequence_plan` and the rendered `visible_output_bundle.scene_blocks` into the closed shape, with explicit `non_realization_reason` when no block is emitted. |
| `ai_stack/player_action_resolution.py` | **modify** | Extend `_finalize_resolution_envelope` to derive and attach `canonical_path_hold_effect` at the envelope root and inside the frame. No other behaviour change. |
| `ai_stack/langgraph/langgraph_runtime_executor.py` | **modify** | In `_resolve_player_action`, lift `canonical_path_hold_effect` from the resolver envelope into `update["canonical_path_hold_effect"]`. In `_package_output` (or a dedicated post-render step), build `narrator_consequence_realization` from `narrator_consequence_plan` + `visible_output_bundle.scene_blocks` and set `update["narrator_consequence_realization"]`. |
| `world-engine/app/story_runtime/manager.py` | **modify** | Extend `_build_langfuse_path_summary` to read `canonical_path_hold_effect`, `narrator_consequence_realization`, and `visible_block_emitted` from graph state and place them on the per-event summary. Extend `get_thin_path_summary` rows with the three keys. No semantic change to existing fields. |
| `ai_stack/tests/test_pr_b_canonical_path_hold_effect_contract.py` | **add** | Closed-enum + structural contract tests for `canonical_path_hold_effect.v1` (eligible mundane → hold dict; unknown/criminal/high-risk → `None`; derived from contract fields). |
| `ai_stack/tests/test_pr_b_narrator_consequence_realization_contract.py` | **add** | Closed-enum + structural contract tests for `narrator_consequence_realization.v1` (`requires_model_realization=true` → either `visible_block_emitted=true` or `non_realization_reason`; safety triple; no plot facts / new people / new rooms). |
| `tests/test_pr_b_live_effect_propagation.py` | **add** | Graph-state propagation tests: `_turn_holds_canonical_path_for_free_player_action(graph_state)` is True for mundane free actions; the canonical pointer (manager fallback) does not advance; the thin-path-summary surface exposes the two new dicts; no Director-Pause / Pulse / pointer-repair / Pi runtime keys. |
| `docs/implementation_logs/pr_b_live_effect_propagation_piv.md` | **add (this file)** | PIV artifact. |
| `docs/MVPs/npc_interactivity_piv_log.md` | **modify** | PR-B row transitions from "Not started" to "Draft" with a link to this PIV. |

No other file is modified.

## 10. Pre-existing baseline observations (out of PR-B scope)

The following failures exist at HEAD on 2026-05-19 **before** PR-B and are explicitly **not** caused by PR-B:

```
tests/test_capability_matrix_documentation_readiness.py::test_capability_matrix_doc_links_resolve
```

Reason: stale Markdown link to a relocated character-voice YAML (documented since PR-0).

```
ai_stack/tests/test_action_resolution_interact_fallback.py::test_semantic_resolution_required_uses_full_dramatic_pipeline_not_short_path
```

Reason: assertion `result.get("selected_scene_function")` is `None` for the `semantic_resolution_required` short-circuit branch (the resolver returns before the scene-function selection node). This is a pre-existing observability gap separate from PR-B's live-effect propagation scope.

PR-B re-runs these tests after the change and reports whether either remains failing for an unrelated reason. PR-B does **not** fix them.

## 11. Acceptance evidence for PR-B itself

PR-B must satisfy, against repository HEAD after the commit:

1. `docs/implementation_logs/pr_b_live_effect_propagation_piv.md` (this file) exists with every required section.
2. `docs/MVPs/npc_interactivity_piv_log.md` lists PR-B with `Status: Draft` and a link to this PIV.
3. `ai_stack/canonical_path_hold_effect_contracts.py` exists, exports closed-enum constants, and defines a builder that takes the `free_player_action_resolution.v1` dict (plus optional current canonical step id) and returns the hold-effect dict or `None`.
4. `ai_stack/narrator_consequence_realization_contracts.py` exists, exports closed-enum constants, and defines a builder that takes the `narrator_consequence_plan` and the rendered `visible_output_bundle.scene_blocks` and returns the realization dict (always — with `non_realization_reason` populated when no block is emitted).
5. `ai_stack/player_action_resolution.py` `_finalize_resolution_envelope` emits the hold-effect dict on every return path where the resolver classified a successful mundane / free action commit; emits `None` otherwise. PR-A's tests still pass.
6. `ai_stack/langgraph/langgraph_runtime_executor.py` lifts the hold-effect dict into `graph_state["canonical_path_hold_effect"]` from the resolver envelope, and lifts the realization dict into `graph_state["narrator_consequence_realization"]` after `_render_visible`.
7. `world-engine/app/story_runtime/manager.py` thin-path-summary builder includes the three new keys when present, and `get_thin_path_summary` exposes them on each row.
8. The new test modules are green; the PR-A test module (`ai_stack/tests/test_free_player_action_resolution_contract.py`), `tests/test_npc_interactivity_piv_baseline.py`, `tests/gates/test_adr_0039_pi_scope.py`, `tests/gates/test_adr0039_pi_scope.py`, and `tests/gates/test_table_b_anti_hardcoding_gate.py` remain green.
9. `world-engine/tests/test_mvp3_ldss_integration.py::test_ldss_fallback_holds_canonical_step_for_free_player_action` and `::test_ldss_fallback_advances_canonical_step_without_free_action_hold` remain green (live hold behaviour unaffected).
10. Pre-existing failures recorded in §10 remain in their pre-PR-B state and are explicitly reported as separate in the PR final report.

## 12. Footer

- Verification date: 2026-05-19
- Repository SHA at verification time: HEAD prior to this commit (PR-A draft)
- Author handoff: PR-C (Director Pause mode, `director_gathering_state.v1`, `compute_gathering_state`) may begin once this PIV is merged. PR-C consumes `canonical_path_hold_effect.v1` plus the resolver's `presence_breaks_gathering_evidence` triple (delivered by PR-A) to derive the final `presence_breaks_gathering` decision.
