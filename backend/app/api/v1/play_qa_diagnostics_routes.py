"""QA canonical turn diagnostics routes (Phase D).

Exposes the canonical dramatic turn record for QA debugging via:
- /api/v1/play/<session_id>/qa-diagnostics-canonical-turn

Gated by JWT + feature flag FEATURE_VIEW_QA_CANONICAL_TURN.
"""

from __future__ import annotations

import hashlib
from typing import Any

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import select

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_VIEW_QA_CANONICAL_TURN
from app.auth.permissions import require_feature
from app.extensions import db, limiter
from app.governance.envelopes import fail, ok
from app.models import GameSaveSlot, User
from app.services.game_service import get_story_diagnostics, get_story_state
def _current_user() -> User | None:
    uid = get_jwt_identity()
    if uid is None:
        return None
    try:
        return db.session.get(User, int(uid))
    except (TypeError, ValueError):
        return None


def _player_session_slot_key(run_id: str) -> str:
    digest = hashlib.sha1(run_id.encode("utf-8")).hexdigest()[:24]
    return f"player-{digest}"


def _canonical_runtime_state_for_play_run(run_id: str) -> tuple[dict[str, Any] | None, str | None]:
    user = _current_user()
    if user is None:
        return None, None
    slot = db.session.scalar(
        select(GameSaveSlot).where(
            GameSaveSlot.user_id == user.id,
            GameSaveSlot.slot_key == _player_session_slot_key(run_id),
        )
    )
    if slot is None:
        return None, None
    metadata = slot.metadata_json if isinstance(slot.metadata_json, dict) else {}
    runtime_session_id = str(
        metadata.get("runtime_session_id") or metadata.get("world_engine_story_session_id") or ""
    ).strip()
    if not runtime_session_id:
        return None, None
    state = get_story_state(runtime_session_id)
    diagnostics = get_story_diagnostics(runtime_session_id)
    rows = diagnostics.get("diagnostics") if isinstance(diagnostics.get("diagnostics"), list) else []
    latest = rows[-1] if rows and isinstance(rows[-1], dict) else {}
    if not latest:
        latest = state.get("last_committed_turn") if isinstance(state.get("last_committed_turn"), dict) else {}
    if not latest:
        return None, runtime_session_id
    runtime_state = dict(latest)
    runtime_state.setdefault("session_id", runtime_session_id)
    runtime_state.setdefault("module_id", state.get("module_id"))
    runtime_state.setdefault("current_scene_id", state.get("current_scene_id"))
    runtime_state.setdefault("turn_number", latest.get("turn_number"))
    runtime_state.setdefault("trace_id", latest.get("trace_id"))
    if "graph_diagnostics" not in runtime_state and isinstance(runtime_state.get("graph"), dict):
        runtime_state["graph_diagnostics"] = runtime_state["graph"]
    runtime_state["canonical_play_path"] = True
    runtime_state["play_run_id"] = run_id
    runtime_state["runtime_session_id"] = runtime_session_id
    return runtime_state, runtime_session_id


@api_v1_bp.route("/play/<session_id>/qa-diagnostics-canonical-turn", methods=["GET"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_VIEW_QA_CANONICAL_TURN)
def get_qa_canonical_turn_diagnostics(session_id: str):
    """QA-facing canonical dramatic turn record for this session's current turn.

    Returns the operator canonical turn record (Phase D) in QA projection form,
    with three-tier field classification:
    - Tier A (primary): responder selection, validation, quality, vitality
    - Tier B (detailed): summarized continuity, social state, scene assessment
    - Tier C (raw JSON): full canonical record available via raw_canonical_record_available flag

    Access: JWT + FEATURE_VIEW_QA_CANONICAL_TURN
    """
    try:
        from ai_stack.story_runtime.turn.god_of_carnage_turn_seams import build_operator_canonical_turn_record
        from ai_stack.story_runtime.turn.qa_canonical_turn_projection import build_qa_canonical_turn_projection

        runtime_state, runtime_session_id = _canonical_runtime_state_for_play_run(session_id)
        if not isinstance(runtime_state, dict):
            return fail(
                "canonical_play_session_not_found",
                f"Canonical player session for run {session_id} was not found.",
                404,
                {"runtime_session_id": runtime_session_id},
            )

        # Build canonical record from current runtime state
        canonical_record = build_operator_canonical_turn_record(runtime_state)

        # Build QA projection (three-tier view)
        qa_projection = build_qa_canonical_turn_projection(canonical_record)
        qa_projection["canonical_play_path"] = True
        qa_projection["play_run_id"] = session_id
        qa_projection["runtime_session_id"] = runtime_session_id

        # Include raw canonical record if requested
        include_raw = str(request.args.get("include_raw", "0")).lower() in {"1", "true", "yes"}
        if include_raw:
            qa_projection["raw_canonical_record"] = canonical_record
        else:
            qa_projection["raw_canonical_record"] = None

        return ok(qa_projection)

    except ImportError as e:
        return fail(
            "import_error",
            f"Missing dependency (ai_stack or projection module): {str(e)[:100]}",
            500,
            {},
        )
    except Exception as exc:
        return fail(
            "qa_diagnostics_error",
            f"Failed to build QA diagnostics: {str(exc)[:200]}",
            500,
            {},
        )


__all__ = []
