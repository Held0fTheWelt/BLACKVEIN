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
- `npc_required_initiatives_realized`
- `multi_npc_initiative_realized`
- `npc_carry_forward_closed`
- `npc_forbidden_actor_absent`
- `visible_block_origin_present`
- `required_visible_origin_preserved`
- `visible_projection_contract_pass`
- `voice_consistency_policy_present`
- `voice_semantic_classification_present`
- `voice_cross_actor_confusion_absent`
- `voice_forbidden_markers_absent`
- `voice_consistency_contract_pass`
- `hierarchical_memory_present`
- `memory_policy_applied`
- `memory_write_from_committed_turn`
- `memory_context_bounded`
- `hierarchical_memory_contract_pass`

For runtime aspects and hierarchical memory, MCP reads the backend/world-engine ledger and Langfuse scores. It does not infer beat realization, authority ownership, capability realization, NPC agency closure, voice classification, visible-origin preservation, or memory correctness from visible text, and it does not treat mock/fallback/degraded generation as healthy runtime evidence.
