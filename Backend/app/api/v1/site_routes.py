"""Public site API: slogan resolution for placement (no auth)."""
from flask import current_app, jsonify, request

from app.api.v1 import api_v1_bp
from app.extensions import limiter
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


@api_v1_bp.route("/site/settings", methods=["GET"])
@limiter.limit("60 per minute")
def site_settings():
    """Public read-only site settings (e.g. slogan_rotation_interval_seconds, slogan_rotation_enabled)."""
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
    slogans = list_slogans_for_placement(placement, lang)
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
    slogan = resolve_slogan_for_placement(placement, lang)
    if not slogan:
        return jsonify({"text": None, "placement_key": placement, "language_code": lang}), 200
    return jsonify({
        "text": slogan.text,
        "placement_key": slogan.placement_key,
        "language_code": slogan.language_code,
    }), 200
