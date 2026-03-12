"""Wiki API: public page by slug; legacy file GET/PUT; wiki-admin in wiki_admin_routes."""
from pathlib import Path

import markdown
from flask import current_app, jsonify, request

from app.api.v1 import api_v1_bp
from app.utils.html_sanitizer import sanitize_wiki_html
from app.auth.permissions import get_current_user, require_jwt_moderator_or_admin
from app.extensions import limiter
from app.services import log_activity
from app.services.wiki_service import get_wiki_page_by_slug


def _wiki_path():
    """Return Path to Backend/content/wiki.md. Resolved from app root."""
    app_root = Path(current_app.root_path)
    return app_root.parent / "content" / "wiki.md"


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
    return jsonify({
        "title": trans.title,
        "slug": trans.slug,
        "content_markdown": trans.content_markdown,
        "html": html,
        "language_code": trans.language_code,
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
