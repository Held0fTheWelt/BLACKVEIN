#!/usr/bin/env python3
"""
World of Shadows — multi-component test runner.

Orchestrates pytest for component and repository suites. Component suites are
``backend``, ``frontend``, ``administration``, ``engine``, ``database``,
``writers_room``, ``improvement``, and ``ai_stack``. Repository suites cover
root ``tests/*`` groups (integration, branching, smoke, and related trees).
Each pytest suite uses its own working directory (repo root for ``ai_stack`` and
all ``root_*`` suites).

``--suite all`` runs all Python suite groups in deterministic order: component suites
plus root ``tests/*`` groups. ``writers_room`` and ``improvement`` remain selectable
isolated slices (their tests are also collected under ``backend/tests``).

Optional ``--scope`` maps to ``pytest -m`` for backend, writers_room, improvement,
administration, and engine (see ``--help``). Optional ``--domain`` selects backend
pytest markers registered in ``backend/pytest.ini`` (combines with ``--scope``).
Additional ``--suite`` choices ``backend_runtime``, ``engine_runtime``,
``engine_opening_contracts``, ``ai_stack_graph``, … run strict focused blocks for
fast iteration; full component suites remain the gate. Optional ``--parallel``
enables pytest-xdist (two-pass: parallel then
``@pytest.mark.serial``).

Optional non-Python lanes are opt-in: ``--with-playwright`` and
``--with-compose-smoke``.

**Invocation** (from repository root)::

    python tests/run_tests.py
    python tests/run_tests.py --suite backend --scope contracts
    python tests/run_tests.py --suite all --quick

Or ``cd tests`` then ``python run_tests.py …``. See ``tests/TESTING.md`` for full runner
contracts (``--quick``, ``--scope``, coverage roots, and ``--suite all`` semantics).

**One-shot dependency install (recommended for a fresh clone / CI-like venv):** from the
repository root run ``./setup-test-environment.sh`` (Linux/macOS/Git Bash) or
``setup-test-environment.bat`` (Windows cmd), or the equivalent
``scripts/install-full-test-env.sh`` / ``scripts/install-full-test-env.ps1`` /
``scripts/install-full-test-env.bat``. That installs backend, frontend, administration-tool,
and world-engine dev requirements plus editable ``story_runtime_core`` and ``ai_stack[test]``,
then verifies the LangGraph export surface required by the **engine** and **ai_stack** suites.
Without that closure, :func:`check_environment` fails fast with ``pip`` hints instead of
mid-suite ``ModuleNotFoundError``. Those scripts install **only** from tracked
``requirements*.txt`` files and use ``python -m pip`` (no remote pipe-to-shell bootstrap).

**Root editable alone:** ``pip install -e .`` at the repository root installs **``world-of-shadows-hub``**
with the same pinned **backend runtime + pytest** closure as ``backend/requirements*.txt`` (see
root ``pyproject.toml``), so ``python tests/run_tests.py --suite backend`` works in a fresh
venv with no extra install step. **Other suites** (frontend, administration, engine, ai_stack)
still need ``setup-test-environment.*`` or their component ``requirements-dev.txt`` installs.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Paths
TESTS_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = TESTS_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
ADMIN_TOOL_DIR = PROJECT_ROOT / "administration-tool"
WORLD_ENGINE_DIR = PROJECT_ROOT / "world-engine"
DATABASE_DIR = PROJECT_ROOT / "database"
REPORTS_DIR = TESTS_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
ROOT_TESTS_DIR = PROJECT_ROOT / "tests"

# Authoritative pytest-cov roots (single source of truth). Mirrors component ``pytest.ini``
# where noted: ``administration-tool`` uses ``--cov=.`` + ``.coveragerc``; ``world-engine`` and
# ``database`` use explicit ``--cov=`` targets; ``database`` omits ``--cov-fail-under`` (thin slice
# of ``backend/app``). See ``docs/testing/COVERAGE_SEMANTICS.md``.
BACKEND_APP_ROOT = str(BACKEND_DIR / "app")
FRONTEND_APP_ROOT = str(FRONTEND_DIR / "app")
WORLD_ENGINE_APP_ROOT = str(WORLD_ENGINE_DIR / "app")
AI_STACK_ROOT = str(PROJECT_ROOT / "ai_stack")

BACKEND_BLOCK_SUITES: tuple[str, ...] = (
    "backend_runtime",
    "backend_observability",
    "backend_services",
    "backend_content",
    "backend_routes_core",
    "backend_mcp",
    "backend_play",
    "backend_rest",
)
ENGINE_BLOCK_SUITES: tuple[str, ...] = (
    "engine_foundation",
    "engine_http_ws",
    "engine_runtime",
    "engine_opening_contracts",
    "engine_persistence",
    "engine_observability",
    "engine_rest",
)
AI_STACK_BLOCK_SUITES: tuple[str, ...] = (
    "ai_stack_graph",
    "ai_stack_goc",
    "ai_stack_capabilities",
    "ai_stack_narrative",
    "ai_stack_retrieval_research",
    "ai_stack_quality",
    "ai_stack_rest",
)
BACKEND_SUITE_FAMILY: tuple[str, ...] = ("backend", *BACKEND_BLOCK_SUITES, "writers_room", "improvement")
ENGINE_SUITE_FAMILY: tuple[str, ...] = ("engine", *ENGINE_BLOCK_SUITES)
AI_STACK_SUITE_FAMILY: tuple[str, ...] = ("ai_stack", *AI_STACK_BLOCK_SUITES)

BACKEND_PLAY_TARGETS: tuple[str, ...] = (
    "tests/test_backend_playservice_integration.py",
    "tests/test_game_routes.py",
    "tests/test_game_service_play_http.py",
    "tests/test_mvp4_contract_playability.py",
    "tests/test_mvp4_contract_playability_e2e.py",
    "tests/test_mvp4_full_handoff_integration.py",
    "tests/test_mvp4_runtime_profile_handoff.py",
    "tests/test_player_session_live_opening_contract.py",
    "tests/test_play_service_client.py",
    "tests/test_play_service_control.py",
    "tests/test_world_engine_backend_api_contracts.py",
    "tests/test_world_engine_console_routes.py",
    "tests/test_world_engine_control_center.py",
)

ENGINE_FOUNDATION_TARGETS: tuple[str, ...] = (
    "tests/test_api_key_guard.py",
    "tests/test_api_security.py",
    "tests/test_authority_version_and_route_family_truth.py",
    "tests/test_backend_bridge_contract.py",
    "tests/test_canonical_runtime_contract.py",
    "tests/test_config_contract.py",
    "tests/test_config_startup_and_auth.py",
    "tests/test_config_validation.py",
    "tests/test_environment_security.py",
    "tests/test_internal_api_key_guard.py",
    "tests/test_narrative_policy_and_package_loader.py",
    "tests/test_preview_isolation_registry_contract.py",
    "tests/test_repo_root.py",
    "tests/test_validator_lane_truth.py",
)
ENGINE_HTTP_WS_TARGETS: tuple[str, ...] = (
    "tests/test_api.py",
    "tests/test_api_advanced_contracts.py",
    "tests/test_api_contracts.py",
    "tests/test_content_feed_http_contract.py",
    "tests/test_http_api_contracts.py",
    "tests/test_http_api_extended.py",
    "tests/test_http_health_and_templates.py",
    "tests/test_http_join_context.py",
    "tests/test_http_runs.py",
    "tests/test_http_snapshot_and_transcript.py",
    "tests/test_http_tickets.py",
    "tests/test_phase2_ws_session_loop_endpoint.py",
    "tests/test_runtime_config_client_http.py",
    "tests/test_ui_auth_shell.py",
    "tests/test_ui_backend_proxy.py",
    "tests/test_ui_runtime_pages.py",
    "tests/test_websocket.py",
    "tests/test_websocket_security.py",
    "tests/test_ws_auth.py",
    "tests/test_ws_isolation.py",
    "tests/test_ws_rejoin.py",
    "tests/test_ws_runtime_commands_and_isolation.py",
    "tests/test_ws_state_transitions.py",
)
ENGINE_RUNTIME_TARGETS: tuple[str, ...] = (
    "tests/runtime",
    "tests/test_adr0041_validator_dispatch_harness.py",
    "tests/test_beat_progression_carry_forward.py",
    "tests/test_canonical_turn_lifecycle.py",
    "tests/test_goc_knowledge_runtime_path_summary.py",
    "tests/test_goc_multi_speaker_actor_line_split.py",
    "tests/test_live_story_runtime_governance.py",
    "tests/test_planner_truth_and_runtime_surfaces.py",
    "tests/test_runtime_commands.py",
    "tests/test_runtime_engine.py",
    "tests/test_runtime_lobby_rules.py",
    "tests/test_runtime_manager.py",
    "tests/test_runtime_npc_behaviors.py",
    "tests/test_runtime_open_world.py",
    "tests/test_runtime_visibility.py",
    "tests/test_session_authority.py",
    "tests/test_story_progression_merge.py",
    "tests/test_story_runtime_api.py",
    "tests/test_story_runtime_callback_web.py",
    "tests/test_story_runtime_consequence_cascade.py",
    "tests/test_story_runtime_environment_state.py",
    "tests/test_story_runtime_narrative_commit.py",
    "tests/test_story_runtime_narrative_threads.py",
    "tests/test_story_runtime_rag_runtime.py",
    "tests/test_story_runtime_runtime_world.py",
    "tests/test_story_runtime_shell_readout.py",
    "tests/test_story_runtime_short_path_persist_convergence.py",
    "tests/test_story_runtime_w5_narrator_projection.py",
    "tests/test_story_session_runtime_projection_contract.py",
    "tests/test_story_session_w5_round_trip.py",
    "tests/test_story_window_projection.py",
    "tests/test_turn_execution.py",
)
ENGINE_OPENING_CONTRACT_TARGETS: tuple[str, ...] = (
    "tests/test_goc_narrator_path_opening.py",
    "tests/test_goc_player_input_greeting_imperative.py",
    "tests/test_ldss_opening_fallback_actor_lane.py",
    "tests/test_mvp1_experience_identity.py",
    "tests/test_mvp2_npc_coercion_state_delta.py",
    "tests/test_mvp2_object_admission.py",
    "tests/test_mvp2_runtime_state_actor_lanes.py",
    "tests/test_mvp3_complete_integration.py",
    "tests/test_mvp3_ldss_integration.py",
    "tests/test_mvp3_narrative_agent_orchestration.py",
    "tests/test_mvp3_narrative_streaming_endpoint.py",
    "tests/test_mvp4_contract_opening_truthfulness.py",
    "tests/test_mvp4_runtime_profile_handoff.py",
    "tests/test_opening_movement_split.py",
)
ENGINE_PERSISTENCE_TARGETS: tuple[str, ...] = (
    "tests/test_aead_json_persistence.py",
    "tests/test_branch_timeline_store.py",
    "tests/test_branching_tree_store.py",
    "tests/test_callback_web_store.py",
    "tests/test_consequence_cascade_store.py",
    "tests/test_data_integrity.py",
    "tests/test_persistence_contracts.py",
    "tests/test_recovery_contracts.py",
    "tests/test_store.py",
    "tests/test_store_config.py",
    "tests/test_store_json.py",
    "tests/test_store_recovery.py",
    "tests/test_store_sqlalchemy.py",
    "tests/test_story_runtime_branching_simulation_tree.py",
    "tests/test_story_runtime_branching_tree_api.py",
    "tests/test_story_session_persistence.py",
    "tests/test_ticket_manager.py",
    "tests/test_ticket_manager_and_validation.py",
    "tests/test_tickets.py",
)
ENGINE_OBSERVABILITY_TARGETS: tuple[str, ...] = (
    "tests/test_engine_observability_surfaces.py",
    "tests/test_engine_runtime_profiles_coverage.py",
    "tests/test_langfuse_adapter_payload.py",
    "tests/test_mvp4_diagnostics_integration.py",
    "tests/test_narrative_governance_api.py",
    "tests/test_return_movement_diagnostics.py",
    "tests/test_story_runtime_aspect_ledger.py",
    "tests/test_thin_path_summary_api.py",
    "tests/test_trace_middleware.py",
    "tests/test_trace_propagation_contract.py",
)
ENGINE_BLOCK_TARGETS: tuple[str, ...] = (
    *ENGINE_FOUNDATION_TARGETS,
    *ENGINE_HTTP_WS_TARGETS,
    *ENGINE_RUNTIME_TARGETS,
    *ENGINE_OPENING_CONTRACT_TARGETS,
    *ENGINE_PERSISTENCE_TARGETS,
    *ENGINE_OBSERVABILITY_TARGETS,
)

AI_STACK_GRAPH_TARGETS: tuple[str, ...] = (
    "ai_stack/tests/test_action_resolution_interact_fallback.py",
    "ai_stack/tests/test_adr0041_plan_projection_evidence.py",
    "ai_stack/tests/test_adr0041_runtime_graph_sidecar.py",
    "ai_stack/tests/test_ai_integration_with_session.py",
    "ai_stack/tests/test_goc_runtime_graph_seams_and_diagnostics.py",
    "ai_stack/tests/test_langgraph_agent_nodes.py",
    "ai_stack/tests/test_langgraph_orchestrator.py",
    "ai_stack/tests/test_langgraph_runtime.py",
    "ai_stack/tests/test_langgraph_state_schema.py",
    "ai_stack/tests/test_p0_action_resolution_regression.py",
    "ai_stack/tests/test_phase1_live_wiring.py",
    "ai_stack/tests/test_phase2_ws_session_loop.py",
    "ai_stack/tests/test_semantic_planner_graph_authority.py",
)
AI_STACK_GOC_TARGETS: tuple[str, ...] = (
    "ai_stack/tests/test_actor_lane_absence_governance.py",
    "ai_stack/tests/test_character_mind_goc.py",
    "ai_stack/tests/test_goc_closure_residuals.py",
    "ai_stack/tests/test_goc_director_surface_hints_yaml.py",
    "ai_stack/tests/test_goc_dramatic_alignment.py",
    "ai_stack/tests/test_goc_field_initialization_envelope.py",
    "ai_stack/tests/test_goc_frozen_vocab.py",
    "ai_stack/tests/test_goc_g9_roadmap_scenarios.py",
    "ai_stack/tests/test_goc_gate_evaluation.py",
    "ai_stack/tests/test_goc_knowledge_runtime_gates.py",
    "ai_stack/tests/test_goc_narrator_path.py",
    "ai_stack/tests/test_goc_npc_transcript_projection.py",
    "ai_stack/tests/test_goc_opening_transition.py",
    "ai_stack/tests/test_goc_roadmap_semantic_surface.py",
    "ai_stack/tests/test_goc_scene_identity.py",
    "ai_stack/tests/test_goc_scripted_continuation.py",
    "ai_stack/tests/test_goc_souffleuse.py",
    "ai_stack/tests/test_goc_structured_setting_knowledge.py",
    "ai_stack/tests/test_goc_transcript_shell_validation.py",
    "ai_stack/tests/test_human_input_attribution_visible_render.py",
    "ai_stack/tests/test_legacy_actor_lane_hydration.py",
    "ai_stack/tests/test_opening_narrator_contract.py",
    "ai_stack/tests/test_opening_sequence_bundle.py",
    "ai_stack/tests/test_opening_shape_normalizer.py",
    "ai_stack/tests/test_semantic_move_interpretation_goc.py",
    "ai_stack/tests/test_semantic_planner_contracts.py",
    "ai_stack/tests/test_semantic_scene_planner.py",
    "ai_stack/tests/test_wave1_closure_actor_contract.py",
    "ai_stack/tests/test_wave2_actor_truth_preservation.py",
    "ai_stack/tests/test_wave3_multi_actor_vitality.py",
    "ai_stack/tests/test_w5_actor_situation_extractor.py",
    "ai_stack/tests/test_w5_actor_situation_models.py",
    "ai_stack/tests/test_w5_actor_situation_projection.py",
    "ai_stack/tests/test_w5_actor_situation_validation.py",
)
AI_STACK_CAPABILITIES_TARGETS: tuple[str, ...] = (
    "ai_stack/tests/test_capabilities.py",
    "ai_stack/tests/test_capabilities_registry_handlers.py",
    "ai_stack/tests/test_capability_selector.py",
    "ai_stack/tests/test_capability_selector_runtime_projection.py",
    "ai_stack/tests/test_capability_validator_dispatch.py",
    "ai_stack/tests/test_capability_validator_dispatch_feature_flag.py",
    "ai_stack/tests/test_capability_validator_dispatch_plan_enforced.py",
    "ai_stack/tests/test_capability_validator_dispatch_runtime_projection.py",
    "ai_stack/tests/test_capability_validator_plan.py",
    "ai_stack/tests/test_capability_validator_registry.py",
    "ai_stack/tests/test_capability_validator_registry_inventory.py",
    "ai_stack/tests/test_capability_validator_runtime_projection.py",
    "ai_stack/tests/test_capability_validator_turn_class_coverage.py",
    "ai_stack/tests/test_canonical_path_resolver.py",
    "ai_stack/tests/test_canonical_prompt_catalog.py",
    "ai_stack/tests/test_canonical_step_ldss_output.py",
    "ai_stack/tests/test_director_capability_manager.py",
    "ai_stack/tests/test_free_player_action_resolution_contract.py",
    "ai_stack/tests/test_ldss_canonical_step_integration.py",
    "ai_stack/tests/test_player_action_intent_surface.py",
    "ai_stack/tests/test_player_action_resolution.py",
    "ai_stack/tests/test_validation_authority_bridge.py",
)
AI_STACK_NARRATIVE_TARGETS: tuple[str, ...] = (
    "ai_stack/tests/test_active_listening_contracts.py",
    "ai_stack/tests/test_callback_web_contracts.py",
    "ai_stack/tests/test_character_mind_data_driven.py",
    "ai_stack/tests/test_character_voice_runtime_enforcement.py",
    "ai_stack/tests/test_consequence_cascade_contracts.py",
    "ai_stack/tests/test_context_synthesis_engine.py",
    "ai_stack/tests/test_context_synthesis_retry_loop.py",
    "ai_stack/tests/test_dramatic_effect_contract.py",
    "ai_stack/tests/test_dramatic_effect_gate.py",
    "ai_stack/tests/test_dramatic_irony_runtime.py",
    "ai_stack/tests/test_environment_state_contracts.py",
    "ai_stack/tests/test_expectation_variation_engine.py",
    "ai_stack/tests/test_genre_awareness_engine.py",
    "ai_stack/tests/test_hierarchical_memory_contracts.py",
    "ai_stack/tests/test_improvisational_coherence_engine.py",
    "ai_stack/tests/test_information_disclosure_contracts.py",
    "ai_stack/tests/test_meta_narrative_awareness_engine.py",
    "ai_stack/tests/test_module_runtime_policy.py",
    "ai_stack/tests/test_narrative_aspect_contracts.py",
    "ai_stack/tests/test_narrative_momentum_engine.py",
    "ai_stack/tests/test_narrative_runtime_agent.py",
    "ai_stack/tests/test_narrator_consequence_contract.py",
    "ai_stack/tests/test_npc_agency_contracts.py",
    "ai_stack/tests/test_npc_agency_long_horizon_claim_readiness.py",
    "ai_stack/tests/test_npc_agency_planner.py",
    "ai_stack/tests/test_pacing_rhythm_engine.py",
    "ai_stack/tests/test_phase2_autonomous_tick.py",
    "ai_stack/tests/test_phase2_director_pulse.py",
    "ai_stack/tests/test_phase2_dual_mode.py",
    "ai_stack/tests/test_phase2_off_stage_updates.py",
    "ai_stack/tests/test_phase2_stage_f_capability_feeding.py",
    "ai_stack/tests/test_phase2_stage_g_off_stage_commits.py",
    "ai_stack/tests/test_phase2_stream_readiness.py",
    "ai_stack/tests/test_phase_c_reaction_order_governance.py",
    "ai_stack/tests/test_pi14_silence_negative_space.py",
    "ai_stack/tests/test_player_narrative_cards.py",
    "ai_stack/tests/test_pr_b_canonical_path_hold_effect_contract.py",
    "ai_stack/tests/test_pr_b_narrator_consequence_realization_contract.py",
    "ai_stack/tests/test_pr_c_director_pause_mode.py",
    "ai_stack/tests/test_relationship_state_machine.py",
    "ai_stack/tests/test_responder_reconciliation.py",
    "ai_stack/tests/test_return_movement_resolution.py",
    "ai_stack/tests/test_scene_direction_subdecision_matrix.py",
    "ai_stack/tests/test_scene_director_goc_extended.py",
    "ai_stack/tests/test_scene_energy_engine.py",
    "ai_stack/tests/test_sensory_context_engine.py",
    "ai_stack/tests/test_social_pressure_engine.py",
    "ai_stack/tests/test_social_state_goc.py",
    "ai_stack/tests/test_story_runtime_experience_policy.py",
    "ai_stack/tests/test_story_runtime_playability.py",
    "ai_stack/tests/test_symbolic_object_resonance_engine.py",
    "ai_stack/tests/test_temporal_control_engine.py",
    "ai_stack/tests/test_tonal_consistency_engine.py",
    "ai_stack/tests/test_visible_narrative_contract.py",
    "ai_stack/tests/test_wos_vsl_mvp_closure.py",
)
AI_STACK_RETRIEVAL_RESEARCH_TARGETS: tuple[str, ...] = (
    "ai_stack/tests/test_canon_improvement_contract.py",
    "ai_stack/tests/test_rag.py",
    "ai_stack/tests/test_research_aspect_golden.py",
    "ai_stack/tests/test_research_canon_improvement_golden.py",
    "ai_stack/tests/test_research_claims.py",
    "ai_stack/tests/test_research_contract_enforcement.py",
    "ai_stack/tests/test_research_exploration_bounded.py",
    "ai_stack/tests/test_research_exploration_golden.py",
    "ai_stack/tests/test_research_intake_golden.py",
    "ai_stack/tests/test_research_langgraph_extended.py",
    "ai_stack/tests/test_research_review_bundle_golden.py",
    "ai_stack/tests/test_research_store_extended.py",
    "ai_stack/tests/test_research_verification_golden.py",
    "ai_stack/tests/test_retrieval_governance_summary.py",
    "ai_stack/tests/test_retrieval_governance_wiring.py",
    "ai_stack/tests/test_retrieval_runtime_planner.py",
    "ai_stack/tests/test_semantic_embedding.py",
)
AI_STACK_QUALITY_TARGETS: tuple[str, ...] = (
    "ai_stack/tests/test_ai_config.py",
    "ai_stack/tests/test_ai_stack_package_exports.py",
    "ai_stack/tests/test_langchain_integration.py",
    "ai_stack/tests/test_langchain_reviver_compat.py",
    "ai_stack/tests/test_langfuse_evaluator_catalog.py",
    "ai_stack/tests/test_langfuse_evidence.py",
    "ai_stack/tests/test_mcp_agent_interface.py",
    "ai_stack/tests/test_mcp_canonical_surface.py",
    "ai_stack/tests/test_mcp_canonical_surface_extended.py",
    "ai_stack/tests/test_mcp_static_catalog.py",
    "ai_stack/tests/test_mcp_suite_map_complete.py",
    "ai_stack/tests/test_operational_profile.py",
    "ai_stack/tests/test_quality_lab_evaluator_catalog.py",
    "ai_stack/tests/test_quality_lab_judgment_interpreter.py",
    "ai_stack/tests/test_quality_lab_mcp_exchange_interpreter.py",
    "ai_stack/tests/test_quality_lab_pattern_and_planning.py",
    "ai_stack/tests/test_quality_lab_trace_interpreter.py",
    "ai_stack/tests/test_runtime_aspect_ledger.py",
    "ai_stack/tests/test_runtime_authority_aspects.py",
    "ai_stack/tests/test_runtime_quality_semantics.py",
    "ai_stack/tests/test_runtime_readiness_consumer.py",
    "ai_stack/tests/test_vitality_telemetry_v1.py",
    "ai_stack/tests/test_with_ai_reasoning_decorator.py",
)
AI_STACK_BLOCK_TARGETS: tuple[str, ...] = (
    *AI_STACK_GRAPH_TARGETS,
    *AI_STACK_GOC_TARGETS,
    *AI_STACK_CAPABILITIES_TARGETS,
    *AI_STACK_NARRATIVE_TARGETS,
    *AI_STACK_RETRIEVAL_RESEARCH_TARGETS,
    *AI_STACK_QUALITY_TARGETS,
)

# Human-readable titles for each component (English)
SUITE_DISPLAY_NAMES: dict[str, str] = {
    "backend": "Backend (Flask API and services)",
    "frontend": "Frontend (player/public UI)",
    "administration": "Administration tool (proxy and UI)",
    "engine": "World engine (runtime and HTTP/WS)",
    "database": "Database (migrations and tooling)",
    "writers_room": "Writers-Room workflow (human-in-the-loop production)",
    "improvement": "Improvement loop (mutation / evaluation / recommendation)",
    "ai_stack": "WOS AI stack (LangGraph runtime, RAG, Writers-Room / improvement seed graphs)",
    "story_runtime_core": "Story-runtime core (adapters, builtin templates, delivery)",
    "gates": "MVP foundation gates (architecture enforcement)",
    "root_core": "Repository root core tests",
    "root_integration": "Repository integration tests",
    "root_branching": "Repository branching tests",
    "root_smoke": "Repository smoke tests",
    "root_tools": "Repository tools tests",
    "tools_mcp_server": "wos-mcp stdio server (tools/mcp_server, registry, diagnostics)",
    "root_requirements_hygiene": "Repository requirements hygiene tests",
    "root_e2e_python": "Repository Python end-to-end tests",
    "root_experience_scoring": "Repository experience scoring tests",
    "playwright_e2e": "Playwright browser end-to-end tests",
    "compose_smoke": "Compose smoke lane",
    "mvp5": "MVP5 frontend (block renderer + typewriter + orchestration)",
    # Backend sub-suites (Stage 1 of backend-test-suite-split). Each is a strict subset
    # of ``backend`` and is meant for fast iteration; ``backend`` remains the canonical
    # full-suite gate. Coverage gates are disabled on these subsets because the backend
    # ``--cov-fail-under`` would always fail on a partial run.
    "backend_runtime": "Backend runtime (story_runtime, AI-turn cluster)",
    "backend_observability": "Backend observability (Langfuse, m11, diagnostics)",
    "backend_services": "Backend services layer",
    "backend_content": "Backend content (GoC / WoS canon / templates)",
    "backend_routes_core": "Backend HTTP routes (routes/, web/, api/)",
    "backend_mcp": "Backend MCP server tests",
    "backend_play": "Backend play/session and world-engine bridge contracts",
    "backend_rest": "Backend remainder (top-level + uncategorized tests/)",
    # World-engine focused blocks. These are iteration lanes; ``engine`` remains the
    # full-suite gate with coverage.
    "engine_foundation": "World engine foundation/config/security contracts",
    "engine_http_ws": "World engine HTTP and WebSocket API",
    "engine_runtime": "World engine story runtime internals",
    "engine_opening_contracts": "World engine opening and actor-lane contracts",
    "engine_persistence": "World engine persistence and branching",
    "engine_observability": "World engine observability and diagnostics",
    "engine_rest": "World engine remainder (top-level tests not in focused blocks)",
    # AI stack focused blocks. These run from repo root to avoid top-level ``langgraph``
    # shadowing by the local ``ai_stack/langgraph`` package directory.
    "ai_stack_graph": "AI stack LangGraph and thin-path graph contracts",
    "ai_stack_goc": "AI stack God of Carnage contract bundle",
    "ai_stack_capabilities": "AI stack capabilities and validation",
    "ai_stack_narrative": "AI stack narrative/player-facing runtime engines",
    "ai_stack_retrieval_research": "AI stack retrieval and research lanes",
    "ai_stack_quality": "AI stack quality, observability, and MCP surfaces",
    "ai_stack_rest": "AI stack remainder (tests not in focused blocks)",
}

# CLI --scope value -> pytest ``-m`` marker name (must exist in that component's pytest.ini)
SCOPE_TO_PYTEST_MARKER: dict[str, str] = {
    "contracts": "contract",
    "integration": "integration",
    "e2e": "e2e",
    "security": "security",
}

# CLI --domain value -> pytest ``-m`` marker name. Domain markers are registered in
# ``backend/pytest.ini`` (Stage 2 of backend-test-suite-split) and select cross-folder
# slices of the backend test tree. They combine with --scope via ``and`` so callers can
# write ``--scope contracts --domain auth`` to mean ``-m "contract and auth"``.
DOMAIN_TO_PYTEST_MARKER: dict[str, str] = {
    "auth": "auth",
    "observability": "observability",
    "runtime": "runtime",
    "routes_core": "routes_core",
    "content": "content",
    "services": "services",
    "writers_room": "writers_room",
    "improvement": "improvement",
    "mvp_handoff": "mvp_handoff",
}


def marker_filter_for_suite(suite_name: str, scope: str) -> str | None:
    """Return the marker expression for ``pytest -m`` if ``--scope`` applies to this suite.

    administration-tool and world-engine register ``contract``, ``integration``, and
    ``security`` but not ``e2e`` (see their ``pytest.ini``). Frontend, database, and
    ai_stack do not use this CLI mapping — returns ``None`` (full suite).
    """
    if scope == "all":
        return None
    marker = SCOPE_TO_PYTEST_MARKER.get(scope)
    if marker is None:
        return None
    cfg = SUITE_CONFIGS.get(suite_name)
    if not cfg or cfg.kind != "pytest" or not cfg.supports_scope:
        return None
    if suite_name in BACKEND_SUITE_FAMILY:
        return marker
    if suite_name == "administration" or suite_name in ENGINE_SUITE_FAMILY:
        if scope == "e2e":
            return None
        return marker
    return None


def domain_marker_for_suite(suite_name: str, domain: str) -> str | None:
    """Return the ``--domain`` marker name if the suite uses backend/pytest.ini.

    Domain markers are registered only in ``backend/pytest.ini``. ``backend`` and
    its Stage 1 sub-suites all share that ini; ``writers_room`` and ``improvement``
    use the same backend cwd. Other components ignore ``--domain``.
    """
    if domain == "all":
        return None
    marker = DOMAIN_TO_PYTEST_MARKER.get(domain)
    if marker is None:
        return None
    cfg = SUITE_CONFIGS.get(suite_name)
    if not cfg or cfg.kind != "pytest":
        return None
    if suite_name in BACKEND_SUITE_FAMILY:
        return marker
    return None


def combined_marker_expression(
    suite_name: str,
    scope: str,
    domain: str,
    extra_marker_clauses: tuple[str, ...] = (),
) -> str | None:
    """Combine ``--scope``, ``--domain``, and ``extra_marker_clauses`` via ``and``.

    Each side may be ``None``/``"all"``; missing clauses are dropped. ``extra_marker_clauses``
    are caller-supplied raw pytest marker expressions (e.g. ``"not serial"``) that are
    parenthesized and joined with the rest. Returns ``None`` if no clause survives.
    """
    scope_marker = marker_filter_for_suite(suite_name, scope)
    domain_marker = domain_marker_for_suite(suite_name, domain)
    parts: list[str] = []
    for m in (scope_marker, domain_marker):
        if m:
            parts.append(m)
    for clause in extra_marker_clauses:
        clause = (clause or "").strip()
        if clause:
            parts.append(f"({clause})")
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return " and ".join(parts)


def _capture_flags_for_suite(suite_name: str) -> list[str]:
    """Return suite-specific capture overrides.

    ``story_runtime_core`` is collected from the repository root but owns its own
    package-local pytest config. In some Windows/WSL workspaces pytest's default
    temp-file capture can disappear before teardown; disabling capture keeps the
    runner aligned with the direct command that is reliable locally and in CI.
    """
    if suite_name in {"story_runtime_core", "tools_mcp_server"}:
        return ["--capture=no"]
    return []

# Matches backend/pytest.ini coverage gate when running backend tests
BACKEND_COV_FAIL_UNDER = "85"
FRONTEND_COV_FAIL_UNDER = "90"
# World-engine: measure the app package through one Coverage.py source root.
# ``world-engine/.coveragerc`` owns the explicit omits for story-runtime host
# modules that are integration-heavy and would otherwise dominate the 90% gate.
ENGINE_COV_SOURCES: tuple[str, ...] = (WORLD_ENGINE_APP_ROOT,)
ENGINE_COV_FAIL_UNDER = "90"
DEFAULT_COV_FAIL_UNDER = "80"
# writers_room and improvement suites test only their own modules within the larger app package
# Overall app coverage will be low when these suites run alone (expected—untested modules drag average down)
# Instead, we check that the measured coverage (whatever modules ran) meets a minimal gate
WRITERS_ROOM_COV_FAIL_UNDER = "50"  # Realistic: only 3 modules tested out of ~30+ in app
IMPROVEMENT_COV_FAIL_UNDER = "50"   # Realistic: only 3 modules tested out of ~30+ in app
# story_runtime_core has adapters and utilities tested locally; builtin templates and branching modules
# are tested indirectly through world-engine and backend. Local-only gate is modest.
STORY_RUNTIME_CORE_COV_FAIL_UNDER = "80"  # Callback web + consequence cascade + intent contract covered in-package

# administration-tool: use ``--cov=.`` + ``administration-tool/.coveragerc`` (single source
# trace) — do not list multiple ``--cov=module`` names; Coverage 7.x warns on import order.

@dataclass(frozen=True)
class SuiteConfig:
    """Configuration for one runnable suite.

    ``extra_targets`` and ``ignore_paths`` are additive fields used by the backend
    sub-suite split (Stage 1 of docs/plan backend-test-suite-split). ``extra_targets``
    are appended after ``target`` as additional positional pytest arguments so a single
    suite can run multiple subpaths in one pytest invocation. ``ignore_paths`` are
    emitted as ``--ignore=<path>`` pytest flags so a "rest of backend/tests" suite can
    subtract the directories already covered by other sub-suites. Both fields default
    to empty tuples; bare ``target`` semantics are preserved for every existing suite.
    """

    kind: str  # "pytest" or "external"
    cwd: Path
    target: str
    supports_scope: bool = False
    supports_coverage: bool = True
    extra_targets: tuple[str, ...] = ()
    ignore_paths: tuple[str, ...] = ()


STORY_RUNTIME_CORE_DIR = PROJECT_ROOT / "story_runtime_core"


def _pytest_slice(
    *,
    cwd: Path,
    targets: tuple[str, ...],
    supports_scope: bool = False,
    ignore_paths: tuple[str, ...] = (),
) -> SuiteConfig:
    """Build a partial-suite config from one or more explicit pytest targets."""
    if not targets:
        raise ValueError("pytest slice requires at least one target")
    return SuiteConfig(
        kind="pytest",
        cwd=cwd,
        target=targets[0],
        supports_scope=supports_scope,
        supports_coverage=False,
        extra_targets=targets[1:],
        ignore_paths=ignore_paths,
    )

SUITE_CONFIGS: dict[str, SuiteConfig] = {
    # Component suites
    "backend": SuiteConfig(kind="pytest", cwd=BACKEND_DIR, target="tests", supports_scope=True),
    "frontend": SuiteConfig(kind="pytest", cwd=FRONTEND_DIR, target="tests"),
    "administration": SuiteConfig(kind="pytest", cwd=ADMIN_TOOL_DIR, target="tests", supports_scope=True),
    "engine": SuiteConfig(kind="pytest", cwd=WORLD_ENGINE_DIR, target="tests", supports_scope=True),
    "database": SuiteConfig(kind="pytest", cwd=DATABASE_DIR, target="tests"),
    "writers_room": SuiteConfig(kind="pytest", cwd=BACKEND_DIR, target="tests/writers_room", supports_scope=True),
    "improvement": SuiteConfig(kind="pytest", cwd=BACKEND_DIR, target="tests/improvement", supports_scope=True),
    # Writers-Room / improvement seed graphs and runtime turn graph; imports require repo root on PYTHONPATH.
    "ai_stack": SuiteConfig(kind="pytest", cwd=PROJECT_ROOT, target="ai_stack/tests"),
    # Story-runtime core: builtin templates, adapters, delivery.
    "story_runtime_core": SuiteConfig(kind="pytest", cwd=PROJECT_ROOT, target="story_runtime_core/tests"),
    # Architecture enforcement gates: visitor absence, runtime-profile/content-module separation.
    # Gates tests import from world-engine app (app.governance.*) and story_runtime_core; the
    # gates/conftest.py adds world-engine to sys.path automatically.
    "gates": SuiteConfig(kind="pytest", cwd=PROJECT_ROOT, target="tests/gates", supports_coverage=False),
    # Root-level Python suites
    "root_core": SuiteConfig(kind="pytest", cwd=PROJECT_ROOT, target="tests/test_agency_capability_matrix_truth.py", supports_coverage=False),
    "root_integration": SuiteConfig(kind="pytest", cwd=PROJECT_ROOT, target="tests/integration", supports_coverage=False),
    "root_branching": SuiteConfig(kind="pytest", cwd=PROJECT_ROOT, target="tests/branching", supports_coverage=False),
    "root_smoke": SuiteConfig(kind="pytest", cwd=PROJECT_ROOT, target="tests/smoke", supports_coverage=False),
    "root_tools": SuiteConfig(kind="pytest", cwd=PROJECT_ROOT, target="tests/tools", supports_coverage=False),
    "tools_mcp_server": SuiteConfig(
        kind="pytest", cwd=PROJECT_ROOT, target="tools/mcp_server/tests",
        supports_coverage=False,
    ),
    "root_requirements_hygiene": SuiteConfig(
        kind="pytest", cwd=PROJECT_ROOT, target="tests/requirements_hygiene", supports_coverage=False
    ),
    "root_e2e_python": SuiteConfig(kind="pytest", cwd=PROJECT_ROOT, target="tests/e2e", supports_coverage=False),
    "root_experience_scoring": SuiteConfig(
        kind="pytest", cwd=PROJECT_ROOT, target="tests/experience_scoring_cli", supports_coverage=False
    ),
    # MVP5: Frontend block rendering, typewriter, orchestration
    "mvp5": SuiteConfig(kind="pytest", cwd=FRONTEND_DIR, target="tests", supports_coverage=False),
    # --- Backend sub-suites (Stage 1 of backend-test-suite-split) ---
    # All share cwd=BACKEND_DIR with ``backend``. Coverage gates are off so partial
    # runs do not trip the backend-wide ``--cov-fail-under`` threshold.
    "backend_runtime": SuiteConfig(
        kind="pytest", cwd=BACKEND_DIR, target="tests/runtime",
        supports_scope=True, supports_coverage=False,
    ),
    "backend_observability": SuiteConfig(
        kind="pytest", cwd=BACKEND_DIR, target="tests/test_observability",
        supports_scope=True, supports_coverage=False,
        extra_targets=("tests/test_observability.py", "tests/test_m11_ai_stack_observability.py"),
    ),
    "backend_services": SuiteConfig(
        kind="pytest", cwd=BACKEND_DIR, target="tests/services",
        supports_scope=True, supports_coverage=False,
    ),
    "backend_content": SuiteConfig(
        kind="pytest", cwd=BACKEND_DIR, target="tests/content",
        supports_scope=True, supports_coverage=False,
    ),
    "backend_routes_core": SuiteConfig(
        kind="pytest", cwd=BACKEND_DIR, target="tests/routes",
        supports_scope=True, supports_coverage=False,
        extra_targets=("tests/web", "tests/api"),
    ),
    "backend_mcp": SuiteConfig(
        kind="pytest", cwd=BACKEND_DIR, target="tests/mcp",
        supports_scope=True, supports_coverage=False,
    ),
    "backend_play": _pytest_slice(
        cwd=BACKEND_DIR,
        targets=BACKEND_PLAY_TARGETS,
        supports_scope=True,
    ),
    # ``backend_rest`` runs ``backend/tests`` but subtracts every directory and explicit
    # file already covered by the other sub-suites above (and writers_room/improvement
    # which have their own component suites). Coverage off; ordering preserved.
    "backend_rest": SuiteConfig(
        kind="pytest", cwd=BACKEND_DIR, target="tests",
        supports_scope=True, supports_coverage=False,
        ignore_paths=(
            "tests/runtime",
            "tests/services",
            "tests/content",
            "tests/test_observability",
            "tests/routes",
            "tests/web",
            "tests/api",
            "tests/mcp",
            "tests/writers_room",
            "tests/improvement",
            "tests/test_observability.py",
            "tests/test_m11_ai_stack_observability.py",
            *BACKEND_PLAY_TARGETS,
        ),
    ),
    # --- World-engine focused blocks ---
    # These are partial lanes for systematic checks while changing the runtime. The
    # canonical ``engine`` suite remains the full coverage gate.
    "engine_foundation": _pytest_slice(
        cwd=WORLD_ENGINE_DIR,
        targets=ENGINE_FOUNDATION_TARGETS,
        supports_scope=True,
    ),
    "engine_http_ws": _pytest_slice(
        cwd=WORLD_ENGINE_DIR,
        targets=ENGINE_HTTP_WS_TARGETS,
        supports_scope=True,
    ),
    "engine_runtime": _pytest_slice(
        cwd=WORLD_ENGINE_DIR,
        targets=ENGINE_RUNTIME_TARGETS,
        supports_scope=True,
    ),
    "engine_opening_contracts": _pytest_slice(
        cwd=WORLD_ENGINE_DIR,
        targets=ENGINE_OPENING_CONTRACT_TARGETS,
        supports_scope=True,
    ),
    "engine_persistence": _pytest_slice(
        cwd=WORLD_ENGINE_DIR,
        targets=ENGINE_PERSISTENCE_TARGETS,
        supports_scope=True,
    ),
    "engine_observability": _pytest_slice(
        cwd=WORLD_ENGINE_DIR,
        targets=ENGINE_OBSERVABILITY_TARGETS,
        supports_scope=True,
    ),
    "engine_rest": _pytest_slice(
        cwd=WORLD_ENGINE_DIR,
        targets=("tests",),
        supports_scope=True,
        ignore_paths=ENGINE_BLOCK_TARGETS,
    ),
    # --- AI-stack focused blocks ---
    # All run from the repository root so the installed external ``langgraph`` package is
    # not shadowed by the local ``ai_stack/langgraph`` package directory.
    "ai_stack_graph": _pytest_slice(cwd=PROJECT_ROOT, targets=AI_STACK_GRAPH_TARGETS),
    "ai_stack_goc": _pytest_slice(cwd=PROJECT_ROOT, targets=AI_STACK_GOC_TARGETS),
    "ai_stack_capabilities": _pytest_slice(cwd=PROJECT_ROOT, targets=AI_STACK_CAPABILITIES_TARGETS),
    "ai_stack_narrative": _pytest_slice(cwd=PROJECT_ROOT, targets=AI_STACK_NARRATIVE_TARGETS),
    "ai_stack_retrieval_research": _pytest_slice(cwd=PROJECT_ROOT, targets=AI_STACK_RETRIEVAL_RESEARCH_TARGETS),
    "ai_stack_quality": _pytest_slice(cwd=PROJECT_ROOT, targets=AI_STACK_QUALITY_TARGETS),
    "ai_stack_rest": _pytest_slice(
        cwd=PROJECT_ROOT,
        targets=("ai_stack/tests",),
        ignore_paths=AI_STACK_BLOCK_TARGETS,
    ),
    # Optional external lanes
    "playwright_e2e": SuiteConfig(kind="external", cwd=PROJECT_ROOT / "tests" / "e2e", target="npx playwright test"),
    "compose_smoke": SuiteConfig(
        kind="external", cwd=PROJECT_ROOT / "tests" / "smoke" / "compose_smoke", target="./smoke_curl.sh"
    ),
}

# Suites run for ``--suite all`` (order preserved). This now includes all Python
# suite groups in the repository; optional non-Python lanes remain opt-in flags.
ALL_SUITE_SEQUENCE: tuple[str, ...] = (
    "backend",
    "frontend",
    "administration",
    "engine",
    "database",
    "ai_stack",
    "story_runtime_core",
    "gates",
    "root_core",
    "root_integration",
    "root_branching",
    "root_smoke",
    "root_tools",
    "tools_mcp_server",
    "root_requirements_hygiene",
    "root_e2e_python",
    "root_experience_scoring",
)


class Colors:
    OKBLUE = "\033[0;34m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str) -> None:
    line = "=" * 70
    print(f"{Colors.OKBLUE}{line}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{line}{Colors.ENDC}")


def print_success(text: str) -> None:
    print(f"{Colors.OKGREEN}[OK] {text}{Colors.ENDC}")


def print_error(text: str) -> None:
    print(f"{Colors.FAIL}[FAIL] {text}{Colors.ENDC}")


def print_info(text: str) -> None:
    print(f"{Colors.WARNING}[INFO] {text}{Colors.ENDC}")


def _import_probe(
    *,
    cwd: Path,
    py_code: str,
    env_overrides: dict[str, str] | None = None,
    timeout_s: int = 90,
) -> tuple[bool, str]:
    """Run ``python -c <py_code>`` in ``cwd``; return (ok, stderr_or_stdout_snippet)."""
    env = dict(os.environ)
    if env_overrides:
        env.update(env_overrides)
    try:
        proc = subprocess.run(
            [sys.executable, "-c", py_code],
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout_s}s"
    except OSError as exc:
        return False, str(exc)
    if proc.returncode == 0:
        return True, ""
    out = (proc.stderr or "").strip() or (proc.stdout or "").strip()
    return False, out[:1200]


def _probe_ai_stack_langgraph_lane() -> tuple[bool, str]:
    """Same LangChain / LangGraph / export surface as CI (``ai_stack-tests.yml``, engine job)."""
    graph_py = (
        "import traceback\n"
        "import langchain_core, ai_stack\n"
        "import langgraph\n"
        "if not ai_stack.LANGGRAPH_RUNTIME_EXPORT_AVAILABLE:\n"
        "    print('LANGGRAPH_RUNTIME_EXPORT_ERROR=' + repr(getattr(ai_stack, 'LANGGRAPH_RUNTIME_EXPORT_ERROR', None)))\n"
        "    try:\n"
        "        import ai_stack.langgraph.langgraph_runtime\n"
        "        print('direct_import_ai_stack.langgraph.langgraph_runtime=ok')\n"
        "    except Exception:\n"
        "        traceback.print_exc()\n"
        "    raise AssertionError('pip install -e ./story_runtime_core -e \"./ai_stack[test]\" from repo root')\n"
        "from ai_stack import RuntimeTurnGraphExecutor\n"
        "assert RuntimeTurnGraphExecutor is not None\n"
    )
    return _import_probe(
        cwd=PROJECT_ROOT,
        py_code=graph_py,
        env_overrides={"PYTHONPATH": str(PROJECT_ROOT)},
    )


def check_environment(suites: dict[str, SuiteConfig]) -> bool:
    """Verify pytest and runtime deps for the **selected** suites.

    The runner's own interpreter only needs ``pytest``. Backend/engine/ai_stack tests
    run with component-local ``cwd`` and ``PYTHONPATH`` like CI; we probe those the
    same way so a missing ``flask`` (etc.) fails here instead of after a misleading OK.
    """
    print_header("Environment check")
    ok = True
    try:
        import pytest

        print_success(f"pytest (runner interpreter): {pytest.__version__}")
    except ImportError:
        print_error("pytest is not installed in the active interpreter. Install test deps (e.g. pip install pytest).")
        return False
    try:
        import coverage

        print_success(f"coverage (runner interpreter): {coverage.__version__}")
    except ImportError:
        print_info("coverage not installed in the active interpreter (optional unless you use --coverage).")

    labels = set(suites.keys())
    if not labels:
        print_info("No suites selected; skipping stack probes.")
        print()
        return True

    # --- Same import surface as backend / database / writers_room / improvement / frontend conftests ---
    needs_backend_stack = bool(
        (labels & set(BACKEND_SUITE_FAMILY))
        or (
            labels
            & {
                "frontend",
                "administration",
                "database",
                "root_core",
                "root_integration",
                "root_branching",
                "root_smoke",
                "root_tools",
                "root_requirements_hygiene",
                "root_e2e_python",
                "root_experience_scoring",
                "gates",
            }
        )
    )
    if needs_backend_stack:
        print_info("Probing backend Flask stack (cwd=backend, PYTHONPATH=backend) …")
        py = (
            "import flask, flask_sqlalchemy, sqlalchemy, flask_jwt_extended, werkzeug\n"
            "import pydantic\n"
        )
        env_py = os.environ.get("PYTHONPATH", "")
        merged = str(BACKEND_DIR)
        if env_py:
            merged = merged + os.pathsep + env_py
        passed, err = _import_probe(
            cwd=BACKEND_DIR,
            py_code=py,
            env_overrides={"PYTHONPATH": merged},
        )
        if passed:
            print_success(
                "Backend-related suites: Flask, Flask-SQLAlchemy, SQLAlchemy, "
                "Flask-JWT-Extended, Werkzeug, Pydantic importable (see backend/requirements*.txt)."
            )
        else:
            ok = False
            print_error(
                "Backend stack import probe failed. Install backend dependencies, for example: "
                "`cd backend && pip install -r requirements-dev.txt` (or requirements.txt), then retry."
            )
            if err:
                print_info(err)

        opt_passed, opt_err = _import_probe(
            cwd=PROJECT_ROOT,
            py_code="import ai_stack.langgraph.langgraph_runtime",
            env_overrides={"PYTHONPATH": str(PROJECT_ROOT)},
        )
        if not opt_passed:
            print_info(
                "Optional: some backend tests import ``ai_stack.langgraph.langgraph_runtime``. "
                "If those fail: ``pip install -e ./story_runtime_core -e \\\"./ai_stack[test]\\\"`` "
                f"from repo root. ({opt_err[:400]})" if opt_err else ""
            )

    if "frontend" in labels:
        print_info("Probing frontend Flask stack (cwd=frontend, PYTHONPATH=frontend) …")
        fe_py = "import flask, requests\n"
        fe_merged = str(FRONTEND_DIR)
        fe_env = os.environ.get("PYTHONPATH", "")
        if fe_env:
            fe_merged = fe_merged + os.pathsep + fe_env
        fe_passed, fe_err = _import_probe(
            cwd=FRONTEND_DIR,
            py_code=fe_py,
            env_overrides={"PYTHONPATH": fe_merged},
        )
        if fe_passed:
            print_success("Frontend suite: Flask and Requests importable (see frontend/pyproject.toml).")
        else:
            ok = False
            print_error(
                "Frontend stack import probe failed. Install frontend deps, for example: "
                "`pip install -r frontend/requirements-dev.txt` or `pip install -e ./frontend[test]`."
            )
            if fe_err:
                print_info(fe_err)

    if "administration" in labels:
        print_info("Probing administration-tool Flask stack …")
        ad_py = "import flask, werkzeug\n"
        ad_merged = str(ADMIN_TOOL_DIR)
        ad_env = os.environ.get("PYTHONPATH", "")
        if ad_env:
            ad_merged = ad_merged + os.pathsep + ad_env
        ad_passed, ad_err = _import_probe(
            cwd=ADMIN_TOOL_DIR,
            py_code=ad_py,
            env_overrides={"PYTHONPATH": ad_merged},
        )
        if ad_passed:
            print_success("Administration suite: Flask and Werkzeug importable (see administration-tool/pyproject.toml).")
        else:
            ok = False
            print_error(
                "Administration-tool stack import probe failed. Install deps, for example: "
                "`pip install -r administration-tool/requirements-dev.txt`."
            )
            if ad_err:
                print_info(ad_err)

    # --- World engine (FastAPI app package ``app`` under world-engine/) ---
    if labels & set(ENGINE_SUITE_FAMILY):
        print_info("Probing world-engine stack (cwd=world-engine, PYTHONPATH=repo+world-engine) …")
        sep = os.pathsep
        we_py = f"{WORLD_ENGINE_DIR}{sep}{PROJECT_ROOT}"
        py = "import fastapi, sqlalchemy, httpx\n"
        passed, err = _import_probe(
            cwd=WORLD_ENGINE_DIR,
            py_code=py,
            env_overrides={"PYTHONPATH": we_py},
        )
        if passed:
            print_success(
                "World engine suite: FastAPI, SQLAlchemy, HTTPX importable "
                "(see world-engine/requirements.txt and requirements-dev.txt)."
            )
        else:
            ok = False
            print_error(
                "World-engine stack import probe failed. Install engine deps, for example: "
                "`pip install -r world-engine/requirements-dev.txt`, then retry."
            )
            if err:
                print_info(err)

        print_info("Probing ai_stack LangGraph export (StoryRuntimeManager imports RuntimeTurnGraphExecutor) …")
        g_passed, g_err = _probe_ai_stack_langgraph_lane()
        if g_passed:
            print_success("World engine suite: LangChain/LangGraph OK; RuntimeTurnGraphExecutor exported from ai_stack.")
        else:
            ok = False
            print_error(
                "ai_stack LangGraph surface not importable with repo root on PYTHONPATH. "
                "From repo root: `pip install -e ./story_runtime_core` and `pip install -e \"./ai_stack[test]\"`."
            )
            if g_err:
                print_info(g_err)

    # --- ai_stack (repo root on PYTHONPATH; editable installs per CI) ---
    if labels & set(AI_STACK_SUITE_FAMILY):
        print_info("Probing ai_stack (cwd=repo root, PYTHONPATH=repo) …")
        sep = os.pathsep
        root_py = str(PROJECT_ROOT)
        existing = os.environ.get("PYTHONPATH", "")
        if existing:
            root_py = root_py + sep + existing
        py = (
            "import importlib.util\n"
            "for mod in ('story_runtime_core', 'ai_stack'):\n"
            "    assert importlib.util.find_spec(mod), f'missing package: {mod}'\n"
        )
        passed, err = _import_probe(
            cwd=PROJECT_ROOT,
            py_code=py,
            env_overrides={"PYTHONPATH": root_py},
        )
        if passed:
            print_success("ai_stack suite: story_runtime_core and ai_stack importable from repo root.")
        else:
            ok = False
            print_error(
                "ai_stack import probe failed. From repo root run: "
                "`pip install -e ./story_runtime_core -e ./ai_stack[test]` "
                "(same as .github/workflows/ai-stack-tests.yml), then retry."
            )
            if err:
                print_info(err)

        print_info("Probing ai_stack LangChain / LangGraph graph lane (merge bar; same as CI) …")
        g_passed, g_err = _probe_ai_stack_langgraph_lane()
        if g_passed:
            print_success(
                "ai_stack suite: langchain_core, langgraph importable; LANGGRAPH_RUNTIME_EXPORT_AVAILABLE and "
                "RuntimeTurnGraphExecutor OK."
            )
        else:
            ok = False
            print_error(
                "ai_stack graph lane failed (often ModuleNotFoundError: langchain_core). "
                "From repo root: ``pip install -e ./story_runtime_core -e \\\"./ai_stack[test]\\\"`` "
                "or ``pip install -r ai_stack/requirements-test.txt`` plus editable ``ai_stack``."
            )
            if g_err:
                print_info(g_err)

    if "tools_mcp_server" in labels:
        print_info("Probing tools/mcp_server stack (cwd=repo root) …")
        passed, err = _import_probe(
            cwd=PROJECT_ROOT,
            py_code="import pydantic, requests\n",
            env_overrides={"PYTHONPATH": str(PROJECT_ROOT)},
        )
        if passed:
            print_success("tools_mcp_server suite: Pydantic and Requests importable (see tools/mcp_server/pyproject.toml).")
        else:
            ok = False
            print_error(
                "tools_mcp_server import probe failed. From repo root run: "
                "`pip install -e \"./tools/mcp_server[test]\"`, then retry."
            )
            if err:
                print_info(err)

    print()
    return ok


def _subprocess_env_for_suite(suite_name: str) -> dict[str, str] | None:
    """Put repo root and/or world-engine on PYTHONPATH for suites that require them."""
    if (
        suite_name not in AI_STACK_SUITE_FAMILY
        and suite_name not in ENGINE_SUITE_FAMILY
        and suite_name not in ("gates", "story_runtime_core")
    ):
        return None
    env = dict(os.environ)
    sep = os.pathsep
    existing = env.get("PYTHONPATH", "")
    parts = [p for p in existing.split(sep) if p]
    wanted = [str(PROJECT_ROOT)]
    if suite_name in ENGINE_SUITE_FAMILY or suite_name in AI_STACK_SUITE_FAMILY or suite_name == "gates":
        wanted.append(str(WORLD_ENGINE_DIR))
    if suite_name == "gates":
        wanted.append(str(BACKEND_DIR))
    parts = wanted + [p for p in parts if p not in wanted]
    env["PYTHONPATH"] = sep.join(parts)
    return env


def show_test_stats(suites: dict[str, SuiteConfig], *, scope: str = "all", domain: str = "all") -> bool:
    """Run collect-only per suite. Returns False if any collection subprocess fails."""
    print_header("Test collection (collect-only)")
    all_ok = True
    for suite_name, cfg in suites.items():
        if cfg.kind != "pytest":
            continue
        suite_cwd, test_path = cfg.cwd, cfg.target
        targets_to_check = (test_path, *cfg.extra_targets)
        missing = [tp for tp in targets_to_check if not ((suite_cwd / tp).is_dir() or (suite_cwd / tp).is_file())]
        if missing:
            print_info(f"{suite_name}: no tests directory or file ({', '.join(str(suite_cwd / tp) for tp in missing)})")
            continue
        collect_argv = ["--collect-only", "-q", "--no-cov", *_capture_flags_for_suite(suite_name)]
        m = combined_marker_expression(suite_name, scope, domain)
        if m:
            collect_argv.extend(["-m", m])
        for ignore in cfg.ignore_paths:
            collect_argv.append(f"--ignore={ignore}")
        collect_argv.append(test_path)
        collect_argv.extend(cfg.extra_targets)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", *collect_argv],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(suite_cwd),
                env=_subprocess_env_for_suite(suite_name) or os.environ,
            )
            out = (result.stdout or "") + (result.stderr or "")
            if result.returncode != 0:
                all_ok = False
                print_error(
                    f"{suite_name}: pytest --collect-only failed (exit {result.returncode})."
                )
                tail = "\n".join((result.stderr or result.stdout or "").strip().split("\n")[-12:])
                if tail.strip():
                    print_info(tail)
                continue
            collected_line = None
            for line in out.split("\n"):
                if "collected" in line.lower() and any(c.isdigit() for c in line):
                    collected_line = line.strip()
                    break
            if collected_line:
                print_info(f"{suite_name}: {collected_line}")
            else:
                all_ok = False
                print_error(f"{suite_name}: could not parse collection output (exit 0).")
        except Exception as exc:
            all_ok = False
            print_error(f"{suite_name}: collect-only failed ({exc})")
    print()
    return all_ok


def get_suite_configs(
    suite_names: list[str], *, with_playwright: bool = False, with_compose_smoke: bool = False
) -> dict[str, SuiteConfig]:
    all_suites = dict(SUITE_CONFIGS)
    if "all" in suite_names:
        result = {name: all_suites[name] for name in ALL_SUITE_SEQUENCE if name in all_suites}
    else:
        result: dict[str, SuiteConfig] = {}
        for name in suite_names:
            if name in all_suites:
                result[name] = all_suites[name]
            else:
                print_error(f"Unknown suite: {name}")
        if not result:
            result = {name: all_suites[name] for name in ALL_SUITE_SEQUENCE if name in all_suites}

    if with_playwright:
        result["playwright_e2e"] = all_suites["playwright_e2e"]
    if with_compose_smoke:
        result["compose_smoke"] = all_suites["compose_smoke"]
    return result


def _cov_fail_under_for_suite(suite_name: str) -> str | None:
    cfg = SUITE_CONFIGS.get(suite_name)
    if cfg and not cfg.supports_coverage:
        return None
    if suite_name == "backend":
        return BACKEND_COV_FAIL_UNDER
    if suite_name == "frontend":
        return FRONTEND_COV_FAIL_UNDER
    if suite_name == "writers_room":
        return WRITERS_ROOM_COV_FAIL_UNDER
    if suite_name == "improvement":
        return IMPROVEMENT_COV_FAIL_UNDER
    if suite_name == "story_runtime_core":
        return STORY_RUNTIME_CORE_COV_FAIL_UNDER
    if suite_name == "engine":
        return ENGINE_COV_FAIL_UNDER
    if suite_name == "database":
        # ``database/tests`` touch a thin slice of ``backend/app``; gating the whole tree is misleading.
        return None
    return DEFAULT_COV_FAIL_UNDER


def _cov_sources_for_suite(suite_name: str) -> list[str]:
    """Return one or more ``pytest-cov`` ``--cov=`` sources (explicit paths or import names).

    Avoids ``--cov=.`` for monorepo components so reports target the real package(s) under test.
    Exception: **administration** uses ``--cov=.`` with a local ``.coveragerc`` (flat layout;
    multiple named modules break Coverage.py tracing). See :func:`_append_cov_flags`.
    ``database`` suite measures ``backend/app`` because schema tests import ORM models there
    (there is no separate ``database/`` Python package — only ``database/tests``).
    """
    cfg = SUITE_CONFIGS.get(suite_name)
    if cfg and not cfg.supports_coverage:
        return []
    if suite_name in ("backend", "writers_room", "improvement", "database"):
        return [BACKEND_APP_ROOT]
    if suite_name == "frontend":
        return [FRONTEND_APP_ROOT]
    if suite_name == "engine":
        return list(ENGINE_COV_SOURCES)
    if suite_name == "administration":
        return []
    if suite_name == "ai_stack":
        return [AI_STACK_ROOT]
    if suite_name == "story_runtime_core":
        return ["story_runtime_core"]
    return ["."]


def _append_cov_flags(argv: list[str], suite_name: str) -> None:
    """Append ``--cov=…`` (and administration/story_runtime_core ``--cov-config``) for the suite."""
    cfg = SUITE_CONFIGS.get(suite_name)
    if cfg and not cfg.supports_coverage:
        return
    if suite_name == "administration":
        argv.append("--cov=.")
        argv.append(f"--cov-config={ADMIN_TOOL_DIR / '.coveragerc'}")
        return
    if suite_name == "story_runtime_core":
        argv.append("--cov=story_runtime_core")
        argv.append(f"--cov-config={PROJECT_ROOT / 'story_runtime_core' / '.coveragerc'}")
        return
    for src in _cov_sources_for_suite(suite_name):
        argv.append(f"--cov={src}")
    if suite_name == "engine":
        cfg_path = WORLD_ENGINE_DIR / ".coveragerc"
        if cfg_path.is_file():
            argv.append(f"--cov-config={cfg_path}")


def build_pytest_argv(
    *,
    suite_name: str,
    test_path: str,
    quick: bool,
    coverage_mode: bool,
    verbose: bool,
    scope: str,
    domain: str = "all",
    extra_targets: tuple[str, ...] = (),
    ignore_paths: tuple[str, ...] = (),
    parallel: str | None = None,
    extra_marker_clauses: tuple[str, ...] = (),
) -> list[str]:
    """Build pytest arguments for one component run (cwd = suite working directory).

    ``extra_targets`` are appended after ``target`` as additional positional pytest
    arguments. ``ignore_paths`` are emitted as ``--ignore=<path>`` pytest flags
    (placed before the positional targets, where pytest expects them). ``scope`` and
    ``domain`` markers combine via ``and`` (see :func:`combined_marker_expression`).
    ``parallel`` (``"auto"`` or a numeric string) enables pytest-xdist with
    ``--dist loadfile`` so tests inside one file stay on one worker (Stage 3 of
    backend-test-suite-split); ``None`` keeps the default sequential behavior.
    """
    cov_under = _cov_fail_under_for_suite(suite_name)

    def _append_cov_fail_under(argv_inner: list[str]) -> None:
        if cov_under is not None:
            argv_inner.append(f"--cov-fail-under={cov_under}")

    def _append_parallel(argv_inner: list[str]) -> None:
        if parallel:
            argv_inner.extend(["-n", str(parallel), "--dist", "loadfile"])

    def _append_targets(argv_inner: list[str]) -> None:
        for ignore in ignore_paths:
            argv_inner.append(f"--ignore={ignore}")
        argv_inner.append(test_path)
        argv_inner.extend(extra_targets)

    if quick:
        argv = ["-v", "--tb=short", "--no-cov", "-x", *_capture_flags_for_suite(suite_name)]
        m = combined_marker_expression(suite_name, scope, domain, extra_marker_clauses)
        if m:
            argv.extend(["-m", m])
        _append_parallel(argv)
        _append_targets(argv)
        return argv

    if coverage_mode:
        argv = ["-v", "--tb=short", *_capture_flags_for_suite(suite_name)]
        _append_cov_flags(argv, suite_name)
        argv.extend(
            [
                "--cov-report=term-missing:skip-covered",
                "--cov-report=html",
            ]
        )
        _append_cov_fail_under(argv)
    elif verbose:
        argv = ["-vv", "--tb=long", "-s"]
        _append_cov_flags(argv, suite_name)
        argv.extend(
            [
                "--cov-report=term-missing",
            ]
        )
        _append_cov_fail_under(argv)
    else:
        argv = ["-v", "--tb=short", *_capture_flags_for_suite(suite_name)]
        _append_cov_flags(argv, suite_name)
        argv.extend(
            [
                "--cov-report=term-missing",
            ]
        )
        _append_cov_fail_under(argv)

    m = combined_marker_expression(suite_name, scope, domain, extra_marker_clauses)
    if m:
        argv.extend(["-m", m])

    _append_parallel(argv)
    _append_targets(argv)
    return argv


def run_frontend_jest_lane(suite_name: str) -> bool:
    """Run Jest for ``frontend/tests/*.js`` (play shell modules). Used after pytest for frontend/mvp5."""
    import shutil

    display = SUITE_DISPLAY_NAMES.get(suite_name, suite_name)
    pkg = FRONTEND_DIR / "package.json"
    jest_cfg = FRONTEND_DIR / "jest.config.cjs"
    if not pkg.is_file() or not jest_cfg.is_file():
        print_error("frontend Jest lane requires frontend/package.json and frontend/jest.config.cjs")
        return False
    npm = "npm.cmd" if os.name == "nt" else "npm"
    node = "node.exe" if os.name == "nt" else "node"
    if shutil.which(npm) is None:
        print_error("npm is not in PATH; cannot run frontend Jest tests.")
        return False
    if shutil.which(node) is None:
        print_error("node is not in PATH; cannot run frontend Jest tests.")
        return False
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.is_dir():
        print_info("frontend: installing npm devDependencies (first Jest run) …")
        inst = subprocess.run(
            [npm, "install", "--no-audit", "--no-fund"],
            cwd=str(FRONTEND_DIR),
        )
        if inst.returncode != 0:
            print_error("npm install failed in frontend/")
            return False
    print_header(f"Running: {display} — Jest (frontend/tests/*.js)")
    test = subprocess.run([npm, "test", "--", "--ci"], cwd=str(FRONTEND_DIR))
    if test.returncode != 0:
        print_error("frontend Jest tests failed")
        return False
    print_success("frontend Jest tests passed")
    return True


def run_pytest(
    suite_name: str,
    suite_cwd: Path,
    test_path: str,
    pytest_argv: list[str],
    run_title: str,
    extra_targets: tuple[str, ...] = (),
    acceptable_exit_codes: tuple[int, ...] = (0,),
) -> bool:
    """Run pytest in a subprocess and return True iff its exit code is acceptable.

    By default, only ``0`` counts as success. Callers that want to tolerate
    ``5`` (pytest's "no tests collected") — for example, the serial-only second
    pass under ``--parallel`` when no test in the selection carries the ``serial``
    marker — pass ``acceptable_exit_codes=(0, 5)``.
    """
    print_header(run_title)
    targets_to_check = (test_path, *extra_targets)
    for tp in targets_to_check:
        tests_dir = suite_cwd / tp
        if not (tests_dir.is_dir() or tests_dir.is_file()):
            print_error(f"Tests directory or file not found: {tests_dir}")
            return False

    junit_report = REPORTS_DIR / f"pytest_{suite_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
    cmd = [sys.executable, "-m", "pytest", *pytest_argv, f"--junit-xml={junit_report}"]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(suite_cwd),
            env=_subprocess_env_for_suite(suite_name) or os.environ,
        )
        if result.returncode in acceptable_exit_codes:
            if result.returncode != 0:
                print_info(
                    f"pytest exit code {result.returncode} accepted (no tests collected for this filter)."
                )
            return True
        return False
    except OSError as exc:
        print_error(f"Failed to run pytest: {exc}")
        return False


def _external_lane_preflight(suite_name: str, cfg: SuiteConfig) -> tuple[bool, str]:
    """Return (ready, message) for optional external lanes."""
    if suite_name == "playwright_e2e":
        import shutil

        package_json = cfg.cwd / "package.json"
        config = cfg.cwd / "playwright.config.ts"
        if not package_json.is_file() or not config.is_file():
            return False, "Playwright lane not configured (tests/e2e package files missing)."
        npx_bin = "npx.cmd" if os.name == "nt" else "npx"
        if shutil.which(npx_bin) is None:
            return False, "Playwright lane requires npx in PATH."
        node_bin = "node.exe" if os.name == "nt" else "node"
        if shutil.which(node_bin) is None:
            return False, "Playwright lane requires node in PATH."
        check = subprocess.run(
            [node_bin, "-e", "require.resolve('@playwright/test')"],
            cwd=str(cfg.cwd),
            capture_output=True,
            text=True,
        )
        if check.returncode != 0:
            return (
                False,
                "Playwright dependencies are not installed in tests/e2e. Run `npm install` in tests/e2e first.",
            )
        return True, ""
    if suite_name == "compose_smoke":
        import shutil

        readme = cfg.cwd / "README.md"
        script = cfg.cwd / "smoke_curl.sh"
        if not readme.is_file() or not script.is_file():
            return False, "Compose smoke lane files are missing."
        docker_bin = shutil.which("docker")
        if not docker_bin:
            return False, "Compose smoke lane requires docker in PATH."
        probe = subprocess.run([docker_bin, "compose", "version"], capture_output=True, text=True)
        if probe.returncode != 0:
            return False, "Compose smoke lane requires Docker Compose v2."
        return True, ""
    return True, ""


def run_external_lane(suite_name: str, cfg: SuiteConfig) -> bool:
    ready, reason = _external_lane_preflight(suite_name, cfg)
    if not ready:
        print_info(f"Skipping '{suite_name}' lane: {reason}")
        return True

    if suite_name == "playwright_e2e":
        cmd = ["npx", "playwright", "test"]
        if os.name == "nt":
            cmd = ["npx.cmd", "playwright", "test"]
    elif suite_name == "compose_smoke":
        if os.name == "nt":
            cmd = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "./smoke_curl.sh",
            ]
        else:
            cmd = ["bash", "./smoke_curl.sh"]
    else:
        print_error(f"Unknown external lane: {suite_name}")
        return False

    try:
        result = subprocess.run(cmd, cwd=str(cfg.cwd), timeout=600)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print_error(f"External lane '{suite_name}' timed out after 600 seconds.")
        return False
    except OSError as exc:
        print_error(f"Failed to run external lane '{suite_name}': {exc}")
        return False


def run_tests_for_suites(
    suites: dict[str, SuiteConfig],
    *,
    quick: bool,
    coverage_mode: bool,
    verbose: bool,
    scope: str,
    continue_on_failure: bool,
    domain: str = "all",
    parallel: str | None = None,
) -> tuple[bool, dict[str, bool]]:
    all_passed = True
    results: dict[str, bool] = {}

    for suite_name, cfg in suites.items():
        display = SUITE_DISPLAY_NAMES.get(suite_name, suite_name)
        if cfg.kind == "external":
            title = f"{display} (external lane)"
            print_header(f"Running: {title}")
            ok = run_external_lane(suite_name, cfg)
            results[suite_name] = ok
            all_passed = all_passed and ok
            if not ok:
                print_error(f"{suite_name} lane failed")
            else:
                print_success(f"{suite_name} lane passed")
            print()
            if not ok and quick and not continue_on_failure:
                print_info(
                    "Stopping orchestrator after first failing lane (--quick). "
                    "Re-run with --continue-on-failure to execute remaining suites anyway."
                )
                break
            continue

        suite_cwd, test_path = cfg.cwd, cfg.target
        m = combined_marker_expression(suite_name, scope, domain)
        scope_only_marker = marker_filter_for_suite(suite_name, scope)
        if scope != "all" and scope_only_marker is None:
            if (suite_name == "administration" or suite_name in ENGINE_SUITE_FAMILY) and scope == "e2e":
                print_info(
                    f"Suite '{suite_name}' has no ``e2e`` marker in pytest.ini; running full tests."
                )
            elif suite_name in AI_STACK_SUITE_FAMILY or suite_name in (
                "frontend",
                "database",
                "root_core",
                "root_integration",
                "root_branching",
                "root_smoke",
                "root_tools",
                "tools_mcp_server",
                "root_requirements_hygiene",
                "root_e2e_python",
                "root_experience_scoring",
            ):
                print_info(
                    f"Suite '{suite_name}' does not map --scope '{scope}' to a marker; running full tests."
                )
        if m:
            title = f"{display} — marker '{m}'"
        else:
            title = f"{display} (full)"

        def _do_one_pass(
            extra_clauses: tuple[str, ...],
            parallel_for_pass: str | None,
            title_suffix: str,
            accept_no_tests: bool = False,
        ) -> bool:
            argv = build_pytest_argv(
                suite_name=suite_name,
                test_path=test_path,
                quick=quick,
                coverage_mode=coverage_mode,
                verbose=verbose,
                scope=scope,
                domain=domain,
                extra_targets=cfg.extra_targets,
                ignore_paths=cfg.ignore_paths,
                parallel=parallel_for_pass,
                extra_marker_clauses=extra_clauses,
            )
            acceptable = (0, 5) if accept_no_tests else (0,)
            return run_pytest(
                suite_name,
                suite_cwd,
                test_path,
                argv,
                f"Running: {title}{title_suffix}",
                extra_targets=cfg.extra_targets,
                acceptable_exit_codes=acceptable,
            )

        if parallel:
            # Two-pass execution under --parallel: parallel run for everything that is
            # safe to spread across workers, then a sequential serial-only pass for
            # tests tagged @pytest.mark.serial (DB upgrades, login race, rate limiting).
            ok = _do_one_pass(
                ("not serial",),
                parallel,
                " - parallel pass (excludes @pytest.mark.serial)",
                accept_no_tests=True,
            )
            if ok or continue_on_failure:
                serial_ok = _do_one_pass(
                    ("serial",),
                    None,
                    " - serial pass (sequential, @pytest.mark.serial only)",
                    accept_no_tests=True,
                )
                ok = ok and serial_ok
        else:
            ok = _do_one_pass((), None, "")
        if ok and suite_name in ("frontend", "mvp5"):
            jest_ok = run_frontend_jest_lane(suite_name)
            ok = ok and jest_ok
        results[suite_name] = ok
        all_passed = all_passed and ok
        if not ok:
            print_error(f"{suite_name} tests failed")
        else:
            print_success(f"{suite_name} tests passed")
        print()

        if not ok and quick and not continue_on_failure:
            print_info(
                "Stopping orchestrator after first failing suite (--quick). "
                "Re-run with --continue-on-failure to execute remaining suites anyway."
            )
            break

    return all_passed, results


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run pytest per component and repository suite groups "
            "(backend, frontend, administration-tool, world-engine, database, writers-room, improvement, "
            "ai_stack, and root tests/* groups)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Prerequisites (full ``--suite all``): install all component test deps and editable
``story_runtime_core`` + ``ai_stack[test]`` once. From repo root:
  ./setup-test-environment.sh          (Unix / Git Bash)
  setup-test-environment.bat           (Windows cmd)
  ./scripts/install-full-test-env.sh   (wrapper, same as above)
See tests/TESTING.md (Environment preflight).

Examples (from repository root):
  python tests/run_tests.py
  python tests/run_tests.py --suite backend
  python tests/run_tests.py --suite writers_room
  python tests/run_tests.py --suite improvement
  python tests/run_tests.py --suite frontend
  python tests/run_tests.py --suite backend --scope contracts
  python tests/run_tests.py --suite administration --scope security
  python tests/run_tests.py --suite engine --scope integration
  python tests/run_tests.py --suite engine_runtime engine_opening_contracts --quick
  python tests/run_tests.py --suite ai_stack_graph ai_stack_goc --quick --continue-on-failure
  python tests/run_tests.py --suite writers_room improvement --quick
  python tests/run_tests.py --suite ai_stack --quick
  python tests/run_tests.py --suite all --coverage

``--suite all`` runs all Python suite groups (component suites + root tests/* groups).
Optional non-Python lanes are opt-in:
  python tests/run_tests.py --suite all --with-playwright
  python tests/run_tests.py --suite all --with-compose-smoke
        """,
    )
    parser.add_argument(
        "--suite",
        nargs="+",
        default=["all"],
        choices=[name for name in SUITE_CONFIGS if name not in {"playwright_e2e", "compose_smoke"}] + ["all"],
        help=(
            "Suite groups to run (default: all Python suites). "
            "Use --with-playwright / --with-compose-smoke to add optional external lanes."
        ),
    )
    parser.add_argument(
        "--scope",
        default="all",
        choices=["all", "contracts", "integration", "e2e", "security"],
        help=(
            "Filter by pytest marker where supported: backend, writers_room, improvement "
            "(contract, integration, e2e, security); administration and engine "
            "including engine_* block suites (contract, integration, security - no e2e marker). "
            "frontend, database, ai_stack/ai_stack_* blocks, and root_* suites ignore --scope and run full targets."
        ),
    )
    parser.add_argument(
        "--domain",
        default="all",
        choices=[
            "all",
            "auth",
            "observability",
            "runtime",
            "routes_core",
            "content",
            "services",
            "writers_room",
            "improvement",
            "mvp_handoff",
        ],
        help=(
            "Cross-folder backend domain filter (Stage 2 backend-test-suite-split). "
            "Combines with --scope via 'and' (e.g. --scope contracts --domain auth -> "
            "-m 'contract and auth'). Only applies to backend* sub-suites, writers_room, "
            "and improvement; ignored elsewhere."
        ),
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help=(
            "Per suite: pytest --no-cov -x (stop on first test failure). Orchestrator: skip "
            "pre-run collect-only stats unless --stats; stop after the first failing suite "
            "unless --continue-on-failure."
        ),
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="With --quick, still run collect-only stats before pytest (default: skip when --quick).",
    )
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="With --quick, run every suite even if an earlier suite failed (default: stop early).",
    )
    parser.add_argument("--coverage", action="store_true", help="Coverage with HTML report")
    parser.add_argument("--verbose", action="store_true", help="Verbose pytest and long tracebacks")
    parser.add_argument(
        "--with-playwright",
        action="store_true",
        help="Also run Playwright browser lane (tests/e2e, requires npx and Playwright setup).",
    )
    parser.add_argument(
        "--with-compose-smoke",
        action="store_true",
        help="Also run compose smoke lane (tests/smoke/compose_smoke).",
    )
    parser.add_argument(
        "--parallel",
        nargs="?",
        const="auto",
        default=None,
        metavar="WORKERS",
        help=(
            "Run pytest in parallel via pytest-xdist. ``--parallel`` (no value) uses "
            "``-n auto``; ``--parallel 4`` uses 4 workers. Default: off (sequential). "
            "Always pairs with ``--dist loadfile`` so tests inside one file stay on one "
            "worker. Use --parallel only when test isolation between files is sound; "
            "tag ordering-sensitive tests with ``@pytest.mark.serial``."
        ),
    )
    parser.add_argument(
        "--mvp1",
        action="store_true",
        help="MVP1 suite preset: backend, engine, frontend.",
    )
    parser.add_argument(
        "--mvp2",
        action="store_true",
        help="MVP2 suite preset: backend, engine, ai_stack.",
    )
    parser.add_argument(
        "--mvp3",
        action="store_true",
        help="MVP3 suite preset: backend, engine, ai_stack, story_runtime_core.",
    )
    parser.add_argument(
        "--mvp4",
        action="store_true",
        help="MVP4 suite preset: backend, engine, ai_stack, story_runtime_core, gates.",
    )
    parser.add_argument(
        "--mvp5",
        action="store_true",
        help="MVP5 suite preset: frontend (block renderer, typewriter, orchestration).",
    )

    args = parser.parse_args()

    # Resolve MVP-scoped suite presets (only when --suite is at default "all")
    if args.suite == ["all"]:
        if args.mvp5:
            args.suite = ["frontend", "mvp5"]
        elif args.mvp4:
            args.suite = ["backend", "engine", "ai_stack", "story_runtime_core", "gates"]
        elif args.mvp3:
            args.suite = ["backend", "engine", "ai_stack", "story_runtime_core"]
        elif args.mvp2:
            args.suite = ["backend", "engine", "ai_stack"]
        elif args.mvp1:
            args.suite = ["backend", "engine", "frontend"]

    suites = get_suite_configs(
        args.suite,
        with_playwright=args.with_playwright,
        with_compose_smoke=args.with_compose_smoke,
    )
    if not suites:
        print_error("No valid suites specified")
        return 1

    if not check_environment(suites):
        return 1

    if args.quick and not args.stats:
        print_info("Skipping pre-run collect-only stats (--quick). Use --stats to force collection.")
    else:
        if not show_test_stats(suites, scope=args.scope, domain=args.domain):
            print_error("Test collection (collect-only) failed; fix errors above before running tests.")
            return 1

    all_passed, results = run_tests_for_suites(
        suites,
        quick=args.quick,
        coverage_mode=args.coverage,
        verbose=args.verbose,
        scope=args.scope,
        continue_on_failure=args.continue_on_failure,
        domain=args.domain,
        parallel=args.parallel,
    )

    print_header("Summary")
    for suite, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        symbol = Colors.OKGREEN if passed else Colors.FAIL
        print(f"{symbol}{status}{Colors.ENDC} - {suite}")

    print()
    if all_passed:
        print_success("All selected suites passed.")
        return 0
    print_error("One or more suites failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
