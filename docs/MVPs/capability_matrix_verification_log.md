# Capability Matrix verification log

Last updated: 2026-05-16

This log preserves dated local verification history for the Capability Matrix. It is evidence input, not the current truth map. The current status, ADR relation, semantic names, and maturity summary live in [capability_matrix_status_and_adr_relations.md](capability_matrix_status_and_adr_relations.md). Live/staging claim requirements live in [capability_matrix_live_claim_gates.md](capability_matrix_live_claim_gates.md).

When adding a verification run, include the command, Git SHA or branch if available, environment scope, notable limitations, and whether the evidence is local-only, staging, live-provider, Langfuse, MCP, or mixed. Do not paste secrets. Do not treat local PASS output as live-provider proof.

If a future run records ADR-0041 capability-selection evidence, mark it as selection/diagnostic evidence unless the run also includes runtime execution, validator results, RuntimeAspectLedger projection, and explicit live/staging/provider/Langfuse/MCP proof. A selector PASS, selected capability list, or local ledger row is not live proof by itself.

Historical entries may include machine-local absolute paths because they preserve the command transcript from that workstation. Treat those paths as local environment evidence only, not as portable instructions or live/staging proof. New entries should prefer repo-relative commands, `REPO_ROOT`, or `$PWD`-relative invocation notes whenever practical.

## ADR-0039 runtime surface governance (companion)

[adr0039_runtime_surface_governance_inventory.md](adr0039_runtime_surface_governance_inventory.md) lists **runtime decision surfaces** under [ADR-0039](../ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md): **`ai_stack`**, **`world-engine`**, **`story_runtime_core`**, the **frontend Play Shell**, the **`administration-tool`** operator UI/proxy, **session**, **turn**, **beat / runtime progression** loops, and **critical decision trees** inside those loops. Each row records an `authority_level` (`canonical`, `co_authority`, `preview`, `sidecar`, `diagnostic`, `display_only`).

**Entries in this log must not** treat **preview**, **sidecar**, **diagnostic**, or **display_only** surfaces as canonical runtime authority, seam/commit truth, or live/staging proof. **Frontend / Play Shell** traces are **display / consumption** evidence only—not engine truth unless the same entry ties them to **canonical backend / world-engine** state and documents how. **`administration-tool`** dashboards and proxy responses are **operator display and control-plane** evidence only—the same correlation rules apply. **`story_runtime_core`** inventory rows are **preview** or **diagnostic** unless the run explicitly shows outcomes **committed through canonical runtime mechanisms** (world-engine turn path, validation seam, commit). This file does **not** promote any matrix row and must **not** imply live/staging success without meeting [capability_matrix_live_claim_gates.md](capability_matrix_live_claim_gates.md).

## Local verification snapshot for Π43 / cost-token-provider budgeting observability

- Date: 2026-05-16
- Git SHA at verification time: `6bf83213`
- Scope: **local pytest/static-gate/runtime-path evidence only** - no live-provider, staging, live Langfuse, MCP live-query proof, tenant billing authority, or Capability Matrix promotion claim.
- `python -m py_compile backend/app/services/game/game_service.py` -> passed
- `python -m py_compile world-engine/app/story_runtime/manager.py world-engine/app/observability/langfuse_adapter.py` -> passed
- `python -m py_compile world-engine/tests/test_langfuse_adapter_payload.py world-engine/tests/test_mvp4_diagnostics_integration.py backend/tests/test_game_service_play_http.py` -> passed
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows pytest tests/test_langfuse_adapter_payload.py -q` from `world-engine/` -> 24 passed
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows pytest tests/test_mvp4_diagnostics_integration.py -q` from `world-engine/` -> 15 passed
- `PYTHONPATH=/mnt/d/WorldOfShadows/backend:/mnt/d/WorldOfShadows pytest backend/tests/test_game_service_play_http.py -q` -> 19 passed
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows pytest tests/gates/test_goc_mvp04_observability_diagnostics_gate.py -q` -> 49 passed
- `PYTHONPATH=/mnt/d/WorldOfShadows/backend:/mnt/d/WorldOfShadows pytest backend/tests/test_operational_governance_mvp.py::test_cost_budget_and_usage_endpoints backend/tests/test_operational_governance_mvp.py::test_mvp4_session_summary_exposes_live_cost_budget_and_overrides -q` -> 2 passed
- `PYTHONPATH=/mnt/d/WorldOfShadows pytest tests/gates/test_adr_0039_pi_scope.py -q --tb=short` -> 7 passed

Evidence summary: Π43 remains a bounded local observability/control-plane slice.
World-engine now exposes the Langfuse adapter methods required by shared
ADR-0041/local evidence helpers, records nested observations and semantic scores
as `proof_level=local_only`, and keeps Langfuse as an export surface rather than
the cost source of truth. `StoryRuntimeManager` adds a semantic
`model_generation` phase-cost record from provider adapter metadata when
provider usage is present, marks real provider calls without usage as
`billing_mode=unavailable`, and continues to aggregate canonical
`graph_state["phase_costs"]` into diagnostics. Backend story session / turn calls
now check governed cost hard-stop budgets and runtime token-budget exhaustion
before contacting world-engine.

ADR-0039 discipline for this slice: runtime-facing keys are semantic
(`model_generation`, `phase_costs`, `story_turn`, local proof fields). Tests
assert contract fields, adapter API parity, provider-usage provenance,
aggregation invariants, and hard-stop behavior. They do not use Pi / Π labels as
runtime keys or pass/fail oracles, and local PASS output is not live/staging or
provider proof.

Known limitations: no live provider trace was executed for this snapshot; no
staging Langfuse query or MCP live-query proof is recorded; provider-specific
pre-turn budget matching is limited by the provider information available before
a turn request; tenant billing authority and full cross-tenant spend governance
remain outside this local verification.

---

## Local verification snapshot for ADR-0041 / semantic capability selector core

Latest local verification for the first deterministic selector core:

- `python -m pytest ai_stack/tests/test_capability_selector.py -q` -> 12 passed.
- `python -m pytest tests/gates/test_adr_0039_pi_scope.py -q` -> 7 passed.
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q` -> 11 passed.

Scope: local unit/governance verification only. `live_or_staging_evidence=false`.

Evidence summary: `ai_stack/capabilities/capability_selector.py` implements ADR-0041 local semantic selection, budget caps, activation modes, and RuntimeAspectLedger-compatible local evidence projection. It is not wired into world-engine prompt assembly, selected validator execution, judge execution, Langfuse/MCP live proof, or Capability Matrix promotion.

ADR-0039 discipline: selector code uses semantic capability names only; focused tests assert legacy Pi-style selector keys are rejected and that projection evidence is local-only, not implementation or live/staging proof.

Legacy quarantine (2026-05-15): `ai_stack/story_runtime/legacy_actor_lane_hydration.py` is documented in the Table-B gate as GoC-only compatibility debt; policy floor reads use `module_runtime_policy.minimum_actor_response_count_from_governance` so the shim does not carry `scene_energy` literals.

ADR-0041 plan-enforced dispatch (2026-05-15): local tests only (`test_capability_validator_dispatch_plan_enforced.py`, `test_capability_validator_dispatch_feature_flag.py`); `default_mode=dry_run`; `live_or_staging_evidence=false`; production projection unchanged unless `ADR0041_VALIDATOR_DISPATCH_MODE=plan_enforced` is explicitly set.

ADR-0041 validator registry inventory (2026-05-15): `docs/MVPs/capability_validator_registry_inventory.md`, `ai_stack/capabilities/capability_validator_registry.py`; default registry empty; `live_or_staging_evidence=false`; no Capability Matrix promotion.

ADR-0041 world-engine harness (2026-05-15): `build_adr0041_validator_dispatch_harness_report`; tests under `world-engine/tests/`; run pytest from `world-engine/` so `app` resolves; `live_or_staging_evidence=false`; default ledger projection unchanged (`dry_run`).

ADR-0041 opt-in plan projection sibling (2026-05-15): `ADR0041_PLAN_PROJECTION_ENABLED` adds `runtime_intelligence_projection.adr0041_plan_projection` only; `validator_dispatch_report` stays default `dry_run` with `actually_executed=[]`; evidence remains projection-only (no `run_validation_seam` / validation_outcome changes). Tests: `ai_stack/tests/test_adr0041_plan_projection_evidence.py`, `world-engine/tests/test_adr0041_validator_dispatch_harness.py::test_world_engine_plan_projection_sibling_opt_in`.

ADR-0041 validation authority preview + drift (2026-05-15): with `ADR0041_VALIDATOR_DISPATCH_MODE=plan_enforced` and LangGraph sidecar bundle, `runtime_intelligence_projection.validation_authority_preview` exposes non-commit routing/drift vs seam summary; evidence remains `local_only`; tests `ai_stack/tests/test_adr0041_runtime_graph_sidecar.py`.

ADR-0041 validation authority bridge + seam mirrors (2026-05-15): local pytest `ai_stack/tests/test_validation_authority_bridge.py`, `ai_stack/tests/test_adr0041_runtime_graph_sidecar.py`, `tests/test_capability_matrix_documentation_readiness.py`; `live_or_staging_evidence=false`; docs touch: ADR-0041 seam-mirror / bridge coverage note + this log line only — no runtime, commit/readiness gate, Capability Matrix promotion, or live/staging claim changes in that step.

ADR-0041 bridge partial-transfer readiness (`validation_authority_bridge.v3`, 2026-05-15): bounded `dramatic_effect_gate` / `hard_forbidden_runtime` scopes per turn class; `partial_transfer_ready` requires aligned plan_enforced execution + no `dramatic_effect_mirror_fidelity=partial_defaults` on evidence; `live_or_staging_evidence=false`.

ADR-0041 authority handoff candidate + seam area mapping (2026-05-15): `validation_authority_bridge.v4` adds `seam_concern_coverage`, `seam_area_adr0041_relationship_buckets`, and `authority_handoff_candidate` (shadow-only; `run_validation_seam` still canonical). `PLANNED_ALL_DISPATCH_IDS` includes `SEAM_MIRROR_VALIDATOR_IDS` for inventory parity. Verification: `python -m pytest ai_stack/tests -q` (1868 passed, 1 skipped), gate + matrix docs tests, `cd world-engine && python -m pytest tests/test_adr0041_validator_dispatch_harness.py tests/test_story_runtime_aspect_ledger.py -q`; `live_or_staging_evidence=false`; no Capability Matrix promotion.

ADR-0041 governance wording / Capability Map direction (2026-05-15): documentation-only update in `capability_matrix_status_and_adr_relations.md`, `adr-0041-*.md`, `capability_selection_runtime_design.md` — states ADR-0041 as a **controlled runtime-authority track** with sidecar/projection phases as **safety scaffolding** toward **bounded co-authority**; reiterates no commit/readiness/`validation_outcome` ownership, no live/matrix promotion from local-only proof, ADR-0039 guardrails unchanged.

ADR-0041 production-orchestration readiness audit (2026-05-15): documented flow map and insertion guidance in `docs/MVPs/capability_selection_runtime_design.md` (ADR-0041 Production Orchestration Readiness); **no production orchestration implemented**. Canonical dispatch field: **`actually_executed`** (repo-wide search: no `actually_detected`). World-engine pytest: prefer `cd world-engine && python -m pytest …` to avoid `ModuleNotFoundError: app` when running from repo root.

ADR-0041 scoped co-authority decision preview (2026-05-15): `validation_authority_bridge.v5` adds `opening_event_coverage` to the bounded critical scope and `ADR0041_SCOPED_CO_AUTHORITY_ENABLED=true` may emit `runtime_intelligence_projection.validation_co_authority_decision` only when plan-enforced sidecar execution is `partial_transfer_ready`. Verification: `python -m pytest ai_stack/tests/test_validation_authority_bridge.py ai_stack/tests/test_capability_validator_dispatch_feature_flag.py -q`; `validation_outcome_changed=false`, `commit_gate_changed=false`, `readiness_gate_changed=false`; `run_validation_seam` remains canonical; `live_or_staging_evidence=false`; no Capability Matrix promotion.

ADR-0041 readiness co-authority preview (2026-05-15): `ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED=true` may emit `runtime_intelligence_projection.readiness_co_authority_preview` with machine-readable policy stage (`shadow_only`, `readiness_preview_candidate`, `readiness_preview_allow`, `readiness_preview_block`, `not_eligible`) and bounded blockers/evidence while `affects_commit=false`, `affects_readiness=false`, `validation_outcome_changed=false`, `commit_gate_changed=false`, `readiness_gate_changed=false`. Verification: `python -m pytest ai_stack/tests/test_validation_authority_bridge.py ai_stack/tests/test_adr0041_runtime_graph_sidecar.py ai_stack/tests/test_capability_validator_dispatch_feature_flag.py -q`, `cd world-engine && python -m pytest tests/test_adr0041_validator_dispatch_harness.py -q`; `run_validation_seam` remains canonical; `proof_level=local_only`; no live/staging claim or Capability Matrix promotion.

ADR-0041 scoped readiness enforcement pilot (2026-05-15): `ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED=true` may emit `runtime_intelligence_projection.readiness_co_authority_enforcement` and mirror it as `runtime_intelligence_projection.readiness_policy_input` with `readiness_input=allow|block|no_decision`, bounded scope, blockers/evidence, and explicit pilot-stage flags. Output may serve as a real readiness policy input for governed aggregation, but remains non-mutating (`validation_outcome_changed=false`, `commit_gate_changed=false`, `readiness_gate_changed=false`, `affects_commit=false`, `affects_readiness=false`, `proof_level=local_only`, `live_or_staging_evidence=false`). Verification: `python -m pytest ai_stack/tests -q`, table-B/ADR-0039 gates, `cd world-engine && python -m pytest tests/test_adr0041_validator_dispatch_harness.py tests/test_story_runtime_aspect_ledger.py -q`; no commit behavior changes; no live/staging claim or Capability Matrix promotion.

ADR-0041 scoped readiness aggregation pilot (2026-05-15): `ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED=true` with scoped co-authority, readiness preview, and enforcement all enabled may emit `runtime_intelligence_projection.readiness_aggregation_decision` (`seam_readiness`, `aggregated_readiness`, `adr0041_veto_applied`, `adr0041_can_upgrade_seam_reject=false`). Seam is canonical for allow/reject; ADR-0041 may veto seam-allowed readiness only under bounded policy; no upgrade of seam reject to allow; no `validation_outcome` or commit mutation. Verification: `ai_stack/tests/test_validation_authority_bridge.py`, `ai_stack/tests/test_adr0041_runtime_graph_sidecar.py`, `ai_stack/tests/test_capability_validator_dispatch_feature_flag.py`.

ADR-0041 runtime readiness consumer contract (2026-05-15): `ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED=true` plus the same upstream flags may apply `readiness_aggregation_decision` as a **veto-only** overlay on `runtime_session_ready` / `can_execute` in `backend/app/api/v1/game_routes.py::_player_session_bundle` via `ai_stack/story_runtime/runtime_readiness_consumer.py::resolve_runtime_readiness_with_adr0041`; default without the flag leaves final readiness byte-compatible with `evaluate_session_opening_readiness`; `validation_outcome` and commit unchanged; `proof_level=local_only`; no live/staging or Capability Matrix promotion. Read-only echoes: `governance.adr0041_readiness_projection_echo`, Inspector `authority_projection.adr0041_readiness_projection_echo`, operator turn-history `adr0041_readiness_projection_echo`. **Single mutating consumer** under `backend/app` enforced by `backend/tests/test_adr0041_readiness_consumer_single_mutation_site.py`. Verification: `ai_stack/tests/test_runtime_readiness_consumer.py`, `backend/tests/test_runtime_readiness_consumer_bundle.py`, `ai_stack/tests/test_capability_validator_dispatch_feature_flag.py`.

ADR-0041 readiness consumer consolidation + operator/inspector echo (2026-05-15): same contract; `pytest` marker `timing_sensitive` for wall-clock API smokes (`backend/pytest.ini`); local default `WOS_API_PERF_BUDGET_MS` headroom raised for non-CI runs in `test_user_profile.py` perf smokes.

---

## Local verification snapshot for Pi31 / narrative momentum runtime aspect

- Date: 2026-05-15
- Git SHA at verification time: `dcfad220` (dirty worktree; local Pi31 documentation/test follow-up changes not committed at run time)
- Scope: **local pytest/static-gate evidence only** - no live-provider, staging, live Langfuse, MCP live-query proof, or ADR-0009 promotion proof claim.
- `python -m py_compile ai_stack/contracts/narrative_momentum_contracts.py ai_stack/story_runtime/narrative/narrative_momentum_engine.py ai_stack/module_runtime_policy.py ai_stack/story_runtime/runtime_aspect_ledger.py ai_stack/langgraph/langgraph_runtime_state.py ai_stack/langgraph/langgraph_runtime_executor.py ai_stack/story_runtime/story_runtime_playability.py world-engine/app/story_runtime/commit_models.py world-engine/app/story_runtime/manager.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py` -> passed
- `python -m pytest ai_stack/tests/test_narrative_momentum_engine.py -q --tb=short` -> 3 passed
- `python -m pytest ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_runtime_aspect_ledger.py ai_stack/tests/test_runtime_authority_aspects.py -q --tb=short` -> 52 passed
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows python -m pytest world-engine/tests/test_planner_truth_and_runtime_surfaces.py -q --tb=short` -> 11 passed
- `python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py -q --tb=short` -> 40 passed
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py tests/test_capability_matrix_documentation_readiness.py -q --tb=short` -> 21 passed

Evidence summary: Pi31 is now represented by the generic
`narrative_momentum` runtime aspect. The module policy normalizes
`runtime_intelligence.narrative_momentum`; LangGraph derives bounded state and
target from scene energy, pacing rhythm, social pressure, expectation
variation, semantic move evidence, and prior planner truth; structured
`narrative_momentum_events` validate progress, allowed transitions, velocity,
stall budget, and source refs; planner truth persists state/target/validation;
`RuntimeAspectLedger.narrative_momentum` projects evidence; and MCP exposes
semantic `narrative_momentum_*` matrix fields.

ADR-0039 discipline for this slice: production-facing keys use semantic
`narrative_momentum` names only. Tests derive expectations from normalized
policy, exported schema/failure-code constants, state-machine transitions,
structured event payloads, planner-truth persistence, ledger projection, MCP
row fields, and the anti-hardcoding surface allowlist. Generated momentum
prose, copied authored examples, and Pi-number score or branch names are not
pass/fail oracles.

Known limitations: this is local implementation evidence only. Fresh staging
traces, provider evidence, player-visible replay, live Langfuse traces, and MCP
live-query proof remain outside this snapshot.

---

## Local verification snapshot for Pi33 / symbolic object resonance

- Date: 2026-05-15
- Git SHA at verification time: `22a4bccb` (dirty worktree; local Pi33 documentation/test follow-up changes not committed at run time)
- Scope: **local pytest/static-gate evidence only** - no live-provider, staging, live Langfuse, MCP live proof, or ADR-0009 promotion proof claim.
- `python -m py_compile ai_stack/contracts/symbolic_object_resonance_contracts.py ai_stack/story_runtime/narrative/symbolic_object_resonance_engine.py ai_stack/module_runtime_policy.py ai_stack/story_runtime/runtime_aspect_ledger.py ai_stack/langgraph/langgraph_runtime_state.py ai_stack/langgraph/langgraph_runtime_executor.py world-engine/app/story_runtime/commit_models.py world-engine/app/story_runtime/manager.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py tests/gates/test_table_b_anti_hardcoding_gate.py` -> passed
- `python -m py_compile ai_stack/tests/test_symbolic_object_resonance_engine.py ai_stack/tests/test_runtime_aspect_ledger.py tools/mcp_server/tests/test_langfuse_verify_tools.py world-engine/tests/test_planner_truth_and_runtime_surfaces.py tests/gates/test_table_b_anti_hardcoding_gate.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py` -> passed
- `PYTHONPATH=/mnt/d/WorldOfShadows pytest ai_stack/tests/test_symbolic_object_resonance_engine.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_runtime_aspect_ledger.py tools/mcp_server/tests/test_langfuse_verify_tools.py tests/gates/test_table_b_anti_hardcoding_gate.py tests/gates/test_adr_0039_pi_scope.py tests/test_capability_matrix_documentation_readiness.py -q --tb=short` -> 94 passed
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows pytest tests/test_planner_truth_and_runtime_surfaces.py -q --tb=short` from `world-engine/` -> 10 passed
- `git diff --check` -> exit 0; repository-local CRLF normalization warnings only

Evidence summary: Pi33 is now represented by the generic
`symbolic_object_resonance` runtime aspect. The module policy normalizes
`runtime_intelligence.symbolic_object_resonance`; LangGraph derives a bounded
state/target from canonical object content and structured runtime state;
structured `symbolic_object_resonance_events` validate selected object ids,
symbol ids, resonance roles, source refs, and budget; planner truth persists
state/target/validation; `RuntimeAspectLedger.symbolic_object_resonance`
projects evidence; and MCP exposes semantic `symbolic_object_resonance_*`
matrix fields.

ADR-0039 discipline for this slice: production-facing keys use semantic
`symbolic_object_resonance` names only. Tests derive expectations from
normalized policy, exported schema/failure-code constants, canonical object
roles, structured event payloads, planner-truth persistence, ledger projection,
MCP row fields, and the anti-hardcoding surface allowlist. Generated symbolic
prose, copied authored examples, and Pi-number score or branch names are not
pass/fail oracles.

Known limitations: this is local implementation evidence only. Fresh staging
traces, provider evidence, player-visible replay, live Langfuse traces, and MCP
live-query proof remain outside this snapshot. Combined repo-root pytest runs
that include both backend-style `app` imports and `world-engine/app` imports
still need split invocation to avoid package-name shadowing; the World-Engine
planner-truth test was therefore verified from `world-engine/`.

---

## Local verification snapshot for Π30 / no-dead-end recovery

- Date: 2026-05-15
- Git SHA at verification time: `ad0b5437` (dirty worktree; local Π30 no-dead-end runtime/documentation changes not committed at run time)
- Scope: **local pytest/static-gate evidence only** — no live-provider, staging, live Langfuse, or MCP live proof claim.
- `PYTHONPATH=. python -m py_compile story_runtime_core/recovery/no_dead_end.py story_runtime_core/recovery/__init__.py story_runtime_core/committed_truth.py story_runtime_core/callbacks/callback_web.py story_runtime_core/consequences/consequence_cascade.py ai_stack/story_runtime/runtime_aspect_ledger.py world-engine/app/story_runtime/manager.py` -> passed
- `PYTHONPATH=. python -m pytest story_runtime_core/tests/test_no_dead_end_recovery.py story_runtime_core/tests/test_callback_web.py story_runtime_core/tests/test_consequence_cascade.py -q -s` -> 28 passed
- `PYTHONPATH=. python -m pytest ai_stack/tests/test_runtime_aspect_ledger.py::test_runtime_aspect_ledger_serializes_stably -q -s` -> 1 passed
- `cd world-engine && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=..:. python -m pytest tests/test_story_runtime_narrative_commit.py::test_illegal_proposal_is_blocked_committed_truth tests/test_story_runtime_narrative_commit.py::test_recoverable_validation_rejection_returns_structured_turn tests/test_story_runtime_narrative_commit.py::test_graph_execution_exception_returns_playable_turn tests/test_story_runtime_narrative_commit.py::test_graph_programming_exception_is_not_persisted_as_playable_turn -q -s` -> 4 passed
- `cd world-engine && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=..:. python -m pytest tests/test_story_runtime_short_path_persist_convergence.py::test_graph_exception_recoverable_matches_canonical_narrator_bundle -q -s` -> 1 passed
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m pytest tests/callbacks/test_callback_web.py tests/consequences/test_consequence_cascade.py -q -s` -> 6 passed
- `PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/test_capability_matrix_documentation_readiness.py tests/gates/test_adr_0039_pi_scope.py -q` -> 11 passed
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q -s` -> 13 passed

Evidence summary: Π30 is implemented locally as the bounded
`no_dead_end_recovery.v1` contract. Player-visible committed and recoverable
turns receive recovery class, obstacle kind, attempt fingerprint, bounded
next-step options, commit policy, validation status, and
`turn_aspect_ledger.no_dead_end_recovery`. Recoverable validation rejections
and expected graph `RuntimeError` failures also expose
`recoverable_playability.v1` with `commits_story_truth=false`; programming and
contract exceptions are not converted into playable story turns; recoverable
or false-commit history rows are filtered before callback-web observations and
consequence-cascade atoms or edges are built.

ADR-0039 discipline for this slice: tests assert schema/status fields,
recovery classes, commit flags, exception class boundaries, stable turn ids,
next-step evidence, callback/cascade record counts, ledger projection, and
anti-hardcoding gate behavior. Generated recovery prose, authored example
language, LLM judge categories, and Pi labels are not pass/fail oracles.

Notable local-environment notes: some World-Engine tests emitted non-fatal
FastEmbed cache and missing `observability_credentials` table warnings during
test startup. These warnings did not fail the local verification and are not
live/staging evidence.

---

## Local verification snapshot for Π28 / temporal-control runtime aspect

- Date: 2026-05-15
- Git SHA at verification time: `5b58ec64` (dirty worktree; local temporal-control implementation not committed at run time)
- Scope: **local pytest/static-gate evidence only** — no live-provider, staging, live Langfuse, or MCP live proof claim.
- `python -m py_compile ai_stack/contracts/temporal_control_contracts.py ai_stack/story_runtime/narrative/temporal_control_engine.py ai_stack/module_runtime_policy.py ai_stack/story_runtime/runtime_aspect_ledger.py ai_stack/langgraph/langgraph_runtime_state.py ai_stack/langgraph/langgraph_runtime_executor.py ai_stack/story_runtime/story_runtime_playability.py world-engine/app/story_runtime/commit_models.py world-engine/app/story_runtime/manager.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py tests/gates/test_table_b_anti_hardcoding_gate.py` -> passed
- `python -m pytest ai_stack/tests/test_temporal_control_engine.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_runtime_aspect_ledger.py tests/gates/test_table_b_anti_hardcoding_gate.py -q` -> 39 passed
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows python -m pytest tests/test_planner_truth_and_runtime_surfaces.py -q` from `world-engine/` -> 10 passed
- `PYTHONPATH=/mnt/d/WorldOfShadows python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py -q` -> 32 passed
- `python -m pytest tests/test_capability_matrix_documentation_readiness.py -q` -> 4 passed
- `git diff --check` -> no whitespace errors; local Git emitted LF/CRLF normalization warnings only

Evidence summary: Π28 is implemented as the generic `temporal_control` runtime
aspect. The runtime normalizes module policy, derives bounded temporal state
and a selected operation from structured scene/runtime evidence, passes only
bounded committed refs into the dramatic generation packet, validates structured
`temporal_control_events`, records `turn_aspect_ledger.temporal_control`,
persists planner-truth fields, rehydrates the latest committed state, and
exposes semantic Langfuse/MCP matrix fields.

ADR-0039 discipline for this slice: tests derive expectations from exported
schema constants, normalized module policy, structured committed turn and
consequence refs, validation failure codes, planner-truth rehydration,
runtime-aspect ledger fields, MCP extraction fields, and the Table-B
anti-hardcoding allowlist. Generated flashback/time-skip prose, branch preview
text, judge chronology labels, and Pi-number score names are not pass/fail
oracles.

Known limitations: this is local implementation and fixture/static verification
only. Fresh staging traces, provider evidence, and end-to-end player-visible
replay remain outside this snapshot.

---

## Local verification snapshot for Π27 / relationship state machine

Latest local verification recorded for the bounded durable relationship-state implementation:

- `claude-context` semantic search was used to re-locate the existing Π27 relationship-dynamics surfaces, ADR-0039 boundaries, runtime aspect patterns, planner-truth persistence seams, Langfuse/MCP extraction, and documentation drift points before the concrete code/test pass.
- `python -m py_compile ai_stack/contracts/relationship_state_contracts.py ai_stack/story_runtime/narrative/relationship_state_engine.py ai_stack/module_runtime_policy.py ai_stack/story_runtime/runtime_aspect_ledger.py ai_stack/langgraph/langgraph_runtime_state.py ai_stack/langgraph/langgraph_runtime_executor.py world-engine/app/story_runtime/commit_models.py world-engine/app/story_runtime/manager.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py ai_stack/tests/test_relationship_state_machine.py ai_stack/tests/test_wave3_multi_actor_vitality.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_runtime_aspect_ledger.py world-engine/tests/test_planner_truth_and_runtime_surfaces.py` -> passed.
- `python -m pytest ai_stack/tests/test_relationship_state_machine.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_runtime_aspect_ledger.py ai_stack/tests/test_wave3_multi_actor_vitality.py -q --tb=short` -> 61 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows:/mnt/d/WorldOfShadows/world-engine python -m pytest world-engine/tests/test_planner_truth_and_runtime_surfaces.py -q --tb=short` -> 8 passed.
- `python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py -q --tb=short` -> 31 passed.
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` -> 11 passed.

This evidence is local-only. It proves the contract/runtime/persistence/ledger/MCP wiring for the bounded relationship-state machine, but it is not live-provider or staging proof.

ADR-0039 discipline for Π27: relationship-state tests derive pass/fail evidence from exported schema-version constants, transition/failure-code vocabularies, normalized module policy, canonical relationship content, structured social-state fields, NPC initiative edges, planner-truth rehydration, and ledger/MCP fields. Fixture strings are stimuli or ids only; no generated relationship prose, authored dialogue example, frontend card shape, or LLM-as-a-Judge relationship label is used as the primary oracle.

---

## Local verification snapshot for Π1-Π13 / ADR-0039 re-audit

Latest local re-audit for the implemented/partial Π1-Π13 rows:

- `claude-context` semantic search was used to re-locate Π1-Π13 status notes, ADR-0039 references, and likely test-oracle surfaces before the concrete `rg`/pytest pass.
- `rg -n "\bpi_(0?[1-9]|1[0-3])\b|Π(1|2|3|4|5|6|7|8|9|10|11|12|13)\b" ai_stack backend/app frontend/app frontend/static frontend/templates story_runtime_core tools/mcp_server world-engine/app -g '!**/tests/**' -g '!**/README.md'` -> no active production-code hits.
- `python -m py_compile ai_stack/quality_lab/trace_interpreter.py tests/gates/test_table_b_anti_hardcoding_gate.py` -> passed.
- `python -m pytest ai_stack/tests/test_quality_lab_trace_interpreter.py -q --tb=short` -> 20 passed.
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` -> 6 passed.
- `python -m pytest ai_stack/tests/test_hierarchical_memory_contracts.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_context_synthesis_engine.py ai_stack/tests/test_context_synthesis_retry_loop.py ai_stack/tests/test_character_voice_runtime_enforcement.py ai_stack/tests/test_scene_energy_engine.py ai_stack/tests/test_narrative_aspect_contracts.py ai_stack/tests/test_god_of_carnage_semantic_move_interpretation.py ai_stack/tests/test_npc_agency_long_horizon_claim_readiness.py ai_stack/tests/test_npc_agency_planner.py ai_stack/tests/test_npc_agency_contracts.py ai_stack/tests/test_langgraph_runtime.py ai_stack/tests/test_rag.py ai_stack/tests/test_story_runtime_playability.py ai_stack/tests/test_runtime_authority_aspects.py tools/mcp_server/tests/test_registry.py tools/mcp_server/tests/test_langfuse_verify_tools.py story_runtime_core/tests/test_input_interpreter.py tests/branching/test_branching_forecast.py tests/branching/test_branching_tree_record.py tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` -> 238 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows python -m pytest world-engine/tests/test_story_runtime_rag_runtime.py world-engine/tests/test_story_runtime_aspect_ledger.py world-engine/tests/test_story_runtime_branching_simulation_tree.py world-engine/tests/test_story_runtime_branching_tree_api.py world-engine/tests/test_branching_tree_store.py world-engine/tests/test_branch_timeline_store.py world-engine/tests/test_runtime_engine.py -q --tb=short` -> 50 passed.

Audit result: no production code currently branches on legacy `pi_1` through `pi_13` / `Π1` through `Π13` control labels. The anti-hardcoding gate now guards all Π1-Π13 legacy control ids, not only the previously covered `pi_11`. Quality Lab trace interpretation now imports the canonical runtime-ledger aspect list (`ASPECT_KEYS`) instead of carrying a parallel local aspect-name oracle.

ADR-0039 discipline by row: Π1 memory assertions target committed-turn policy, snapshot bounds, and raw-payload exclusion; Π2 graph proof targets state/path invariants; Π3 RAG proof targets retrieval/context-pack metadata and governance wiring; Π4 MCP proof targets registry/descriptor/schema contracts; Π5 self-correction proof targets feedback codes and retry diagnostics; Π6 governance proof targets commit/aspect-ledger contracts; Π7 remains partial until `npc_agency_claim_readiness.v1` live evidence; Π8 proof targets branch schema, fingerprints, lifecycle, and bounds; Π9 context synthesis proof targets authority/provenance/gap fields; Π10-Π12 remain policy/schema/aspect driven; Π13 input semantics derive guarded kinds from shared intent contracts and actor hints from canonical alias maps. Literal input phrases in tests are incidental stimuli, not the pass/fail oracle.

---

## Local verification snapshot for Π17 / callback web

Latest local verification recorded for the bounded callback web implementation:

- `python -m py_compile ai_stack/contracts/callback_web_contracts.py ai_stack/langgraph/langgraph_runtime_state.py ai_stack/langgraph/langgraph_runtime_executor.py ai_stack/module_runtime_policy.py ai_stack/story_runtime/runtime_aspect_ledger.py story_runtime_core/callbacks/__init__.py story_runtime_core/callbacks/callback_web.py story_runtime_core/branching/branch_timeline.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py world-engine/app/story_runtime/callback_web_store.py world-engine/app/story_runtime/manager.py world-engine/app/api/http.py world-engine/app/main.py world-engine/app/config.py` -> passed.
- `PYTHONPATH=. python -m pytest ai_stack/tests/test_callback_web_contracts.py ai_stack/tests/test_module_runtime_policy.py -q` -> 12 passed.
- `PYTHONPATH=. python -m pytest ai_stack/tests/test_langgraph_state_schema.py ai_stack/tests/test_runtime_authority_aspects.py -q` -> 38 passed.
- `PYTHONPATH=. python -m pytest tests/callbacks/test_callback_web.py tests/branching/test_branch_timeline.py -q` -> 8 passed.
- `PYTHONPATH=. python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py -q` -> 29 passed.
- `cd world-engine && PYTHONPATH=..:. python -m pytest tests/test_callback_web_store.py tests/test_story_runtime_callback_web.py tests/test_story_runtime_branching_tree_api.py -q` -> 5 passed.
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` -> 6 passed.

ADR-0039 discipline for Π17: callback tests derive pass/fail evidence from exported schema-version constants, edge-kind vocabularies, session/turn ids, branch lifecycle fields, stable ids, and bounded list lengths. Fixture strings are stimuli or ids only; no generated callback prose, branch preview text, or authored example paragraph is used as the primary oracle.

---

## Local verification snapshot for Π21 / consequence cascade

Latest local verification recorded for the bounded consequence cascade implementation:

- `claude-context` semantic search was used to re-locate the Π21 row, new runtime/store/API/ledger surfaces, and ADR-0039 evidence after implementation.
- `python -m py_compile ai_stack/contracts/consequence_cascade_contracts.py story_runtime_core/consequences/consequence_cascade.py story_runtime_core/consequences/__init__.py ai_stack/story_runtime/runtime_aspect_ledger.py ai_stack/module_runtime_policy.py ai_stack/langgraph/langgraph_runtime_state.py ai_stack/langgraph/langgraph_runtime_executor.py world-engine/app/story_runtime/consequence_cascade_store.py world-engine/app/story_runtime/manager.py world-engine/app/api/http.py world-engine/app/main.py world-engine/app/config.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py` -> passed.
- `PYTHONPATH=. python -m pytest ai_stack/tests/test_consequence_cascade_contracts.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_runtime_aspect_ledger.py tests/consequences/test_consequence_cascade.py tests/gates/test_table_b_anti_hardcoding_gate.py -q` -> 30 passed.
- `cd world-engine && PYTHONPATH=..:. python -m pytest tests/test_consequence_cascade_store.py tests/test_story_runtime_consequence_cascade.py tests/test_story_runtime_branching_tree_api.py -q` -> 4 passed.
- `PYTHONPATH=. python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py -q` -> 29 passed.

ADR-0039 discipline for Π21: cascade tests derive pass/fail evidence from exported schema-version constants, edge-kind vocabularies, status vocabularies, normalized policy bounds, authority flags, stable ids, and branch lifecycle fields. Fixture strings are stimuli or ids only; no generated consequence prose, branch preview text, or authored example paragraph is used as the primary oracle.

---

## Local verification snapshot for Π6 / runtime intelligence

Latest local verification recorded for the modular runtime-intelligence work:

- `python -m pytest tests/gates/test_adr_live_runtime_commit_semantics_gate.py tests/gates/test_table_b_anti_hardcoding_gate.py -q` → 10 passed.
- `python -m pytest ai_stack/tests/test_runtime_authority_aspects.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_langgraph_runtime.py ai_stack/tests/test_action_resolution_interact_fallback.py -q` → 38 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows:/mnt/d/WorldOfShadows/world-engine python -m pytest world-engine/tests/test_story_runtime_aspect_ledger.py world-engine/tests/test_live_story_runtime_governance.py world-engine/tests/test_authority_version_and_route_family_truth.py world-engine/tests/test_story_runtime_narrative_commit.py -q` → 50 passed.
- `python tests/run_tests.py --suite story_runtime_core --quick` → 156 passed.
- `python tests/run_tests.py --suite ai_stack --quick` → 1565 passed, 1 skipped.
- `python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py -q` → 29 passed.

The full backend suite was also run during parallel Quality Lab work and finished with 4390 passed, 2 skipped, 3 unrelated 401 failures in forum/M11 observability tests. Treat that result as a moving-worktree snapshot, not as a Π6 blocker.

---

## Local verification snapshot for Π7 / NPC agency long-horizon runtime slice

Latest local verification recorded for the current NPC agency long-horizon, private-plan, closure, operator, and scoring work:

- `python -m py_compile ai_stack/contracts/npc_agency_contracts.py ai_stack/story_runtime/npc_agency/npc_agency_long_horizon.py ai_stack/story_runtime/npc_agency/npc_agency_claim_readiness.py ai_stack/story_runtime/npc_agency/npc_agency_realization.py ai_stack/langgraph/langgraph_runtime_executor.py ai_stack/story_runtime/runtime_aspect_ledger.py world-engine/app/story_runtime/commit_models.py world-engine/app/story_runtime/manager.py backend/app/services/story_runtime/operator_turn_history_service.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py` → passed.
- `pytest ai_stack/tests/test_npc_agency_long_horizon_claim_readiness.py ai_stack/tests/test_npc_agency_planner.py ai_stack/tests/test_npc_agency_contracts.py -q --tb=short` → 18 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows pytest world-engine/tests/test_planner_truth_and_runtime_surfaces.py world-engine/tests/test_story_runtime_narrative_threads.py::test_prior_planner_truth_passed_to_graph_from_committed_truth -q --tb=short` → 8 passed.
- `pytest ai_stack/tests/test_runtime_aspect_ledger.py -q --tb=short` → 3 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows pytest world-engine/tests/test_trace_middleware.py::test_langfuse_emits_runtime_aspect_spans_and_reasoned_scores -q --tb=short` → 1 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows pytest tools/mcp_server/tests/test_langfuse_verify_tools.py -q --tb=short` → 29 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows/backend:/mnt/d/WorldOfShadows pytest backend/tests/services/test_operator_turn_history_service.py -q --tb=short` → 4 passed.

This evidence closes the deterministic long-horizon runtime implementation slice for independent planning, durable carry-forward closure, private-plan resolution, and operator/Langfuse/MCP scoring. It must **not** promote Π7 to full `implemented` until live staging traces and product-level replay satisfy `npc_agency_claim_readiness.v1`.

---

## Local verification snapshot for Π9 / context synthesis

Latest local verification recorded for the deterministic context-synthesis work:

- `python -m py_compile ai_stack/story_runtime/narrative/context_synthesis_engine.py ai_stack/langgraph/langgraph_runtime_executor.py ai_stack/langgraph/langgraph_runtime_state.py ai_stack/tests/test_context_synthesis_engine.py ai_stack/tests/test_context_synthesis_retry_loop.py` → passed.
- `python -m pytest ai_stack/tests/test_context_synthesis_engine.py ai_stack/tests/test_context_synthesis_retry_loop.py -q --tb=short` → 5 passed.
- `python -m pytest ai_stack/tests/test_langgraph_runtime.py -q --tb=short` → 14 passed.
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` → 3 passed.
- `python -m pytest ai_stack/tests/test_langgraph_state_schema.py -q --tb=short` → 20 passed.
- `python -m pytest ai_stack/tests/test_retrieval_governance_wiring.py -q --tb=short` → 26 passed.

The tests assert structure, provenance, authority boundaries, diagnostics, and graph wiring rather than expected narrative prose, in line with ADR-0039.

---

## Local verification snapshot for Π10 / voice consistency enforcement

Latest local verification recorded for the bounded runtime voice-consistency work:

- `python -m py_compile ai_stack/contracts/character_voice_contract.py ai_stack/story_runtime/npc_agency/character/god_of_carnage_character_voice.py ai_stack/story_runtime/npc_agency/character/character_voice_semantic_classifier.py ai_stack/story_runtime/npc_agency/character/character_voice_validation.py ai_stack/langgraph/langgraph_runtime_executor.py ai_stack/story_runtime/runtime_aspect_ledger.py ai_stack/story_runtime/story_runtime_playability.py world-engine/app/story_runtime/manager.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py` → passed.
- `python -m pytest ai_stack/tests/test_character_voice_runtime_enforcement.py -q` → 10 passed.
- `python -m pytest ai_stack/tests/test_character_voice_runtime_enforcement.py ai_stack/tests/test_runtime_aspect_ledger.py ai_stack/tests/test_story_runtime_playability.py -q` → 21 passed.
- `python -m pytest ai_stack/tests/test_langgraph_runtime.py ai_stack/tests/test_semantic_planner_graph_authority.py ai_stack/tests/test_semantic_planner_golden_cases.py -q` → 26 passed.
- `python -m pytest ai_stack/tests/test_runtime_authority_aspects.py ai_stack/tests/test_wave2_actor_truth_preservation.py ai_stack/tests/test_wave3_multi_actor_vitality.py ai_stack/tests/test_langfuse_evaluator_catalog.py -q` → 87 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows:/mnt/d/WorldOfShadows/world-engine python -m pytest world-engine/tests/test_story_runtime_aspect_ledger.py -q` → 19 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows python -m pytest world-engine/tests/test_trace_middleware.py::test_langfuse_emits_runtime_aspect_spans_and_reasoned_scores -q` → 1 passed.
- `python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py -q` → 29 passed.
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q` → 3 passed.

ADR-0039 discipline for this slice: tests derive their failing marker from canonical `character_voice.yaml` policy, derive positive and cross-actor semantic fixtures from canonical profile dimensions for all active GoC actors, assert structured validator/aspect/Langfuse/MCP outcomes, and verify that `dialogue_examples` are not serialized into runtime voice profiles.

---

## Local verification snapshot for Π11 / Scene Energy

Latest local verification recorded for the policy-driven Scene Energy implementation:

- `python -m py_compile ai_stack/contracts/scene_energy_contracts.py ai_stack/story_runtime/narrative/scene_energy_engine.py ai_stack/module_runtime_policy.py ai_stack/story_runtime/runtime_aspect_ledger.py ai_stack/langgraph/langgraph_runtime_state.py ai_stack/story_runtime/story_runtime_playability.py ai_stack/langgraph/langgraph_runtime_executor.py ai_stack/langgraph/langgraph_runtime_package_output_dramatic_review.py ai_stack/langgraph/langgraph_runtime_package_output_sections.py world-engine/app/story_runtime/commit_models.py world-engine/app/story_runtime/manager.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py backend/app/services/inspector_turn_projection_sections_assembly_filled.py ai_stack/tests/test_scene_energy_engine.py ai_stack/tests/test_runtime_aspect_ledger.py tests/gates/test_table_b_anti_hardcoding_gate.py` -> passed.
- `python -m pytest ai_stack/tests/test_scene_energy_engine.py ai_stack/tests/test_runtime_aspect_ledger.py tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` -> 12 passed.
- `python -m pytest ai_stack/tests/test_module_runtime_policy.py -q --tb=short` -> 8 passed.
- `python -m pytest ai_stack/tests/test_runtime_authority_aspects.py -q --tb=short` -> 18 passed.
- `python -m pytest ai_stack/tests/test_god_of_carnage_scene_director_extended.py::TestBuildPacingAndSilence ai_stack/tests/test_god_of_carnage_scene_director_extended.py::TestOffScopeKeywordVariations -q --tb=short` -> 29 passed.
- `python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py::test_summarize_runtime_aspect_matrix_reads_ledger_from_path_summary -q --tb=short` -> 1 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows python -m pytest world-engine/tests/test_trace_middleware.py::test_langfuse_emits_runtime_aspect_spans_and_reasoned_scores -q --tb=short` -> 1 passed.
- `python -m pytest world-engine/tests/test_story_runtime_aspect_ledger.py -q --tb=short` -> 20 passed.

ADR-0039 discipline for this slice: positive target expectations are loaded from `runtime_intelligence.scene_energy` policy; validation tests assert contract-defined structured fields and failure codes; no generated narration/prose substring is used as primary oracle. The anti-hardcoding gate keeps legacy `pi_11` / `Π11` IDs forbidden while allowing `scene_energy` only on reviewed canonical aspect surfaces.

---

## Local verification snapshot for Π12 / thematic tracking

Latest local verification recorded for the bounded policy-driven thematic tracking work:

- `python -m py_compile ai_stack/story_runtime/narrative/narrative_aspect_semantic_classifier.py ai_stack/contracts/narrative_aspect_contracts.py ai_stack/story_runtime/runtime_aspect_ledger.py world-engine/app/story_runtime/manager.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py` -> passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows python -m pytest ai_stack/tests/test_narrative_aspect_contracts.py ai_stack/tests/test_module_runtime_policy.py::test_narrative_aspect_policy_loads_from_generic_module_content -q --tb=short` -> 7 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows python -m pytest world-engine/tests/test_story_runtime_aspect_ledger.py -q --tb=short` -> 20 passed.
- `python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py -q --tb=short` -> 29 passed.
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` -> included in the Π11 Scene Energy verification above; gate now passes with `scene_energy` limited to canonical aspect surfaces and legacy `pi_11` / `Π11` still forbidden.

ADR-0039 discipline for this slice: tests derive positive semantic evidence from `semantic_profile` policy dimensions, assert structured classifier/ledger/MCP fields, and avoid using fixed narrative prose as the primary oracle.

---

## Local verification snapshot for Π14 / silence negative space

Latest local verification recorded for the bounded GoC silence / negative-space implementation:

- `python -m py_compile ai_stack/contracts/silence_negative_space_contract.py ai_stack/story_runtime/director/god_of_carnage_scene_director.py ai_stack/story_runtime/semantic_planner/god_of_carnage_semantic_move_interpretation.py ai_stack/contracts/semantic_move_contract.py ai_stack/story_runtime/god_of_carnage/god_of_carnage_dramatic_alignment.py ai_stack/langgraph/langgraph_runtime_executor.py story_runtime_core/input_interpreter.py backend/app/runtime/input_interpreter.py` -> passed.
- `python -m pytest ai_stack/tests/test_pi14_silence_negative_space.py -q` -> 6 passed.
- `python -m pytest ai_stack/tests/test_semantic_planner_golden_cases.py ai_stack/tests/test_god_of_carnage_semantic_move_interpretation.py ai_stack/tests/test_god_of_carnage_dramatic_alignment.py -q` -> 61 passed.
- `python -m pytest ai_stack/tests/test_god_of_carnage_scene_director_extended.py -q` -> 176 passed.
- `python -m pytest ai_stack/tests/test_semantic_planner_contracts.py ai_stack/tests/test_semantic_planner_graph_authority.py -q` -> 8 passed.
- `python -m pytest backend/tests/runtime/test_input_interpreter.py story_runtime_core/tests/test_input_interpreter.py -q` -> 29 passed.
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q` -> 5 passed.

ADR-0039 discipline for this slice: tests assert `silence_negative_space.v1`, frozen semantic/silence vocabularies, reason codes, routing flags, `blocks_forced_speech`, and graph/director state. The tests do not use generated narration or copied prose as the primary oracle.

---

## Local verification snapshot for Π15 / environmental story

Latest local verification recorded for the bounded durable environment-state implementation:

- `python -m py_compile ai_stack/contracts/environment_state_contracts.py ai_stack/story_runtime/player_action_resolution.py ai_stack/langgraph/langgraph_synthetic_action_resolution.py ai_stack/langgraph/langgraph_runtime_executor.py ai_stack/langgraph/langgraph_runtime_package_output.py ai_stack/story_runtime/turn/god_of_carnage_turn_seams.py world-engine/app/story_runtime/manager.py world-engine/app/story_runtime_shell_readout.py backend/app/api/v1/game_routes.py` -> passed.
- `python -m pytest ai_stack/tests/test_environment_state_contracts.py ai_stack/tests/test_player_action_resolution.py ai_stack/tests/test_return_movement_resolution.py ai_stack/tests/test_narrator_consequence_contract.py ai_stack/tests/test_langgraph_runtime.py::test_runtime_turn_graph_emits_player_action_resolution_surface` -> 38 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine python -m pytest world-engine/tests/test_story_runtime_environment_state.py world-engine/tests/test_story_runtime_shell_readout.py world-engine/tests/test_runtime_engine.py` -> 29 passed.
- `python -m pytest ai_stack/tests/test_god_of_carnage_structured_setting_knowledge.py backend/tests/content/test_content_compiler.py backend/tests/content/test_module_loader.py` -> 43 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine python -m pytest world-engine/tests/test_story_runtime_api.py::test_state_after_create_includes_committed_canonical_turn_count world-engine/tests/test_story_runtime_api.py::test_state_counter_projection_after_opening_and_first_player_turn` -> 2 passed.

ADR-0039 discipline for this slice: tests load or derive expected rooms, objects, actor lanes, schema versions, render markers, and shell projection fields from canonical module policy/content. They do not use generated environment narration as the primary oracle.

---

## Local verification snapshot for Π16 / dramatic irony

Latest local verification recorded for the bounded dramatic-irony implementation:

- `python -m py_compile ai_stack/contracts/dramatic_irony_contracts.py ai_stack/story_runtime/narrative/dramatic_irony_runtime.py ai_stack/story_runtime/story_runtime_playability.py ai_stack/module_runtime_policy.py ai_stack/langgraph/langgraph_runtime_executor.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py` -> passed.
- `python -m pytest ai_stack/tests/test_dramatic_irony_runtime.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_story_runtime_playability.py -q --tb=short` -> 24 passed.
- `python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py::test_summarize_runtime_aspect_matrix_reads_ledger_from_path_summary -q --tb=short` -> 1 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows:/mnt/d/WorldOfShadows/world-engine python -m pytest tests/test_planner_truth_and_runtime_surfaces.py -q --tb=short` -> 7 passed.
- `python -m pytest ai_stack/tests/test_runtime_aspect_ledger.py tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` -> 11 passed.

ADR-0039 discipline for this slice: tests derive leak examples from selected private-plan records and policy-normalized surface modes; prompt safety asserts hidden fact summaries are absent from compact context; MCP/ledger tests assert schema fields and violation codes rather than narrative prose.

---

## Local verification snapshot for Π18 / pacing rhythm

Latest local verification recorded for the bounded policy-driven pacing-rhythm work:

- `python -m py_compile ai_stack/contracts/pacing_rhythm_contracts.py ai_stack/story_runtime/narrative/pacing_rhythm_engine.py ai_stack/module_runtime_policy.py ai_stack/story_runtime/runtime_aspect_ledger.py ai_stack/langgraph/langgraph_runtime_state.py ai_stack/langgraph/langgraph_runtime_executor.py ai_stack/story_runtime/story_runtime_playability.py ai_stack/langgraph/langgraph_runtime_package_output_sections.py ai_stack/langgraph/langgraph_runtime_package_output_dramatic_review.py world-engine/app/story_runtime/commit_models.py world-engine/app/story_runtime/manager.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py tests/gates/test_table_b_anti_hardcoding_gate.py ai_stack/tests/test_pacing_rhythm_engine.py ai_stack/tests/test_runtime_aspect_ledger.py tools/mcp_server/tests/test_langfuse_verify_tools.py` -> passed.
- `python -m pytest ai_stack/tests/test_pacing_rhythm_engine.py ai_stack/tests/test_runtime_aspect_ledger.py::test_runtime_projection_exposes_pacing_rhythm_aspect ai_stack/tests/test_module_runtime_policy.py::test_module_runtime_policy_loads_goc_without_runtime_hardcoding tools/mcp_server/tests/test_langfuse_verify_tools.py::test_summarize_runtime_aspect_matrix_reads_ledger_from_path_summary tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` -> 14 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows python -m pytest ai_stack/tests/test_pacing_rhythm_engine.py ai_stack/tests/test_runtime_aspect_ledger.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_story_runtime_playability.py tools/mcp_server/tests/test_langfuse_verify_tools.py tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` -> 65 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows python -m pytest world-engine/tests/test_story_runtime_aspect_ledger.py world-engine/tests/test_planner_truth_and_runtime_surfaces.py -q --tb=short` -> 28 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows python -m pytest ai_stack/tests/test_langgraph_runtime.py -q --tb=short` -> 14 passed.

ADR-0039 discipline for this slice: tests load cadence profiles from normalized module policy, use exported failure-code constants, and assert ledger/MCP fields plus structured visible-block and actor-turn counts. Generated narration, copied scene prose, and LLM-as-a-Judge pacing categories are not pass/fail oracles.

---

## Local verification snapshot for Π19 / subtext

Latest local verification recorded for the bounded surface-vs-intent subtext implementation:

- `PYTHONPATH=/mnt/d/WorldOfShadows:/mnt/d/WorldOfShadows/world-engine python -m py_compile ai_stack/contracts/semantic_move_contract.py ai_stack/story_runtime/semantic_planner/god_of_carnage_subtext_policy.py ai_stack/story_runtime/semantic_planner/god_of_carnage_semantic_move_interpretation.py ai_stack/story_runtime/director/god_of_carnage_scene_director.py ai_stack/langgraph/langgraph_runtime_executor.py world-engine/app/story_runtime/manager.py backend/app/services/inspector/inspector_turn_projection_assembly_helpers.py backend/app/services/story_runtime/operator_turn_history_service.py` -> passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows:/mnt/d/WorldOfShadows/world-engine python -m pytest ai_stack/tests/test_god_of_carnage_scene_director_extended.py ai_stack/tests/test_wave3_multi_actor_vitality.py ai_stack/tests/test_semantic_planner_golden_cases.py ai_stack/tests/test_semantic_planner_graph_authority.py -q --tb=short` -> 227 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows:/mnt/d/WorldOfShadows/world-engine python -m pytest ai_stack/tests/test_semantic_planner_contracts.py ai_stack/tests/test_god_of_carnage_semantic_move_interpretation.py -q --tb=short` -> 27 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows python -m pytest world-engine/tests/test_goc_knowledge_runtime_path_summary.py world-engine/tests/test_return_movement_diagnostics.py world-engine/tests/test_trace_middleware.py::test_langfuse_path_spans_include_intent_semantic_director_fields world-engine/tests/test_trace_middleware.py::test_langfuse_scores_include_intent_surface_contract_evidence world-engine/tests/test_trace_middleware.py::test_langfuse_scores_use_shared_extended_intent_contract -q --tb=short` -> 5 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows/backend:/mnt/d/WorldOfShadows python -m pytest backend/tests/services/test_inspector_turn_projection_assembly_helpers.py backend/tests/services/test_operator_turn_history_service.py -q --tb=short` -> 8 passed.
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` -> 6 passed.

ADR-0039 discipline for this slice: tests derive expected subtext labels from `subtext_policy.yaml`, assert bounded contract fields, policy rule ids, trace/score propagation, and inspector projections, and avoid generated narration or prose literals as primary oracles.

---

## Local verification snapshot for Π20 / information disclosure

Latest local verification recorded for the bounded policy-driven information-disclosure work:

- `python -m py_compile ai_stack/contracts/information_disclosure_contracts.py ai_stack/story_runtime/narrative/information_disclosure_engine.py ai_stack/module_runtime_policy.py ai_stack/story_runtime/runtime_aspect_ledger.py ai_stack/langgraph/langgraph_runtime_state.py ai_stack/langgraph/langgraph_runtime_executor.py world-engine/app/story_runtime/manager.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py` -> passed.
- `python -m pytest ai_stack/tests/test_information_disclosure_contracts.py ai_stack/tests/test_module_runtime_policy.py -q --tb=short` -> 13 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows:/mnt/d/WorldOfShadows/world-engine python -m pytest world-engine/tests/test_story_runtime_aspect_ledger.py::test_runtime_projection_records_information_disclosure_contract -q --tb=short` -> 1 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows:/mnt/d/WorldOfShadows/world-engine python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py::test_summarize_runtime_aspect_matrix_reads_ledger_from_path_summary -q --tb=short` -> 1 passed.
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` -> 5 passed.

ADR-0039 discipline for this slice: tests derive selected/withheld/forbidden units from policy-normalized structures, assert contract failure codes and ledger/MCP fields, and keep `pi_20` / `mystery_rationing` out of production scan roots. Narrative text is never the primary pass/fail oracle.

---

## Local verification snapshot for Π22 / tension calibration

Latest local verification recorded for the bounded continuous social-pressure work:

- Date: 2026-05-15
- Scope: local runtime/contract verification only; no live provider, staging
  trace, or player-visible replay claim.
- `python -m py_compile ai_stack/contracts/social_pressure_contracts.py ai_stack/story_runtime/narrative/social_pressure_engine.py ai_stack/module_runtime_policy.py ai_stack/story_runtime/runtime_aspect_ledger.py ai_stack/langgraph/langgraph_runtime_state.py ai_stack/langgraph/langgraph_runtime_executor.py world-engine/app/story_runtime/commit_models.py world-engine/app/story_runtime/manager.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py` -> passed.
- `python -m pytest ai_stack/tests/test_runtime_authority_aspects.py -q --tb=short` -> 23 passed.
- `python -m pytest ai_stack/tests/test_social_pressure_engine.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_runtime_aspect_ledger.py -q --tb=short` -> 26 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows python -m pytest world-engine/tests/test_planner_truth_and_runtime_surfaces.py -q --tb=short` -> 10 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py::test_summarize_runtime_aspect_matrix_reads_ledger_from_path_summary -q --tb=short` -> 1 passed.
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` -> 13 passed.

The latest closure adds the dedicated `social_pressure` runtime aspect: `thread_pressure_state=high_unresolved_thread_pressure` and `social_risk_band=high` now feed a continuous score, not only a categorical band; the score/band/trend are ledgered, persisted in planner truth, and rehydrated as bounded prior state.

The 2026-05-15 follow-up closes the final-validator diagnostic gap: the
validator-written `turn_aspect_ledger.social_pressure` row preserves normalized
policy flags (`expected.policy_present`, `expected.policy_enabled`) and
self-correction attempts now carry `trigger_source="social_pressure"` plus
`social_pressure_failure_before_retry` when social-pressure validation rejects
before retry.

ADR-0039 discipline for this slice: tests assert normalized policy thresholds, schema versions, metric/band consistency, aspect-ledger projection, MCP matrix fields, and planner-truth rehydration. Generated narrative text is not the primary oracle.

---

## Local verification snapshot for Π24 / improvisational coherence

Latest local verification recorded for the bounded structured acceptance contract:

- Git SHA at verification time: `7aee14eb` (dirty worktree).
- Environment scope: local pytest; no live-provider or staging claim.
- `python -m pytest ai_stack/tests/test_improvisational_coherence_engine.py ai_stack/tests/test_runtime_aspect_ledger.py::test_runtime_projection_exposes_improvisational_coherence_aspect ai_stack/tests/test_module_runtime_policy.py::test_module_runtime_policy_loads_goc_without_runtime_hardcoding tools/mcp_server/tests/test_langfuse_verify_tools.py::test_summarize_runtime_aspect_matrix_reads_ledger_from_path_summary -q --tb=short` -> 5 passed.
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` -> 9 passed.
- `python -m pytest tests/test_capability_matrix_documentation_readiness.py -q --tb=short` -> 4 passed.

ADR-0039 discipline for this slice: tests assert normalized module policy, exported schema/failure constants, ledger projection, MCP matrix fields, and anti-hardcoding coverage for `pi_24` / `Π24` and the reviewed semantic `improvisational_coherence` surfaces. Generated narration, copied scene prose, and generic yes-and judge labels are not primary oracles.

---

## Local verification snapshot for Π25 / meta-control input isolation

Latest local verification recorded for bounded Meta/OOC input handling:

- Git SHA at verification time: `7aee14eb` on `master` (dirty worktree).
- Environment scope: local py_compile/pytest/docs check; no live-provider or staging claim.
- `PYTHONPATH=. python -m py_compile story_runtime_core/player_input_intent_contract.py ai_stack/language_io/language_adapter.py story_runtime_core/language_adapter.py ai_stack/story_runtime/player_action_resolution.py ai_stack/contracts/runtime_turn_contracts.py ai_stack/langgraph/langgraph_runtime_package_output_repro.py ai_stack/quality_lab/runtime_quality_semantics.py ai_stack/langgraph/langgraph_runtime_executor.py` -> passed.
- `PYTHONPATH=. pytest story_runtime_core/tests/test_input_interpreter.py ai_stack/tests/test_player_action_resolution.py ai_stack/tests/test_langgraph_runtime.py -q -s` -> 38 passed.
- `git diff --check` -> no whitespace errors; local Git emitted LF/CRLF normalization warnings only.

Evidence summary: Meta/OOC input now resolves to `player_input_kind=meta` and routes through LangGraph `meta_control_turn` to `package_output`. The path records `adapter_invocation_mode=meta_control_path`, `graph_path_summary=meta_control_deterministic`, `generation_required=false`, and `commit_not_applicable=true`; it skips story action resolution, retrieval, model invocation, `validate_seam`, and `commit_seam`.

ADR-0039 discipline for this slice: tests assert shared intent-contract flags, graph node execution/exclusion, adapter invocation mode, repro metadata, and commit applicability fields. Literal input strings are stimuli only; no generated acknowledgement text or story prose is a pass/fail oracle.

---

## Local verification snapshot for Π25 / adaptive meta-narrative awareness v2

Latest local verification recorded for adaptive in-world meta-awareness,
direct fourth-wall scope, and selected-memory-ref self-awareness:

- Date: 2026-05-15.
- Environment scope: local py_compile/pytest/docs check; no live-provider,
  staging, durable long-term-memory-store, or live Langfuse claim.
- `PYTHONPATH=. python -m py_compile ai_stack/contracts/meta_narrative_awareness_contracts.py ai_stack/story_runtime/narrative/meta_narrative_awareness_engine.py ai_stack/story_runtime/story_runtime_experience.py ai_stack/module_runtime_policy.py ai_stack/story_runtime/runtime_aspect_ledger.py ai_stack/langgraph/langgraph_runtime_executor.py ai_stack/tests/test_meta_narrative_awareness_engine.py ai_stack/tests/test_runtime_aspect_ledger.py tests/integration/test_story_runtime_experience.py ai_stack/tests/test_module_runtime_policy.py` -> passed.
- `PYTHONPATH=. pytest ai_stack/tests/test_meta_narrative_awareness_engine.py ai_stack/tests/test_runtime_aspect_ledger.py tests/integration/test_story_runtime_experience.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_langgraph_runtime.py -q --tb=short` -> 59 passed.
- `PYTHONPATH=. pytest tests/test_capability_matrix_documentation_readiness.py -q --tb=short` -> 4 passed.
- `PYTHONPATH=. pytest tests/gates/test_adr_0039_pi_scope.py -q --tb=short` -> 7 passed.
- `PYTHONPATH=. pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` -> 12 passed.

Evidence summary: `meta_narrative_awareness` now has a v2 contract surface for
`adaptive` and `full` tiers. The GoC policy defaults to subtle behavior but can
allow full fourth-wall play, narrator negotiation, and cross-session
self-awareness when Story Runtime Experience settings explicitly opt in. The
target includes adaptive signal codes, direct-address budget, allowed
fourth-wall levels, and selected memory ref ids. Validation rejects direct
address outside scope, unverified memory refs, private player data disclosure,
fabricated memory, prompt/tool/model disclosure, and player-control claims.

ADR-0039 discipline for this slice: tests assert schema/policy fields,
structured event contracts, selected memory ref ids, direct-address counts,
failure codes, and ledger projection. Generated fourth-wall prose remains
non-oracular.

---

## Local verification snapshot for Π25 / opt-in meta-narrative awareness

Latest local verification recorded for the bounded story-play meta-awareness aspect:

- Date: 2026-05-15.
- Git SHA at verification time: `1f46b6a8` on `master` (dirty worktree).
- Environment scope: local py_compile/pytest/docs check; no live-provider, staging, or live Langfuse claim.
- `PYTHONPATH=. python -m py_compile ai_stack/contracts/meta_narrative_awareness_contracts.py ai_stack/story_runtime/narrative/meta_narrative_awareness_engine.py ai_stack/story_runtime/story_runtime_experience.py ai_stack/module_runtime_policy.py ai_stack/story_runtime/runtime_aspect_ledger.py ai_stack/langgraph/langgraph_runtime_state.py ai_stack/langgraph/langgraph_runtime_executor.py` -> passed.
- `PYTHONPATH=. pytest ai_stack/tests/test_meta_narrative_awareness_engine.py tests/integration/test_story_runtime_experience.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_langgraph_runtime.py -q -s` -> 44 passed.

Evidence summary: `meta_narrative_awareness` is now a separate story-play RuntimeAspectLedger aspect. Activation requires module support plus Story Runtime Experience opt-in, configured actor ids, selected eligible actors, actor-lane safety, and nonzero policy budget. The GoC module currently clamps to `subtle` / `rare`. Validation consumes structured `meta_narrative_awareness_events` and can reject unauthorized actors, forbidden awareness modes, prompt/tool/model disclosure, direct full fourth-wall address in subtle mode, unbounded rewrite, and player-control claims before commit.

ADR-0039 discipline for this slice: runtime code uses the semantic name `meta_narrative_awareness`; Pi / Π vocabulary remains Capability Matrix index language. Tests assert policy normalization, opt-in gating, graph node execution, structured failure codes, and ledger projection rather than generated meta-flavored prose.

---

## Local verification snapshot for ADR-0039 / Pi-test coverage and MCP evidence scope

Latest local verification recorded for ADR-0039 as an active Capability Matrix governance source:

- Git SHA at verification time: `118b2c6c` on `master` (dirty worktree).
- Environment scope: local pytest/static-gate evidence only; no live-provider, staging, or live Langfuse claim.
- `python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py -q` -> 31 passed.
- `python -m pytest tests/gates/test_adr0039_* -q` -> 1 passed.
- `python -m pytest tests/gates/test_adr_0039_* -q` -> 7 passed.
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` -> 9 passed.
- `python -m pytest tests/test_capability_matrix_documentation_readiness.py -q --tb=short` -> 4 passed.
- `python -m pytest ai_stack/tests/test_pi14_silence_negative_space.py ai_stack/tests/test_semantic_planner_golden_cases.py::test_pi14_no_lexical_silence_reaches_director_pipeline -q` -> 7 passed.

ADR-0039 discipline for this slice: the new ADR gate discovers every Pi / Π-labeled test file and requires an explicit coverage rationale. The Π14 silence runtime path now uses semantic `silence_negative_space_signal` fields instead of active `pi14_*` runtime keys, and `run_projection_tests` reports `evidence_scope=local_pytest`, `proof_level=local_only`, and `live_or_staging_evidence=false` so MCP verification cannot be mistaken for staging/live proof.

---

## Local verification snapshot for ADR-0039 governance gates (2026-05-15 re-audit)

- Date: 2026-05-15
- Git SHA at verification time: `f0136c30` (dirty worktree; governance fixes not committed at run time)
- Scope: **local governance verification only** — Pi / Π vocabulary gates, Table B anti-hardcoding, Capability Matrix doc readiness, MCP handler repo-root portability. No capability promotion and no live/staging/Langfuse provider claim.
- `python -m pytest tests/gates/test_adr_0039_pi_scope.py -q --tb=short` -> 7 passed
- `python -m pytest tests/gates/test_adr0039_pi_scope.py -q --tb=short` -> 1 passed
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q --tb=short` -> 10 passed
- `python -m pytest tests/test_capability_matrix_documentation_readiness.py -q --tb=short` -> 4 passed
- `python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py::test_run_projection_tests_handler_has_no_machine_absolute_repo_paths -q --tb=short` -> 1 passed

Evidence scope: `live_or_staging_evidence=false` (MCP `run_projection_tests` and this log entry are local-only). Local PASS lines above are **not** live-, provider-, or staging proof.

Known limitations at that snapshot: no real provider traces; no fresh staging Langfuse scores; no end-to-end replay evidence. `sensory_context` was still diagnostic/local-only until focused implementation and projection tests landed in a later local snapshot.

---

## Local verification snapshot for Π26 / sensory-context runtime aspect

- Date: 2026-05-15
- Git SHA at verification time: `1f46b6a8` (dirty worktree; local implementation and adjacent governance fixes not committed at run time)
- Scope: **local pytest/static-gate evidence only** — no live-provider, staging, or live Langfuse claim.
- `python -m py_compile ai_stack/contracts/sensory_context_contracts.py ai_stack/story_runtime/narrative/sensory_context_engine.py ai_stack/module_runtime_policy.py ai_stack/story_runtime/runtime_aspect_ledger.py ai_stack/langgraph/langgraph_runtime_state.py ai_stack/langgraph/langgraph_runtime_executor.py ai_stack/story_runtime/story_runtime_playability.py ai_stack/langchain/bridges.py world-engine/app/story_runtime/commit_models.py world-engine/app/story_runtime/manager.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py tests/gates/test_table_b_anti_hardcoding_gate.py tools/mcp_server/tests/test_langfuse_verify_tools.py` -> passed
- `python -m pytest ai_stack/tests/test_sensory_context_engine.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_runtime_aspect_ledger.py ai_stack/tests/test_god_of_carnage_structured_setting_knowledge.py ai_stack/tests/test_narrator_consequence_contract.py -q` -> 53 passed
- `PYTHONPATH=/mnt/d/WorldOfShadows python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py -k "runtime_aspect" -q` -> 4 passed, 27 deselected
- `python -m pytest tests/test_capability_matrix_documentation_readiness.py -q` -> 4 passed
- `python -m pytest tests/gates/test_adr_0039_pi_scope.py tests/gates/test_adr0039_pi_scope.py -q` -> 8 passed
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q` -> 11 passed
- `git diff --check` -> no whitespace errors; local Git emitted LF/CRLF normalization warnings only

Evidence summary: Π26 is implemented as the generic `sensory_context` runtime aspect. The runtime selects bounded authored layers from normalized module policy, narrator sensory palette, scene affordances, location/object focus, adjacent runtime targets, prior planner truth, and output language; validates structured `sensory_context_events`; records `turn_aspect_ledger.sensory_context`; persists planner-truth fields; and exposes semantic Langfuse/MCP matrix fields. There are no Pi-number score names or production control-flow keys.

ADR-0039 discipline for this slice: tests derive expectations from schema constants, normalized policy, canonical sensory/affordance content, structured event rows, ledger projection, MCP extraction fields, and anti-hardcoding scopes. Generated narration, copied scene prose, and sensory quality labels are not pass/fail oracles.

Known limitations: this is local implementation and mocked/fixture verification only. Fresh staging traces, provider evidence, and end-to-end player-visible replay remain outside this snapshot.

---

## Local verification snapshot for ADR-0041 semantic capability selection projection

- Date: 2026-05-15
- Git SHA at verification time: `7784f246` (dirty worktree; local ADR-0041 projection changes not committed at run time)
- Scope: **local pytest/static-gate evidence only** — no live-provider, staging, live Langfuse, or MCP live proof claim.
- `python -m pytest ai_stack/tests/test_capability_selector.py -q` -> 15 passed
- `python -m pytest ai_stack/tests/test_capability_selector_runtime_projection.py -q` -> 7 passed
- `python -m pytest ai_stack/tests/test_runtime_aspect_ledger.py -q` -> 15 passed
- `PYTHONPATH=world-engine:. python -m pytest world-engine/tests/test_story_runtime_aspect_ledger.py -q` -> 21 passed
- `python -m pytest tests/gates/test_adr_0039_pi_scope.py -q` -> 7 passed
- `python -m pytest tests/gates/test_adr0039_* -q` -> 1 passed
- `python -m pytest tests/gates/test_adr_0039_* -q` -> 7 passed
- `python -m pytest tests/test_capability_matrix_documentation_readiness.py -q` -> 4 passed
- `git diff --check` -> no whitespace errors; local Git emitted LF/CRLF normalization warnings only

Evidence summary: ADR-0041 now exposes a local-only semantic selector payload at
`runtime_intelligence_projection.capability_selection` for initialized runtime
aspect ledgers. The projection records selected, observed, judged, and excluded
semantic capability names, activation modes, budget, reason, warnings,
`proof_level=local_only`, and `live_or_staging_evidence=false`.

Selector correction included in this snapshot: explicit player turns with NPC
response evidence remain `turn_kind=player_input` and `active_actor=player`.
`npc_agency` can be selected as a conditional enforced capability alongside
`player_intent_inference` and `action_resolution`, but the evidence does not
convert the turn into an NPC turn.

ADR-0039 discipline for this slice: selector projection uses semantic capability
names only, adds no active Pi / Π runtime keys, does not mark
`turn_aspect_ledger.capability_selection` as passed, and does not promote
Capability Matrix maturity. The projection does not change prompt authority,
validator execution, judge execution, generated story content, or
commit/readiness gates.

Known limitations: full prompt assembly integration, selected validator gating,
judge execution, Langfuse/MCP live proof, and Capability Matrix promotion remain
future work.

---

## Local verification snapshot for Π32 / genre awareness

- Date: 2026-05-15
- Git SHA at verification time: `22a4bccb` (dirty worktree; local genre-awareness coverage additions not committed at run time)
- Scope: **local pytest/static-gate evidence only** - no live-provider, staging, live Langfuse, or broad genre-adaptation claim.
- `python -m py_compile ai_stack/contracts/genre_awareness_contracts.py ai_stack/story_runtime/narrative/genre_awareness_engine.py ai_stack/module_runtime_policy.py ai_stack/story_runtime/runtime_aspect_ledger.py ai_stack/langgraph/langgraph_runtime_state.py ai_stack/langgraph/langgraph_runtime_executor.py ai_stack/langgraph/langgraph_runtime_package_output_sections.py ai_stack/story_runtime/story_runtime_playability.py world-engine/app/story_runtime/commit_models.py world-engine/app/story_runtime/manager.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py` -> passed
- `python -m pytest ai_stack/tests/test_genre_awareness_engine.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_runtime_aspect_ledger.py ai_stack/tests/test_capability_selector.py ai_stack/tests/test_capability_selector_runtime_projection.py -q --tb=short` -> 51 passed
- `PYTHONPATH=/mnt/d/WorldOfShadows:/mnt/d/WorldOfShadows/world-engine python -m pytest world-engine/tests/test_planner_truth_and_runtime_surfaces.py -q --tb=short` -> 10 passed
- `PYTHONPATH=/mnt/d/WorldOfShadows python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py -q --tb=short` -> 38 passed
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py tests/gates/test_adr_0039_pi_scope.py tests/test_capability_matrix_documentation_readiness.py -q --tb=short` -> 27 passed
- `git diff --check -- ai_stack/tests/test_genre_awareness_engine.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_runtime_aspect_ledger.py world-engine/tests/test_planner_truth_and_runtime_surfaces.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py tools/mcp_server/tests/test_langfuse_verify_tools.py tests/gates/test_table_b_anti_hardcoding_gate.py docs/MVPs/capability_matrix_status_and_adr_relations.md docs/MVPs/capability_matrix_live_claim_gates.md world-engine/app/story_runtime/manager.py` -> no whitespace errors; local Git emitted LF/CRLF normalization warnings only

Evidence summary: Π32 is represented as the generic `genre_awareness` local
contract surface. Module policy declares a bounded genre profile under
`runtime_intelligence.genre_awareness`; the engine derives
`genre_awareness.v1` state/target, validates structured
`genre_awareness_events`, projects `RuntimeAspectLedger.genre_awareness`,
persists planner-truth genre fields, and exposes Langfuse/MCP
`genre_awareness_*` matrix fields.

ADR-0039 discipline for this slice: production-facing keys use semantic
`genre_awareness` names only. Tests assert normalized policy, schema/failure
constants, structured event fields, ledger projection, MCP row fields, and the
anti-hardcoding canonical-surface guard. Generated genre prose and legacy Π32
labels are not pass/fail oracles.

Known limitations: local evidence only; no live/staging trace proof, no
provider replay, and no claim of general multi-genre adaptation beyond the
bounded module-authored policy contract.

---

## Local verification snapshot for ADR-0041 validator execution-plan projection

- Date: 2026-05-15
- Git SHA at verification time: `2d4ec860` (dirty worktree; local ADR-0041 validator-plan changes not committed at run time)
- Scope: **local pytest/static-gate evidence only** — no live-provider, staging, live Langfuse, MCP live proof, validator-execution, or judge-execution claim.
- `python -m pytest ai_stack/tests/test_capability_selector.py -q` -> 12 passed
- `python -m pytest ai_stack/tests/test_capability_selector_runtime_projection.py -q` -> 6 passed
- `python -m pytest ai_stack/tests/test_capability_validator_plan.py -q` -> 8 passed
- `python -m pytest ai_stack/tests/test_capability_validator_runtime_projection.py -q` -> 5 passed
- `python -m pytest ai_stack/tests/test_runtime_aspect_ledger.py -q` -> 14 passed
- `python -m pytest world-engine/tests/test_story_runtime_aspect_ledger.py -q` -> 21 passed
- `python -m pytest tests/gates/test_adr_0039_pi_scope.py -q` -> 7 passed
- `python -m pytest tests/gates/test_adr0039_* -q` -> 1 passed
- `python -m pytest tests/gates/test_adr_0039_* -q` -> 7 passed
- `python -m pytest tests/test_capability_matrix_documentation_readiness.py -q` -> 4 passed
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q` -> 13 passed
- `git diff --check` -> no whitespace errors; local Git emitted LF/CRLF normalization warnings only

Evidence summary: ADR-0041 now exposes
`runtime_intelligence_projection.validator_execution_plan` as local-only
planning evidence. The plan maps enforced semantic capabilities to planned local
validator IDs, observed semantic capabilities to non-blocking diagnostic IDs,
excluded capabilities to skipped validator IDs, and budget-disallowed judge IDs
to `judges_disallowed`. The projection records `execution_changed=false`.

ADR-0039 discipline for this slice: validator-plan IDs are semantic lowercase
identifiers only, no active Pi / Π runtime keys are introduced, local planning
evidence is not implementation proof, and no local plan is treated as
live/staging proof. The Capability Matrix is not promoted by this projection.

Known limitations: actual validator dispatch/gating, prompt assembly
integration, judge execution, Langfuse/MCP live proof, and Capability Matrix
promotion remain future work.

---

## Local verification snapshot for Π35 / tonal consistency

- Date: 2026-05-15
- Git SHA at verification time: `ba2601c9` (dirty worktree; local follow-up
  Pi35 hard-loop/documentation edits not committed at run time)
- Scope: **local pytest/static-gate/runtime-path evidence only** - no
  live-provider, staging, live Langfuse, MCP live proof, or ADR-0009 promotion
  proof.
- `python -m py_compile ai_stack/contracts/tonal_consistency_contracts.py ai_stack/story_runtime/narrative/tonal_consistency_classifier.py ai_stack/story_runtime/narrative/tonal_consistency_engine.py ai_stack/langgraph/langgraph_runtime_executor.py ai_stack/langgraph/langgraph_runtime_state.py ai_stack/langgraph/langgraph_runtime_package_output_sections.py ai_stack/story_runtime/story_runtime_playability.py ai_stack/story_runtime/live_runtime_commit_semantics.py world-engine/app/story_runtime/manager.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py` -> passed
- `python -m pytest ai_stack/tests/test_tonal_consistency_engine.py ai_stack/tests/test_runtime_authority_aspects.py::test_tonal_consistency_failure_triggers_hard_live_retry_diagnostics ai_stack/tests/test_story_runtime_playability.py tests/gates/test_adr_live_runtime_commit_semantics_gate.py tools/mcp_server/tests/test_langfuse_verify_tools.py::test_runtime_aspect_matrix_reads_tonal_consistency_ledger_fields tools/mcp_server/tests/test_langfuse_verify_tools.py::test_runtime_aspect_matrix_recommends_tonal_consistency_repair -q` -> 27 passed
- `python -m pytest tests/gates/test_table_b_anti_hardcoding_gate.py tests/gates/test_adr_0039_pi_scope.py tests/gates/test_adr0039_pi_scope.py tests/test_capability_matrix_documentation_readiness.py -q` -> 30 passed
- `python -m pytest ai_stack/tests/test_runtime_authority_aspects.py -q` -> 26 passed
- `python -m pytest ai_stack/tests/test_runtime_aspect_ledger.py tools/mcp_server/tests/test_langfuse_verify_tools.py -q` -> 59 passed
- `python -m pytest ai_stack/tests/test_langgraph_runtime.py -q` -> 15 passed
- `git diff --check -- ai_stack/story_runtime/story_runtime_playability.py ai_stack/tests/test_runtime_authority_aspects.py docs/technical/runtime/tonal_consistency_contract.md docs/MVPs/capability_matrix_status_and_adr_relations.md docs/MVPs/capability_matrix_live_claim_gates.md docs/technical/content/god_of_carnage_structured_content.md docs/ADR/adr-0009-evaluation-is-a-promotion-gate.md world-engine/app/story_runtime/manager.py` -> no whitespace errors; local Git emitted LF/CRLF normalization warnings only
- `python -m pytest ai_stack/tests/test_tonal_consistency_engine.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_runtime_aspect_ledger.py::test_runtime_projection_exposes_tonal_consistency_aspect ai_stack/tests/test_capability_selector.py tools/mcp_server/tests/test_langfuse_verify_tools.py::test_runtime_aspect_matrix_reads_tonal_consistency_ledger_fields tools/mcp_server/tests/test_langfuse_verify_tools.py::test_runtime_aspect_matrix_recommends_tonal_consistency_repair -q --tb=short` -> 31 passed
- `python -m pytest ai_stack/tests/test_tonal_consistency_engine.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_runtime_aspect_ledger.py ai_stack/tests/test_capability_selector.py tools/mcp_server/tests/test_langfuse_verify_tools.py -q --tb=short` -> 77 passed
- `python -m pytest tests/gates/test_adr_0039_pi_scope.py tests/gates/test_adr0039_pi_scope.py tests/gates/test_table_b_anti_hardcoding_gate.py tests/test_capability_matrix_documentation_readiness.py -q --tb=short` -> 25 passed
- `git diff --check -- ai_stack/contracts/tonal_consistency_contracts.py ai_stack/story_runtime/narrative/tonal_consistency_engine.py ai_stack/module_runtime_policy.py ai_stack/story_runtime/runtime_aspect_ledger.py ai_stack/capabilities/capability_selector.py ai_stack/tests/test_tonal_consistency_engine.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_runtime_aspect_ledger.py ai_stack/tests/test_capability_selector.py tools/mcp_server/tools_registry_handlers_langfuse_verify.py tools/mcp_server/tests/test_langfuse_verify_tools.py content/modules/god_of_carnage/module.yaml docs/technical/runtime/tonal_consistency_contract.md docs/MVPs/capability_matrix_status_and_adr_relations.md` -> no whitespace errors; local Git emitted LF/CRLF normalization warnings only

Evidence summary: Π35 is now represented as the generic
`tonal_consistency` runtime contract surface. GoC policy declares a bounded
tone profile under `runtime_intelligence.tonal_consistency`; the runtime now
derives a `tonal_consistency.v1` target in LangGraph after scene
energy/pacing/social pressure, injects compact bounded context into the
generation packet, validates visible output with the independent deterministic
policy-marker classifier, projects `RuntimeAspectLedger.tonal_consistency`,
emits Langfuse/MCP `tonal_consistency_*` fields, routes failures through
bounded self-correction, and converts exhausted hard-loop failures into
recoverable rejection/no healthy commit. ADR-0033 live-success evaluation also
marks failed tonal consistency as not live-success.

ADR-0039 discipline for this slice: production-facing keys use semantic
`tonal_consistency` names only. Tests derive expectations from normalized
policy, exported schema/failure-code constants, structured classification
payloads, independent classifier source, marker-class counts, ledger
projection, and MCP row fields.
Generated narration, copied dialogue examples, and LLM-as-a-Judge tone
categories are not pass/fail oracles.

Known limitations: no live/staging traces, no provider evidence, no ADR-0009
promotion package, and no readiness-consumer promotion. Runtime hard-loop
enforcement is local/tested evidence, not live-proven promotion evidence.

---

## Local verification snapshot for Π34 / active listening envelope

- Date: 2026-05-15
- Git SHA at verification time: `ba2601c9` (dirty worktree; local Π34
  active-listening/docs/test adjustments not committed at run time)
- Scope: **local pytest/static-gate evidence only** - no live-provider,
  staging, live Langfuse, MCP live proof, production validator-gating, broad
  production NLU, or commit/readiness promotion claim.
- `python -m pytest ai_stack/tests/test_active_listening_contracts.py ai_stack/tests/test_runtime_aspect_ledger.py::test_runtime_projection_exposes_active_listening_authority_aspects ai_stack/tests/test_langgraph_runtime.py::test_runtime_turn_graph_delivers_director_context_to_model_prompt -q` -> 5 passed
- `python -m pytest ai_stack/tests/test_runtime_aspect_ledger.py ai_stack/tests/test_capability_validator_plan.py ai_stack/tests/test_capability_selector_runtime_projection.py ai_stack/tests/test_capability_validator_runtime_projection.py -q` -> 39 passed
- `python -m pytest ai_stack/tests/test_active_listening_contracts.py ai_stack/tests/test_runtime_aspect_ledger.py::test_runtime_projection_exposes_active_listening_authority_aspects ai_stack/tests/test_langgraph_runtime.py::test_runtime_turn_graph_delivers_director_context_to_model_prompt ai_stack/tests/test_capability_selector.py ai_stack/tests/test_capability_validator_registry_inventory.py ai_stack/tests/test_capability_validator_turn_class_coverage.py tests/test_capability_matrix_documentation_readiness.py tests/gates/test_adr_0039_pi_scope.py tests/gates/test_adr0039_* tests/gates/test_adr_0039_* -q` -> 61 passed

Evidence summary: Π34 now has a bounded local active-listening envelope. The
runtime derives `broad_nlu_listening.v1` from structured interpreted input and
semantic move evidence, derives `conversational_memory.v1` from bounded
hierarchical-memory refs, builds `prompt_authority.v1` as a source-bound
model-visible generation constraint packet, inserts those records into the
dramatic generation packet / prompt, and projects all three through
`RuntimeAspectLedger`.

ADR-0039 discipline for this slice: production-facing keys use semantic names
only. Tests assert schema constants, structured source refs, no raw
input/prompt storage, no commit/readiness/validation mutation, selector/plan
observer status, prompt-packet presence, and ledger projection. Generated
dialogue understanding, copied example prose, and legacy Π labels are not
pass/fail oracles.

Known limitations: no live/staging traces, no provider proof, no MCP live
proof, no production selected-validator gating, and no claim of unbounded
conversational memory or broad production NLU. The row remains partial/local
evidence.

---

## Local verification snapshot — administration-tool operator defaults (ADR-0039)

- Date: 2026-05-15
- Scope: local pytest + Table-B module literal gate; no live stack.
- Commands (representative): `python -m pytest administration-tool/tests/test_manage_operator_defaults_rendered.py administration-tool/tests/test_context_processor.py administration-tool/tests/test_operator_site_defaults_fetch.py backend/tests/test_slogans.py::test_site_settings_returns_rotation_fields backend/tests/test_admin_security.py::TestSiteSettingsAPI backend/tests/test_game_routes.py::test_game_content_endpoints_seed_and_publish tests/gates/test_table_b_anti_hardcoding_gate.py::test_module_specific_literals_stay_inside_documented_compatibility_debt tests/gates/test_adr0039_runtime_surface_governance.py -q --tb=short`
- Product rule: manage defaults come from `site_settings` via `GET /api/v1/site/settings` (`content_module_id` / `default_runtime_template_id`); game-content new drafts clone published experiences only (`GET /api/v1/game/content/experiences?status=published`).
