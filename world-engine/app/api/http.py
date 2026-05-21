from __future__ import annotations

# Compatibility facade: keep ``app.api.http`` stable while route concerns live in
# ``app.api.http_routes``. Tests monkeypatch this value directly, so the auth
# helper in ``common`` reads it dynamically from this module.
from app.config import PLAY_SERVICE_INTERNAL_API_KEY

from .http_routes.common import (
    _flush_langfuse_background,
    _get_narrative_loader,
    _get_preview_registry,
    _get_runtime_health,
    _get_validator_config,
    _langfuse_root_status,
    _require_internal_api_key,
    _trace_classification_from_request,
    get_manager,
    get_story_manager,
    router,
)
from .http_routes.models import (
    BranchTimelineArchiveRequest,
    BranchingSimulationTreeRequest,
    BranchingTreeCreateRequest,
    BranchingTreeExpireRequest,
    BranchingTreeSelectRequest,
    CreateRunRequest,
    CreateStorySessionRequest,
    ExecuteStoryTurnRequest,
    IdentityPayload,
    JoinContextRequest,
    NarrativePreviewLoadRequest,
    NarrativePreviewSessionEndRequest,
    NarrativePreviewSessionStartRequest,
    NarrativePreviewUnloadRequest,
    NarrativeReloadRequest,
    NarrativeTurnValidationRequest,
    TerminateRunRequest,
    TicketRequest,
)
from .http_routes.health_routes import health, ready
from .http_routes.play_run_routes import (
    create_join_context,
    create_run,
    create_ticket,
    delete_run,
    get_internal_run_details,
    get_internal_transcript,
    get_run_details,
    get_snapshot,
    get_transcript,
    list_runs,
    list_templates,
    terminate_run_internal,
)
from .http_routes.runtime_config_routes import (
    reload_story_runtime_governed_config,
    story_runtime_config_status,
)
from .http_routes.story_session_routes import (
    create_story_session,
    execute_story_turn,
    generate_story_session_opening,
    list_story_sessions,
)
from .http_routes.story_state_routes import (
    get_story_diagnostics,
    get_story_runtime_diagnostic_snapshot,
    get_story_state,
    get_story_thin_path_summary,
    get_story_w5_actor,
    get_story_w5_conflicts,
    get_story_w5_narrator_projection,
    get_story_w5_npc_projection,
    get_story_w5_snapshot,
    get_story_w5_validation,
)
from .http_routes.branching_routes import (
    archive_story_branch_timeline,
    build_story_branching_simulation_tree,
    compact_story_branch_timeline,
    create_story_branching_tree,
    expire_story_branching_tree,
    get_story_branch_timeline,
    get_story_branching_tree,
    list_story_branch_timeline_events,
    list_story_branching_trees,
    select_story_branching_tree_node,
)
from .http_routes.narrative_web_routes import (
    get_narrative_gov_summary,
    get_story_callback_web,
    get_story_consequence_cascade,
    get_story_diagnostics_envelope,
    list_story_callback_web_edges,
    list_story_consequence_cascade_edges,
    rebuild_story_callback_web,
    rebuild_story_consequence_cascade,
    stream_narrator_blocks,
)
from .http_routes.narrative_package_routes import (
    narrative_load_preview,
    narrative_preview_end_session,
    narrative_preview_start_session,
    narrative_reload_active,
    narrative_unload_preview,
)
from .http_routes.narrative_runtime_routes import (
    narrative_runtime_health,
    narrative_runtime_state,
    narrative_runtime_validate_and_recover,
    narrative_runtime_validator_config,
)
