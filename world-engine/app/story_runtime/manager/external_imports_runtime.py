from __future__ import annotations

from ai_stack.story_runtime.narrator.goc_narrator_path import (
    NARRATOR_PATH_ADAPTER,
    NARRATOR_PATH_INVOCATION_MODE,
    build_goc_narrator_path_opening,
    build_goc_scripted_continuation,
)
from ai_stack.goc_souffleuse import (
    SOUFFLEUSE_ADAPTER,
    SOUFFLEUSE_BLOCK_TYPE,
    SOUFFLEUSE_INTERNAL_LANGUAGE,
    SOUFFLEUSE_INVOCATION_MODE,
    SOUFFLEUSE_OPENING_ROLE_ORIENTATION,
    build_goc_opening_souffleuse_projection,
)
from ai_stack.goc_knowledge_runtime_gates import (
    build_knowledge_path_summary,
    build_narrator_packet,
)
from ai_stack.story_runtime.semantic_planner.semantic_move_contract import SEMANTIC_MOVE_TYPES
from ai_stack.opening_shape_normalizer import normalize_opening_narration_beats
from ai_stack.visible_narrative_contract import (
    _goc_visible_lane_text_fold,
    dedupe_goc_speaker_colon_stutter_visible,
    finalize_visible_scene_blocks,
    prune_goc_actor_actions_subsumed_by_prior_actor_lines,
    sanitize_visible_block_text,
)
from app.config import APP_VERSION
from app.repo_root import resolve_wos_repo_root
from app.observability.audit_log import log_story_runtime_failure, log_story_turn_event
from app.observability.langfuse_adapter import LangfuseAdapter
from app.observability.runtime_metrics import StoryRuntimeMetrics
from app.observability.trace import get_langfuse_trace_id
from app.story_runtime.governed_runtime import build_governed_story_runtime_components
from app.story_runtime.live_governance import (
    BlockedLiveStoryRoutingPolicy,
    LiveStoryGovernanceError,
    is_governed_resolved_config_operational,
    opening_text_contains_preview_placeholder,
)
from app.story_runtime.commit_models import (
    BeatProgression,
    resolve_narrative_commit,
)
from app.story_runtime.canonical_turn_lifecycle import TurnLifecycleChain
from app.story_runtime.branch_timeline_store import JsonBranchTimelineStore
from app.story_runtime.branching_tree_store import JsonBranchingTreeStore
from app.story_runtime.callback_web_store import JsonCallbackWebStore
from app.story_runtime.consequence_cascade_store import JsonConsequenceCascadeStore
from app.story_runtime.story_session_store import JsonStorySessionStore
from app.story_runtime.runtime_world import (
    initialize_runtime_world,
    runtime_world_session_diagnostic,
)
from app.story_runtime.module_turn_hooks import (
    GOD_OF_CARNAGE_MODULE_ID,
    goc_append_continuity_impacts,
    goc_host_experience_template,
    goc_npc_shell_legal_name,
    goc_prior_continuity_for_graph,
    goc_player_role_display_name,
    goc_shell_actor_firstname,
)
from app.story_runtime.narrative_threads import (
    NARRATIVE_COMMIT_HISTORY_TAIL,
    StoryNarrativeThreadSet,
    ThreadUpdateTrace,
    build_graph_thread_export,
    thread_continuity_metrics,
    update_narrative_threads,
)

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
