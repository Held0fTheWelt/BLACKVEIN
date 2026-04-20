"""Public site API: slogan resolution for placement (no auth); admin PUT for site settings."""
from flask import current_app, jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.permissions import require_jwt_admin
from app.extensions import db, limiter
from app.i18n import validate_language_code
from app.services.slogan_service import list_slogans_for_placement, resolve_slogan_for_placement


def _public_site_settings():
    """Read-only site settings for landing (rotation). Returns dict."""
    from app.models import SiteSetting
    rows = {r.key: r.value for r in SiteSetting.query.filter(
        SiteSetting.key.in_(["slogan_rotation_interval_seconds", "slogan_rotation_enabled"])
    ).all()}
    interval = rows.get("slogan_rotation_interval_seconds")
    enabled = rows.get("slogan_rotation_enabled")
    return {
        "slogan_rotation_interval_seconds": int(interval) if interval is not None and str(interval).isdigit() else 60,
        "slogan_rotation_enabled": str(enabled).lower() not in ("0", "false", "no", "off") if enabled is not None else True,
    }


_MIN_ROTATION_INTERVAL = 5
_MAX_ROTATION_INTERVAL = 86400
_DEFAULT_ROTATION_INTERVAL = 60


def _coerce_rotation_interval(raw):
    """Clamp rotation interval; invalid values become default 60; min 5, max 86400."""
    if raw is None:
        return _DEFAULT_ROTATION_INTERVAL
    try:
        if isinstance(raw, str):
            s = raw.strip()
            if not s or not s.lstrip("-").isdigit():
                return _DEFAULT_ROTATION_INTERVAL
            n = int(s)
        else:
            n = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_ROTATION_INTERVAL
    if n < _MIN_ROTATION_INTERVAL:
        return _MIN_ROTATION_INTERVAL
    if n > _MAX_ROTATION_INTERVAL:
        return _MAX_ROTATION_INTERVAL
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
    """Public read-only site settings (e.g. slogan_rotation_interval_seconds, slogan_rotation_enabled)."""
    return jsonify(_public_site_settings()), 200


@api_v1_bp.route("/site/settings", methods=["PUT"])
@limiter.limit("30 per minute")
@require_jwt_admin
def site_settings_put():
    """Admin-only: update slogan rotation interval and/or enabled flag."""
    ct = (request.content_type or "").lower()
    if "application/json" not in ct:
        return jsonify({"error": "Expected JSON body"}), 400
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

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

    db.session.commit()
    return jsonify(_public_site_settings()), 200


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
        return jsonify({"error": "placement is required"}), 400
    lang = (request.args.get("lang") or "").strip() or current_app.config.get("DEFAULT_LANGUAGE", "de")
    validated_lang, err = validate_language_code(lang)
    if err:
        return jsonify({"error": err}), 400
    slogans = list_slogans_for_placement(placement, validated_lang)
    items = [
        {"text": s.text, "placement_key": s.placement_key, "language_code": s.language_code}
        for s in slogans
    ]
    return jsonify({"items": items}), 200


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
        return jsonify({"error": "placement is required"}), 400
    lang = (request.args.get("lang") or "").strip() or current_app.config.get("DEFAULT_LANGUAGE", "de")
    validated_lang, err = validate_language_code(lang)
    if err:
        return jsonify({"error": err}), 400
    slogan = resolve_slogan_for_placement(placement, validated_lang)
    if not slogan:
        return jsonify({"text": None, "placement_key": placement, "language_code": validated_lang}), 200
    return jsonify({
        "text": slogan.text,
        "placement_key": slogan.placement_key,
        "language_code": slogan.language_code,
    }), 200
