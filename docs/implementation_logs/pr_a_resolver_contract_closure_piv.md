# PR-A — Resolver Contract Closure (PIV Artifact)

**PR title:** PR-A — Resolver Contract Closure (`free_player_action_resolution.v1`)
**Status:** Draft (this commit)
**Date:** 2026-05-19
**Roadmap section:** Phase 1 §3.0 / §3.4 / §3.6 of [`NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md`](../../NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md); sub-phase **1.d.0** (Resolver-Vertrag schließen).
**Roadmap index entry:** [`docs/MVPs/npc_interactivity_piv_log.md`](../MVPs/npc_interactivity_piv_log.md)
**Supersedes / extends:** [PR-0 PIV](pr_0_npc_interactivity_contracts_piv.md)
**Governance:** [ADR-0057 Phase-1 amendment](../ADR/adr-0057-canon-safe-player-freedom-and-affordance-inference.md), [ADR-0039](../ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md), [ADR-0062](../ADR/adr-0062-director-realization-thin-path.md).

**Reviewer rule (binding):** Every `file:line` reference in this artifact was verified against repository HEAD on 2026-05-19 prior to writing code. False or invented `file:line` references are reject-worthy. Where a PR-0 anchor has shifted, the discrepancy is recorded in §6 explicitly.

---

## 1. Scope (one paragraph)

PR-A closes the resolver contract surface named in ADR-0057's Phase-1 amendment as `free_player_action_resolution.v1`. It guarantees that every player turn classified as a free action (movement, perception, object interaction, actor-directed input, unknown / impossible) produces a structured, per-turn contract dict carrying `resolved_target_type`, `resolved_target_id`, `target_location`, `presence_breaks_gathering` (preliminary, Director-final), `affordance_status`, `canon_safety`, `canonical_risk`, `action_commit_policy`, and `classification_reason` when a field is `null`. The implementation rides on the existing `resolve_player_action` semantic path (verified at [`ai_stack/player_action_resolution.py:502`](../../ai_stack/player_action_resolution.py)) and **does not** introduce verb / room / actor whitelists, locale literals, `step.mode` switching, pointer repair, Director-Pause runtime, NPC pulse, or player-block logic. PR-A delivers the resolver evidence that PR-B (live-effect propagation) and PR-C (`compute_gathering_state`) need to compose against; PR-A neither implements PR-B/PR-C symbols nor mutates any of the surfaces those PRs own.

## 2. Consumer scan — what consumes the resolver output today

| Surface today | File:line (verified 2026-05-19) | What it does today | What PR-A changes |
|---|---|---|---|
| `resolve_player_action()` entry | [`ai_stack/player_action_resolution.py:502`](../../ai_stack/player_action_resolution.py) | Builds `PlayerActionFrameContract` + `AffordanceResolutionContract`; returns frame, affordance, scene model, `kanon_break`, `kanon_break_reason`. | PR-A adds a `free_player_action_resolution` dict to the returned envelope **and** embeds the same payload inside `player_action_frame` so existing graph-state propagation flows it through without further node changes. |
| Resolver semantic payload selection | [`ai_stack/player_action_resolution.py:430`](../../ai_stack/player_action_resolution.py) `_semantic_payload()` | Resolves `semantic_action` / `semantic_resolution` / `ai_semantic_resolution` from interpreted input. | Reused unchanged. PR-A pulls `canon_safety` / `canonical_risk` / `inference_mode` / participation-evidence fields from the same payload. |
| Resolver inferred-target path | [`ai_stack/player_action_resolution.py:276`](../../ai_stack/player_action_resolution.py) `_inferred_target_from_semantics()` | Builds an inferred `(target_id, target_type, status, policy, semantic_inference)` for mundane gaps, honoring `player_freedom_policy.yaml`. | Reused unchanged. The inferred branch's `semantic_inference["canon_safety"]` / `canonical_risk` fields feed the new contract. |
| Canonical-path-effect derivation | [`ai_stack/player_action_resolution.py:324`](../../ai_stack/player_action_resolution.py) `_canonical_path_effect_from_policy()` | Derives `canonical_path_effect: hold_current_step` from `player_freedom_policy.canonical_path_control`. | Reused unchanged. The contract carries this through, but PR-A does **not** alter the propagation surface (PR-B owns `canonical_path_hold_effect.v1`). |
| Affordance contract data class | [`ai_stack/action_resolution_contracts.py:79`](../../ai_stack/action_resolution_contracts.py) `AffordanceResolutionContract` | Holds `status`, `action_commit_policy`, `reason`, `resolved_target`, `target_resolution_source`, `access_status`. | Reused unchanged. The PR-A contract is a projection over `frame` + `affordance` fields, not a mutation of the data class. |
| Player action frame data class | [`ai_stack/action_resolution_contracts.py:131`](../../ai_stack/action_resolution_contracts.py) `PlayerActionFrameContract` | Carries the resolved frame; `to_dict()` exposes `resolved_target_id`, `resolved_target_type`, `affordance_status`, `canonical_path_effect`. | Reused unchanged. PR-A enriches the returned dict (after `to_dict()`) with the new contract payload key; the dataclass itself is not modified. |
| LangGraph resolver node | [`ai_stack/langgraph/langgraph_runtime_executor.py:6260`](../../ai_stack/langgraph/langgraph_runtime_executor.py) `_resolve_player_action` (call site `:6280`) | Calls `resolve_player_action()`, lifts `player_action_frame` / `affordance_resolution` / `scene_affordance_model` / `kanon_break` into graph state, builds local-context transition + narrator consequence plan. | Reused unchanged. The new contract rides inside `frame["free_player_action_resolution"]`; no executor change is required for graph propagation. PR-B / PR-C may add a dedicated graph key later. |
| Canonical-path-control graph block | [`ai_stack/langgraph/langgraph_runtime_executor.py:4703`](../../ai_stack/langgraph/langgraph_runtime_executor.py) | Constructs `canonical_path_control` projection from policy. | Untouched. PR-B owns the `canonical_path_hold_effect.v1` extension. |
| Hold-effect read at commit | [`world-engine/app/story_runtime/manager.py:8683-8687`](../../world-engine/app/story_runtime/manager.py) `_turn_holds_canonical_path_for_free_player_action()` | Returns `True` iff `player_action_frame.canonical_path_effect == "hold_current_step"`. | Untouched. PR-A relies on the existing literal flowing through unchanged. |
| Thin-path operator endpoint | [`world-engine/app/api/http.py:1061-1075`](../../world-engine/app/api/http.py) and [`world-engine/app/story_runtime/manager.py:14164`](../../world-engine/app/story_runtime/manager.py) `get_thin_path_summary()` | Per-turn Resolver → Director → Narrator evidence; reads from `event.observability_path_summary`. | Untouched in PR-A. The new contract is available in graph state inside `player_action_frame["free_player_action_resolution"]`; a follow-up commit (this PR or PR-B) may surface it in the thin-path row without changing the endpoint contract. PR-A's acceptance does not depend on the endpoint change. |
| Diagnostic snapshot envelope stub | [`ai_stack/runtime_diagnostic_snapshot_contracts.py:57-67`](../../ai_stack/runtime_diagnostic_snapshot_contracts.py) `ResolverOutputPlaceholder` (contract_name `"free_player_action_resolution.v1"` at `:65`); enumeration in `REQUIRED_CONTRACT_PLACEHOLDER_NAMES` at `:167-172`. | PR-0 stub: not imported by any production module (enforced by `tests/test_npc_interactivity_piv_baseline.py::test_runtime_diagnostic_snapshot_stub_is_not_imported_by_production_code`). | Untouched. PR-A delivers the **payload** for the placeholder; the stub stays uncoupled from production until a future composer needs it. |
| Named-characters predicate (content) | [`content/modules/god_of_carnage/canonical_path/005_statement_reading.yaml:36`](../../content/modules/god_of_carnage/canonical_path/005_statement_reading.yaml) `named_characters: [veronique, michel, annette, alain]` | Declares co-presence required for the step. | Untouched. The Director consumes this in PR-C; PR-A only carries `target_location` so the Director can later compose `presence_breaks_gathering` for real. |
| Player-freedom policy (content) | [`content/modules/god_of_carnage/knowledge/player_freedom_policy.yaml:1-69`](../../content/modules/god_of_carnage/knowledge/player_freedom_policy.yaml) | Declares `canonical_path_control`, `plausible_affordance_inference`, `semantic_resolution_requirements`. | Untouched. The contract reads `canon_safety` / `canonical_risk` from the AI semantic payload, which is in turn gated by this policy through `_semantic_allows_plausible_inference` at [`ai_stack/player_action_resolution.py:236`](../../ai_stack/player_action_resolution.py). |
| Module-level player-freedom switch | [`ai_stack/module_runtime_policy.py:410-416`](../../ai_stack/module_runtime_policy.py) | Projects `runtime_intelligence.player_freedom.{enabled, policy_ref, canonical_path_control, plausible_affordance_inference}` into the runtime governance policy. | Untouched. |

**Cross-cutting observation.** The contract is a **per-turn projection** over the existing `player_action_frame` + `affordance_resolution` + `semantic_inference` data. PR-A introduces:

- one new module: `ai_stack/free_player_action_resolution_contracts.py` (closed enum constants + builder).
- targeted edits in `ai_stack/player_action_resolution.py` to call the builder and emit the contract on **every** return path (meta-control, semantic-resolution-required, speech-only, main inference path).

No graph node is added. No new endpoint family is introduced. No runtime aspect ledger row is added.

## 3. Existing-path probe — what runs today for the action classes PR-A targets

This probe records the runtime behavior observed against verified anchors **before** PR-A lands. It complements PR-0 §3.

- **Movement input ("Gehe in die Küche", paraphrased).** Today: `resolve_player_action()` calls `_row_by_id(affordance_model, "kitchen", "location")` (line range [`:362-383`](../../ai_stack/player_action_resolution.py)) and resolves to `affordance_status="allowed"`, `action_commit_policy="commit_action"`, `target_resolution_source="ai_semantic_resolution.content_id"`. The frame exposes `resolved_target_id` / `resolved_target_type` (per [`action_resolution_contracts.py:131`](../../ai_stack/action_resolution_contracts.py)). It does **not** expose `target_location` or `canon_safety` / `canonical_risk` at the top level of the contract, and there is no `classification_reason` when a null target is returned. PR-A closes this surface.
- **Object interaction ("Öffne den Fahrstuhl", paraphrased).** Today: same code path; the elevator row resolves to `affordance_status="prevented"` (via `_access` and `_status_policy_for_access` at [`:163-181`](../../ai_stack/player_action_resolution.py)). PR-A re-projects this into the contract's tighter `affordance_status ∈ {allowed, unknown_target}` enum (closed per ADR-0057 amendment); `commit_policy="no_commit"` cases project to `affordance_status="allowed"` with the canonical block still rejecting the action via the existing `_status_policy_for_access` semantics. The contract never invents a new enum value.
- **Unknown / impossible target ("Gehe nach Mordor", paraphrased).** Today: `_resolve_query` returns `("unknown_target", "needs_clarification", None, None, "semantic_catalog_no_match", None)` ([`:386-408`](../../ai_stack/player_action_resolution.py)). PR-A enriches this with `classification_reason="semantic_catalog_no_match"` (mirroring the existing `target_resolution_source`) and `canonical_risk="medium"` (fail-closed default — no silent low-risk fallback when the resolver could not bind a target safely).
- **Criminal / impossible morality ("Ich ziehe ein Messer" / "Ich entwickle Superkräfte", paraphrased).** Today: `_inferred_target_from_semantics` rejects the inference because the `semantic_inference.canonical_risk != "low"` or `canon_safety` is outside the allowed set per `player_freedom_policy.yaml:62-65`. The fallback is `unknown_target` / `needs_clarification`. PR-A projects the same outcome into the contract: `affordance_status="unknown_target"`, `action_commit_policy="needs_clarification"`, `canonical_risk="medium" | "high"`, with `classification_reason` populated from the semantic payload's `reason` / `reasoning_summary` (when present) or `target_resolution_source` (when absent).
- **Actor-directed input.** Today: the actor branch of `_resolve_query` and `_row_by_id` resolves `resolved_target_type="actor"` from `affordance_model.actors`. PR-A surfaces it as the contract's `resolved_target_type="actor"` and leaves `target_location=null` (actor targeting is not a location movement).
- **Meta / non-story control input.** Today: short-circuited at [`:523-554`](../../ai_stack/player_action_resolution.py); the contract still emits with `resolved_target_type="none"`, `action_commit_policy="needs_clarification"` (because no commit semantic is meaningful for meta), and `classification_reason="meta_input_control_path"`. The resolver's existing meta-control evidence path is unchanged.

**Gap closed by PR-A vs. PR-0 §3 observations:** PR-0 recorded that paraphrased movement inputs did not reliably produce `resolved_target_type: "location"` plus `resolved_target_id` across registers. The fix is **not** a verb/room whitelist; the fix is to formalize the contract output so every classified free action carries the eight required fields plus the fail-closed enrichment, making the gap **measurable** by the contract assertions PR-A's tests enforce. Reliability of the upstream semantic classification (LLM) is out of scope for PR-A; the contract surfaces unreliability via `unknown_target` + `classification_reason`, never as a silent generic fallback.

## 4. Live-smoke feasibility probe

| Evidence channel | Today | After PR-A |
|---|---|---|
| Langfuse spans for `resolve_player_action` | Available via the existing thin-path-summary surface ([ADR-0062](../ADR/adr-0062-director-realization-thin-path.md)). The resolver output flows through `_resolve_player_action` ([`ai_stack/langgraph/langgraph_runtime_executor.py:6260`](../../ai_stack/langgraph/langgraph_runtime_executor.py)) into graph state. | The contract dict travels inside `player_action_frame["free_player_action_resolution"]`. Existing Langfuse trace consumers that already log `player_action_frame` keys (no schema renames required) pick up the eight contract fields without any executor change. |
| Operator endpoint for per-turn evidence | `GET /api/story/sessions/{session_id}/thin-path-summary` ([`world-engine/app/api/http.py:1061-1075`](../../world-engine/app/api/http.py)) reads from `event.observability_path_summary` ([`world-engine/app/story_runtime/manager.py:14164-14222`](../../world-engine/app/story_runtime/manager.py)). | PR-A's contract is accessible via the existing `graph_state["player_action_frame"]["free_player_action_resolution"]` projection; surfacing it on the thin-path row is a **safe, minimal projection** that PR-A may add but does not depend on for acceptance. PR-A does **not** introduce a new endpoint family. |
| Diagnostic snapshot envelope | [`ai_stack/runtime_diagnostic_snapshot_contracts.py:57-172`](../../ai_stack/runtime_diagnostic_snapshot_contracts.py) declares `ResolverOutputPlaceholder` with `contract_name="free_player_action_resolution.v1"`. PR-0 tests guarantee the stub is not imported by production. | Untouched. The contract payload PR-A emits **is** the payload the placeholder reserves. When a future composer wires the envelope (PR-B or later), it reads from `player_action_frame["free_player_action_resolution"]`; no change to the stub is required for PR-A acceptance. |
| Headless tests against the contract | None today: no test exercises the eight required fields as a single closed enum surface. | PR-A delivers `ai_stack/tests/test_free_player_action_resolution_contract.py` with parametrized, paraphrased DE/EN inputs covering movement, object, actor, unknown, criminal/impossible, and meta classes; assertions are on contract field names and closed enum values, never on the raw input string. |
| Live-smoke session | The existing `WOS_THIN_PATH_LIVE_SMOKE=1 python -m pytest tests/smoke/test_thin_path_pr_a_live_smoke.py` (per ADR-0062) exercises the Resolver → Director → Narrator path. | PR-A does **not** require modifying the live smoke. The headless contract tests prove the resolver shape; the live smoke continues to ride the thin path unchanged. A future commit may extend the live smoke with assertions over the new contract fields. |

**Feasibility verdict.** PR-A is observable via existing Langfuse / graph-state surfaces without changing endpoints, UI templates, or the diagnostic-snapshot stub. The new contract is a per-turn projection that flows through the existing `player_action_frame` channel.

## 5. Anti-dead-end checkpoints

Each checkpoint names a failure mode that PR-A must expose as observable evidence, not silent degradation. Tests enforce each checkpoint.

1. **Silent null `resolved_target_id`.** Forbidden. When the resolver cannot bind a target, the contract carries `resolved_target_id=null` **with** `classification_reason` populated (one of `semantic_resolution_missing_target`, `semantic_catalog_no_match`, `semantic_ai_resolution_required`, `meta_input_control_path`, or a semantic-payload `reason`/`reasoning_summary` string). Asserted in `test_unknown_target_fails_closed_with_classification_reason`.
2. **Silent low-risk default for unsafe / unknown actions.** Forbidden. When `action_commit_policy == "needs_clarification"`, the contract's `canonical_risk` is **never** `"low"`; the default is `"medium"`, escalated to `"high"` when the semantic payload reports `canonical_risk: high` or `canon_safety` outside the allowed mundane set. Asserted in `test_unknown_target_canonical_risk_is_medium_or_high` and `test_criminal_or_impossible_action_stays_clarification`.
3. **`target_location` populated for non-location targets.** Forbidden. The contract's `target_location` is non-null **only** when `resolved_target_type == "location"`; otherwise `null`. Asserted in `test_actor_directed_input_target_location_is_null` and `test_object_interaction_target_location_is_null_or_container`.
4. **`presence_breaks_gathering` over-claiming Director authority.** Forbidden. PR-A's contract emits `presence_breaks_gathering=false` by default, with a sibling `presence_breaks_gathering_authority="director_final"` provenance marker and `presence_breaks_gathering_evidence` carrying `target_location`, `participation_relevance`, `visibility_audibility` for the Director to compose later. PR-A must not implement Director composition. Asserted in `test_presence_breaks_gathering_is_preliminary_resolver_signal` and (negatively) by the PR-0 baseline `test_pr_0_does_not_implement_pr_abc_runtime_symbols_in_untouched_files` — PR-A must **not** introduce `def compute_gathering_state` or `def presence_breaks_gathering` symbols anywhere in the runtime files PR-0 pledged to leave untouched.
5. **Enum drift.** Forbidden. The contract's closed enums are exactly:
   - `resolved_target_type ∈ {location, object, actor, none}`
   - `affordance_status ∈ {allowed, unknown_target}`
   - `canon_safety ∈ {canon_compatible, content_silent_mundane, non_load_bearing, reversible_local_detail}` (or `null` when `canonical_risk` carries the risk band)
   - `canonical_risk ∈ {low, medium, high}`
   - `action_commit_policy ∈ {commit_action, needs_clarification}`
   Any other value is a contract violation. Asserted in `test_contract_enums_are_closed`.
6. **Exact-string fixture dependency.** Forbidden. Tests parametrize multiple paraphrased DE / EN inputs per action class and assert on field names / enum values, not on the raw string. The semantic dict the tests construct **simulates** an upstream LLM payload; reliability of the LLM is out of PR-A's scope. Asserted by the structure of `tests/`.
7. **Premature PR-B / PR-C symbol implementation.** Forbidden. PR-A must not introduce `compute_gathering_state`, `gathering_paused`, `canonical_path_hold_effect` propagation, or `narrator_consequence_realization` populating logic. Asserted by `tests/test_npc_interactivity_piv_baseline.py::test_pr_0_does_not_implement_pr_abc_runtime_symbols_in_untouched_files` (the regex scan keeps applying after PR-A lands; PR-A does not add the forbidden `def {symbol}` shapes anywhere in scope).
8. **Active Pi / Π runtime keys.** Forbidden. The new module uses semantic capability names only. Asserted by `tests/gates/test_adr_0039_pi_scope.py::test_production_runtime_vocabulary_has_no_active_pi_control_tokens` and the regex check inside the new tests file.

## 6. Plan-file reference reconciliation (verified)

The roadmap and PR-0 PIV cite several `file:line` anchors. PR-A re-verified the following on 2026-05-19 prior to writing code. Discrepancies are recorded; the verified column wins.

| Source | Cited anchor | Verified anchor (2026-05-19) | Status |
|---|---|---|---|
| Plan §1.5, PR-0 §2 | `ai_stack/player_action_resolution.py` `resolve_player_action()` def | [`ai_stack/player_action_resolution.py:502`](../../ai_stack/player_action_resolution.py) | Matches. |
| PR-0 §2 | `ai_stack/module_runtime_policy.py:413` | Verified — `canonical_path_control` projection lives at [`ai_stack/module_runtime_policy.py:410-416`](../../ai_stack/module_runtime_policy.py) (`player_freedom` dict). | Matches with one-line tolerance. |
| PR-0 §2 | `ai_stack/langgraph/langgraph_runtime_executor.py:3996` `_build_npc_agency_plan_projection` def, call at `:4279`; `canonical_path_control` block at `:4703` | All three remain stable. Additionally verified `_resolve_player_action` node def at [`:6260`](../../ai_stack/langgraph/langgraph_runtime_executor.py) and the call to `resolve_player_action` at [`:6280`](../../ai_stack/langgraph/langgraph_runtime_executor.py). | Matches. |
| PR-0 §2 | `ai_stack/director/scene_director_goc.py:655` `_build_responder_set` def, call at `:911` | Matches. PR-A does not touch this surface. | Matches. |
| PR-0 §2 | `world-engine/app/story_runtime/manager.py:8683-8687` `_turn_holds_canonical_path_for_free_player_action` def, `:8746` gate | Matches. PR-A does not touch this surface. | Matches. |
| PR-0 §2 | `content/modules/god_of_carnage/canonical_path/005_statement_reading.yaml:36` `named_characters: [veronique, michel, annette, alain]` | Verified line 36. | Matches. |
| ADR-0062 / ADR-0057 | `world-engine/app/api/http.py` thin-path-summary endpoint | Verified at [`:1061-1075`](../../world-engine/app/api/http.py); manager impl at [`world-engine/app/story_runtime/manager.py:14164`](../../world-engine/app/story_runtime/manager.py). | Matches. |
| PR-0 stub | `ai_stack/runtime_diagnostic_snapshot_contracts.py` placeholder reservations | Verified — `ResolverOutputPlaceholder.contract_name = "free_player_action_resolution.v1"` at [`:65`](../../ai_stack/runtime_diagnostic_snapshot_contracts.py); `REQUIRED_CONTRACT_PLACEHOLDER_NAMES` at [`:167-172`](../../ai_stack/runtime_diagnostic_snapshot_contracts.py). | Matches. |
| Existing tests | `ai_stack/tests/test_player_action_resolution.py` | Verified — current tests cover movement, object, prevented, unknown-target, plausible-inference, speech, meta cases; PR-A adds a sibling test module that asserts the new contract shape. | Matches. |

## 7. What existing paths PR-A reuses (does not own)

PR-A's discipline is **reuse, do not rebuild**.

- **Semantic payload extraction**: [`ai_stack/player_action_resolution.py:430`](../../ai_stack/player_action_resolution.py) `_semantic_payload()` already pulls the AI's structured output.
- **Content grounding**: [`ai_stack/player_action_resolution.py:362-408`](../../ai_stack/player_action_resolution.py) `_row_by_id` + `_resolve_query` already match catalog ids and fall back to `unknown_target`.
- **Plausible inference gate**: [`ai_stack/player_action_resolution.py:236-321`](../../ai_stack/player_action_resolution.py) `_semantic_allows_plausible_inference` + `_inferred_target_from_semantics` already enforce the YAML-driven canon-safe inference rules.
- **Canonical-path-effect derivation**: [`ai_stack/player_action_resolution.py:324-338`](../../ai_stack/player_action_resolution.py) `_canonical_path_effect_from_policy` already reads `canonical_path_control.default_for_free_player_action`.
- **Frame data class** at [`ai_stack/action_resolution_contracts.py:131`](../../ai_stack/action_resolution_contracts.py) — unchanged.
- **LangGraph propagation** at [`ai_stack/langgraph/langgraph_runtime_executor.py:6260`](../../ai_stack/langgraph/langgraph_runtime_executor.py) — unchanged. The contract rides inside the frame dict, which the executor already lifts into graph state at `:6293`.

## 8. What PR-A must not touch

Hard constraints. PR-A's diff stays inside this guardrail; tests above enforce the negatives.

- **`ai_stack/narrator/narrator_consequence_contracts.py`** — owned by PR-B (`narrator_consequence_realization.v1`).
- **`ai_stack/canonical_path_resolver.py`** — owned by canonical-path loading; unchanged.
- **`ai_stack/director/scene_director_goc.py`** — owned by PR-C (Director composition and `gathering_paused` gate).
- **`ai_stack/langgraph/langgraph_runtime_executor.py`** lines around `_resolve_player_action` (no executor logic change; the contract rides inside the frame), `_build_npc_agency_plan_projection`, and the `canonical_path_control` block (PR-B / PR-C own those).
- **`ai_stack/live_dramatic_scene_simulator.py`** — LDSS and mandatory-beat consumption stay unchanged.
- **`ai_stack/runtime_aspect_ledger.py`** — `ASPECT_KEYS` unchanged; no Director-Pause aspect row added.
- **`ai_stack/narrator/goc_narrator_path.py`** — Turn 0 narrator path unchanged.
- **`ai_stack/goc_souffleuse.py`** — Souffleuse path unchanged.
- **`ai_stack/runtime_diagnostic_snapshot_contracts.py`** — PR-0 stub stays uncoupled from production; PR-A does **not** import it from `ai_stack/player_action_resolution.py` or any other production module (enforced by `tests/test_npc_interactivity_piv_baseline.py::test_runtime_diagnostic_snapshot_stub_is_not_imported_by_production_code`).
- **`world-engine/app/story_runtime/manager.py`** — `_turn_holds_canonical_path_for_free_player_action`, `_build_langfuse_path_summary`, `get_thin_path_summary`, commit / readiness, all unchanged. PR-A does not modify the manager.
- **`world-engine/app/web/templates/ui/**`** — no UI page change.
- **`world-engine/app/api/**`** — no new endpoint family.
- **`frontend/static/**`** — no block-streaming or cut-in change.
- **`content/modules/**`** — no content edit; the policy YAML stays the source of truth.
- **PR-A must not introduce** any of the symbols `compute_gathering_state`, `gathering_paused`, `presence_breaks_gathering` **as a `def` or `class`** anywhere in scope. They appear only as contract field names (dict keys), constants, or test asserts. The PR-0 baseline regex (`\bdef\s+{symbol}\b|\bclass\s+{symbol}\b`) keeps passing.
- **PR-A must not introduce** `step.mode` switching, pointer repair, NPC pulse, Block-Stream-Bus, Cut-In handling, or Player-Hold logic.
- **PR-A must not introduce** verb / room / actor / locale literal whitelists in any scanned production file (`tests/gates/test_table_b_anti_hardcoding_gate.py`).

## 9. Files PR-A adds / modifies

| Path | Action | Reason |
|---|---|---|
| `ai_stack/free_player_action_resolution_contracts.py` | **add** | Closed enum constants + builder for `free_player_action_resolution.v1`. |
| `ai_stack/player_action_resolution.py` | **modify** | Call the builder on every return path; embed the contract dict inside `player_action_frame` and emit a sibling `"free_player_action_resolution"` key in the resolver output. No other behavior change. |
| `ai_stack/tests/test_free_player_action_resolution_contract.py` | **add** | Parametrized headless tests over movement (DE paraphrases across registers), object, actor, unknown-target, criminal/impossible, meta-control, and field-completeness; no exact-string fixture coupling; no Pi / Π keys. |
| `docs/implementation_logs/pr_a_resolver_contract_closure_piv.md` | **add (this file)** | PIV artifact. |
| `docs/MVPs/npc_interactivity_piv_log.md` | **modify** | PR-A row transitions from "Not started" to "Draft" with a link to this PIV. |

No other file is modified.

## 10. Pre-existing baseline observation (out of PR-A scope)

The known PR-0-recorded failure remains at HEAD on 2026-05-19:

```
tests/test_capability_matrix_documentation_readiness.py::test_capability_matrix_doc_links_resolve
```

Reason (per PR-0 §9): a stale markdown link to a relocated character-voice YAML. PR-A does **not** fix this; it belongs to a separate doc-hygiene change and is not caused by the resolver contract closure.

## 11. Acceptance evidence for PR-A itself

PR-A must satisfy, against repository HEAD after the commit:

1. `docs/implementation_logs/pr_a_resolver_contract_closure_piv.md` (this file) exists with every required section.
2. `docs/MVPs/npc_interactivity_piv_log.md` lists PR-A with `Status: Draft` and a link to this PIV.
3. `ai_stack/free_player_action_resolution_contracts.py` exists, exports the closed enum constants, and defines a builder that takes the resolver's per-turn data and returns the contract dict.
4. `ai_stack/player_action_resolution.py` `resolve_player_action()` emits the contract on every return path; every returned dict contains `"free_player_action_resolution"` carrying all eight required fields plus `classification_reason` (or `null` when not applicable) and the `presence_breaks_gathering_*` provenance triple.
5. `ai_stack/tests/test_free_player_action_resolution_contract.py` is green for movement (multiple DE/EN paraphrases), object, actor, unknown-target, criminal/impossible, meta-control, and field-completeness assertions.
6. `tests/test_npc_interactivity_piv_baseline.py` remains green (PR-0 acceptance not regressed).
7. `tests/gates/test_adr_0039_pi_scope.py` and `tests/gates/test_adr0039_pi_scope.py` remain green.
8. `tests/gates/test_table_b_anti_hardcoding_gate.py` remains green.
9. `tests/test_capability_matrix_documentation_readiness.py` keeps its single pre-existing failure (recorded above as not caused by PR-A); other tests in that file remain green.

## 12. Footer

- Verification date: 2026-05-19
- Repository SHA at verification time: HEAD prior to this commit
- Author handoff: PR-B (live-effect propagation) may begin once this PIV is merged. PR-B will read the contract from `player_action_frame["free_player_action_resolution"]` in graph state.
