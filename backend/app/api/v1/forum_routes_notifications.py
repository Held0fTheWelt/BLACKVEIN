"""Notification endpoints (register on api_v1_bp)."""

from __future__ import annotations

from flask import jsonify, request
from flask_jwt_extended import jwt_required

from app.api.v1 import api_v1_bp
from app.api.v1.forum_routes_helpers import _parse_int, _require_user
from app.extensions import db, limiter
from app.models import Notification
from app.services.forum_service import get_post_by_id, get_thread_by_id, _utc_now


@api_v1_bp.route("/notifications", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def notifications_list():
    """
    List notifications for current user.
    Query: page, limit, unread_only (boolean).
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp

    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)
    unread_only = request.args.get("unread_only", "").lower() in ("1", "true", "yes")

    q = Notification.query.filter_by(user_id=user.id)
    if unread_only:
        q = q.filter_by(is_read=False)
    q = q.order_by(Notification.created_at.desc())

    total = q.count()
    page = max(1, page)
    limit = max(1, min(limit, 100))
    start = (page - 1) * limit
    end = start + limit

    items = q.offset(start).limit(limit).all()
    items_data = []
    for n in items:
        d = n.to_dict()
        if n.target_type == "forum_thread":
            thread = get_thread_by_id(n.target_id)
            d["thread_slug"] = thread.slug if thread and thread.deleted_at is None else None
            d["target_post_id"] = None
        elif n.target_type == "forum_post":
            post = get_post_by_id(n.target_id)
            if post and post.thread and post.thread.deleted_at is None:
                d["thread_slug"] = post.thread.slug
                d["target_post_id"] = post.id
            else:
                d["thread_slug"] = None
                d["target_post_id"] = None
        else:
            d["thread_slug"] = None
            d["target_post_id"] = None
        items_data.append(d)

    return jsonify({
        "items": items_data,
        "total": total,
        "page": page,
        "per_page": limit,
    }), 200


@api_v1_bp.route("/notifications/<int:notification_id>/read", methods=["PATCH", "PUT"])
@limiter.limit("60 per minute")
@jwt_required()
def notification_mark_read(notification_id: int):
    """Mark a notification as read. Only the owner can mark it."""
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    n = Notification.query.filter_by(id=notification_id, user_id=user.id).first()
    if not n:
        return jsonify({"error": "Not found"}), 404
    n.is_read = True
    n.read_at = _utc_now()
    db.session.commit()
    return jsonify(n.to_dict()), 200


@api_v1_bp.route("/notifications/read-all", methods=["POST", "PUT"])
@limiter.limit("30 per minute")
@jwt_required()
def notifications_mark_all_read():
    """Mark all notifications for the current user as read."""
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    now = _utc_now()
    updated = Notification.query.filter_by(user_id=user.id, is_read=False).update(
        {Notification.is_read: True, Notification.read_at: now},
        synchronize_session=False,
    )
    db.session.commit()
    return jsonify({"message": "Marked all as read", "updated": updated}), 200
