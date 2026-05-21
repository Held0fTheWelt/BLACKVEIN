"""WebSocket session-loop helper package."""

from .constants import *
from .cut_in import apply_cut_in
from .feature_flags import is_follow_up_semantic_composition_enabled, is_ws_session_loop_enabled
from .follow_up_event import build_post_cut_in_follow_up_event
from .handoff import build_player_cut_in_handoff, build_post_cut_in_replanning_decision
from .messages import (
    cut_in_state_for_kind,
    msg_autonomous_tick_evaluated,
    msg_block_completed,
    msg_block_cut,
    msg_block_started,
    msg_player_cut_in_handoff,
    msg_post_cut_in_follow_up_event,
    msg_post_cut_in_replanning_decision,
    msg_replanning_decision,
    msg_stream_error,
    msg_stream_idle,
    msg_stream_started,
)
from .replanning import (
    build_replanned_event_after_cut_in,
    build_replanning_decision,
    build_replanning_request,
)
from .state import WSSessionLoopState

__all__ = [
    name for name in globals()
    if name.isupper()
    or name in {
        "WSSessionLoopState",
        "FollowUpSemanticProvider",
        "apply_cut_in",
        "build_player_cut_in_handoff",
        "build_post_cut_in_follow_up_event",
        "build_post_cut_in_replanning_decision",
        "build_replanned_event_after_cut_in",
        "build_replanning_decision",
        "build_replanning_request",
        "cut_in_state_for_kind",
        "is_follow_up_semantic_composition_enabled",
        "is_ws_session_loop_enabled",
        "msg_autonomous_tick_evaluated",
        "msg_block_completed",
        "msg_block_cut",
        "msg_block_started",
        "msg_player_cut_in_handoff",
        "msg_post_cut_in_follow_up_event",
        "msg_post_cut_in_replanning_decision",
        "msg_replanning_decision",
        "msg_stream_error",
        "msg_stream_idle",
        "msg_stream_started",
    }
]
