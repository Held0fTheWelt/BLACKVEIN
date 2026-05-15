# Capability Selection Runtime Design

Last updated: 2026-05-15

This document is the implementation-readiness companion for
[ADR-0041: Semantic Capability Selection and Runtime Capability Budgeting](../ADR/adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md).
It is implementation guidance for the local selector core and future runtime
integration. It does not change world-engine runtime behavior, promote
Capability Matrix status, or create live/staging proof.

## Implementation Status

The first local deterministic selector core now exists in
`ai_stack/capability_selector.py`, with focused tests in
`ai_stack/tests/test_capability_selector.py`.

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
`ai_stack/capability_validator_dispatch.py`. Default mode is `dry_run`: it
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

A semantic validator registry inventory now exists in
`docs/MVPs/capability_validator_registry_inventory.md` with code-backed rows in
`ai_stack/capability_validator_registry.py`. `build_default_semantic_validator_registry()`
returns an empty map; `build_available_semantic_validator_registry()` exposes thin
adapters only for inventory rows marked `safe_for_local_plan_enforced`.
`build_player_turn_enforced_semantic_validator_registry()` covers the normal
player-turn enforced set when opt-in plan-enforced dispatch is used in tests.
`build_npc_conflict_enforced_semantic_validator_registry()` covers the NPC
conflict-turn enforced set the same way.

Turn-class coverage (drift guard, no runtime wiring): `TURN_CLASS_ENFORCED_VALIDATORS`,
`get_turn_class_enforced_validators`, `get_registry_coverage_for_turn_class`, and
`assert_turn_class_registry_coverage` in `ai_stack/capability_validator_registry.py`
with tests in `ai_stack/tests/test_capability_validator_turn_class_coverage.py`.
For each of `opening_scene`, `normal_player_turn`, and `npc_conflict_turn`, local-only
registry builders are expected to register every enforced validator ID; observer
diagnostics remain non-blocking and must not appear in enforced sets.

World-engine **test harness only**: ``build_adr0041_validator_dispatch_harness_report``
(``ai_stack/runtime_aspect_ledger.py``) enables plan-enforced local validator execution when tests pass
``harness_allow_plan_enforced_local_dispatch=True`` and an explicit registry; ledger normalization does not
invoke it. Evidence: ``world-engine/tests/test_adr0041_validator_dispatch_harness.py``.

Current boundaries:

- Not wired into world-engine prompt assembly.
- Not wired into selected validator execution or gating.
- Not wired into judge execution.
- Not wired into Langfuse/MCP live or staging proof.
- Not Capability Matrix promotion evidence.

## ADR-0041 Production Orchestration Readiness (audit 2026-05-15)

**Verdict:** Production wiring for plan-aware dispatch is **not** ready; **do not**
enable `plan_enforced` in live LangGraph/world-engine paths until an explicit ADR
slice defines gate policy, registry sourcing, and rollback. **Do not begin implementation yet**
— use only the patch map below.

### Current state

- **Default path:** `normalize_runtime_aspect_ledger` → `build_runtime_intelligence_projection` →
  `build_semantic_validator_dispatch_report_projection` → **always `dry_run`**,
  `actually_executed=[]`, `commit_gate_changed=false`, local-only proof flags.
- **Harness path:** `build_adr0041_validator_dispatch_harness_report` — tests only; **not** invoked from ledger normalization.
- **Semantic naming / Pi:** Validator IDs remain semantic contract names; **no `actually_detected`** symbol exists in the repo (canonical field is **`actually_executed`**).

### Runtime validation flow map (discovered paths)

| Path | Symbol / anchor | What it does | When | Blocking vs narrative | Commit / readiness | LLM/Judge | Classification |
|------|-------------------|--------------|------|------------------------|-------------------|-----------|----------------|
| GoC validation seam | `ai_stack/goc_turn_seams.py::run_validation_seam` | Proposal validation (`validation_outcome`): actor lane, dramatic-effect gate, GoC rules | After generation proposal, before commit | **Blocking** for rejected outcomes | **Drives** retry/degraded path via executor + aspect ledger | No judge by default in seam | **must_not_be_plan_routed** (canonical commitment seam — ADR-0041 dispatch must not replace this without governance) |
| LangGraph validation node | `ai_stack/langgraph_runtime_executor.py` — `_run_validation` closure calling `run_validation_seam`; `_build_runtime_aspect_validation`; retry loop `decide_playability_recovery` | Packages seam outcome into `validation_outcome`, aspect ledger aspects, per-contract validation dicts on graph state | During graph execution on turn | **Blocking** / degraded leniency | **Indirectly** affects commit via `validation_outcome` + ledger | Optional provider generation upstream; seam local | **must_not_be_plan_routed** without separate ADR |
| Aspect ledger normalization | `ai_stack/runtime_aspect_ledger.py::normalize_runtime_aspect_ledger` → `build_runtime_intelligence_projection` | Adds **`runtime_intelligence_projection`** (capability selection, validator plan, **dry-run** dispatch report) | On ledger normalize | **Non-blocking** for gameplay (projection) | **Does not** change commit/readiness | No | **dry_run_projection_only** + **safe_candidate_for_future_plan_enforced** (attach *additional* evidence only) |
| ADR-0041 harness | `ai_stack/runtime_aspect_ledger.py::build_adr0041_validator_dispatch_harness_report` | Optional plan-enforced execution in tests | Explicit test call only | Test-scoped | No | No | **dry_run_projection_only** (production) / harness-only execution |
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

### Option analysis (next phases)

**Option A — Projection-only remains default (recommended near-term)**

- Benefits: Zero gameplay risk; aligns with current architecture; Table-B / ADR-0039 friendly.
- Risks: Dispatch stays non-authoritative; operators may confuse projection with enforcement.
- Tests: Extend `ai_stack/tests/test_runtime_aspect_ledger.py` if projection shape grows.
- ADR-0039: Continue semantic IDs only; no Pi keys.
- ADR-0041: Completes “explainability” layer only.
- **Implement next:** Yes — **only** enriched projection or sibling diagnostic payload under explicit flag.

**Option B — Feature-flagged local execution, no gate effects**

- Benefits: Real adapter execution in production graph with observable traces; still no commit coupling.
- Risks: Latency, double-validation conceptual drift vs `run_validation_seam`, operational confusion.
- Tests: LangGraph integration tests + world-engine smoke from `world-engine/` cwd; assert `validation_outcome` unchanged when flag off.
- ADR-0039: Same; add assertions judges never run.
- ADR-0041: Moves from “plan” to “observe executed adapters.”
- **Implement next:** Only **after** Option A policy text + flag/registry ownership decided.

**Option C — Execution + gate-readiness preview (still no gate mutation)**

- Benefits: Rehearses future governance without changing commits.
- Risks: Two sources of “truth” (`validation_outcome` vs preview) — documentation burden.
- Tests: Snapshot tests for preview dict; property: preview disagreeing with seam does **not** fail turn.
- **Implement next:** After Option B proves stable.

### Recommended next narrow step

Document and implement **Option A only**: add an explicit env/feature flag that toggles **additional**
projection payload (or sibling key) populated via the **same** registry builders used in tests,
with **default off** and **fail-closed** to current dry-run shape. **Do not** call harness from
`normalize_runtime_aspect_ledger` until named ADR acceptance.

### Future patch map (do not implement yet)

| Element | Guidance |
|---------|----------|
| Minimal insertion | `runtime_aspect_ledger.build_runtime_intelligence_projection` → conditional branch around semantic dispatch (~726–728) **or** diagnostics-only merge |
| Feature flag | New explicit flag (e.g. `ADR0041_SEMANTIC_DISPATCH_EXECUTION_IN_LEDGER`) **plus** existing dispatch mode resolution; **missing/invalid → dry_run** |
| Registry source | Explicit runtime-provided mapping **or** static opt-in builder — **never** implicit empty-as-success |
| Fallback | No registry → dry-run projection identical to today |
| Judges | Remain disallow-listed; registry builders unchanged |
| Tests | `test_runtime_aspect_ledger`, harness tests, new LangGraph contract test if touching executor |
| Risks | Drift between seam validators and ADR-0041 adapter set |
| Rollback | Flag default off; delete branch |

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
Runtime Context / Scene Director
        ->
Situation Classifier
        ->
Capability Selector
        ->
Capability Budgeter
        ->
Prompt / Runtime Assembly
        ->
Runtime Execution
        ->
Selected Validators / Judges
        ->
RuntimeAspectLedger Projection
        ->
Langfuse / MCP / Operator Evidence
```

The selector should sit after scene/runtime context is known and before prompt
or runtime assembly. It must be deterministic-first. LLM-based selection is a
fallback for ambiguous or high-stakes situations, not the normal path.

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

This is an initial vocabulary. Implementers should refine it as contracts land,
but new signal names must remain semantic and ADR-0039 compliant.

## Output Shape

Future selector output should be JSON-safe and ledger-friendly:

```json
{
  "turn_kind": "opening",
  "active_actor": "narrator",
  "modes": {
    "narrator_authority": "enforce",
    "scene_energy": "enforce",
    "environment_state": "enforce",
    "information_disclosure": "enforce",
    "voice_consistency": "enforce",
    "thematic_tracking": "observe",
    "callback_web": "observe",
    "sensory_context": "observe",
    "npc_agency": "off",
    "action_resolution": "off"
  },
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
    "sensory_context"
  ],
  "excluded": [
    "npc_agency",
    "action_resolution",
    "consequence_cascade",
    "long_horizon_forecast"
  ],
  "budget": {
    "max_enforced": 5,
    "llm_judges_allowed": false,
    "heavy_forecast_allowed": false
  },
  "judge_allowlist": [],
  "validator_allowlist": [
    "narrator_authority",
    "scene_energy",
    "environment_state",
    "information_disclosure",
    "voice_consistency"
  ],
  "reason_codes": [
    "opening_turn",
    "narrator_only_authority",
    "no_player_input",
    "no_npc_decision"
  ],
  "evidence_scope": "local_selection",
  "live_or_staging_evidence": false
}
```

The exact schema belongs to a later implementation ADR or code change.

## Activation Modes

| Mode | Meaning | Runtime authority | Commit blocking |
|------|---------|-------------------|-----------------|
| `off` | Intentionally excluded for this turn | none | no |
| `observe` | Cheap diagnostics or ledger observation | none | no, unless later ADR promotes it |
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

These numbers are initial defaults, not proven operating limits. Future
implementation should collect cost and quality evidence before tuning them.

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

Future projection should use semantic names:

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
      "sensory_context"
    ],
    "excluded": [
      "npc_agency",
      "action_resolution",
      "consequence_cascade",
      "long_horizon_forecast"
    ],
    "budget": {
      "max_enforced": 5,
      "llm_judges_allowed": false
    },
    "reason": "Opening scene with narrator-only authority and no player action."
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
needs execution, validation, RuntimeAspectLedger projection, and live/staging
evidence before any live claim.

## Future Implementation Plan

1. Write a selector schema and fixture examples.
2. Create a semantic-name manifest with ADR-0039 guardrails.
3. Implement deterministic situation classification.
4. Implement selection for opening, player, NPC conflict, high-stakes, and
   recovery turns.
5. Wire selected `enforce` capabilities into runtime/prompt assembly.
6. Gate validators by selected `enforce` capabilities.
7. Gate LLM-as-a-Judge by budget and reason.
8. Project selection evidence into RuntimeAspectLedger.
9. Add MCP/Langfuse scoped diagnostics.
10. Add tests only after implementation begins.

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
