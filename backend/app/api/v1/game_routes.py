"""Game API routes.

The implementation lives in named implementation concerns under
``backend/app/api/v1/game/``. This module remains the stable public namespace
for Flask route registration and tests that patch route service seams.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SEGMENT_FILES: tuple[str, ...] = (
    "imports_and_dependencies.py",
    "trace_identity_and_auth_helpers.py",
    "error_response_and_bootstrap_helpers.py",
    "session_slot_and_run_identity_helpers.py",
    "story_window_scene_block_helpers.py",
    "shell_turn_counter_helpers.py",
    "player_shell_state_projection.py",
    "session_loop_bundle_evidence.py",
    "player_session_bundle_visible_output.py",
    "player_session_bundle_response.py",
    "player_session_binding_persistence.py",
    "runtime_profile_handoff_validation.py",
    "runtime_profile_merge_and_compile.py",
    "ensure_player_session_resume.py",
    "ensure_player_session_create.py",
    "template_catalog_helpers.py",
    "bootstrap_template_and_run_list_routes.py",
    "run_creation_route.py",
    "player_session_create_route.py",
    "player_session_resume_and_opening_routes.py",
    "player_turn_trace_start.py",
    "player_turn_execution_and_flush.py",
    "ticket_routes.py",
    "character_routes.py",
    "save_slot_routes.py",
    "content_feed_and_editor_routes.py",
    "content_publication_routes.py",
    "content_governance_review_routes.py",
    "content_governance_publishable_and_ops_routes.py",
)


def _read_segment_source(base_dir: Path, filename: str) -> str:
    """Load one game route implementation file without changing its namespace."""
    path = base_dir / filename
    spec = importlib.util.spec_from_file_location(f"{__name__}.{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load game route slice: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return str(getattr(module, "SOURCE"))


def _load_game_route_segments() -> None:
    """Execute the game route implementation files in this module namespace."""
    base_dir = Path(__file__).with_name("game")
    source_parts = [_read_segment_source(base_dir, filename) for filename in _SEGMENT_FILES]
    compiled = compile("\n".join(source_parts), f"{__name__}.__generated__", "exec")
    exec(compiled, globals())


_load_game_route_segments()
