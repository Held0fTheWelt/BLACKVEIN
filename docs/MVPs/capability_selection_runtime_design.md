# Capability Selection Runtime Design

Last updated: 2026-05-16

This document is the implementation-readiness companion for
[ADR-0041: Controlled Runtime Capability Authority](../ADR/adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md).
It is implementation guidance for the local selector core and future runtime
integration. It does not change world-engine runtime behavior, promote
Capability Matrix status, or create live/staging proof.

## Strategic direction: runtime authority (not sidecar-only)

ADR-0041 **semantic capability selection** is an **elemental runtime building block** whose **target role** is **controlled runtime authority**—situation classification, capability selection, lean validator routing, seam drift visibility, scoped transfer preparation, and eventual **bounded co-authority** for proven concern slices.

**Current phases** (dry-run, projection, opt-in plan-enforced sidecar, bridge, preview, handoff-candidate, scoped co-authority decision preview) are **safety scaffolding**, valid only as **intermediate** steps. They must not become the **final** architecture by inertia. **`run_validation_seam` stays canonical** for `validation_outcome`, commit, and readiness **until an explicit governance decision** changes that.

When reading the Capability Map/matrix, separate **local implementation** from **runtime-path participation**, **shadow/preview** layers from **partial-transfer readiness**, and **real co-authority** from **live/staging verification**—see [capability_matrix_status_and_adr_relations.md](capability_matrix_status_and_adr_relations.md) § ADR-0041 runtime authority direction.

## Administration operator defaults (ADR-0039 surface)

The **administration-tool** manage UI does **not** treat any content module or experience template as an implicit browser default. Operator-visible defaults are injected server-side from:

- **Backend** public `GET /api/v1/site/settings` fields `content_module_id` and `default_runtime_template_id` (stored in `site_settings`; legacy keys `default_content_module_id` / `default_experience_template_id` remain equivalent), merged when the operator host does not set `ADMIN_DEFAULT_*` env overrides, and
- **Game content**: new draft starters use **`GET /api/v1/game/content/experiences?status=published`** (moderator JWT via proxy) — no silent placeholder template id in static JS.

Narrative governance pages show an explicit **configuration required** JSON panel when `content_module_id` is missing.

See `docs/MVPs/adr0039_runtime_surface_governance_inventory.md` surface `administration_tool_operator_ui_and_proxy`.

## Implementation Status

The first local deterministic selector core now exists in
`ai_stack/capabilities/capability_selector.py`, with focused tests in
`ai_stack/tests/test_capability_selector.py`.

2026-05-15 selector correction (historical Π34 context): explicit player-turn
signals keep player-turn authority even when NPC agency evidence is present.
For `turn_kind=player` / `player_input` or clear player input without an NPC
actor signal, `npc_decision_required=true` now means: keep
`turn_kind=player_input`, keep `active_actor=player`, enforce
`player_intent_inference` and `action_resolution` when applicable, and add
`npc_agency` as a conditional enforced capability. It does **not** reclassify
the turn as `npc_turn`. Tests:
`ai_stack/tests/test_capability_selector.py` and
`ai_stack/tests/test_capability_selector_runtime_projection.py`.

2026-05-16 active-listening envelope (historical Π34 context): normal player
turns also observe `broad_nlu_listening`, `conversational_memory`, and
`prompt_authority`. LangGraph derives those records from structured
`interpreted_input`, `semantic_move_record`, `hierarchical_memory_context`, and
capability-selection projection evidence, then inserts them into the dramatic
generation packet / prompt and writes `RuntimeAspectLedger` aspect rows. This
is bounded prompt-envelope evidence only: it stores no raw player input or raw
prompt text in those aspect records and keeps `commit_gate_changed=false`,
`readiness_gate_changed=false`, and `validation_outcome_changed=false`.

The RuntimeAspectLedger runtime intelligence projection now exposes
`runtime_intelligence_projection.capability_selection` as local-only evidence
derived from existing turn context. This projection does not set
`turn_aspect_ledger.capability_selection` to passed, does not change commit or
readiness status, and does not execute validators or judges.

The local validator planning layer now exposes
`runtime_intelligence_projection.validator_execution_plan`. It maps enforced
capabilities to planned local validator IDs, observed capabilities to
non-blocking diagnostic IDs, excluded capabilities to skipped validator IDs, and
budget-disallowed judge IDs to `judges_disallowed`. The projection always emits
`execution_changed=false`.

The dry-run validator dispatch layer now exposes
`runtime_intelligence_projection.validator_dispatch_report` from
`ai_stack/capabilities/capability_validator_dispatch.py`. Default mode is `dry_run`: it
reports `validators_would_run`, `diagnostics_would_run`, `validators_would_skip`,
and `judges_would_be_disallowed` without executing validators or changing commit
or readiness gates. `actually_executed` remains empty and
`execution_changed=false`.

An explicit opt-in `plan_enforced` mode is available through
`ADR0041_VALIDATOR_DISPATCH_MODE=plan_enforced` or test-harness `mode=` overrides.
It requires a registered local validator registry, does not execute judges, does
not change commit/readiness gates, and remains `proof_level=local_only`. Missing
or invalid env values fail closed to `dry_run`. Production validator orchestration
and commit/readiness integration remain pending.

A second explicit flag, `ADR0041_SCOPED_CO_AUTHORITY_ENABLED=true`, can emit
`runtime_intelligence_projection.validation_co_authority_decision` when
`plan_enforced` graph sidecar execution is present and the selected turn class is
`partial_transfer_ready`. This is the current `scoped_co_authority` step: it may
produce `readiness_preview` and `validation_preview`, but it keeps
`validation_outcome_changed=false`, `commit_gate_changed=false`, and
`readiness_gate_changed=false`.

A semantic validator registry inventory now exists in
`docs/MVPs/capability_validator_registry_inventory.md` with code-backed rows in
`ai_stack/capabilities/capability_validator_registry.py`. `build_default_semantic_validator_registry()`
returns an empty map; `build_available_semantic_validator_registry()` exposes thin
adapters only for inventory rows marked `safe_for_local_plan_enforced`.
`build_player_turn_enforced_semantic_validator_registry()` covers the normal
player-turn enforced set when opt-in plan-enforced dispatch is used in tests.
`build_npc_conflict_enforced_semantic_validator_registry()` covers the NPC
conflict-turn enforced set the same way.

Turn-class coverage (drift guard, no runtime wiring): `TURN_CLASS_ENFORCED_VALIDATORS`,
`get_turn_class_enforced_validators`, `get_registry_coverage_for_turn_class`, and
`assert_turn_class_registry_coverage` in `ai_stack/capabilities/capability_validator_registry.py`
with tests in `ai_stack/tests/test_capability_validator_turn_class_coverage.py`.
For each of `opening_scene`, `normal_player_turn`, and `npc_conflict_turn`, local-only
registry builders are expected to register every enforced validator ID; observer
diagnostics remain non-blocking and must not appear in enforced sets.

World-engine **test harness only**: ``build_adr0041_validator_dispatch_harness_report``
(``ai_stack/story_runtime/runtime_aspect_ledger/__init__.py``) enables plan-enforced local validator execution when tests pass
``harness_allow_plan_enforced_local_dispatch=True`` and an explicit registry; ledger normalization does not
invoke it. Evidence: ``world-engine/tests/test_adr0041_validator_dispatch_harness.py``.

Current boundaries:

- Only the bounded Π34 active-listening envelope is wired into LangGraph
  prompt/packet assembly; broader selected-capability prompt authority remains
  governed future work.
- Not wired into commit/readiness gating.
- Not wired into judge execution.
- Not wired into Langfuse/MCP live or staging proof.
- Not Capability Matrix promotion evidence.

## ADR-0041 Production Orchestration Readiness (audit 2026-05-15)

**Verdict:** Plan-enforced dispatch is **opt-in only** (`ADR0041_VALIDATOR_DISPATCH_MODE=plan_enforced`).
Scoped co-authority decision preview is also **opt-in only**
(`ADR0041_SCOPED_CO_AUTHORITY_ENABLED=true`). **Do not** treat ADR-0041 local
results as commit/readiness truth; **`run_validation_seam`** remains canonical
for `validation_outcome`. Broader production rollout (registry sourcing,
operational policy, rollback, commit/readiness policy) still needs an explicit
governance slice.

### Current state

- **Default path:** `normalize_runtime_aspect_ledger` → `build_runtime_intelligence_projection` →
  `build_semantic_validator_dispatch_report_projection` → **always `dry_run`**,
  `actually_executed=[]`, `commit_gate_changed=false`, local-only proof flags.
  Top-level `validation_authority_preview` is **absent** on this path.
- **Opt-in LangGraph path:** When `plan_enforced` is set, `validate_seam` attaches
  `_adr0041_runtime_graph_dispatch_context` (dispatch context + seam summary **echo** only).
  Ledger normalization then merges a **plan-enforced** `validator_dispatch_report` (turn-class
  registry) and sets `runtime_intelligence_projection.validation_authority_preview` plus
  `validation_authority_bridge` and **top-level** `authority_handoff_candidate` (duplicate of the bridge field)
  with explicit `affects_commit=false` / `affects_readiness=false` and drift classification vs the seam
  summary. With `ADR0041_SCOPED_CO_AUTHORITY_ENABLED=true` and `partial_transfer_ready=true`,
  the same path can add **top-level** `validation_co_authority_decision`; this is a bounded
  runtime authority decision preview, not gate mutation. With
  `ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED=true`, the same path can also add
  **top-level** `readiness_co_authority_preview` (policy stage + blockers/evidence) as
  policy-grade runtime output without mutating real readiness. With
  `ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED=true`, the path can emit
  **top-level** `readiness_co_authority_enforcement` (`allow|block|no_decision`) as explicit
  `readiness_policy_input` for downstream governance, still without mutating final readiness gates.
- **Harness path:** `build_adr0041_validator_dispatch_harness_report` — tests only; **not** invoked from ledger normalization.
- **Semantic naming / Pi:** Validator IDs remain semantic contract names; **no `actually_detected`** symbol exists in the repo (canonical field is **`actually_executed`**).

### Runtime validation flow map (discovered paths)

| Path | Symbol / anchor | What it does | When | Blocking vs narrative | Commit / readiness | LLM/Judge | Classification |
|------|-------------------|--------------|------|------------------------|-------------------|-----------|----------------|
| GoC validation seam | `ai_stack/story_runtime/turn/god_of_carnage_turn_seams.py::run_validation_seam` | Proposal validation (`validation_outcome`): actor lane, dramatic-effect gate, GoC rules | After generation proposal, before commit | **Blocking** for rejected outcomes | **Drives** retry/degraded path via executor + aspect ledger | No judge by default in seam | **must_not_be_plan_routed** (canonical commitment seam — ADR-0041 dispatch must not replace this without governance) |
| LangGraph validation node | `ai_stack/langgraph/langgraph_runtime_executor.py` — `_run_validation` closure calling `run_validation_seam`; `_build_runtime_aspect_validation`; retry loop `decide_playability_recovery` | Packages seam outcome into `validation_outcome`, aspect ledger aspects, per-contract validation dicts on graph state | During graph execution on turn | **Blocking** / degraded leniency | **Indirectly** affects commit via `validation_outcome` + ledger | Optional provider generation upstream; seam local | **must_not_be_plan_routed** without separate ADR |
| Aspect ledger normalization | `ai_stack/story_runtime/runtime_aspect_ledger/__init__.py::normalize_runtime_aspect_ledger` → `build_runtime_intelligence_projection` | Adds **`runtime_intelligence_projection`** (capability selection, validator plan, **dry-run** dispatch report by default; optional **plan-enforced** dispatch + `validation_authority_preview` when graph bundle + env; optional `readiness_aggregation_decision` when aggregation flag + prerequisites) | On ledger normalize | **Non-blocking** for gameplay (projection) | **Does not** change commit/readiness or `validation_outcome` | No | **dry_run_projection_only** default; **plan_enforced_sidecar** = local routing preview + drift + optional readiness aggregation (veto-only vs seam) |
| ADR-0041 runtime readiness consumer (bundle) | `ai_stack/story_runtime/runtime_readiness_consumer.py::resolve_runtime_readiness_with_adr0041` → `backend/app/api/v1/game_routes.py::_player_session_bundle` | When `ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED=true` and upstream ADR-0041 flags + `readiness_aggregation_decision` are present, may **veto** legacy-allowed `runtime_session_ready` / `can_execute` only; never upgrades reject→allow; exposes diagnostics under `governance.adr0041_runtime_readiness_consumer` and read-only `governance.adr0041_readiness_projection_echo` (no extra aggregation). Inspector `authority_projection.adr0041_readiness_projection_echo` and operator turn-history `adr0041_readiness_projection_echo` mirror the same read-only ledger slices. **Single mutating consumer** under `backend/app` (guard test). | Player session bundle assembly | **Player-path readiness display** only | **Does not** change `validation_outcome` or commit; default without flag = legacy fields unchanged | No | **opt_in_veto_only** |
| ADR-0041 harness | `ai_stack/story_runtime/runtime_aspect_ledger/__init__.py::build_adr0041_validator_dispatch_harness_report` | Optional plan-enforced execution in tests | Explicit test call only | Test-scoped | No | No | **dry_run_projection_only** (production) / harness-only execution |
| Commit narrative capture | `world-engine/app/story_runtime/commit_models.py` — `resolve_narrative_commit` family | Snapshots validator layers / validation blobs into commit record | Commit persistence | N/A | **Yes** (record shape) | N/A | **requires_commit_policy_decision** if ADR-0041 results ever feed this |
| Recoverable / blocking ledger | `world-engine/app/story_runtime/manager.py` — `_recoverable_runtime_aspect_ledger`, `_runtime_aspect_commit_blocking_failure` | Marks validation/commit aspects failed/partial; detects blocking failures | Recoverable error paths | Can block “clean” commit path | **Yes** | No | **must_not_be_plan_routed** blindly |

### Safe insertion candidates (future)

1. **Post-projection enrichment (preferred minimal):** After `build_semantic_validator_dispatch_report_projection` inside a **new optional branch** (feature flag + explicit registry), merge **additional** `validator_dispatch_report` fields or a **sibling** key (e.g. `semantic_validator_dispatch_execution_preview`) so default payload stays byte-stable dry-run. **Insertion anchor:** `build_semantic_validator_dispatch_report_projection` call site inside `build_runtime_intelligence_projection` (`runtime_aspect_ledger.py`, ~726–728).
2. **LangGraph side-channel (non-commit):** After validation seam resolves but **before** mutating `validation_outcome`, run ADR-0041 dispatch **only if** flag+registry — record diagnostics on state **without** changing `validation_outcome`. **Anchor:** `langgraph_runtime_executor.py` near `update["validation_outcome"] = outcome` (~8081) — **high risk of duplication**; prefer ledger projection first.
3. **World-engine envelope only:** Attach harness output to diagnostics envelope returned to API — **anchor:** `manager.py` paths that assemble turn diagnostics (search `diagnostics` / `turn_aspect_ledger`). Lowest coupling; still requires flag/registry discipline.

### Unsafe / deferred areas

- **Replacing or short-circuiting `run_validation_seam`** with registry adapters.
- **Feeding ADR-0041 `passed` into commit/readiness** without a dedicated ADR and golden tests.
- **Auto-building registry from Capability Matrix** (hidden promotion risk).
- **Inferring `plan_enforced` from turn situation alone** (already forbidden by harness design).

### Authority status model

| Stage | Current state |
|-------|---------------|
| `dry_run` | Default ledger projection; no validators execute. |
| `plan_enforced` | Implemented behind `ADR0041_VALIDATOR_DISPATCH_MODE=plan_enforced` plus graph sidecar. |
| `authority_preview` | Implemented as `validation_authority_preview` and bridge drift fields. |
| `authority_handoff_candidate` | Implemented as a shadow governance signal. |
| `scoped_co_authority` | Implemented as `validation_co_authority_decision` behind `ADR0041_SCOPED_CO_AUTHORITY_ENABLED=true`; preview-only today. |
| `readiness_co_authority_preview` | Implemented as policy-grade preview behind `ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED=true`; still non-mutating for commit/readiness. |
| `scoped_readiness_enforcement_pilot` | Implemented as `readiness_co_authority_enforcement` + `readiness_policy_input` behind `ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED=true`; explicit policy input only, no default readiness-gate mutation. |
| `scoped_readiness_aggregation_pilot` | Implemented as `readiness_aggregation_decision` behind `ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED=true` plus prerequisite flags; seam-canonical allow/reject with ADR-0041 veto-only; no upgrade of seam reject; projection/diagnostics only unless the runtime readiness consumer applies the field. |
| `runtime_readiness_consumer` | Implemented behind `ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED=true` plus the same upstream flags; applies veto-only overlay to player-bundle `runtime_session_ready` / `can_execute` from `readiness_aggregation_decision`; does not mutate `validation_outcome` or commit. |
| `scoped_primary_authority` | Not implemented. |
| `full runtime authority` | Not implemented and explicitly long-term. |

### Future patch map

| Element | Guidance |
|---------|----------|
| Minimal insertion | Keep the existing `runtime_aspect_ledger.build_runtime_intelligence_projection` sidecar branch; do not add a second commitment path. |
| Feature flags | Preserve `ADR0041_VALIDATOR_DISPATCH_MODE` and `ADR0041_SCOPED_CO_AUTHORITY_ENABLED`; missing/invalid values fail closed. |
| Registry source | Explicit runtime-provided mapping **or** static opt-in builder — **never** implicit empty-as-success |
| Fallback | No registry → dry-run projection identical to today |
| Judges | Remain disallow-listed; registry builders unchanged |
| Tests | `test_runtime_aspect_ledger`, bridge tests, harness tests, LangGraph contract tests if touching executor |
| Risks | Drift between seam validators and ADR-0041 adapter set |
| Rollback | Flags default off; remove the co-authority decision copy without touching `run_validation_seam` |

### World-engine pytest convention

Several suites import `app.*` and expect **`world-engine/` on `sys.path`**.

```bash
cd world-engine
python -m pytest tests/test_story_runtime_aspect_ledger.py tests/test_adr0041_validator_dispatch_harness.py -q
```

Running the same paths **from the repository root** often yields `ModuleNotFoundError: No module named 'app'` — this is an **environment/cwd convention**, not an implementation regression.

## Problem Solved

The Capability Matrix is broad by design. It records what capabilities exist,
what maturity they have, what ADR owns them, and what evidence is required.
The runtime still needs a cheaper, situation-aware way to decide which
capabilities matter for one turn.

Capability selection reduces cost by:

- avoiding prompt assembly for irrelevant capabilities;
- running validators only for selected `enforce` capabilities;
- keeping cheap diagnostics separate from commit gates;
- preventing heavy forecasts and LLM-as-a-Judge calls on ordinary turns;
- making selection reasons auditable in RuntimeAspectLedger, MCP, and
  Langfuse analysis.

Capability selection does not prove implementation, correctness, or live
success. It only explains the current turn's capability budget and activation
choices.

## What It Does Not Solve

Capability selection does not replace capability implementation, runtime
contracts, validators, RuntimeAspectLedger projection, MCP/Langfuse evidence,
or Capability Matrix promotion rules. It does not guarantee that an enforced
capability realized correctly. It does not make local evidence live/staging
proof. It does not allow Pi / Π labels to become runtime identifiers.

## Over-Validation and Under-Selection Controls

The selector avoids over-validating by running validators only for selected
`enforce` capabilities and by keeping `observe` diagnostics non-blocking. It
avoids under-selecting by using explicit situation signals, reason codes,
fallback recovery defaults, and audit checks for missing capability evidence on
failed, degraded, or recovered turns.

## Runtime Placement

Target architecture:

```text
Runtime / LangGraph Turn State
        ->
Situation Classifier
        ->
Semantic Capability Selector
        ->
Turn-Class Capability Plan
        ->
Validator Router
        ->
Deterministic Local Validators
        ->
Authority Bridge vs. run_validation_seam
        ->
Scoped Runtime Authority Decision
        ->
Readiness / Commit Policy (later and bounded)
```

The authority layer should sit after scene/runtime context is known and before
any future readiness or commit policy handoff. It must be deterministic-first.
LLM-based selection or judging is a fallback for ambiguous or high-stakes
situations, not the normal path.

## Input Signals

Initial signal vocabulary:

```yaml
turn_kind:
  - opening
  - player_input
  - npc_turn
  - narrator_bridge
  - recovery
  - system_transition
active_actor:
  - narrator
  - player
  - npc
  - system
player_input_present: boolean
npc_decision_required: boolean
action_resolution_required: boolean
visible_projection_required: boolean
interpersonal_pressure: none | low | medium | high
scene_phase: opening | escalation | confrontation | aftermath | recovery
last_turn_quality: healthy | degraded | fallback
canonical_scene_seed: boolean
non_lexical_input_present: boolean
knowledge_gap_present: boolean
world_state_change_requested: boolean
```

This is the current local selector vocabulary. Later runtime integrations may
refine it as contracts land, but new signal names must remain semantic and
ADR-0039 compliant.

## Output Shape

Current local selector output is JSON-safe and ledger-friendly. It is emitted by
`CapabilitySelectionResult.to_runtime_aspect_projection()` as local-only
evidence. Abbreviated opening-scene example:

```json
{
  "capability_selection": {
    "schema_version": "capability_selection.v1",
    "turn_kind": "opening",
    "active_actor": "narrator",
    "selected": [
      "narrator_authority",
      "scene_energy",
      "environment_state",
      "information_disclosure",
      "voice_consistency"
    ],
    "observed_only": [
      "thematic_tracking",
      "callback_web",
      "sensory_context",
      "genre_awareness"
    ],
    "judged": [],
    "excluded": [
      "npc_agency",
      "player_intent_inference",
      "action_resolution",
      "broad_nlu_listening",
      "conversational_memory",
      "prompt_authority",
      "consequence_cascade",
      "long_horizon_forecast",
      "silence_negative_space",
      "dramatic_irony"
    ],
    "activation_modes": {
      "narrator_authority": "enforce",
      "scene_energy": "enforce",
      "environment_state": "enforce",
      "information_disclosure": "enforce",
      "voice_consistency": "enforce",
      "thematic_tracking": "observe",
      "callback_web": "observe",
      "sensory_context": "observe",
      "genre_awareness": "observe",
      "npc_agency": "off",
      "broad_nlu_listening": "off",
      "conversational_memory": "off",
      "prompt_authority": "off",
      "action_resolution": "off"
    },
    "budget": {
      "max_enforced": 5,
      "llm_judges_allowed": false,
      "heavy_forecast_allowed": false
    },
    "reason": "Opening scene with narrator-only authority and no player action.",
    "warnings": [
      "llm_judges_disabled_by_budget",
      "heavy_forecast_disabled_by_budget"
    ],
    "evidence_scope": "local_runtime_selection",
    "proof_level": "local_only",
    "live_or_staging_evidence": false
  }
}
```

The concrete projection also records `warnings`, `implementation_proof=false`,
`implemented_by_runtime=false`, `live_verified=false`, `staging_verified=false`,
`provider_verified=false`, and `capability_promoted=false`. Future extensions
must remain semantic-name-only and preserve ADR-0039 boundaries.

## Activation Modes

| Mode | Meaning | Runtime authority | Commit blocking |
|------|---------|-------------------|-----------------|
| `off` | Intentionally excluded for this turn | none | no |
| `observe` | Cheap diagnostics or ledger observation; may be model-visible only through an explicitly documented non-gating prompt envelope | no control-flow authority | no, unless later ADR promotes it |
| `enforce` | Affects prompt/runtime/validation/readiness | yes | may block according to capability contract |
| `judge` | Heavy LLM-as-a-Judge or external evaluator allowed | qualitative/evaluation only | not by itself; must tie to deterministic gate or promotion rule |

`judge` is not a default mode. It is a budgeted evaluator permission layered
on top of the selected capability set.

## Cost Budgets

Initial defaults:

```yaml
opening_scene:
  max_enforced_capabilities: 5
  allow_llm_judges: false
  allow_heavy_forecast: false

normal_player_turn:
  max_enforced_capabilities: 6
  allow_llm_judges: conditional
  allow_heavy_forecast: false

npc_conflict_turn:
  max_enforced_capabilities: 7
  allow_llm_judges: conditional
  allow_heavy_forecast: conditional

high_stakes_turn:
  max_enforced_capabilities: 8
  allow_llm_judges: true
  allow_heavy_forecast: conditional

fallback_recovery:
  max_enforced_capabilities: 3
  allow_llm_judges: false
  allow_heavy_forecast: false
```

These numbers are initial defaults, not proven operating limits. Further
runtime integration should collect cost and quality evidence before tuning them.

## Opening Scene Design

Opening signal:

```yaml
turn_kind: opening
active_actor: narrator
player_input_present: false
npc_decision_required: false
scene_visibility_required: true
canonical_scene_seed: true
```

Expected selector result:

```yaml
enforce:
  - narrator_authority
  - scene_energy
  - environment_state
  - information_disclosure
  - voice_consistency
observe:
  - thematic_tracking
  - callback_web
  - sensory_context
off:
  - npc_agency
  - player_intent_inference
  - action_resolution
  - consequence_cascade
  - long_horizon_forecast
  - silence_negative_space
  - dramatic_irony
```

Important boundary: `sensory_context` in opening-scene selection remains
diagnostic/local-only unless an owning ADR, focused tests, world-engine
projection evidence, and live/staging proof support a stronger claim. Selection
does not promote it.

## Player, NPC, and Recovery Turns

`normal_player_turn` should usually enforce player input interpretation,
action resolution when required, narrator authority, environment state,
information disclosure, and voice/visible projection contracts. NPC agency,
consequence cascade, and long-horizon forecast remain conditional.

If a player turn carries NPC-response evidence (`npc_decision_required=true` or
an existing `npc_agency` ledger aspect), the selector keeps the turn classified
as `player_input` and keeps `active_actor=player`. The NPC evidence activates
`npc_agency` alongside player intent/action capabilities; it is not authority to
reinterpret the turn as an NPC turn.

`npc_conflict_turn` may enforce NPC agency when an NPC decision is required and
interpersonal pressure is medium or high. It may also enforce social pressure,
voice consistency, information disclosure, and dramatic irony when a knowledge
gap is present.

`fallback_recovery` should keep the enforced set small. It should prioritize
playability, narrator authority, validation/commit clarity, and visible
projection. Heavy judges and forecasts stay off.

## Validator and Judge Selection

Validator rules:

- Run validators for `enforce` capabilities only.
- Run cheap diagnostics for `observe` capabilities where useful.
- Do not run validators or judges for `off` capabilities.
- Record skipped validators as intentionally skipped when useful for audit.

Judge rules:

- LLM-as-a-Judge may run only when local validation is ambiguous, the turn is
  high-stakes, live/staging evaluation is explicitly requested, a capability
  promotion gate requires it, or a regression investigation requires it.
- Opening scenes should not use heavy judges by default.
- Judge output is qualitative unless a deterministic gate or promotion rule
  gives it a specific role.

## RuntimeAspectLedger Projection

The current local projection uses semantic names:

```json
{
  "capability_selection": {
    "turn_kind": "opening",
    "active_actor": "narrator",
    "selected": [
      "narrator_authority",
      "scene_energy",
      "environment_state",
      "information_disclosure",
      "voice_consistency"
    ],
    "observed_only": [
      "thematic_tracking",
      "callback_web",
      "sensory_context",
      "genre_awareness"
    ],
    "excluded": [
      "npc_agency",
      "player_intent_inference",
      "action_resolution",
      "broad_nlu_listening",
      "conversational_memory",
      "prompt_authority",
      "consequence_cascade",
      "long_horizon_forecast",
      "silence_negative_space",
      "dramatic_irony"
    ],
    "budget": {
      "max_enforced": 5,
      "llm_judges_allowed": false
    },
    "reason": "Opening scene with narrator-only authority and no player action."
  }
}
```

For the implemented player-turn/NPC-agency edge, the local projection keeps the
same player authority boundary:

```json
{
  "capability_selection": {
    "turn_kind": "player_input",
    "active_actor": "player",
    "selected": [
      "player_intent_inference",
      "action_resolution",
      "npc_agency"
    ],
    "evidence_scope": "local_runtime_selection",
    "proof_level": "local_only",
    "live_or_staging_evidence": false
  }
}
```

Local ledger evidence is not live/staging proof. MCP and Langfuse should display
the scope of selection evidence and use it to debug over-selection,
under-selection, and false-green claims.

## Manifest Sketch

Future declarative manifest shape:

```yaml
capabilities:
  narrator_authority:
    cost_tier: low
    default_mode: observe
    activate_when:
      - turn_kind: opening
      - active_actor: narrator
      - visible_projection_required: true
    excludes:
      - npc_agency
      - action_resolution
    evidence:
      ledger_aspect: narrator_authority
      langfuse_score: narrator_authority_contract_pass

  npc_agency:
    cost_tier: medium
    default_mode: off
    activate_when:
      - active_actor: npc
      - npc_decision_required: true
      - interpersonal_pressure: medium_or_high
    exclude_when:
      - turn_kind: opening
      - active_actor: narrator
    evidence:
      ledger_aspect: npc_agency
      langfuse_score: npc_agency_contract_pass

  consequence_cascade:
    cost_tier: high
    default_mode: off
    activate_when:
      - world_state_change_requested: true
      - action_resolution_required: true
    evidence:
      ledger_aspect: consequence_cascade
```

Manifest keys must be semantic names. Pi / Π labels may appear only in
documentation comments or matrix cross-reference tables, never as active
runtime keys.

## MCP and Langfuse Interpretation

MCP and Langfuse diagnostics should report:

- selected, observed-only, and excluded capabilities;
- activation mode per capability;
- budget used and budget limit;
- validator and judge allowlists;
- skipped validators and skipped judges;
- reason codes;
- evidence scope and environment.

They must not report selection as live success. A selected capability still
needs runtime execution, validation evidence, and live/staging proof before any
live claim.

## Implementation Progress and Remaining Work

Implemented locally:

1. Selector data contract: situation signals, activation modes, budget fields,
   reason strings, warnings, and evidence shape.
2. Deterministic situation classification for opening, player, NPC, recovery,
   system, and high-stakes-style budgeted turns.
3. Deterministic selection for opening, player, NPC conflict, high-stakes, and
   recovery situations.
4. RuntimeAspectLedger runtime intelligence projection for
   `capability_selection`.
5. ADR-0039-compliant tests over structured selector and ledger evidence,
   including the player-turn/NPC-agency boundary.
6. Bounded Π34 active-listening prompt envelope and ledger projection for
   `broad_nlu_listening`, `conversational_memory`, and `prompt_authority`.

Still pending / governed:

1. A declarative selector manifest, if the implementation moves beyond the
   current Python registry constants.
2. Additional world-engine prompt/runtime assembly authority beyond the bounded
   Π34 envelope.
3. Production selected-validator gating beyond opt-in local plan-enforced
   sidecar behavior.
4. LLM-as-a-Judge execution from budgeted judge metadata.
5. Live/staging Langfuse and MCP proof for any Capability Matrix promotion.

## Future Audit Checklist

Auditors should verify:

- selector uses semantic names only;
- no active Pi / Π keys are introduced;
- selected capabilities are visible in ledger evidence;
- selected validators match selected `enforce` capabilities;
- excluded capabilities do not run unnecessary validators;
- judge mode is not used by default;
- opening scene remains narrator-focused and cost-bounded;
- local evidence is not treated as live/staging evidence;
- Capability Matrix statuses are not promoted from selection alone;
- MCP/Langfuse evidence includes scope and environment metadata.
