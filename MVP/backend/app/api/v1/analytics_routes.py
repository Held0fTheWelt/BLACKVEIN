"""Community analytics endpoints: dashboard metrics and insights."""
from flask import current_app, jsonify, request
from flask_jwt_extended import jwt_required

from app.api.v1 import api_v1_bp
from app.auth.permissions import get_current_user
from app.extensions import limiter
from app.services.analytics_service import (
    get_analytics_summary,
    get_analytics_timeline,
    get_analytics_users,
    get_analytics_content,
    get_analytics_moderation,
)


@api_v1_bp.route("/admin/analytics/summary", methods=["GET"])
@limiter.limit("30 per minute")
@jwt_required()
def admin_analytics_summary():
    """
    GET /api/v1/admin/analytics/summary
    Community summary: user counts, thread/post counts, report queue status.
    Query params: date_from, date_to (YYYY-MM-DD, optional, default 30d)
    Requires: admin role
    """
    current_user = get_current_user()
    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    try:
        result = get_analytics_summary(date_from=date_from, date_to=date_to)
        return jsonify(result), 200
    except Exception as e:
        current_app.logger.exception("Analytics error in admin_analytics_summary")
        return jsonify({"error": "Failed to fetch analytics"}), 500


@api_v1_bp.route("/admin/analytics/timeline", methods=["GET"])
@limiter.limit("30 per minute")
@jwt_required()
def admin_analytics_timeline():
    """
    GET /api/v1/admin/analytics/timeline
    Daily activity counts: threads, posts, reports, moderation actions.
    Query params: date_from, date_to, metric (threads|posts|reports|actions, optional)
    Requires: admin or moderator role
    """
    current_user = get_current_user()
    if not current_user or not (current_user.is_admin or current_user.has_role("moderator")):
        return jsonify({"error": "Admin or moderator access required"}), 403

    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    metric = request.args.get("metric")

    try:
        result = get_analytics_timeline(date_from=date_from, date_to=date_to, metric=metric)
        return jsonify(result), 200
    except Exception as e:
        current_app.logger.exception("Analytics error in admin_analytics_timeline")
        return jsonify({"error": "Failed to fetch timeline"}), 500


@api_v1_bp.route("/admin/analytics/users", methods=["GET"])
@limiter.limit("30 per minute")
@jwt_required()
def admin_analytics_users():
    """
    GET /api/v1/admin/analytics/users
    Top contributors and user distribution by role.
    Query params: limit (1-100, default 10), sort_by (contributions|activity|joined)
    Requires: admin role
    """
    current_user = get_current_user()
    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    try:
        limit_param = request.args.get("limit", "10")
        limit = int(limit_param)
        limit = max(1, min(limit, 100))
    except ValueError:
        limit = 10

    sort_by = request.args.get("sort_by", "contributions")

    try:
        result = get_analytics_users(limit=limit, sort_by=sort_by)
        return jsonify(result), 200
    except Exception as e:
        current_app.logger.exception("Analytics error in admin_analytics_users")
        return jsonify({"error": "Failed to fetch user analytics"}), 500


@api_v1_bp.route("/admin/analytics/content", methods=["GET"])
@limiter.limit("30 per minute")
@jwt_required()
def admin_analytics_content():
    """
    GET /api/v1/admin/analytics/content
    Popular tags, trending threads, and content freshness distribution.
    Query params: date_from, date_to, limit (1-100, default 10)
    Requires: admin or moderator role
    """
    current_user = get_current_user()
    if not current_user or not (current_user.is_admin or current_user.has_role("moderator")):
        return jsonify({"error": "Admin or moderator access required"}), 403

    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    try:
        limit_param = request.args.get("limit", "10")
        limit = int(limit_param)
        limit = max(1, min(limit, 100))
    except ValueError:
        limit = 10

    try:
        result = get_analytics_content(date_from=date_from, date_to=date_to, limit=limit)
        return jsonify(result), 200
    except Exception as e:
        current_app.logger.exception("Analytics error in admin_analytics_content")
        return jsonify({"error": "Failed to fetch content analytics"}), 500


@api_v1_bp.route("/admin/analytics/moderation", methods=["GET"])
@limiter.limit("30 per minute")
@jwt_required()
def admin_analytics_moderation():
    """
    GET /api/v1/admin/analytics/moderation
    Report queue status, resolution trends, and moderator activity.
    Query params: date_from, date_to, priority_filter (optional)
    Requires: admin or moderator role
    """
    current_user = get_current_user()
    if not current_user or not (current_user.is_admin or current_user.has_role("moderator")):
        return jsonify({"error": "Admin or moderator access required"}), 403

    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    priority_filter = request.args.get("priority_filter")

    try:
        result = get_analytics_moderation(date_from=date_from, date_to=date_to, priority_filter=priority_filter)
        return jsonify(result), 200
    except Exception as e:
        current_app.logger.exception("Analytics error in admin_analytics_moderation")
        return jsonify({"error": "Failed to fetch moderation analytics"}), 500
