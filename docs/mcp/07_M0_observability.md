# M0 Observability · MCP Calls

## Goals

- Every MCP tool call is traceable.
- Tool calls can explain turns (why guard accept/reject).
- Foundation for later B/C agentics.

## Trace IDs

- `trace_id`: UUID per MCP request
- `session_id`: optional, if tool is session-related
- `turn_id`: optional, if tool is turn-related

## Logging Fields (MCP Server)

- `timestamp`
- `trace_id`
- `tool`
- `duration_ms`
- `status` (ok/error)
- `args_hash` (SHA-256)
- `response_hash` (SHA-256)
- `backend_url` (if HTTP)

## Backend Headers (optional, recommended)

- `X-WoS-Trace-Id: <uuid>`
- `X-WoS-Client: mcp-operator`

## LLM-as-a-Judge semantics (MCP)

- Canonical evaluator names, categories, reasoning prompts, and rubric text live in `docs/llm-as-a-judge/LLM-as-a-Judge Definition Table - Judges.csv`.
- `ai_stack/langfuse_evaluator_catalog.py` mirrors that table for MCP: category severity (positive / warning / failure / neutral), evaluator groups (runtime aspect integrity, authority/origin, dramatic realization, recovery/playability, relationship pressure), repair-card hints, and Langfuse filter bundles (`GENERATION` + `story.model.generation`, caller-selected environment such as `staging` or `live`, primary turn trace `world-engine.turn.execute`, alternate backend root `backend.turn.execute` where the repo still emits that root span).
- Langfuse tools such as `fetch_langfuse_trace_scores`, `summarize_opening_judge_scores`, and `build_opening_quality_context` emit `llm_judge_interpretation`, `judge_score_coverage_gaps` (observability gaps only), and `evaluator_column_metadata` so operators see **qualitative** signals separately from deterministic gates (`live_runtime_contract_pass`, `actor_lane_safety_pass`, etc.).

## Runtime aspect evidence (Langfuse verification)

MCP Langfuse verification normalizes deterministic runtime evidence separately from judge interpretation. Operators can query turn-level rows for:

- `turn_aspect_ledger_present`
- `beat_selected`
- `beat_realized`
- `narrator_required_when_expected`
- `npc_takeover_absent`
- `capability_selection_present`
- `selected_capabilities_realized`
- `npc_agency_plan_present`
- `npc_independent_planning_used`
- `npc_long_horizon_state_present`
- `npc_private_plan_resolution_present`
- `npc_private_plan_visibility_respected`
- `npc_intention_threads_carried_forward`
- `npc_required_initiatives_realized`
- `multi_npc_initiative_realized`
- `npc_carry_forward_closed`
- `npc_forbidden_actor_absent`
- `npc_agency_claim_readiness_status`
- `npc_agency_full_claim_allowed`
- `visible_block_origin_present`
- `required_visible_origin_preserved`
- `visible_projection_contract_pass`
- `voice_consistency_policy_present`
- `voice_semantic_classification_present`
- `voice_cross_actor_confusion_absent`
- `voice_forbidden_markers_absent`
- `voice_consistency_contract_pass`
- `information_disclosure_policy_present`
- `information_disclosure_target_selected`
- `information_disclosure_selected_units`
- `information_disclosure_visible_units`
- `information_disclosure_withheld_units`
- `information_disclosure_budget_used`
- `information_disclosure_budget_pass`
- `information_disclosure_premature_reveal_absent`
- `information_disclosure_contract_pass`
- `information_disclosure_failure_codes`
- `expectation_variation_policy_present`
- `expectation_variation_target_selected`
- `expectation_variation_selected_ids`
- `expectation_variation_selected_types`
- `expectation_variation_realized_ids`
- `expectation_variation_realized_types`
- `expectation_variation_budget_used`
- `expectation_variation_budget_pass`
- `expectation_variation_setup_supported`
- `expectation_variation_contract_pass`
- `expectation_variation_failure_codes`
- `sensory_context_target_present`
- `sensory_context_intensity`
- `sensory_context_location_id`
- `sensory_context_object_id`
- `sensory_context_contract_pass`
- `sensory_context_required_layers_realized`
- `sensory_context_source_refs_valid`
- `sensory_context_failure_codes`
- `dramatic_irony_policy_present`
- `dramatic_irony_opportunity_present`
- `dramatic_irony_selected_opportunities`
- `dramatic_irony_realized_opportunities`
- `dramatic_irony_realization_status`
- `dramatic_irony_leak_blocked`
- `dramatic_irony_contract_pass`
- `dramatic_irony_violation_codes`
- `hierarchical_memory_present`
- `memory_policy_applied`
- `memory_write_from_committed_turn`
- `memory_context_bounded`
- `hierarchical_memory_contract_pass`

For runtime aspects and hierarchical memory, MCP reads the backend/world-engine ledger and Langfuse scores. It does not infer beat realization, authority ownership, capability realization, NPC agency closure, long-horizon NPC state, private-plan visibility, voice classification, information-disclosure correctness, expectation-variation support, sensory-layer realization, dramatic-irony realization or private-plan leak safety, visible-origin preservation, or memory correctness from visible text, and it does not treat mock/fallback/degraded generation as healthy runtime evidence.
