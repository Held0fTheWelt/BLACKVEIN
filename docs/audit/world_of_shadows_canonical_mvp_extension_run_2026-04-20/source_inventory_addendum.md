# Source inventory addendum for extension run

## Purpose

This addendum lists the additional source families explicitly mined during the extension run because they contained unique still-valid material that had remained underrepresented.

## High-value source families revisited

### Earlier complete MVP family (`world_of_shadows_complete_mvp_v21.zip`)

Classifications:

- historical but still content-bearing,
- partial canonical authority for broader WoS target,
- strong source for package lifecycle, runtime-health, settings, and operator workflow material.

Important files re-mined:

- `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/00_executive_overview.md`
- `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/01_revised_mvp_spec.md`
- `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/05_admin_tool_governance_surface.md`
- `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/07_evaluation_and_quality_gates.md`
- `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/12_live_play_correction_and_fallbacks.md`
- `docs/MVPs/MVP_Operational_Settings_Gogernance/01_scope_and_goals.md`
- `docs/MVPs/MVP_Operational_Settings_Gogernance/02_architecture_and_trust_model.md`
- `docs/MVPs/MVP_Operational_Settings_Gogernance/05_admin_bootstrap_and_ui.md`
- `docs/MVPs/MVP_Operational_Settings_Gogernance/09_cost_usage_and_budgeting.md`
- `docs/MVPs/MVP_MCP_Operations_Cockpit_WoS/ROADMAP_MVP_MCP_OPERATIONS_COCKPIT_WOS.md`

### Prior preservation-audit package

Classifications:

- current canonical candidate,
- already consolidated but still extendable,
- base package for this new extension run.

### Current repository test surface

Classifications:

- direct implementation evidence,
- direct proof where runnable,
- environment-limited proof where optional dependencies are missing.

Commands re-run in this pass:

- `world-engine/tests/test_runtime_manager.py -k 'builtin or published'`
- `ai_stack/tests/test_rag.py -k 'sparse_fallback'`
- `world-engine/tests/test_story_runtime_rag_runtime.py ai_stack/tests/test_langgraph_runtime.py -k 'fallback'`
- `backend/tests/test_session_routes.py -k 'shell_readout_projection or execute_turn_proxies_to_world_engine'`

## Classification summary

The extension run did not discover evidence that the restored areas were obsolete.
It discovered that they were still valid but underrepresented.
That is why the material was integrated rather than rejected as ballast.
