"""Wiki admin API: pages CRUD and translations (submit-review, approve, publish, auto-translate)."""
from flask import g, jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.permissions import get_current_user, require_editor_or_n8n_service, require_jwt_moderator_or_admin
from app.extensions import limiter, db
from app.i18n import normalize_language
from app.services import log_activity
from app.models import WikiPage, ForumThread
from app.services.wiki_service import (
    approve_wiki_translation,
    create_wiki_page,
    get_wiki_page_by_id,
    list_wiki_page_translations,
    list_wiki_pages,
    get_wiki_page_translation,
    publish_wiki_translation,
    submit_review_wiki_translation,
    update_wiki_page,
    upsert_wiki_page_translation,
)


def _page_to_dict(page):
    return {
        "id": page.id,
        "key": page.key,
        "parent_id": page.parent_id,
        "sort_order": page.sort_order,
        "is_published": page.is_published,
        "created_at": page.created_at.isoformat() if page.created_at else None,
        "updated_at": page.updated_at.isoformat() if page.updated_at else None,
    }


def _translation_to_dict(t):
    return {
        "id": t.id,
        "page_id": t.page_id,
        "language_code": t.language_code,
        "title": t.title,
        "slug": t.slug,
        "content_markdown": t.content_markdown,
        "translation_status": t.translation_status,
        "source_language": t.source_language,
        "reviewed_by": t.reviewed_by,
        "reviewed_at": t.reviewed_at.isoformat() if t.reviewed_at else None,
    }


@api_v1_bp.route("/wiki-admin/pages", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
def wiki_admin_pages_list():
    """List all wiki pages. Requires moderator/admin."""
    pages = list_wiki_pages()
    return jsonify({"items": [_page_to_dict(p) for p in pages]}), 200


@api_v1_bp.route("/wiki-admin/pages", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def wiki_admin_pages_create():
    """Create a wiki page. Body: key, parent_id?, sort_order?, is_published?. Requires moderator/admin."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    key = (data.get("key") or "").strip()
    parent_id = data.get("parent_id")
    sort_order = int(data.get("sort_order", 0))
    is_published = bool(data.get("is_published", True))
    page, err = create_wiki_page(key=key, parent_id=parent_id, sort_order=sort_order, is_published=is_published)
    if err:
        return jsonify({"error": err}), 400 if err != "Key already in use" else 409
    return jsonify(_page_to_dict(page)), 201


@api_v1_bp.route("/wiki-admin/pages/<int:page_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def wiki_admin_pages_update(page_id):
    """Update wiki page. Body: key?, sort_order?, is_published?. Requires moderator/admin."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    kwargs = {}
    if "key" in data:
        kwargs["key"] = data.get("key")
    if "sort_order" in data:
        kwargs["sort_order"] = int(data.get("sort_order", 0))
    if "is_published" in data:
        kwargs["is_published"] = bool(data.get("is_published"))
    page, err = update_wiki_page(page_id, **kwargs)
    if err:
        return jsonify({"error": err}), 404 if err == "Page not found" else 400
    return jsonify(_page_to_dict(page)), 200


@api_v1_bp.route("/wiki-admin/pages/<int:page_id>/translations", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
def wiki_admin_translations_list(page_id):
    """List translation status per language for page. Requires moderator/admin."""
    items, err = list_wiki_page_translations(page_id)
    if err:
        return jsonify({"error": err}), 404
    return jsonify({"items": items}), 200


@api_v1_bp.route("/wiki-admin/pages/<int:page_id>/translations/<lang>", methods=["GET"])
@limiter.limit("60 per minute")
@require_editor_or_n8n_service
def wiki_admin_translation_get(page_id, lang):
    """Get one wiki translation. Requires moderator/admin or n8n X-Service-Key."""
    if not normalize_language(lang):
        return jsonify({"error": "Unsupported language"}), 400
    trans = get_wiki_page_translation(page_id, lang)
    if not trans:
        return jsonify({"error": "Translation not found"}), 404
    return jsonify(_translation_to_dict(trans)), 200


@api_v1_bp.route("/wiki-admin/pages/<int:page_id>/translations/<lang>", methods=["PUT"])
@limiter.limit("30 per minute")
@require_editor_or_n8n_service
def wiki_admin_translation_put(page_id, lang):
    """Create or update wiki page translation. Body: title, slug, content_markdown, translation_status?. Requires moderator/admin or n8n X-Service-Key (machine_draft only)."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    translation_status = data.get("translation_status")
    if getattr(g, "is_n8n_service", False):
        translation_status = "machine_draft"
    trans, err = upsert_wiki_page_translation(
        page_id,
        lang,
        title=data.get("title"),
        slug=data.get("slug"),
        content_markdown=data.get("content_markdown"),
        translation_status=translation_status,
    )
    if err:
        status = 404 if err == "Page not found" else 400
        return jsonify({"error": err}), status
    return jsonify(_translation_to_dict(trans)), 200


@api_v1_bp.route("/wiki-admin/pages/<int:page_id>/translations/<lang>/submit-review", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def wiki_admin_translation_submit_review(page_id, lang):
    """Set translation status to review_required. Requires moderator/admin."""
    trans, err = submit_review_wiki_translation(page_id, lang)
    if err:
        return jsonify({"error": err}), 404
    log_activity(
        actor=get_current_user(),
        category="wiki",
        action="translation_submit_review",
        status="success",
        message=f"Wiki translation {page_id}/{lang} submitted for review",
        route=request.path,
        method=request.method,
        target_type="wiki_translation",
        target_id=f"{page_id}:{lang}",
    )
    return jsonify(_translation_to_dict(trans)), 200


@api_v1_bp.route("/wiki-admin/pages/<int:page_id>/translations/<lang>/approve", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def wiki_admin_translation_approve(page_id, lang):
    """Set translation status to approved. Requires moderator/admin."""
    user = get_current_user()
    trans, err = approve_wiki_translation(page_id, lang, reviewer_id=user.id if user else None)
    if err:
        return jsonify({"error": err}), 404
    log_activity(
        actor=user,
        category="wiki",
        action="translation_approve",
        status="success",
        message=f"Wiki translation {page_id}/{lang} approved",
        route=request.path,
        method=request.method,
        target_type="wiki_translation",
        target_id=f"{page_id}:{lang}",
    )
    return jsonify(_translation_to_dict(trans)), 200


@api_v1_bp.route("/wiki-admin/pages/<int:page_id>/translations/<lang>/publish", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def wiki_admin_translation_publish(page_id, lang):
    """Set translation status to published. Requires moderator/admin."""
    trans, err = publish_wiki_translation(page_id, lang)
    if err:
        return jsonify({"error": err}), 404
    log_activity(
        actor=get_current_user(),
        category="wiki",
        action="translation_publish",
        status="success",
        message=f"Wiki translation {page_id}/{lang} published",
        route=request.path,
        method=request.method,
        target_type="wiki_translation",
        target_id=f"{page_id}:{lang}",
    )
    return jsonify(_translation_to_dict(trans)), 200


@api_v1_bp.route("/wiki-admin/pages/<int:page_id>/translations/auto-translate", methods=["POST"])
@limiter.limit("20 per minute")
@require_jwt_moderator_or_admin
def wiki_admin_auto_translate(page_id):
    """Request machine translation for missing languages. Body: target_language?. Triggers n8n when N8N_WEBHOOK_URL set."""
    data = request.get_json(silent=True) or {}
    target_lang = (data.get("target_language") or "").strip().lower() or None
    from flask import current_app
    supported = current_app.config.get("SUPPORTED_LANGUAGES", ["de", "en"])
    page = get_wiki_page_by_id(page_id)
    if not page:
        return jsonify({"error": "Page not found"}), 404
    if target_lang and target_lang not in supported:
        return jsonify({"error": "Unsupported target language"}), 400
    items, _ = list_wiki_page_translations(page_id)
    missing = [it["language_code"] for it in items if it.get("translation_status") == "missing"]
    if target_lang:
        missing = [target_lang] if target_lang in missing else []
    from app.i18n import get_default_language
    from app.n8n_trigger import trigger_webhook
    source_lang = get_default_language()
    for lang in missing:
        trigger_webhook("wiki.translation.requested", {
            "page_id": page_id,
            "target_language": lang,
            "source_language": source_lang,
        })
    return jsonify({
        "message": "Auto-translate requested; translations will be created as machine_draft by automation.",
        "translations": items,
    }), 202


# --- Discussion Thread Links (Phase 5) ----------------------------------------


@api_v1_bp.route("/wiki/<int:page_id>/discussion-thread", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def wiki_link_discussion_thread(page_id: int):
    """
    Link a discussion thread to a wiki page (moderator/admin only).
    Body: discussion_thread_id.
    """
    page = get_wiki_page_by_id(page_id)
    if not page:
        return jsonify({"error": "Wiki page not found"}), 404

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    try:
        thread_id = int(data.get("discussion_thread_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "discussion_thread_id must be an integer"}), 400

    thread = ForumThread.query.get(thread_id)
    if not thread:
        return jsonify({"error": "Discussion thread not found"}), 404

    page.discussion_thread_id = thread_id
    db.session.commit()
    log_activity(
        actor=get_current_user(),
        category="wiki",
        action="discussion_linked",
        status="success",
        message=f"Discussion thread {thread_id} linked to wiki page {page_id}",
        route=request.path,
        method=request.method,
        target_type="wiki_page",
        target_id=str(page_id),
    )
    return jsonify({
        "id": page.id,
        "discussion_thread_id": page.discussion_thread_id,
    }), 200


@api_v1_bp.route("/wiki/<int:page_id>/discussion-thread", methods=["DELETE"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def wiki_unlink_discussion_thread(page_id: int):
    """
    Unlink a discussion thread from a wiki page (moderator/admin only).
    """
    page = get_wiki_page_by_id(page_id)
    if not page:
        return jsonify({"error": "Wiki page not found"}), 404

    page.discussion_thread_id = None
    db.session.commit()
    log_activity(
        actor=get_current_user(),
        category="wiki",
        action="discussion_unlinked",
        status="success",
        message=f"Discussion thread unlinked from wiki page {page_id}",
        route=request.path,
        method=request.method,
        target_type="wiki_page",
        target_id=str(page_id),
    )
    return jsonify({"message": "Discussion thread unlinked"}), 200
