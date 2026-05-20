---
inventory_version: 1
adr_owner: Engineering / Runtime governance
surfaces:
  - surface_id: ai_stack_langgraph_runtime_executor
    primary_files:
      - ai_stack/langgraph/langgraph_runtime_executor.py
    symbols:
      - RuntimeTurnGraphExecutor
    runtime_role: LangGraph turn execution, validation node wiring, ADR-0041 validate_seam sidecar attachment
    authority_level: canonical
    can_mutate_validation_outcome: true
    can_mutate_commit: true
    can_mutate_readiness: indirect
    can_mutate_frontend_playability: indirect
    allowed_feature_flags: ADR0041_VALIDATOR_DISPATCH_MODE and related ADR-0041 envs (bounded; fail-closed without sidecar)
    known_false_green_risks: plan_enforced appearance without graph sidecar; treating projection as seam
    module_specific_assumptions: none required at executor layer; module data from session
    tests_gates:
      - ai_stack/tests/test_adr0041_runtime_graph_sidecar.py
      - ai_stack/tests/test_validation_authority_bridge.py

  - surface_id: ai_stack_goc_validation_seam
    primary_files:
      - ai_stack/story_runtime/turn/god_of_carnage_turn_seams.py
    symbols:
      - run_validation_seam
    runtime_role: Canonical GoC validation outcome for proposals
    authority_level: canonical
    can_mutate_validation_outcome: true
    can_mutate_commit: false
    can_mutate_readiness: indirect
    can_mutate_frontend_playability: indirect
    allowed_feature_flags: policy via explicit validation config
    known_false_green_risks: bypassing seam with plan-only projection
    module_specific_assumptions: GoC module contracts
    tests_gates:
      - ai_stack/tests/test_player_action_resolution.py
      - ai_stack/tests/test_actor_lane_absence_governance.py

  - surface_id: ai_stack_runtime_aspect_ledger
    primary_files:
      - ai_stack/runtime_aspect_ledger.py
    symbols:
      - normalize_runtime_aspect_ledger
      - build_runtime_intelligence_projection
    runtime_role: Aspect ledger and runtime_intelligence_projection (capability selection, validator plan, dispatch report)
    authority_level: sidecar
    can_mutate_validation_outcome: false
    can_mutate_commit: false
    can_mutate_readiness: false
    can_mutate_frontend_playability: false
    allowed_feature_flags: ADR-0041 projection and readiness aggregation flags (explicit; local-only proof)
    known_false_green_risks: Env plan_enforced without sidecar historically implied live routing; must stay dry_run
    module_specific_assumptions: none for projection core
    tests_gates:
      - ai_stack/tests/test_runtime_aspect_ledger.py
      - ai_stack/tests/test_capability_validator_dispatch_feature_flag.py

  - surface_id: adr0041_scoped_co_authority_and_readiness_consumer
    primary_files:
      - ai_stack/runtime_readiness_consumer.py
      - ai_stack/runtime_aspect_ledger.py
    symbols:
      - resolve_runtime_readiness_with_adr0041
    runtime_role: Veto-only readiness overlay; scoped co-authority preview bounded by flags and sidecar
    authority_level: co_authority
    can_mutate_validation_outcome: false
    can_mutate_commit: false
    can_mutate_readiness: true
    can_mutate_frontend_playability: true
    allowed_feature_flags: ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED and upstream prerequisite flags
    known_false_green_risks: Silent upgrade reject to allow
    module_specific_assumptions: requires graph sidecar and explicit flags per ADR-0041
    tests_gates:
      - ai_stack/tests/test_validation_authority_bridge.py
      - backend/tests/test_runtime_readiness_consumer_bundle.py

  - surface_id: world_engine_story_runtime_manager
    primary_files:
      - world-engine/app/story_runtime/manager.py
    symbols:
      - StoryRuntimeManager
    runtime_role: Session lifecycle, turn execution host, LDSS integration, commit packaging
    authority_level: canonical
    can_mutate_validation_outcome: indirect
    can_mutate_commit: true
    can_mutate_readiness: indirect
    can_mutate_frontend_playability: indirect
    allowed_feature_flags: governed runtime config reload paths
    known_false_green_risks: Empty opening vs shell ready mismatch
    module_specific_assumptions: template and module binding from content pipeline
    tests_gates:
      - world-engine/tests/test_story_runtime_narrative_commit.py
      - world-engine/tests/test_story_runtime_aspect_ledger.py

  - surface_id: world_engine_commit_models
    primary_files:
      - world-engine/app/story_runtime/commit_models.py
    symbols:
      - resolve_narrative_commit
    runtime_role: Narrative commit record shape and commit seam helpers
    authority_level: canonical
    can_mutate_validation_outcome: false
    can_mutate_commit: true
    can_mutate_readiness: false
    can_mutate_frontend_playability: indirect
    allowed_feature_flags: none ad hoc
    known_false_green_risks: ADR-0041 fields feeding commit without governance decision
    module_specific_assumptions: documented commit policy
    tests_gates:
      - world-engine/tests/test_story_runtime_narrative_commit.py

  - surface_id: backend_game_player_session_bundle
    primary_files:
      - backend/app/api/v1/game_routes.py
      - ai_stack/live_runtime_commit_semantics.py
    symbols:
      - _player_session_bundle
      - evaluate_session_opening_readiness
    runtime_role: Player-session JSON bundle; opening readiness; ADR-0041 readiness overlay
    authority_level: canonical
    can_mutate_validation_outcome: false
    can_mutate_commit: false
    can_mutate_readiness: true
    can_mutate_frontend_playability: true
    allowed_feature_flags: ADR-0041 consumer envs (veto-only)
    known_false_green_risks: runtime_session_ready with empty story_entries
    module_specific_assumptions: goc polish paths where module_id matches GoC
    tests_gates:
      - backend/tests/test_player_session_live_opening_contract.py
      - backend/tests/test_runtime_readiness_consumer_bundle.py

  - surface_id: frontend_play_shell_routes_templates
    primary_files:
      - frontend/app/routes_play.py
      - frontend/templates/session_shell.html
      - frontend/static/play_shell.js
    symbols:
      - session_view
      - play_execute
    runtime_role: Play shell HTTP and template; displays backend bundle fields only
    authority_level: display_only
    can_mutate_validation_outcome: false
    can_mutate_commit: false
    can_mutate_readiness: false
    can_mutate_frontend_playability: false
    allowed_feature_flags: diagnostics query toggles
    known_false_green_risks: Locally derived ready or live labels without bundle fields
    module_specific_assumptions: none for canonical path
    tests_gates:
      - frontend/tests/test_routes_extended.py

  - surface_id: story_runtime_core_input_interpretation
    primary_files:
      - story_runtime_core/input_interpreter.py
      - ai_stack/language_io/language_adapter.py
      - story_runtime_core/language_adapter.py
      - story_runtime_core/models.py
    symbols:
      - interpret_player_input
      - prepare_player_input_semantic_resolution
    runtime_role: AI semantic resolution contract shaping player input before engine graph
    authority_level: preview
    can_mutate_validation_outcome: false
    can_mutate_commit: false
    can_mutate_readiness: false
    can_mutate_frontend_playability: false
    allowed_feature_flags: none as authority
    known_false_green_risks: Module literals in generic branches without debt documentation
    module_specific_assumptions: GoC builtins where explicitly scoped; prefer policy/registry over literals
    tests_gates:
      - story_runtime_core/tests/test_input_interpreter.py
      - story_runtime_core/tests/test_player_input_semantics_de.py
      - story_runtime_core/tests/test_player_input_semantics_en.py

  - surface_id: ai_stack_active_listening_envelope
    primary_files:
      - ai_stack/contracts/active_listening_contracts.py
      - ai_stack/langgraph/langgraph_runtime_executor.py
      - ai_stack/runtime_aspect_ledger.py
    symbols:
      - derive_broad_nlu_listening
      - derive_conversational_memory_context
      - build_prompt_authority_packet
    runtime_role: Bounded Π34 active-listening prompt envelope; derives structured discourse, committed-memory refs, and source-bound prompt authority for model-visible assembly and ledger diagnostics
    authority_level: diagnostic
    can_mutate_validation_outcome: false
    can_mutate_commit: false
    can_mutate_readiness: false
    can_mutate_frontend_playability: false
    allowed_feature_flags: none as commit or readiness authority
    known_false_green_risks: Treating local prompt-envelope presence as broad NLU, unbounded conversational memory, production validator gating, live proof, or commit/readiness authority
    module_specific_assumptions: none; consumes structured runtime state and bounded hierarchical-memory context
    tests_gates:
      - ai_stack/tests/test_active_listening_contracts.py
      - ai_stack/tests/test_langgraph_runtime.py
      - ai_stack/tests/test_runtime_aspect_ledger.py

  - surface_id: story_runtime_core_no_dead_end_recovery
    primary_files:
      - story_runtime_core/recovery/no_dead_end.py
    symbols:
      - stable_recovery_id
      - validate_no_dead_end_recovery_record
    runtime_role: Structured recovery evidence contract; must not assert commit or seam approval
    authority_level: diagnostic
    can_mutate_validation_outcome: false
    can_mutate_commit: false
    can_mutate_readiness: false
    can_mutate_frontend_playability: false
    allowed_feature_flags: none
    known_false_green_risks: Treating recovery class as live success or healthy commit
    module_specific_assumptions: none at contract layer
    tests_gates:
      - story_runtime_core/tests/test_no_dead_end_recovery.py

  - surface_id: story_runtime_core_branching_and_consequences
    primary_files:
      - story_runtime_core/branching/simulation_tree.py
      - story_runtime_core/branching/decision_point.py
      - story_runtime_core/consequences/consequence_cascade.py
      - story_runtime_core/callbacks/callback_web.py
    symbols:
      - make_simulation_tree
      - finalize_simulation_tree
      - DecisionPoint
    runtime_role: Branching, forecasting, callback and consequence helpers; not commit authority unless wired through engine
    authority_level: diagnostic
    can_mutate_validation_outcome: false
    can_mutate_commit: false
    can_mutate_readiness: false
    can_mutate_frontend_playability: false
    allowed_feature_flags: none as commit authority
    known_false_green_risks: Decision trees bypassing engine commit
    module_specific_assumptions: documented where used from world-engine or tools
    tests_gates:
      - story_runtime_core/tests/test_callback_web.py
      - story_runtime_core/tests/test_consequence_cascade.py

  - surface_id: administration_tool_operator_ui_and_proxy
    primary_files:
      - administration-tool/app.py
      - administration-tool/route_registration.py
      - administration-tool/route_registration_proxy.py
    symbols:
      - create_app
    runtime_role: Operator Flask app, manage routes, and backend/world-engine proxy; displays and triggers actions only through approved APIs
    authority_level: display_only
    can_mutate_validation_outcome: false
    can_mutate_commit: false
    can_mutate_readiness: false
    can_mutate_frontend_playability: false
    allowed_feature_flags: deployment and auth configuration only
    known_false_green_risks: Local dashboard or proxy response treated as canonical runtime or live health without backend/engine correlation; treating empty operator defaults as an implicit module/template (defaults must come from GET /api/v1/site/settings aliases content_module_id / default_runtime_template_id, env ADMIN_DEFAULT_*, or moderator-published game content — not from static HTML literals)
    module_specific_assumptions: Narrative admin pages require configured content_module_id or they show an explicit configuration-missing panel; game content "new draft" starters clone from GET /game/content/experiences?status=published only; manage/base.html exposes data-content-module-id and data-default-template-id plus frontend_config.contentModuleId / defaultRuntimeTemplateId
    tests_gates:
      - administration-tool/tests/test_proxy_contract.py
      - administration-tool/tests/test_manage_world_engine_control_center.py
      - administration-tool/tests/test_manage_operator_defaults_rendered.py

  - surface_id: observability_mcp_langfuse_projection
    primary_files:
      - tools/mcp_server/tools_registry_handlers_langfuse_verify.py
    symbols: []
    runtime_role: MCP and verification payloads; local-only evidence unless explicitly marked otherwise
    authority_level: diagnostic
    can_mutate_validation_outcome: false
    can_mutate_commit: false
    can_mutate_readiness: false
    can_mutate_frontend_playability: false
    allowed_feature_flags: governed tool registry
    known_false_green_risks: Machine-local paths; PASS labels as proof
    module_specific_assumptions: Config.repo_root discovery
    tests_gates:
      - tools/mcp_server/tests/test_langfuse_verify_tools.py
      - tests/gates/test_adr_0039_pi_scope.py
---

# ADR-0039 — Runtime surface governance inventory

Normative companion to [ADR-0039: Gate tests and runtime evidence discipline](../ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md).

This inventory names **decision surfaces** where runtime truth, readiness, commit, or player-visible state can be distorted. **Source code is authoritative** over prose here.

## story_runtime_core (required scope)

The shared package **`story_runtime_core/`** is part of the same runtime governance boundary as `ai_stack`, `world-engine`, backend play routes, the Play Shell, and the **`administration-tool/`** operator surface:

- **Input interpretation and semantic language adaptation** (`interpret_player_input`, `language_adapter`) shape proposals and commands; they must not be treated as validation seam approval or commit.
- **Recovery** (`recovery/no_dead_end.py`) emits structured evidence classes only; playable recovery must not be promoted to live or staging success without engine and observability proof.
- **Branching / consequences / callbacks** are planner- or diagnostic-side unless explicitly integrated into the canonical commit path by World-Engine; they must not bypass `run_validation_seam` or narrative commit authority.

## Administration-tool (operator surface)

The **`administration-tool/`** app is **display and control-plane only** for runtime and governance: it proxies or calls **backend** and **world-engine** APIs. Dashboards, runtime health, and inspector views must **not** be treated as canonical story commit, validation seam outcomes, or live success unless the same claim is evidenced from **authoritative services** (and documented per [capability_matrix_live_claim_gates.md](capability_matrix_live_claim_gates.md)). Static templates and JS must **not** invent readiness, healthy, or live semantics that the engine did not return.

## Authority levels (enum)

`canonical` | `co_authority` | `preview` | `sidecar` | `diagnostic` | `display_only`

## Change process

1. Land code or contract change.
2. Update the YAML front matter above (`surfaces` list) and `primary_files`.
3. Extend `tests_gates` references when new tests protect the surface.
4. Keep ADR-0039 § Runtime surface governance in sync.
