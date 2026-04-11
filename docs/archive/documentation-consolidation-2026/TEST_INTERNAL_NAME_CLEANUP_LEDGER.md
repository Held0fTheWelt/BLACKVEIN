# Internal test name cleanup ledger (2026 consolidation)

Per-file record of **function-level** renames and comment/docstring tweaks that remove historical encoding.

## `backend/tests/runtime/test_runtime_validation_commands_orchestration.py`

| Old internal name | New internal name | Category | Reason |
|-------------------|-------------------|----------|--------|
| `test_g_t4_01_end_to_end_truth_three_surfaces_gate` | `test_full_validation_runtime_writers_room_improvement_operator_truth` | historical_internal_label | States three-surface operator truth scope. |
| `test_g_t4_02_bootstrap_validation_gate` | `test_full_validation_bootstrap_profiles_and_staged_integration` | historical_internal_label | Bootstrap + staged integration. |
| `test_g_t4_03_cross_surface_contract_gate` | `test_full_validation_operator_comparison_and_cross_surface_contracts` | historical_internal_label | Operator comparison + cross-surface contracts. |
| `test_g_t4_04_negative_degraded_honesty_gate` | `test_full_validation_degraded_runtime_and_improvement_honesty` | historical_internal_label | Negative paths honesty. |
| `test_g_t4_05_drift_resistance_gate` | `test_full_validation_audit_schema_drift_resistance` | historical_internal_label | Drift resistance scope. |
| `test_g_t4_06_validation_command_reality_gate` | `test_full_validation_documented_pytest_command_matches_code` | historical_internal_label | Doc/command parity. |
| `test_g_t4_07_required_suite_stability_gate` | `test_full_validation_proof_modules_pass_without_gate_recursion` | historical_internal_label | Subprocess proof modules. |
| `test_g_t4_08_documentation_and_closure_truth_gate` | `test_full_validation_docs_reference_task4_gates_and_commands` | historical_internal_label | Documentation completeness. |

Also: imports `architecture_style_doc` and resolves legacy `docs/architecture/*` paths for gate markdown.

## `backend/tests/runtime/test_runtime_operator_comparison_cross_surface.py`

| Old internal name | New internal name | Category | Reason |
|-------------------|-------------------|----------|--------|
| `test_g_t3_01_compact_truth_model_gate` | `test_operator_comparison_compact_truth_payload_under_bootstrap` | historical_internal_label | Describes payload shape under bootstrap. |
| `test_g_t3_02_direct_readability_gate` | `test_operator_comparison_bounded_http_readability` | historical_internal_label | Bounded HTTP readability. |
| `test_g_t3_03_policy_execution_comparison_gate` | `test_operator_comparison_policy_execution_fields` | historical_internal_label | Policy execution comparison fields. |
| `test_g_t3_04_cross_surface_comparison_gate` | `test_operator_comparison_runtime_writers_room_improvement_shape` | historical_internal_label | Three-surface shape. |
| `test_g_t3_05_primary_concern_visibility_gate` | `test_operator_comparison_primary_concern_visible_when_present` | historical_internal_label | Primary concern visibility. |
| `test_g_t3_06_no_deep_reconstruction_dependency_gate` | `test_operator_comparison_no_hidden_reconstruction_dependency` | historical_internal_label | No hidden reconstruction. |
| `test_g_t3_07_documentation_truth_gate` | `test_operator_comparison_docs_list_task3_gate_ids` | historical_internal_label | Doc listing task. |
| `test_g_t3_08_authority_semantic_safety_gate` | `test_operator_comparison_authority_semantics_safe` | historical_internal_label | Authority semantics guard. |

Doc path loop now uses `architecture_style_doc()` instead of hard-coded `docs/architecture/`.

## `backend/tests/runtime/test_cross_surface_operator_audit_contract.py`

| Old internal name | New internal name | Category | Reason |
|-------------------|-------------------|----------|--------|
| `test_g_conv_08_cross_surface_area2_truth_coherence` | `test_operator_truth_coherent_across_bounded_http_surfaces` | historical_internal_label | Cross-surface coherence. |
| `test_g_conv_08_runtime_truth_keys_match_bounded_http_surface` | `test_runtime_operator_truth_keys_align_with_bounded_http` | historical_internal_label | Runtime vs HTTP key alignment. |

## `backend/tests/runtime/test_runtime_model_ranking_synthesis_contracts.py`

| Old internal name | New internal name | Category | Reason |
|-------------------|-------------------|----------|--------|
| `test_g_canon_rank_01_canonical_stage_existence_gate` | `test_runtime_ranking_stage_id_is_canonical` | historical_internal_label | Stage id contract. |
| `test_g_canon_rank_01_pipeline_order_in_staged_execution` | `test_runtime_ranking_follows_signal_before_synthesis_in_stages` | historical_internal_label | Pipeline ordering. |
| `test_g_canon_rank_02_semantic_boundary_gate` | `test_runtime_ranking_signal_and_synthesis_routing_contracts_distinct` | historical_internal_label | Semantic boundaries. |
| `test_g_canon_rank_03_canonical_visibility_gate` | `test_runtime_ranking_surfaces_in_traces_summary_rollup_and_audit` | historical_internal_label | Visibility surfaces. |
| `test_g_canon_rank_04_operator_equality_gate` | `test_runtime_ranking_compact_operator_truth_matches_orchestration_summary` | historical_internal_label | Operator equality. |
| `test_g_canon_rank_05_no_implicit_downgrade_gate` | `test_runtime_ranking_surfaces_preserved_across_path_variants` | historical_internal_label | Path variants preserve ranking. |
| `test_g_canon_rank_06_inventory_startup_truth_gate` | `test_runtime_ranking_required_in_staged_inventory_and_closure_doc` | historical_internal_label | Inventory + doc alignment. |
| `test_g_canon_rank_07_documentation_truth_gate` | `test_runtime_ranking_documentation_lists_canonical_gate_ids` | historical_internal_label | Documentation gate ids. |
| `test_g_canon_rank_08_authority_guard_safety_gate` | `test_runtime_ranking_paths_complete_with_guard_outcomes` | historical_internal_label | Guard outcomes. |
| `test_g_canon_rank_orchestration_effect_ranked_paths` | `test_runtime_ranking_orchestration_effects_on_ranked_paths` | vague_behavior_name | Orchestration effects clarified. |
| `test_g_canon_rank_slm_only_suppressed_ranking_trace` | `test_runtime_ranking_slm_only_skip_traced_without_bounded_call` | historical_internal_label | SLM-only skip semantics. |

Module docstring generalized; `DOCS_*` paths now resolved via `architecture_style_doc`.

## `backend/tests/runtime/test_runtime_routing_registry_composed_proofs.py`

| Change | Category | Reason |
|--------|----------|--------|
| Documentation loop uses `architecture_style_doc` | misleading_fixture_or_helper_name (path helper) | Legacy `docs/architecture` no longer valid. |
| Removed unused `REPO_ROOT` | maintainability | After path helper adoption. |

## `ai_stack/tests/test_goc_multi_turn_experience_quality.py`

| Old internal name | New internal name | Category | Reason |
|-------------------|-------------------|----------|--------|
| `test_phase3_run_c_fail_and_degraded_are_explained` | `test_experience_multiturn_primary_failure_fallback_and_degraded_explained` | historical_phase_marker | S5 anchor name describes failure/fallback/degraded explanation without phase id. |
