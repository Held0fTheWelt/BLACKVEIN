"""Admin-only API: activity logs list and export, moderator assignments."""
import json
from flask import jsonify, request, Response

from app.api.v1 import api_v1_bp
from app.auth.permissions import require_jwt_admin, get_current_user
from app.auth.admin_security import admin_security
from app.extensions import limiter, db
from app.services.activity_log_service import list_activity_logs
from app.services import log_activity
from app.services.metrics_service import get_metrics
from app.utils.csv_safe import csv_safe_cell
from app.models import User, ForumCategory, ModeratorAssignment


def _parse_int(value, default, min_val=None, max_val=None):
    if value is None:
        return default
    try:
        n = int(value)
        if min_val is not None and n < min_val:
            return default
        if max_val is not None and n > max_val:
            return max_val
        return n
    except (TypeError, ValueError):
        return default


@api_v1_bp.route("/admin/logs", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_logs_list():
    """
    List activity logs (admin only). Query: q, category, status, date_from, date_to, page, limit.
    Response: items, total, page, limit. Newest first.
    """
    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 50, min_val=1, max_val=100)
    q = request.args.get("q", "").strip() or None
    category = request.args.get("category", "").strip() or None
    status = request.args.get("status", "").strip() or None
    date_from = request.args.get("date_from", "").strip() or None
    date_to = request.args.get("date_to", "").strip() or None

    items, total = list_activity_logs(
        page=page,
        limit=limit,
        q=q,
        category=category,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    return jsonify({
        "items": [e.to_dict() for e in items],
        "total": total,
        "page": page,
        "limit": limit,
    }), 200


@api_v1_bp.route("/admin/metrics", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_metrics():
    """User growth and activity metrics for admin dashboards. Query: range=24h|7d|30d|12m (invalid → 24h)."""
    range_key = (request.args.get("range") or "24h").strip()
    return jsonify(get_metrics(range_key)), 200


@api_v1_bp.route("/admin/logs/export", methods=["GET"])
@limiter.limit("10 per minute")
@admin_security(require_2fa=False, require_super_admin=False, rate_limit="5/minute", audit_log=True)
def admin_logs_export():
    """Export activity logs as CSV (admin only). Same filters as list; limit max 5000."""
    limit = _parse_int(request.args.get("limit"), 5000, min_val=1, max_val=5000)
    q = request.args.get("q", "").strip() or None
    category = request.args.get("category", "").strip() or None
    status = request.args.get("status", "").strip() or None
    date_from = request.args.get("date_from", "").strip() or None
    date_to = request.args.get("date_to", "").strip() or None

    items, _ = list_activity_logs(
        page=1,
        limit=limit,
        q=q,
        category=category,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )

    lines = [
        "id,created_at,actor_user_id,actor_username_snapshot,actor_role_snapshot,category,action,status,message,route,method,tags,meta,target_type,target_id"
    ]
    for e in items:
        tags_str = ";".join(e.tags or [])
        meta_str = json.dumps(e.meta) if e.meta else ""
        row = [
            csv_safe_cell(e.id),
            csv_safe_cell(e.created_at.isoformat() if e.created_at else ""),
            csv_safe_cell(e.actor_user_id),
            csv_safe_cell(e.actor_username_snapshot),
            csv_safe_cell(e.actor_role_snapshot),
            csv_safe_cell(e.category),
            csv_safe_cell(e.action),
            csv_safe_cell(e.status),
            csv_safe_cell((e.message or "").replace("\n", " ")),
            csv_safe_cell(e.route),
            csv_safe_cell(e.method),
            csv_safe_cell(tags_str),
            csv_safe_cell(meta_str),
            csv_safe_cell(e.target_type),
            csv_safe_cell(e.target_id),
        ]
        lines.append(",".join(row))

    return Response(
        "\n".join(lines),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=wos-activity-logs.csv"},
    )


# --- Moderator Assignment Management ------------------------------------------


@api_v1_bp.route("/admin/moderator-assignments", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_list_moderator_assignments():
    """
    List all moderator-category assignments (admin only).
    Query: page, limit, user_id (filter), category_id (filter).
    """
    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 50, min_val=1, max_val=100)
    user_id_filter = _parse_int(request.args.get("user_id"), None)
    category_id_filter = _parse_int(request.args.get("category_id"), None)

    q = ModeratorAssignment.query
    if user_id_filter:
        q = q.filter_by(user_id=user_id_filter)
    if category_id_filter:
        q = q.filter_by(category_id=category_id_filter)

    total = q.count()
    items = q.offset((page - 1) * limit).limit(limit).all()

    return jsonify({
        "items": [a.to_dict() for a in items],
        "total": total,
        "page": page,
        "limit": limit,
    }), 200


@api_v1_bp.route("/admin/moderator-assignments", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_admin
def admin_create_moderator_assignment():
    """
    Assign a moderator to a category (admin only).
    Body: user_id (int), category_id (int).
    """
    admin_user = get_current_user()
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    try:
        user_id = int(data.get("user_id"))
        category_id = int(data.get("category_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "user_id and category_id must be integers"}), 400

    # Verify user exists and is a moderator
    user = User.query.get(user_id)
    if not user or not user.is_moderator_or_admin:
        return jsonify({"error": "User not found or is not a moderator/admin"}), 404

    # Verify category exists
    category = ForumCategory.query.get(category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    # Check for existing assignment
    existing = ModeratorAssignment.query.filter_by(
        user_id=user_id,
        category_id=category_id,
    ).first()
    if existing:
        return jsonify({"error": "Moderator is already assigned to this category"}), 409

    # Create assignment
    assignment = ModeratorAssignment(
        user_id=user_id,
        category_id=category_id,
        assigned_by=admin_user.id,
    )
    db.session.add(assignment)
    db.session.commit()

    log_activity(
        actor=admin_user,
        category="admin",
        action="moderator_assigned",
        status="success",
        message=f"Moderator {user.username} assigned to category {category.slug}",
        route=request.path,
        method=request.method,
        target_type="moderator_assignment",
        target_id=str(assignment.id),
        metadata={"user_id": user_id, "category_id": category_id},
    )

    return jsonify(assignment.to_dict()), 201


@api_v1_bp.route("/admin/moderator-assignments/<int:assignment_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@require_jwt_admin
def admin_delete_moderator_assignment(assignment_id: int):
    """
    Remove a moderator from a category (admin only).
    """
    admin_user = get_current_user()
    assignment = ModeratorAssignment.query.get(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404

    user = User.query.get(assignment.user_id)
    category = ForumCategory.query.get(assignment.category_id)

    db.session.delete(assignment)
    db.session.commit()

    log_activity(
        actor=admin_user,
        category="admin",
        action="moderator_unassigned",
        status="success",
        message=(
            f"Moderator {user.username if user else 'unknown'} unassigned from category "
            f"{category.slug if category else 'unknown'}"
        ),
        route=request.path,
        method=request.method,
        target_type="moderator_assignment",
        target_id=str(assignment_id),
        metadata={"user_id": assignment.user_id, "category_id": assignment.category_id},
    )

    return jsonify({"message": "Unassigned"}), 200


@api_v1_bp.route("/admin/moderator-assignments/user/<int:user_id>", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_list_user_assignments(user_id: int):
    """
    List all categories a moderator is assigned to (admin only).
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    assignments = ModeratorAssignment.query.filter_by(user_id=user_id).all()
    categories = []
    for assignment in assignments:
        cat = ForumCategory.query.get(assignment.category_id)
        if cat:
            categories.append(cat.to_dict())

    return jsonify({
        "user_id": user_id,
        "username": user.username,
        "categories": categories,
        "total": len(categories),
    }), 200