# ADR-0057: Canon-Safe Player Freedom and Affordance Inference

Status: Accepted

Date: 2026-05-18

## Context

The live runtime must let the selected player character move, observe, wait,
and interact freely after the narrator handoff. The canonical path remains the
directed story spine, but it must not behave like a rail that forbids ordinary
movement or mundane object use.

The content module cannot become a second exhaustive database of every possible
object or container content. Where authored content is silent, the engine needs
a semantic AI contract that can fill small, local gaps without breaking canon.

## Decision

The runtime separates three surfaces:

1. Player local context: the player's current room, perception, and immediate
   interaction state.
2. Canonical path: the directed narrator/dialogue spine.
3. Canon-safe inferred affordances: AI-resolved mundane, reversible details that
   are not promoted to canonical facts.

Free movement, perception, waiting, and mundane object interaction may update
player local context, but they hold the current canonical step unless content
explicitly marks a progression point. If a required participant is away or
temporarily prevented, the Director may stage a social hold instead of spending
mandatory dialogue.

When the content catalog has no exact object match, the semantic resolver may
commit an inferred target only when the AI marks it with the safety fields
required by the module's player_freedom_policy. The engine must not contain
object-specific or verb-specific maps for this decision.

## Consequences

- No verb maps, locale maps, or object-specific engine branches are introduced.
- Known content ids remain preferred.
- Plausible inferred details are narrator-realized and local to runtime state.
- Object interactions that require semantic realization use the model path
  instead of a deterministic empty/template short path.
- **ADR-0062 (2026-05-19):** mundane player movement and perception on the default
  turn path use the **Director realization thin path** (`director_compose_realization`
  → `realize_via_capabilities` → LLM in `session_output_language`). The removed
  `authoritative_action_resolution` node must not echo English `description` fields
  from affordance YAML. See [ADR-0062](adr-0062-director-realization-thin-path.md).
- Free actions without a resolved AI semantic payload are represented as
  `semantic_resolution_required` with `needs_clarification` action policy.
  They must not be guessed into a generic `interact` verb by engine maps, and
  they must still keep the full Director/model runtime path rather than falling
  into deterministic short-path handling.
- Backend-local diagnostic previews and improvement sandbox simulations inherit
  the same rule. Unquoted free text that looks like a nod, movement, or object
  action must remain `unknown` / `ambiguous` until semantic AI evidence or a
  structural command/dialogue marker resolves it; tests must not reintroduce
  verb-map expectations through those side paths.
- Multi-turn runtime smoke tests must preserve the same boundary: unresolved
  free-text inputs may produce a safe `establish_situational_pressure` semantic
  move and `establish_pressure` scene function while still exercising the full
  Director/model path. Tests must not force keyword-derived scene functions such
  as `escalate_conflict`, `withhold_or_evade`, or `probe_motive` unless resolved
  action, speech, or semantic-move evidence exists.
- Prior continuity may still influence the responder set, secondary reactor
  enablement, social asymmetry, and pattern-variation diagnostics for an
  unresolved move. It does not by itself justify changing the safe
  `establish_pressure` scene-function default.
- Breadth/playability and long-run operator-readiness regressions should
  therefore count non-preview execution, resolver evidence, gate credibility,
  responder variation, and explainable degradation for unresolved player text.
  They should not treat scene-function diversity as required coverage until the
  fixture supplies resolved action, speech, or semantic-move evidence.
- Recoverable validation rejects on unresolved free text can be
  `degraded_explainable` / `conditional_pass` for operator-readiness coverage
  when diagnostics preserve validation status, alignment summary, and fallback
  path evidence. Tests should not require a hard dramatic-quality `fail` where
  the runtime reports an explainable recoverable degradation.
- The canonical path can wait while the player explores, instead of wandering.

## Amendment (2026-05-19) — Phase-1 NPC interactivity runtime contracts

This amendment names the four runtime contracts that PR-A, PR-B, and PR-C of the NPC interactivity roadmap (see [`NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md`](../../NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md) §3.0 and §3.4) will produce. PR-0 (this commit) does not implement any of the four; it only fixes their names and required fields so that multiple agents do not implement the same idea under different shapes. The companion PIV artifact lives at [`docs/implementation_logs/pr_0_npc_interactivity_contracts_piv.md`](../implementation_logs/pr_0_npc_interactivity_contracts_piv.md); the roadmap index lives at [`docs/MVPs/npc_interactivity_piv_log.md`](../MVPs/npc_interactivity_piv_log.md).

### Vocabulary discipline (binding for all four contracts)

- No verb / action / room whitelists. The Possibility × Morality axes (plan §2.1) are evaluated semantically; the contracts carry the result, never the input string match.
- Contract **vocabularies** (e.g. `affordance_status ∈ {allowed, unknown_target}`, `canon_safety ∈ {canon_compatible, content_silent_mundane, non_load_bearing, reversible_local_detail}`, `canonical_risk ∈ {low, medium, high}`, `action_commit_policy ∈ {commit_action, needs_clarification}`) are part of the contract and are allowed. They are **closed enumerations** for that specific contract field; they are not module-data whitelists.
- Semantic runtime names only. Π / Pi labels remain index-only in the Capability Matrix and must not appear as active runtime keys, MCP payload fields, Langfuse score names, or UI routing identifiers. See [ADR-0039](adr-0039-gate-tests-no-hardcoded-oracle-bypass.md) and the production scans in `tests/gates/test_adr_0039_pi_scope.py` and `tests/gates/test_table_b_anti_hardcoding_gate.py`.
- `presence_breaks_gathering` is **Director-derived from resolver output**, not raw Resolver authority. The Resolver answers _what does the action mean in the world_ (target type, target id, possibility, morality, target location). The Director answers _what does that mean for the gathering_ (paused or not). See §3.4 of the plan and ADR-0061 (Draft).
- Director-Pause is **not** Player-Hold. Player-Hold is the legacy "the player must wait" reading; Director-Pause inverts it: the gathering waits while the player remains free. The two read sites differ — Player-Hold reads at `world-engine/app/story_runtime/manager/` (canonical-step pointer hold for mundane player inference); Director-Pause is the new `director_gathering_state.v1` consulted by responder selection and mandatory-beat consumption. ADR-0061 owns the latter.

### Contract 1 — `free_player_action_resolution.v1`

Produced per turn by the player-action resolver (entry: `ai_stack/story_runtime/player_action_resolution.py:502`).

Required fields:

- `resolved_target_type` — closed enum: `location | object | actor | none`.
- `resolved_target_id` — string or `null`; if `null`, **must** include `classification_reason` describing why no target was bound (semantic resolution uncertain, ambiguous reference, etc.). A silent `null` is rejected.
- `target_location` — room id when the resolved target is a movement to a location, otherwise `null`.
- `presence_breaks_gathering` — boolean. **Director-derived** from the resolver output composed with `participation_relevance` and `visibility / audibility` signals; see ADR-0061 (Draft) for the composition rule. Carried in the contract so the per-turn snapshot exposes it.
- `affordance_status` — closed enum: `allowed | unknown_target`.
- `canon_safety` — closed enum: `canon_compatible | content_silent_mundane | non_load_bearing | reversible_local_detail` (plus a numeric risk band for non-mundane cases, captured under `canonical_risk`).
- `canonical_risk` — closed enum: `low | medium | high`.
- `action_commit_policy` — closed enum: `commit_action | needs_clarification`.

Invariants:

- Every player input that the resolver classifies as a free action must populate **all** required fields. `null` is allowed only with the matching `classification_reason`. PR-A delivers the resolver behavior that enforces this; PR-0 declares the contract.
- The contract is **not** a runtime aspect ledger row. It is a per-turn frame attached to `player_action_frame` / `affordance_resolution` in graph_state and exposed via the existing operator endpoint family from [ADR-0062](adr-0062-director-realization-thin-path.md).

### Contract 2 — `director_gathering_state.v1`

Produced atomically per tick by the Director (the canonical surface lives in `ai_stack/story_runtime/director/god_of_carnage_scene_director.py` once PR-C lands).

Required fields:

- `paused` — boolean.
- When `paused == true`:
  - `step_id` — current canonical step at the entry to the pause.
  - `missing_actor_ids` — list of actor ids that should be co-present per `named_characters` but are not.
  - `since_turn` — turn number at which the pause entered.
  - `presence_required_for_step` — snapshot of `named_characters` for that step at entry time (so subsequent canonical edits do not retroactively alter the snapshot).

Invariants:

- Atomic per tick. The `paused: false → true` and `paused: true → false` transitions each emit exactly one state-change event so the per-turn snapshot can carry the transition without polling.
- Director-derived. Inputs are `actor_locations` (runtime world), `participation_relevance` and `visibility / audibility` (from the resolver's semantic classification of the player action), and `named_characters` (content). The Resolver does **not** carry gathering knowledge; the Director composes the pause decision.
- Mandatory-beat consumption pauses while `paused == true`. The player remains free. NPC mundane actions remain free. The narrator may emit at most one transition reaction block on entry (optional, content-led).
- See [ADR-0061 (Draft)](adr-0061-director-pause-mode-for-gathering-interruption.md) for the full state-machine contract.

### Contract 3 — `canonical_path_hold_effect.v1`

Carried in graph_state alongside the existing `canonical_path_control` block (the construction site lives at `ai_stack/langgraph/langgraph_runtime_executor.py:4703`). Read by `world-engine/app/story_runtime/manager/`.

Required fields:

- `effect_kind` — closed enum: `hold_current_step`.
- `source` — closed enum: `ai_semantic_plausible_inference | gathering_paused | social_wait_policy | (additional content-declared source names in module YAML)`.
- `until_condition` — short semantic description of the resolution condition (e.g. "named_characters[current_step] ⊆ scene presence", "player re-enters gathering room"). Diagnostic only; not parsed by runtime branching.

Invariants:

- The effect is **propagated**, not re-derived at the read site. PR-B is responsible for delivering the propagation; PR-0 declares the contract.
- The read site at `manager.py:8683-8687` remains the single authority for "did the canonical step advance this turn or not". No additional branching key is introduced.

### Contract 4 — `narrator_consequence_realization.v1`

Carried alongside `narrator_consequence_packet` in graph_state (the consumer surface lives in `ai_stack/contracts/narrator_consequence_contracts.py`).

Required fields:

- `source` — closed enum: `ai_semantic_plausible_inference | gathering_paused_reaction | (additional content-declared source names)`.
- `requires_model_realization` — boolean.
- `realized_block_id` — block id of the visible narrator block this packet produced, or `null`.
- `non_realization_reason` — string. Required when `requires_model_realization == true` and `realized_block_id == null`.

Invariants:

- When `requires_model_realization: true`, the outcome must be either a visible `narrator` block in the committed `visible_scene_output.blocks` stream **or** an explicit `non_realization_reason`. A silent missing block is rejected.
- The block-content invariants of the existing narrator consequence validator stand: no new people, no new rooms, no plot-bearing facts.
- PR-B closes the live narrator-emission gap (plan §3.2); PR-0 only declares the contract.

### Cross-contract guarantees

- All four contracts are **per-turn snapshots** that flow through existing graph-state keys, the operator `thin-path-summary` endpoint family from ADR-0062, and Langfuse spans. No new endpoint family is introduced for PR-0.
- The Phase-1 diagnostic UI extension (plan §3.5) reads from one snapshot envelope (`runtime_diagnostic_snapshot.v1`) that wraps all four contracts plus the existing `realization_plan.v1` / thin-path evidence. PR-0 provides the envelope stub; PR-A/B/C populate it.
- The contracts are diagnostic and contractual, not authoritative state. Commit / Readiness logic is unchanged in PR-0.
