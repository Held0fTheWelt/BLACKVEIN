"""Public site API: slogan resolution for placement (no auth); admin PUT for site settings."""
import re
from flask import current_app, jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.permissions import require_jwt_admin
from app.extensions import db, limiter
from app.i18n import validate_language_code
from app.services.slogan_service import list_slogans_for_placement, resolve_slogan_for_placement
from app.config.route_constants import route_site_config, route_status_codes

_OPERATOR_SETTING_KEYS = (
    "slogan_rotation_interval_seconds",
    "slogan_rotation_enabled",
    "default_content_module_id",
    "default_experience_template_id",
)
_OPERATOR_ID_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,127}$")


def _coerce_operator_identifier(raw) -> str:
    """Normalize module / experience template ids from site_settings rows."""
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s or _OPERATOR_ID_RE.fullmatch(s) is None:
        return ""
    return s


def _public_site_settings():
    """Read-only site settings for landing (rotation) and operator UI defaults."""
    from app.models import SiteSetting
    rows = {
        r.key: r.value
        for r in SiteSetting.query.filter(SiteSetting.key.in_(_OPERATOR_SETTING_KEYS)).all()
    }
    interval = rows.get("slogan_rotation_interval_seconds")
    enabled = rows.get("slogan_rotation_enabled")
    return {
        "slogan_rotation_interval_seconds": int(interval) if interval is not None and str(interval).isdigit() else 60,
        "slogan_rotation_enabled": str(enabled).lower() not in ("0", "false", "no", "off") if enabled is not None else True,
        "default_content_module_id": _coerce_operator_identifier(rows.get("default_content_module_id")),
        "default_experience_template_id": _coerce_operator_identifier(rows.get("default_experience_template_id")),
    }


def _coerce_rotation_interval(raw):
    """Clamp rotation interval; invalid values become default 60; min 5, max 86400."""
    if raw is None:
        return route_site_config.default_rotation_interval
    try:
        if isinstance(raw, str):
            s = raw.strip()
            if not s or not s.lstrip("-").isdigit():
                return route_site_config.default_rotation_interval
            n = int(s)
        else:
            n = int(raw)
    except (TypeError, ValueError):
        return route_site_config.default_rotation_interval
    if n < route_site_config.min_rotation_interval:
        return route_site_config.min_rotation_interval
    if n > route_site_config.max_rotation_interval:
        return route_site_config.max_rotation_interval
    return n


def _coerce_rotation_enabled(raw):
    """Interpret loose truthy/falsey; None if unrecognized."""
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return raw != 0
    s = str(raw).strip().lower()
    if s in ("0", "false", "no", "off", ""):
        return False
    if s in ("1", "true", "yes", "on"):
        return True
    return None


def _upsert_site_setting(key: str, value: str) -> None:
    from app.models import SiteSetting

    row = db.session.get(SiteSetting, key)
    if row is None:
        db.session.add(SiteSetting(key=key, value=value))
    else:
        row.value = value


@api_v1_bp.route("/site/settings", methods=["GET"])
@limiter.limit("60 per minute")
def site_settings():
    """Public read-only site settings (rotation + operator default content identifiers)."""
    return jsonify(_public_site_settings()), route_status_codes.ok


@api_v1_bp.route("/site/settings", methods=["PUT"])
@limiter.limit("30 per minute")
@require_jwt_admin
def site_settings_put():
    """Admin-only: update slogan rotation, operator default module/template, and related flags."""
    ct = (request.content_type or "").lower()
    if "application/json" not in ct:
        return jsonify({"error": "Expected JSON body"}), route_status_codes.bad_request
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), route_status_codes.bad_request

    if "slogan_rotation_interval_seconds" in data:
        coerced = _coerce_rotation_interval(data["slogan_rotation_interval_seconds"])
        _upsert_site_setting("slogan_rotation_interval_seconds", str(coerced))

    if "slogan_rotation_enabled" in data:
        raw_en = data["slogan_rotation_enabled"]
        if raw_en is None:
            en = False
        elif isinstance(raw_en, bool):
            en = raw_en
        else:
            parsed = _coerce_rotation_enabled(raw_en)
            en = parsed if parsed is not None else True
        _upsert_site_setting("slogan_rotation_enabled", "true" if en else "false")

    if "default_content_module_id" in data:
        mid = _coerce_operator_identifier(data.get("default_content_module_id"))
        if mid:
            _upsert_site_setting("default_content_module_id", mid)

    if "default_experience_template_id" in data:
        tid = _coerce_operator_identifier(data.get("default_experience_template_id"))
        if tid:
            _upsert_site_setting("default_experience_template_id", tid)

    db.session.commit()
    return jsonify(_public_site_settings()), route_status_codes.ok


@api_v1_bp.route("/site/slogans", methods=["GET"])
@limiter.limit("60 per minute")
def site_slogans():
    """
    List all slogans for a placement and language (for rotation on landing). Public.
    Query: placement (required), lang (optional).
    Returns { "items": [ { "text", "placement_key", "language_code" }, ... ] }.
    """
    placement = (request.args.get("placement") or "").strip()
    if not placement:
        return jsonify({"error": "placement is required"}), route_status_codes.bad_request
    lang = (request.args.get("lang") or "").strip() or current_app.config.get("DEFAULT_LANGUAGE", "de")
    validated_lang, err = validate_language_code(lang)
    if err:
        return jsonify({"error": err}), route_status_codes.bad_request
    slogans = list_slogans_for_placement(placement, validated_lang)
    items = [
        {"text": s.text, "placement_key": s.placement_key, "language_code": s.language_code}
        for s in slogans
    ]
    return jsonify({"items": items}), route_status_codes.ok


@api_v1_bp.route("/site/slogan", methods=["GET"])
@limiter.limit("120 per minute")
def site_slogan():
    """
    Resolve one slogan for a placement and language. Public endpoint.
    Query: placement (required), lang (optional, default from config).
    Returns { "text", "placement_key", "language_code" } or { "text": null } when no slogan.
    """
    placement = (request.args.get("placement") or "").strip()
    if not placement:
        return jsonify({"error": "placement is required"}), route_status_codes.bad_request
    lang = (request.args.get("lang") or "").strip() or current_app.config.get("DEFAULT_LANGUAGE", "de")
    validated_lang, err = validate_language_code(lang)
    if err:
        return jsonify({"error": err}), route_status_codes.bad_request
    slogan = resolve_slogan_for_placement(placement, validated_lang)
    if not slogan:
        return jsonify({"text": None, "placement_key": placement, "language_code": validated_lang}), route_status_codes.ok
    return jsonify({
        "text": slogan.text,
        "placement_key": slogan.placement_key,
        "language_code": slogan.language_code,
    }), route_status_codes.ok
