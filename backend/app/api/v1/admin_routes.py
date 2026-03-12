"""Admin-only API: activity logs list and export."""
import json
from flask import jsonify, request, Response

from app.api.v1 import api_v1_bp
from app.auth.permissions import require_jwt_admin
from app.extensions import limiter
from app.services.activity_log_service import list_activity_logs
from app.utils.csv_safe import csv_safe_cell


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


@api_v1_bp.route("/admin/logs/export", methods=["GET"])
@limiter.limit("10 per minute")
@require_jwt_admin
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
