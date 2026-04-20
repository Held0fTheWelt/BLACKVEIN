"""Wiki API: public page by slug; legacy file GET/PUT; wiki-admin in wiki_admin_routes."""
from pathlib import Path

import markdown
from flask import current_app, jsonify, request

from app.api.v1 import api_v1_bp
from app.utils.html_sanitizer import sanitize_wiki_html
from app.auth.permissions import get_current_user, require_jwt_moderator_or_admin
from app.extensions import db, limiter
from app.models import ForumThread
from app.services import log_activity
from app.services.wiki_service import (
    get_wiki_page_by_slug,
    get_suggested_threads_for_wiki_page,
    list_related_threads_for_page,
)

def _wiki_path():
    """Return Path to Backend/content/wiki.md. Resolved from a fixed base path."""
    # Use a fixed base path for critical files
    base_path = Path(__file__).parent.parent / "content" / "wiki.md"
    return base_path

@api_v1_bp.route("/wiki/<slug>", methods=["GET"])
@limiter.limit("60 per minute")
def wiki_page_get(slug):
    """Public: get wiki page by slug. Query: lang. Returns title, slug, content_markdown, html, language_code."""
    lang = request.args.get("lang", "").strip() or None
    page, trans = get_wiki_page_by_slug(slug, lang=lang)
    if not page or not trans:
        return jsonify({"error": "Not found"}), 404
    try:
        raw_html = markdown.markdown(trans.content_markdown or "", extensions=["extra"])
        html = sanitize_wiki_html(raw_html) if raw_html else None
    except Exception:
        html = None
    payload = {
        "title": trans.title,
        "slug": trans.slug,
        "content_markdown": trans.content_markdown,
        "html": html,
        "language_code": trans.language_code,
    }
    # Contextual discussion information
    if page.discussion_thread_id is not None:
        thread = db.session.get(ForumThread, page.discussion_thread_id)
        if thread and thread.deleted_at is None:
            payload["discussion"] = {
                "type": "primary",
                "thread_id": thread.id,
                "thread_slug": thread.slug,
                "thread_title": thread.title,
                "category": thread.category.slug if thread.category else None,
            }
        else:
            payload["discussion"] = None
    else:
        payload["discussion"] = None

    # Manually linked related threads (with type marker)
    related = list_related_threads_for_page(page.id, limit=5)
    if related:
        payload["related_threads"] = [
            {**t, "type": "related"} for t in related
        ]

    # Auto-suggested threads (distinct from manually linked, with grounded reason)
    suggested = get_suggested_threads_for_wiki_page(page.id, limit=5)
    manual_ids = {t["id"] for t in (related or [])}
    if page.discussion_thread_id:
        manual_ids.add(page.discussion_thread_id)
    unique_suggested = [t for t in suggested if t.get("id") not in manual_ids]
    if unique_suggested:
        payload["suggested_threads"] = [
            {**t, "type": "suggested"} for t in unique_suggested
        ]

    return jsonify(payload), 200


@api_v1_bp.route("/wiki/<int:page_id>/suggested-threads", methods=["GET"])
@limiter.limit("60 per minute")
def wiki_suggested_threads_get(page_id: int):
    """Get auto-suggested forum threads for a wiki page.

    Suggestions are ranked deterministically by:
    1. Tag matches (from the primary discussion thread)
    2. Recent activity (last_post_at DESC, as tie-breaker)

    Automatically excludes:
    - Hidden and deleted threads
    - The primary discussion thread (if set)
    - Manually linked related threads

    Each suggestion includes a grounded 'reason' label indicating the match signal.

    Returns:
    - { "items": [thread_objects_with_reason], "total": count }
    - 404 if page not found
    """
    from app.models import WikiPage

    page = db.session.get(WikiPage, page_id)
    if not page:
        return jsonify({"error": "Wiki page not found"}), 404

    suggested = get_suggested_threads_for_wiki_page(page_id, limit=10)

    return jsonify({
        "items": suggested,
        "total": len(suggested),
    }), 200


@api_v1_bp.route("/wiki", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
def wiki_get():
    """
    Return wiki source (markdown) and optionally rendered HTML.
    Requires JWT with moderator or admin role.
    """
    path = _wiki_path()
    if not path.is_file():
        return jsonify({"content": "", "html": None}), 200
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return jsonify({"error": "Could not read wiki file"}), 500
    try:
        raw_html = markdown.markdown(text, extensions=["extra"])
        html = sanitize_wiki_html(raw_html) if raw_html else None
    except Exception:
        html = None
    return jsonify({"content": text, "html": html}), 200


@api_v1_bp.route("/wiki", methods=["PUT"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def wiki_put():
    """
    Update wiki markdown source. Requires JWT with moderator or admin role.
    Body: { "content": "raw markdown string" }.
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    content = data.get("content")
    if content is None:
        return jsonify({"error": "content is required"}), 400
    if not isinstance(content, str):
        return jsonify({"error": "content must be a string"}), 400

    path = _wiki_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as e:
        current_app.logger.warning("Wiki write failed: %s", e)
        return jsonify({"error": "Could not write wiki file"}), 500

    log_activity(
        actor=get_current_user(),
        category="content",
        action="wiki_updated",
        status="success",
        message="Wiki content updated",
        route=request.path,
        method=request.method,
        target_type="wiki",
        target_id="wiki.md",
    )
    return jsonify({"message": "Updated", "content": content}), 200
