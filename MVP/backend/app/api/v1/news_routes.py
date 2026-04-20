"""Public read-only news API. Only published news is exposed.

List:  GET /api/v1/news?q=&sort=published_at&direction=desc&page=1&limit=20&category=
  Response: { "items": [ { "id", "title", "slug", "summary", "content", "author_id", "author_name",
    "is_published", "published_at", "created_at", "updated_at", "cover_image", "category" } ], "total", "page", "per_page" }

Detail: GET /api/v1/news/<id>
  Response: single object same shape as list item, or { "error": "Not found" } 404.

Write (all require Authorization: Bearer <JWT> and moderator/admin role; 401 if missing/invalid token, 403 if forbidden):
  POST   /api/v1/news             -> create (body: title, slug, content; optional summary, is_published, cover_image, category)
  PUT    /api/v1/news/<id>        -> update (body: optional title, slug, summary, content, cover_image, category)
  DELETE /api/v1/news/<id>        -> delete
  POST   /api/v1/news/<id>/publish   -> set published
  POST   /api/v1/news/<id>/unpublish -> set unpublished
"""
from datetime import datetime, timezone

from flask import g, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.v1 import api_v1_bp
from app.auth import current_user_can_write_news
from app.auth.permissions import get_current_user, require_editor_or_n8n_service, require_jwt_moderator_or_admin
from app.extensions import limiter, db
from app.services import log_activity
from app.i18n import normalize_language, validate_language_code
from app.models import NewsArticle, ForumThread
from app.services.news_service import (
    SORT_FIELDS,
    SORT_ORDERS,
    approve_article_translation,
    create_news,
    delete_news,
    get_article_translation,
    get_news_by_id,
    get_news_by_slug,
    get_news_article_by_id,
    get_suggested_threads_for_article,
    list_article_translations,
    list_news,
    publish_article_translation,
    publish_news,
    submit_review_article_translation,
    unpublish_news,
    update_news,
    upsert_article_translation,
    _translation_to_dict,
    list_related_threads_for_article,
)


def _parse_int(value, default, min_val=None, max_val=None):
    """Parse query param as int; return default if missing/invalid."""
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


def _request_wants_include_drafts():
    """True if request has valid JWT with moderator/admin and query published_only=0 or include_drafts=1."""
    try:
        from flask_jwt_extended import get_jwt_identity
        raw = get_jwt_identity()
        if raw is None:
            return False
    except Exception:
        return False
    if not current_user_can_write_news():
        return False
    p = request.args.get("published_only", "").strip().lower()
    if p in ("0", "false", "no"):
        return True
    d = request.args.get("include_drafts", "").strip().lower()
    if d in ("1", "true", "yes"):
        return True
    return False


@api_v1_bp.route("/news", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required(optional=True)
def news_list():
    """
    List news. By default only published. With JWT (moderator/admin) and published_only=0 or include_drafts=1, includes drafts.
    Query params: q (search), sort, direction, page, limit, category, lang, published_only (0 to include drafts).
    Response: { "items": [...], "total": N, "page": P, "per_page": L }.
    """
    q = request.args.get("q", "").strip() or None
    sort = request.args.get("sort", "published_at").strip() or "published_at"
    if sort not in SORT_FIELDS:
        sort = "published_at"
    direction = request.args.get("direction", "desc").strip().lower() or "desc"
    if direction not in SORT_ORDERS:
        direction = "desc"
    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)
    category = request.args.get("category", "").strip() or None
    lang = request.args.get("lang", "").strip() or None
    published_only = not _request_wants_include_drafts()

    items, total = list_news(
        published_only=published_only,
        search=q,
        sort=sort,
        order=direction,
        page=page,
        per_page=limit,
        category=category,
        lang=lang,
    )
    return jsonify({
        "items": items,
        "total": total,
        "page": page,
        "per_page": limit,
    }), 200


@api_v1_bp.route("/news/<id_or_slug>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required(optional=True)
def news_detail(id_or_slug):
    """
    Get a single news article by id (integer) or slug (string). Public: only published; 404 for draft.
    With JWT (moderator/admin): returns article even if draft. Query: lang for language.
    Response: single news object (id, title, slug, summary, content, author_id, author_name, language_code, ...).
    """
    lang = request.args.get("lang", "").strip() or None
    news = None
    if id_or_slug.isdigit():
        news = get_news_by_id(int(id_or_slug), lang=lang)
    else:
        news = get_news_by_slug(id_or_slug, lang=lang)
    if not news:
        return jsonify({"error": "Not found"}), 404
    if not news.get("is_published"):
        try:
            if get_jwt_identity() is not None and current_user_can_write_news():
                return jsonify(news), 200
        except Exception:
            pass
        return jsonify({"error": "Not found"}), 404
    now = datetime.now(timezone.utc)
    pub_at = news.get("published_at")
    if pub_at:
        try:
            dt = datetime.fromisoformat(pub_at.replace("Z", "+00:00")) if isinstance(pub_at, str) else pub_at
            if hasattr(dt, "tzinfo") and dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt > now:
                return jsonify({"error": "Not found"}), 404
        except (ValueError, TypeError):
            pass
    # Attach discussion context for integration layer (public, safe subset).
    if news.get("id"):
        article_id = news["id"]

        # Primary discussion thread
        article = get_news_article_by_id(article_id)
        if article and article.discussion_thread_id:
            thread = db.session.get(ForumThread, article.discussion_thread_id)
            if thread and thread.deleted_at is None:
                news["discussion"] = {
                    "type": "primary",
                    "thread_id": thread.id,
                    "thread_slug": thread.slug,
                    "thread_title": thread.title,
                    "category": thread.category.slug if thread.category else None,
                }

        # Manually linked related threads
        related = list_related_threads_for_article(article_id, limit=5)
        if related:
            news["related_threads"] = [
                {**t, "type": "related"} for t in related
            ]

        # Auto-suggested threads (excluding duplicates)
        suggested = get_suggested_threads_for_article(article_id, limit=5)
        manual_ids = {t.get("id") for t in (related or [])}
        if article and article.discussion_thread_id:
            manual_ids.add(article.discussion_thread_id)
        unique_suggested = [t for t in suggested if t.get("id") not in manual_ids]
        if unique_suggested:
            news["suggested_threads"] = [
                {**t, "type": "suggested"} for t in unique_suggested
            ]

    return jsonify(news), 200


# --- Protected write endpoints (JWT required) ---


@api_v1_bp.route("/news", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def news_create():
    """
    Create a news article. Requires JWT and moderator/admin role. Body: title, slug, content; optional summary, is_published, cover_image, category.
    author_id is set from JWT identity.
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    title = (data.get("title") or "").strip()
    slug = (data.get("slug") or "").strip()
    content = (data.get("content") or "").strip()
    if not title or not slug or not content:
        return jsonify({"error": "title, slug, and content are required"}), 400
    try:
        author_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid token"}), 401
    summary = data.get("summary")
    if summary is not None:
        summary = (summary or "").strip() or None
    is_published = bool(data.get("is_published", False))
    cover_image = data.get("cover_image")
    if cover_image is not None:
        cover_image = (cover_image or "").strip() or None
    category = data.get("category")
    if category is not None:
        category = (category or "").strip() or None

    article, err = create_news(
        title=title,
        slug=slug,
        content=content,
        summary=summary,
        author_id=author_id,
        is_published=is_published,
        cover_image=cover_image,
        category=category,
    )
    if err:
        status = 409 if err == "Slug already in use" else 400
        return jsonify({"error": err}), status
    log_activity(
        actor=get_current_user(),
        category="news",
        action="news_created",
        status="success",
        message=f"News created: {article.id}",
        route=request.path,
        method=request.method,
        target_type="news",
        target_id=str(article.id),
    )
    out = get_news_by_id(article.id, lang=article.default_language)
    return jsonify(out), 201


@api_v1_bp.route("/news/<int:article_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def news_update(article_id):
    """
    Update a news article. Requires JWT and moderator/admin role. Body: optional title, slug, summary, content, cover_image, category.
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    kwargs = {}
    if "title" in data:
        kwargs["title"] = (data.get("title") or "").strip() or None
    if "slug" in data:
        kwargs["slug"] = (data.get("slug") or "").strip() or None
    if "summary" in data:
        kwargs["summary"] = (data.get("summary") or "").strip() or None
    if "content" in data:
        kwargs["content"] = (data.get("content") or "").strip() or None
    if "cover_image" in data:
        kwargs["cover_image"] = (data.get("cover_image") or "").strip() or None
    if "category" in data:
        kwargs["category"] = (data.get("category") or "").strip() or None

    article, err = update_news(article_id, **kwargs)
    if err:
        status = 409 if err == "Slug already in use" else (404 if err == "News not found" else 400)
        return jsonify({"error": err}), status
    log_activity(
        actor=get_current_user(),
        category="news",
        action="news_updated",
        status="success",
        message=f"News updated: {article.id}",
        route=request.path,
        method=request.method,
        target_type="news",
        target_id=str(article.id),
    )
    out = get_news_by_id(article.id, lang=article.default_language)
    return jsonify(out), 200


@api_v1_bp.route("/news/<int:article_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def news_delete(article_id):
    """Delete a news article. Requires JWT and moderator/admin role."""
    ok, err = delete_news(article_id)
    if err:
        return jsonify({"error": err}), 404
    log_activity(
        actor=get_current_user(),
        category="news",
        action="news_deleted",
        status="success",
        message=f"News deleted: id={article_id}",
        route=request.path,
        method=request.method,
        target_type="news",
        target_id=str(article_id),
    )
    return jsonify({"message": "Deleted"}), 200


@api_v1_bp.route("/news/<int:article_id>/publish", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def news_publish(article_id):
    """Set article as published. Requires JWT and moderator/admin role."""
    article, err = publish_news(article_id)
    if err:
        return jsonify({"error": err}), 404
    log_activity(
        actor=get_current_user(),
        category="news",
        action="news_published",
        status="success",
        message=f"News published: {article.id}",
        route=request.path,
        method=request.method,
        target_type="news",
        target_id=str(article.id),
    )
    out = get_news_by_id(article.id, lang=article.default_language)
    return jsonify(out), 200


@api_v1_bp.route("/news/<int:article_id>/unpublish", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def news_unpublish(article_id):
    """Set article as unpublished. Requires JWT and moderator/admin role."""
    article, err = unpublish_news(article_id)
    if err:
        return jsonify({"error": err}), 404
    log_activity(
        actor=get_current_user(),
        category="news",
        action="news_unpublished",
        status="success",
        message=f"News unpublished: {article.id}",
        route=request.path,
        method=request.method,
        target_type="news",
        target_id=str(article.id),
    )
    out = get_news_by_id(article.id, lang=article.default_language)
    return jsonify(out), 200


# --- Article translations (editorial) ---


@api_v1_bp.route("/news/<int:article_id>/translations", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
def news_translations_list(article_id):
    """List translation status per language for article. Requires moderator/admin."""
    items, err = list_article_translations(article_id)
    if err:
        return jsonify({"error": err}), 404
    return jsonify({"items": items}), 200


@api_v1_bp.route("/news/<int:article_id>/translations/<lang>", methods=["GET"])
@limiter.limit("50 per minute", key_func=lambda: request.headers.get("X-Service-Key", ""))
@require_editor_or_n8n_service
def news_translation_get(article_id, lang):
    """Get one translation by language. Requires moderator/admin or n8n X-Service-Key."""
    validated_lang, err = validate_language_code(lang)
    if err:
        return jsonify({"error": err}), 400
    trans = get_article_translation(article_id, validated_lang)
    if not trans:
        return jsonify({"error": "Translation not found"}), 404
    return jsonify(_translation_to_dict(trans)), 200


@api_v1_bp.route("/news/<int:article_id>/translations/<lang>", methods=["PUT"])
@limiter.limit("50 per minute", key_func=lambda: request.headers.get("X-Service-Key", ""))
@require_editor_or_n8n_service
def news_translation_put(article_id, lang):
    """Create or update a translation. Body: title, slug, summary, content, seo_title, seo_description, translation_status. Requires moderator/admin or n8n X-Service-Key (machine_draft only)."""
    validated_lang, err = validate_language_code(lang)
    if err:
        return jsonify({"error": err}), 400
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    translation_status = data.get("translation_status")
    if getattr(g, "is_n8n_service", False):
        translation_status = "machine_draft"
    trans, err = upsert_article_translation(
        article_id,
        validated_lang,
        title=data.get("title"),
        slug=data.get("slug"),
        summary=data.get("summary"),
        content=data.get("content"),
        seo_title=data.get("seo_title"),
        seo_description=data.get("seo_description"),
        translation_status=translation_status,
    )
    if err:
        status = 404 if err == "News not found" else 400
        if err == "Unsupported language":
            status = 400
        if err.startswith("Slug already"):
            status = 409
        return jsonify({"error": err}), status
    return jsonify(_translation_to_dict(trans)), 200


@api_v1_bp.route("/news/<int:article_id>/translations/<lang>/submit-review", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def news_translation_submit_review(article_id, lang):
    """Set translation status to review_required. Requires moderator/admin."""
    validated_lang, err = validate_language_code(lang)
    if err:
        return jsonify({"error": err}), 400
    trans, err = submit_review_article_translation(article_id, validated_lang)
    if err:
        return jsonify({"error": err}), 404
    log_activity(
        actor=get_current_user(),
        category="news",
        action="translation_submit_review",
        status="success",
        message=f"News translation {article_id}/{validated_lang} submitted for review",
        route=request.path,
        method=request.method,
        target_type="news_translation",
        target_id=f"{article_id}:{validated_lang}",
    )
    return jsonify(_translation_to_dict(trans)), 200


@api_v1_bp.route("/news/<int:article_id>/translations/<lang>/approve", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def news_translation_approve(article_id, lang):
    """Set translation status to approved and set reviewed_by. Requires moderator/admin."""
    validated_lang, err = validate_language_code(lang)
    if err:
        return jsonify({"error": err}), 400
    user = get_current_user()
    reviewer_id = user.id if user else None
    trans, err = approve_article_translation(article_id, validated_lang, reviewer_id=reviewer_id)
    if err:
        return jsonify({"error": err}), 404
    log_activity(
        actor=user,
        category="news",
        action="translation_approve",
        status="success",
        message=f"News translation {article_id}/{validated_lang} approved",
        route=request.path,
        method=request.method,
        target_type="news_translation",
        target_id=f"{article_id}:{validated_lang}",
    )
    return jsonify(_translation_to_dict(trans)), 200


@api_v1_bp.route("/news/<int:article_id>/translations/<lang>/publish", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def news_translation_publish(article_id, lang):
    """Set translation status to published. Requires moderator/admin."""
    validated_lang, err = validate_language_code(lang)
    if err:
        return jsonify({"error": err}), 400
    trans, err = publish_article_translation(article_id, validated_lang)
    if err:
        return jsonify({"error": err}), 404
    log_activity(
        actor=get_current_user(),
        category="news",
        action="translation_publish",
        status="success",
        message=f"News translation {article_id}/{validated_lang} published",
        route=request.path,
        method=request.method,
        target_type="news_translation",
        target_id=f"{article_id}:{validated_lang}",
    )
    return jsonify(_translation_to_dict(trans)), 200


@api_v1_bp.route("/news/<int:article_id>/translations/auto-translate", methods=["POST"])
@limiter.limit("20 per minute")
@require_jwt_moderator_or_admin
def news_auto_translate(article_id):
    """
    Request machine translation for missing languages. Body: target_language (optional, else all missing).
    Triggers n8n webhook when N8N_WEBHOOK_URL is set; n8n writes back as machine_draft via X-Service-Key.
    """
    data = request.get_json(silent=True) or {}
    target_lang = (data.get("target_language") or "").strip().lower() or None
    from app.i18n import get_supported_languages
    supported = get_supported_languages()
    article = get_news_article_by_id(article_id)
    if not article:
        return jsonify({"error": "News not found"}), 404
    if target_lang and target_lang not in supported:
        return jsonify({"error": "Unsupported target language"}), 400
    items, _ = list_article_translations(article_id)
    missing = [it["language_code"] for it in items if it.get("translation_status") == "missing"]
    if target_lang:
        missing = [target_lang] if target_lang in missing else []
    from app.n8n_trigger import trigger_webhook
    default_lang = (article.default_language or "").strip() or None
    for lang in missing:
        trigger_webhook("news.translation.requested", {
            "article_id": article_id,
            "target_language": lang,
            "source_language": default_lang,
        })
    return jsonify({
        "message": "Auto-translate requested; translations will be created as machine_draft by automation.",
        "translations": items,
    }), 202


# --- Discussion Thread Links (Phase 5) ----------------------------------------


@api_v1_bp.route("/news/<int:article_id>/discussion-thread", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def news_link_discussion_thread(article_id: int):
    """
    Link a discussion thread to a news article (moderator/admin only).
    Body: discussion_thread_id.
    """
    user = get_current_user()
    if not user or not current_user_can_write_news():
        return jsonify({"error": "Forbidden"}), 403

    article = get_news_article_by_id(article_id)
    if not article:
        return jsonify({"error": "News article not found"}), 404

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

    article.discussion_thread_id = thread_id
    db.session.commit()
    log_activity(
        actor=user,
        category="news",
        action="discussion_linked",
        status="success",
        message=f"Discussion thread {thread_id} linked to article {article_id}",
        route=request.path,
        method=request.method,
        target_type="news_article",
        target_id=str(article_id),
    )
    return jsonify({
        "id": article.id,
        "discussion_thread_id": article.discussion_thread_id,
    }), 200


@api_v1_bp.route("/news/<int:article_id>/discussion-thread", methods=["DELETE"])
@limiter.limit("30 per minute")
@jwt_required()
def news_unlink_discussion_thread(article_id: int):
    """
    Unlink a discussion thread from a news article (moderator/admin only).
    """
    user = get_current_user()
    if not user or not current_user_can_write_news():
        return jsonify({"error": "Forbidden"}), 403

    article = get_news_article_by_id(article_id)
    if not article:
        return jsonify({"error": "News article not found"}), 404

    article.discussion_thread_id = None
    db.session.commit()
    log_activity(
        actor=user,
        category="news",
        action="discussion_unlinked",
        status="success",
        message=f"Discussion thread unlinked from article {article_id}",
        route=request.path,
        method=request.method,
        target_type="news_article",
        target_id=str(article_id),
    )
    return jsonify({"message": "Discussion thread unlinked"}), 200


@api_v1_bp.route("/news/<int:article_id>/related-threads", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required(optional=True)
def news_related_threads_get(article_id: int):
    """
    List related forum threads for a news article.
    Public, but only returns threads in public categories.
    """
    article = get_news_article_by_id(article_id)
    if not article:
        return jsonify({"error": "News article not found"}), 404
    items = list_related_threads_for_article(article.id, limit=10)
    return jsonify({"items": items}), 200


@api_v1_bp.route("/news/<int:article_id>/related-threads", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def news_related_threads_add(article_id: int):
    """
    Add a related forum thread to a news article.
    Body: thread_id.
    """
    article = get_news_article_by_id(article_id)
    if not article:
        return jsonify({"error": "News article not found"}), 404

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    try:
        thread_id = int(data.get("thread_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "thread_id must be an integer"}), 400

    thread = ForumThread.query.get(thread_id)
    if not thread or thread.deleted_at is not None:
        return jsonify({"error": "Forum thread not found"}), 404

    from app.models import NewsArticleForumThread

    existing = NewsArticleForumThread.query.filter_by(article_id=article.id, thread_id=thread.id).first()
    if existing:
        mapping = existing
    else:
        mapping = NewsArticleForumThread(
            article_id=article.id,
            thread_id=thread.id,
            relation_type="related",
        )
        db.session.add(mapping)
        db.session.commit()

    log_activity(
        actor=get_current_user(),
        category="news",
        action="related_thread_added",
        status="success",
        message=f"Related thread {thread.id} added to article {article.id}",
        route=request.path,
        method=request.method,
        target_type="news_article",
        target_id=str(article.id),
    )
    items = list_related_threads_for_article(article.id, limit=10)
    return jsonify({"items": items}), 200


@api_v1_bp.route("/news/<int:article_id>/related-threads/<int:thread_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
def news_related_threads_delete(article_id: int, thread_id: int):
    """
    Remove a related forum thread from a news article.
    """
    article = get_news_article_by_id(article_id)
    if not article:
        return jsonify({"error": "News article not found"}), 404

    from app.models import NewsArticleForumThread

    mapping = NewsArticleForumThread.query.filter_by(article_id=article.id, thread_id=thread_id).first()
    if not mapping:
        return jsonify({"error": "Related thread mapping not found"}), 404
    db.session.delete(mapping)
    db.session.commit()

    log_activity(
        actor=get_current_user(),
        category="news",
        action="related_thread_removed",
        status="success",
        message=f"Related thread {thread_id} removed from article {article.id}",
        route=request.path,
        method=request.method,
        target_type="news_article",
        target_id=str(article.id),
    )
    items = list_related_threads_for_article(article.id, limit=10)
    return jsonify({"items": items}), 200


@api_v1_bp.route("/news/<int:article_id>/suggested-threads", methods=["GET"])
@limiter.limit("60 per minute")
def news_suggested_threads_get(article_id: int):
    """Get auto-suggested forum threads for a news article.

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
    - 404 if article not found
    """
    article = get_news_article_by_id(article_id)
    if not article:
        return jsonify({"error": "Article not found"}), 404
    if article.status != "published":
        # Non-published articles don't show suggestions to public
        return jsonify({"items": [], "total": 0}), 200

    # Get auto-suggested threads (already excludes manual links and primary)
    suggested = get_suggested_threads_for_article(article_id, limit=10)

    return jsonify({"items": suggested, "total": len(suggested)}), 200
