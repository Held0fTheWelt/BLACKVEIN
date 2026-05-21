"""Game routes implementation concern: imports and dependencies.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''

from __future__ import annotations

import hashlib
import logging
import os
import threading
from typing import Any

from flask import current_app, g, jsonify, request, session
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from sqlalchemy import select

from ai_stack.story_runtime.god_of_carnage.god_of_carnage_frozen_vocabulary import GOC_MODULE_ID
from ai_stack.story_runtime.live_runtime_commit_semantics import evaluate_session_opening_readiness
from ai_stack.story_runtime.runtime_readiness_consumer import (
    build_adr0041_readiness_projection_echo,
    degradation_signals_from_latest_turn,
    resolve_runtime_readiness_with_adr0041,
    runtime_intelligence_projection_from_turn_aspect_ledger,
)
from ai_stack.story_runtime.player_narrative_cards import (
    build_player_facing_narrative_cards,
    player_shell_typewriter_start_index,
)
from ai_stack.contracts.visible_narrative_contract import polish_goc_scene_blocks_for_player_shell

from app.api.v1 import api_v1_bp
from app.auth.permissions import require_jwt_moderator_or_admin
from app.content.compiler import compile_module
from app.content.module_exceptions import ModuleLoadError
from app.extensions import db, limiter
from app.models import GameSaveSlot, User
from app.services.game.game_content_service import (
    GameContentConflictError,
    GameContentLifecycleError,
    GameContentNotFoundError,
    GameContentValidationError,
    apply_editorial_decision,
    create_experience,
    get_experience,
    list_experiences,
    list_published_experience_payloads,
    mark_experience_publishable,
    publish_experience,
    resolve_canonical_module_id_for_template,
    submit_experience_for_review,
    unpublish_experience,
    update_experience,
)
from app.services.game.game_profile_service import (
    NotFoundError,
    OwnershipError,
    ValidationError,
    create_character_for_user,
    get_character_for_user,
    list_characters_for_user,
    list_save_slots_for_user,
    touch_character_last_used,
    update_character_for_user,
    upsert_save_slot_for_user,
    delete_save_slot_for_user,
)
from app.services.game.game_service import (
    GameServiceConfigError,
    GameServiceError,
    create_run as create_play_run,
    create_story_session,
    execute_story_opening,
    execute_story_turn as execute_story_turn_in_engine,
    get_run_details as get_play_run_details,
    get_run_transcript as get_play_run_transcript,
    get_story_state,

    terminate_run as terminate_play_run,
    get_play_service_websocket_url,
    has_complete_play_service_config,
    issue_play_ticket,
    list_runs as list_play_runs,
    list_templates as list_play_templates,
    resolve_join_context,
)
from app.observability.langfuse_adapter import LangfuseAdapter
from app.observability.trace import get_langfuse_trace_id
from app.config.route_constants import route_status_codes, route_pagination_config
from story_runtime_core.langfuse_tracing_environment import is_local_langfuse_evidence_context

logger = logging.getLogger(__name__)


'''
