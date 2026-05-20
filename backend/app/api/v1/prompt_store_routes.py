"""Admin and internal APIs for the database-backed Prompt Store."""

from __future__ import annotations

from flask import current_app, request
from flask_jwt_extended import jwt_required

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE
from app.auth.permissions import get_current_user, require_feature
from app.extensions import limiter
from app.governance.envelopes import fail, fail_from_error, ok
from app.governance.errors import GovernanceError
from app.services.prompts.prompt_store_service import (
    get_active_prompt_bundle,
    get_prompt_record,
    get_prompt_store_status,
    list_prompt_records,
    seed_prompt_store_from_files,
    update_prompt_record,
)


def _actor_identifier() -> str:
    user = get_current_user()
    if user is None:
        return "system"
    return user.username or str(user.id)


def _body() -> dict:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _handle(callback):
    try:
        return ok(callback())
    except GovernanceError as err:
        return fail_from_error(err)
    except Exception as exc:  # pragma: no cover - defensive API boundary
        return fail("prompt_store_error", "Unexpected prompt store failure.", 500, {"error": str(exc)})


def _internal_token_valid() -> bool:
    token = (request.headers.get("X-Internal-Config-Token") or "").strip()
    expected = (current_app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN") or "").strip()
    return bool(expected and token == expected)


@api_v1_bp.route("/admin/prompt-store/status", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_prompt_store_status():
    return _handle(get_prompt_store_status)


@api_v1_bp.route("/admin/prompt-store/prompts", methods=["GET"])
@limiter.limit("120 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_prompt_store_list():
    return _handle(
        lambda: list_prompt_records(
            category=(request.args.get("category") or "").strip() or None,
            prompt_type=(request.args.get("prompt_type") or "").strip() or None,
            domain=(request.args.get("domain") or "").strip() or None,
            tag=(request.args.get("tag") or "").strip() or None,
            drift=(request.args.get("drift") or "").strip() or None,
            search=(request.args.get("q") or "").strip() or None,
        )
    )


@api_v1_bp.route("/admin/prompt-store/prompts/<path:prompt_key>", methods=["GET"])
@limiter.limit("120 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_prompt_store_get(prompt_key: str):
    return _handle(lambda: {"prompt": get_prompt_record(prompt_key)})


@api_v1_bp.route("/admin/prompt-store/prompts/<path:prompt_key>", methods=["PATCH"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_prompt_store_update(prompt_key: str):
    return _handle(lambda: {"prompt": update_prompt_record(prompt_key, _body(), actor=_actor_identifier())})


@api_v1_bp.route("/admin/prompt-store/seed", methods=["POST"])
@limiter.limit("12 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_prompt_store_seed():
    payload = _body()
    overwrite = bool(payload.get("overwrite"))
    return _handle(lambda: seed_prompt_store_from_files(overwrite=overwrite, actor=_actor_identifier()))


@api_v1_bp.route("/internal/prompt-store/bundle", methods=["GET"])
@limiter.limit("300 per minute")
def internal_prompt_store_bundle():
    if not _internal_token_valid():
        return fail("prompt_store_forbidden", "Internal prompt store token is invalid.", 403, {})
    return _handle(get_active_prompt_bundle)


@api_v1_bp.route("/internal/prompt-store/prompts/<path:prompt_key>", methods=["GET"])
@limiter.limit("300 per minute")
def internal_prompt_store_get(prompt_key: str):
    if not _internal_token_valid():
        return fail("prompt_store_forbidden", "Internal prompt store token is invalid.", 403, {})
    return _handle(lambda: {"prompt": get_prompt_record(prompt_key)})
