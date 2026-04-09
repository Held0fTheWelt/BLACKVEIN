# Task 4 — Explicit hardening gate set

These gates are the **reviewable contract** for Task 4. Each gate is satisfied by automated tests and/or documented honest limits. Gate IDs are referenced in `task4_maturity_hardening_closure_report.md` and in architecture updates.

| Gate ID | Scope | Requirement |
|--------|--------|-------------|
| **G-RUN-01** | Runtime staged | Canonical success: preflight → signal → synthesis → packaging; `final_path == slm_then_llm`; routed stages carry `routing_evidence`; `operator_audit` timeline includes packaging; summary aligns with orchestration summary. |
| **G-RUN-02** | Runtime staged | SLM-only: two bounded calls; synthesis skipped; `operator_audit.audit_summary` consistent with `runtime_orchestration_summary` for synthesis skip. |
| **G-RUN-03** | Runtime staged | Degraded paths: (a) early skip both preflight and signal → `degraded_early_skip_then_synthesis` with honest skip traces; (b) signal parse failure → `degraded_parse_forced_synthesis` and forcing gate reason. |
| **G-RUN-04** | Runtime preempted | `agent_orchestration` enabled: staged multi-stage pipeline not run; `operator_audit` uses preempted shape (`staged_pipeline_preempted`, `orchestration_preempted` timeline); no full `runtime_stage_traces` for Task 1 stages. |
| **G-RUN-05** | Runtime legacy | `runtime_staged_orchestration: false`: legacy single route; audit timeline includes `legacy_single_route`. |
| **G-RUN-06** | Runtime authority | Staged paths still yield outcomes through `execute_turn` / guard pipeline (existing semantics); tests assert success paths do not bypass documented guard presence where already asserted. |
| **G-TOOL-01** | Tool loop + staged | Synthesis output may be a tool request; after host tool execution, generation continues via `_generate_with_runtime_policy` and finalizes; transcript order and `finalized_after_tool_use` are consistent. |
| **G-WR-01** | Writers-Room | HTTP review path exposes `operator_audit` and per-stage `routing_evidence` with shared contract keys (see G-XS-01). |
| **G-IMP-01** | Improvement | Experiment/recommendation path exposes `operator_audit`, `task_2a_routing`, `deterministic_recommendation_base` vs `model_assisted_interpretation` separation. |
| **G-BOOT-01** | Bootstrap on | Real `create_app` subclass with `ROUTING_REGISTRY_BOOTSTRAP=True` registers mock; staged `execute_turn_with_ai` succeeds with registry-backed routing. |
| **G-BOOT-02** | Bootstrap off | `TestingConfig` default / explicit bootstrap off leaves registry empty for isolated tests; behavior documented and unchanged. |
| **G-INV-01** | Inventory | `validate_surface_coverage` passes for `runtime_staged`, `writers_room`, and `improvement_bounded` with repository fixtures. |
| **G-XS-01** | Cross-surface | Shared top-level `operator_audit` keys and `audit_schema_version`; per-stage `routing_evidence` minimum key set; `stage_id` equals stage key for bounded surfaces; timeline entry shape (`ordinal`, `stage_key`, `stage_kind`, `bounded_model_call`, `skip_reason`). |
| **G-NEG-01** | Failure honesty | Missing specs / no eligible / missing provider adapter / bounded call skipped: traces and evidence remain diagnostic; no silent upgrade to success semantics. |
| **G-NEG-02** | Improvement routing | `_run_routed_bounded_call` with empty adapter map yields `skip_reason` and `bounded_model_call: false` when routing selects a name not present in adapters. |
| **G-DRIFT-01** | Drift resistance | `audit_schema_version` matches `operator_audit.AUDIT_SCHEMA_VERSION`; stable routing-evidence key subsets regression-locked. |
| **G-DOC-01** | Documentation | `llm_slm_role_stratification.md` and `ai_story_contract.md` describe gates, proven truths, supported degradation, and out-of-scope items without overstating maturity. |

## Out of scope (explicit)

- Redesign of `route_model` policy or routing architecture.
- Changes to `StoryAIAdapter` contract or guard/commit/reject authority.
- Distributed immutable audit logs or new telemetry pipelines.
- Frontend/admin product redesign.
