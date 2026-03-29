import asyncio
from pathlib import Path

import markdown
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, Response, session, url_for

from app.extensions import db, limiter
from app.models import User
from app.services import create_user, log_activity, verify_user
from app.services.user_service import create_email_verification_token
from app.services.mail_service import send_verification_email
from app.services.game_service import has_complete_play_service_config
from app.web.auth import is_safe_redirect, require_web_login, require_web_admin
from app.services.user_service import update_user_last_seen

# W3.3 imports
from app.runtime.session_store import RuntimeSession, create_session as create_runtime_session, get_session as get_runtime_session, update_session as update_runtime_session
from app.runtime.turn_dispatcher import dispatch_turn
from app.runtime import present_all_characters, present_conflict_panel

# W3.5.1 presenter imports
from app.runtime.history_presenter import present_history_panel, HistoryPanelOutput
from app.runtime.debug_presenter import present_debug_panel, DebugPanelOutput

web_bp = Blueprint("web", __name__)


@web_bp.after_request
def _track_web_activity(response):
    """Update last_seen_at for session-authenticated users (throttled). So dashboard and API calls with session refresh activity."""
    try:
        uid = session.get("user_id")
        if uid is not None:
            update_user_last_seen(uid)
    except Exception:
        pass
    return response


@web_bp.route("/health")
def health():
    """Web health check; returns JSON status."""
    return {"status": "ok"}, 200


@web_bp.route("/")
def home():
    """Home: redirect to frontend when FRONTEND_URL is set; else serve legacy home."""
    frontend_url = current_app.config.get("FRONTEND_URL")
    if frontend_url:
        return redirect(frontend_url.rstrip("/") + "/", code=302)
    return render_template("home.html")


@web_bp.route("/login", methods=["GET", "POST"])
def login():
    """Session-based login. Redirects to dashboard if already logged in."""
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("web.dashboard"))
        return render_template("login.html")
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password")
    if not username or password is None:
        flash("Username and password are required.", "error")
        return render_template("login.html")
    user = verify_user(username, password)
    if user:
        if getattr(user, "is_banned", False):
            log_activity(
                actor=user,
                category="auth",
                action="login_blocked_banned",
                status="warning",
                message="Login attempted by banned user",
                route=request.path,
                method=request.method,
                tags=["web"],
            )
            return redirect(url_for("web.blocked"))
        if (
            current_app.config.get("REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN", True)
            and user.email
            and user.email_verified_at is None
        ):
            log_activity(
                actor=user,
                category="auth",
                action="login_blocked_unverified",
                status="warning",
                message="Login attempted before email verification",
                route=request.path,
                method=request.method,
                tags=["web"],
            )
            flash("Please verify your email before logging in. Check your inbox or resend the link.", "error")
            return redirect(url_for("web.login"))
        log_activity(
            actor=user,
            category="auth",
            action="login",
            status="success",
            message="Web login successful",
            route=request.path,
            method=request.method,
            tags=["web"],
        )
        # Regenerate session to prevent session fixation
        session.clear()
        session["user_id"] = user.id
        session["username"] = user.username
        session.modified = True
        from app.services.user_service import update_user_last_seen
        update_user_last_seen(user.id)
        flash(f"Welcome, {user.username}.", "success")
        next_url = request.args.get("next")
        if not (next_url and is_safe_redirect(next_url)):
            next_url = url_for("web.dashboard")
        return redirect(next_url)
    log_activity(
        actor=None,
        category="auth",
        action="login",
        status="error",
        message="Invalid username or password",
        route=request.path,
        method=request.method,
        tags=["web"],
        metadata={"username_provided": bool(username)},
    )
    flash("Invalid username or password.", "error")
    return render_template("login.html")


@web_bp.route("/blocked")
def blocked():
    """Dedicated view for banned/blocked users. No login required."""
    return render_template("blocked.html")


@web_bp.route("/logout", methods=["POST"])
def logout():
    """Clear session and redirect to home. POST only to avoid CSRF/logout-link abuse."""
    uid = session.get("user_id")
    if uid:
        user = db.session.get(User, int(uid))
        if user:
            log_activity(
                actor=user,
                category="auth",
                action="logout",
                status="success",
                message="Web logout",
                route=request.path,
                method=request.method,
                tags=["web"],
            )
    session.clear()
    flash("You have been logged out.", "info")
    frontend_url = current_app.config.get("FRONTEND_URL")
    if frontend_url:
        return redirect(frontend_url.rstrip("/") + "/", code=302)
    return redirect(url_for("web.home"))


@web_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def register():
    """Registration form. Redirects to login on success."""
    if session.get("user_id"):
        return redirect(url_for("web.dashboard"))
    if request.method == "GET":
        require_email = current_app.config.get("REGISTRATION_REQUIRE_EMAIL", False)
        return render_template("register.html", require_email=require_email)
    username = (request.form.get("username") or "").strip()
    # Normalize email to lowercase and strip whitespace
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""
    require_email = current_app.config.get("REGISTRATION_REQUIRE_EMAIL", False)
    if require_email and not email:
        flash("Email is required.", "error")
        return render_template("register.html", username=username, email="", require_email=require_email)
    if password != password_confirm:
        flash("Passwords do not match.", "error")
        return render_template("register.html", username=username, email=email, require_email=require_email)
    user, err = create_user(username, password, email or None)
    if err:
        flash(err, "error")
        return render_template("register.html", username=username, email=email, require_email=require_email)
    log_activity(
        actor=user,
        category="auth",
        action="register",
        status="success",
        message="Web registration successful",
        route=request.path,
        method=request.method,
        tags=["web"],
    )
    if user.email:
        ttl = current_app.config.get("EMAIL_VERIFICATION_TTL_HOURS", 24)
        raw_token = create_email_verification_token(user, ttl_hours=ttl)
        send_verification_email(user, raw_token)
        log_activity(
            actor=user,
            category="auth",
            action="verification_email_sent",
            status="success",
            message="Verification email sent",
            route=request.path,
            method=request.method,
            tags=["web", "email"],
        )
        flash("Account created. Check your email to verify your address, then log in.", "success")
        return redirect(url_for("web.register_pending"))
    flash("Account created. You can log in now.", "success")
    return redirect(url_for("web.login"))


@web_bp.route("/register/pending", methods=["GET"])
def register_pending():
    """Shown after registration; instructs user to check email and use activation link."""
    if session.get("user_id"):
        return redirect(url_for("web.dashboard"))
    return render_template("register_pending.html")


@web_bp.route("/activate/<token>", methods=["GET"])
def activate(token):
    """Activate account via email link. Redirects to login with success or error."""
    from app.services.user_service import verify_email_with_token

    ok, err = verify_email_with_token(token)
    if ok:
        log_activity(
            category="auth",
            action="email_verification_success",
            status="success",
            message="Email verified via activation link",
            route=request.path,
            method=request.method,
            tags=["web", "email"],
        )
        flash("Your email is verified. You can now log in.", "success")
        return redirect(url_for("web.login"))
    log_activity(
        category="auth",
        action="email_verification_failed",
        status="error",
        message=err or "Invalid or expired activation link",
        route=request.path,
        method=request.method,
        tags=["web", "email"],
    )
    flash(err or "Activation link is invalid or has expired.", "error")
    return redirect(url_for("web.login"))


@web_bp.route("/resend-verification", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def resend_verification():
    """Request a new verification email. Generic message to avoid user enumeration."""
    if session.get("user_id"):
        return redirect(url_for("web.dashboard"))
    if request.method == "GET":
        return render_template("resend_verification.html")
    from app.services.user_service import (
        get_user_by_email,
        create_email_verification_token,
    )

    # Normalize email to lowercase and strip whitespace
    email = (request.form.get("email") or "").strip().lower()
    if not email:
        flash("Please enter your email address.", "error")
        return render_template("resend_verification.html")
    user = get_user_by_email(email)
    if user and user.email and user.email_verified_at is None:
        ttl = current_app.config.get("EMAIL_VERIFICATION_TTL_HOURS", 24)
        raw_token = create_email_verification_token(user, ttl_hours=ttl)
        send_verification_email(user, raw_token)
        log_activity(
            actor=user,
            category="auth",
            action="verification_resend",
            status="success",
            message="Verification email resent",
            route=request.path,
            method=request.method,
            tags=["web", "email"],
        )
    flash("If an account with that email is awaiting verification, a new link has been sent.", "info")
    return redirect(url_for("web.login"))


@web_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def forgot_password():
    """Request a password reset link by email."""
    if request.method == "GET":
        return render_template("forgot_password.html")
    # Normalize email to lowercase and strip whitespace
    email = (request.form.get("email") or "").strip().lower()
    if not email:
        flash("Please enter your email address.", "error")
        return render_template("forgot_password.html")
    from app.services.user_service import (
        create_password_reset_token,
        get_user_by_email,
    )
    from app.services.mail_service import send_password_reset_email

    user = get_user_by_email(email)
    if user and user.email:
        token = create_password_reset_token(user)
        send_password_reset_email(user, token)
        log_activity(
            actor=user,
            category="auth",
            action="password_reset_requested",
            status="success",
            message="Password reset link sent",
            route=request.path,
            method=request.method,
            tags=["web", "email"],
        )
    flash(
        "If an account with that email exists, a reset link has been sent.",
        "info",
    )
    return redirect(url_for("web.login"))


@web_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def reset_password(token):
    """Reset password using a valid token from the reset email."""
    from app.services.user_service import (
        get_valid_reset_token,
        reset_password_with_token,
    )

    record = get_valid_reset_token(token)
    if not record:
        flash("This reset link is invalid or has expired.", "error")
        return redirect(url_for("web.forgot_password"))
    if request.method == "GET":
        return render_template("reset_password.html", token=token)
    new_password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""
    if new_password != password_confirm:
        flash("Passwords do not match.", "error")
        return render_template("reset_password.html", token=token)
    ok, err = reset_password_with_token(token, new_password)
    if not ok:
        flash(err, "error")
        return render_template("reset_password.html", token=token)
    log_activity(
        category="auth",
        action="password_reset_completed",
        status="success",
        message="Password reset completed",
        route=request.path,
        method=request.method,
        tags=["web"],
    )
    flash("Password updated. Please log in with your new password.", "success")
    return redirect(url_for("web.login"))


@web_bp.route("/news")
def news():
    """News: redirect to frontend when FRONTEND_URL is set; else serve legacy placeholder."""
    frontend_url = current_app.config.get("FRONTEND_URL")
    if frontend_url:
        return redirect(frontend_url.rstrip("/") + "/news", code=302)
    return render_template("news.html")


def _get_wiki_html(lang=None):
    """Load wiki Markdown: from DB (wiki_pages key=index) if present, else from content/wiki.md. Returns sanitized HTML."""
    from app.services.wiki_service import get_wiki_markdown_for_display
    from app.utils.html_sanitizer import sanitize_wiki_html
    text = get_wiki_markdown_for_display(lang=lang)
    if text is not None and text != "":
        try:
            raw = markdown.markdown(text, extensions=["extra"])
            return sanitize_wiki_html(raw) if raw else None
        except Exception:
            pass
    app_root = Path(current_app.root_path)
    wiki_path = app_root.parent / "content" / "wiki.md"
    if not wiki_path.is_file():
        return None
    try:
        text = wiki_path.read_text(encoding="utf-8")
        raw = markdown.markdown(text, extensions=["extra"])
        return sanitize_wiki_html(raw) if raw else None
    except Exception:
        return None


@web_bp.route("/wiki")
@web_bp.route("/wiki/<path:slug>")
def wiki(slug=None):
    """Wiki view: slug=None shows default page (index); slug set loads page by slug from DB."""
    lang = request.args.get("lang") or session.get("lang")
    if slug:
        from app.services.wiki_service import get_wiki_page_by_slug
        from app.utils.html_sanitizer import sanitize_wiki_html
        page, trans = get_wiki_page_by_slug(slug, lang=lang)
        if not page or not trans:
            return render_template("wiki.html", wiki_html=None, wiki_title=None), 404
        text = trans.content_markdown or ""
        if not text.strip():
            wiki_html = None
        else:
            try:
                raw = markdown.markdown(text, extensions=["extra"])
                wiki_html = sanitize_wiki_html(raw) if raw else None
            except Exception:
                wiki_html = None
        title = (trans.title or slug).strip() or "Wiki"
        return render_template("wiki.html", wiki_html=wiki_html, wiki_title=title)
    wiki_html = _get_wiki_html(lang=lang)
    return render_template("wiki.html", wiki_html=wiki_html, wiki_title=None)


@web_bp.route("/community")
def community():
    """Community: redirect to forum in administration-tool when FRONTEND_URL is set; else serve placeholder."""
    frontend_url = current_app.config.get("FRONTEND_URL")
    if frontend_url:
        return redirect(frontend_url.rstrip("/") + "/forum", code=302)
    return render_template("community.html")


@web_bp.route("/game-menu")
@require_web_login
def game_menu():
    """Game launcher page backed by the existing Flask login/session."""
    uid = session.get("user_id")
    user = db.session.get(User, int(uid)) if uid else None
    play_public_url = current_app.config.get("PLAY_SERVICE_PUBLIC_URL")
    return render_template(
        "game_menu.html",
        current_user=user,
        play_service_configured=has_complete_play_service_config(),
        play_service_public_url=play_public_url,
    )


@web_bp.route("/dashboard")
@require_web_login
def dashboard():
    """Protected page; requires logged-in session. Admin section only visible to admins."""
    uid = session.get("user_id")
    user = db.session.get(User, int(uid)) if uid else None
    return render_template(
        "dashboard.html",
        is_admin=user.is_admin if user else False,
        current_user=user,
    )


@web_bp.route("/dashboard/api/metrics")
@require_web_admin
@limiter.limit("60 per minute")
def dashboard_api_metrics():
    """Real user metrics for admin dashboard. Query: range=24h|7d|30d|12m."""
    range_key = (request.args.get("range") or "24h").strip().lower()
    if range_key not in ("24h", "7d", "30d", "12m"):
        range_key = "24h"
    from app.services.metrics_service import get_metrics
    data = get_metrics(range_key)
    return jsonify(data)


@web_bp.route("/dashboard/api/site-settings", methods=["GET"])
@require_web_admin
@limiter.limit("30 per minute")
def dashboard_api_site_settings_get():
    """Get site settings (admin only). Returns slogan_rotation_interval_seconds, slogan_rotation_enabled."""
    from app.models import SiteSetting
    rows = SiteSetting.query.all()
    data = {}
    for r in rows:
        data[r.key] = r.value
    interval = data.get("slogan_rotation_interval_seconds")
    enabled = data.get("slogan_rotation_enabled")
    return jsonify({
        "slogan_rotation_interval_seconds": int(interval) if interval is not None and str(interval).isdigit() else 60,
        "slogan_rotation_enabled": str(enabled).lower() in ("1", "true", "yes", "on") if enabled is not None else True,
    })


@web_bp.route("/dashboard/api/site-settings", methods=["PUT"])
@require_web_admin
@limiter.limit("30 per minute")
def dashboard_api_site_settings_put():
    """Update site settings (admin only). Body: slogan_rotation_interval_seconds, slogan_rotation_enabled."""
    from app.models import SiteSetting
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    interval = data.get("slogan_rotation_interval_seconds")
    enabled = data.get("slogan_rotation_enabled")
    if interval is not None:
        try:
            v = int(interval)
            v = max(5, min(86400, v))
        except (TypeError, ValueError):
            v = 60
        rec = db.session.get(SiteSetting, "slogan_rotation_interval_seconds")
        if rec:
            rec.value = str(v)
        else:
            db.session.add(SiteSetting(key="slogan_rotation_interval_seconds", value=str(v)))
    if enabled is not None:
        rec = db.session.get(SiteSetting, "slogan_rotation_enabled")
        val = "true" if enabled else "false"
        if rec:
            rec.value = val
        else:
            db.session.add(SiteSetting(key="slogan_rotation_enabled", value=val))
    db.session.commit()
    return dashboard_api_site_settings_get()


@web_bp.route("/dashboard/api/logs")
@require_web_admin
@limiter.limit("60 per minute")
def dashboard_api_logs():
    """Activity logs for dashboard (admin only, session auth). Same shape as GET /api/v1/admin/logs."""
    from app.services.activity_log_service import list_activity_logs

    def _parse_int(val, default, min_v=None, max_v=None):
        if val is None:
            return default
        try:
            n = int(val)
            if min_v is not None and n < min_v:
                return default
            if max_v is not None and n > max_v:
                return max_v
            return n
        except (TypeError, ValueError):
            return default

    page = _parse_int(request.args.get("page"), 1, min_v=1)
    limit = _parse_int(request.args.get("limit"), 50, min_v=1, max_v=100)
    q = request.args.get("q", "").strip() or None
    category = request.args.get("category", "").strip() or None
    status = request.args.get("status", "").strip() or None
    date_from = request.args.get("date_from", "").strip() or None
    date_to = request.args.get("date_to", "").strip() or None

    items, total = list_activity_logs(
        page=page, limit=limit, q=q, category=category, status=status,
        date_from=date_from, date_to=date_to,
    )
    return jsonify({
        "items": [e.to_dict() for e in items],
        "total": total,
        "page": page,
        "limit": limit,
    })


@web_bp.route("/dashboard/api/logs/export")
@require_web_admin
@limiter.limit("10 per minute")
def dashboard_api_logs_export():
    """CSV export of activity logs (admin only, session auth)."""
    from app.services.activity_log_service import list_activity_logs

    def _parse_int(val, default, min_v=None, max_v=None):
        if val is None:
            return default
        try:
            n = int(val)
            if min_v is not None and n < min_v:
                return default
            if max_v is not None and n > max_v:
                return max_v
            return n
        except (TypeError, ValueError):
            return default

    limit = _parse_int(request.args.get("limit"), 5000, min_v=1, max_v=5000)
    q = request.args.get("q", "").strip() or None
    category = request.args.get("category", "").strip() or None
    status = request.args.get("status", "").strip() or None
    date_from = request.args.get("date_from", "").strip() or None
    date_to = request.args.get("date_to", "").strip() or None

    items, _ = list_activity_logs(
        page=1, limit=limit, q=q, category=category, status=status,
        date_from=date_from, date_to=date_to,
    )

    from app.utils.csv_safe import csv_safe_cell
    import json
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


# ── W3.2: Session UI ──────────────────────────────────────────────────────────

_AVAILABLE_MODULES = ["god_of_carnage"]

@web_bp.route("/play")
@require_web_login
def session_start():
    uid = session.get("user_id")
    user = db.session.get(User, int(uid)) if uid else None
    return render_template(
        "session_start.html",
        current_user=user,
        available_modules=_AVAILABLE_MODULES,
    )


@web_bp.route("/play/start", methods=["POST"])
@require_web_login
def session_create():
    from app.services.session_service import create_session
    from app.runtime.session_start import SessionStartError

    module_id = request.form.get("module_id", "").strip()
    if not module_id:
        flash("Please select a module to start a session.", "error")
        return redirect(url_for("web.session_start"))

    try:
        new_session = create_session(module_id)
    except SessionStartError as e:
        flash(f"Could not start session: {e.reason}", "error")
        return redirect(url_for("web.session_start"))

    session["active_session"] = {
        "session_id": new_session.session_id,
        "module_id": new_session.module_id,
        "module_version": new_session.module_version,
        "current_scene_id": new_session.current_scene_id,
        "status": new_session.status.value,
        "turn_counter": new_session.turn_counter,
    }
    return redirect(f"/play/{new_session.session_id}")


@web_bp.route("/play/<session_id>")
@require_web_login
def session_view(session_id):
    uid = session.get("user_id")
    user = db.session.get(User, int(uid)) if uid else None
    active = session.get("active_session", {})
    if active.get("session_id") != session_id:
        flash("Session not found or expired.", "error")
        return redirect(url_for("web.session_start"))

    # Load runtime session and present characters and conflict
    runtime_session = _resolve_runtime_session(session_id)
    characters = []
    conflict = None

    # Create minimal SessionState if runtime_session not available
    if runtime_session:
        session_state = runtime_session.current_runtime_state
        characters = present_all_characters(session_state)
        conflict = present_conflict_panel(session_state)
    else:
        # Graceful fallback with empty session state
        from app.runtime.w2_models import SessionState
        session_state = SessionState(
            session_id=session_id,
            module_id=active.get("module_id", "unknown"),
            module_version="1.0",
            current_scene_id="unknown",
        )

    history_panel = present_history_panel(session_state)

    return render_template("session_shell.html", current_user=user, session_data=active, characters=characters, conflict=conflict, history_panel=history_panel)


# ── W3.3: Session Execution & Helpers ─────────────────────────────────────────

def _resolve_runtime_session(session_id: str) -> RuntimeSession | None:
    """Validates Flask session matches requested session_id and loads RuntimeSession.

    Args:
        session_id: Session ID from URL path

    Returns:
        RuntimeSession if Flask session matches and session exists, None otherwise
    """
    flask_session_id = session.get("active_session", {}).get("session_id")
    if flask_session_id != session_id:
        return None
    return get_runtime_session(session_id)


def _present_turn_result(runtime_session: RuntimeSession, turn_result) -> dict:
    """Map TurnExecutionResult and RuntimeSession to template-facing fields.

    Extracts scene info from module, outcome from result, and formats for template.

    Args:
        runtime_session: Updated RuntimeSession after turn execution
        turn_result: TurnExecutionResult from dispatcher

    Returns:
        Dict with keys: narrative_text, guard_outcome, accepted_delta_paths,
                       rejected_delta_paths, next_scene_id, execution_status
    """
    # Extract scene info from module
    module = runtime_session.module
    current_scene_id = runtime_session.current_runtime_state.current_scene_id
    next_scene_id = turn_result.updated_scene_id if turn_result.updated_scene_id else current_scene_id

    # Get scene from module (defensive coding: check if scenes exist)
    scene_data = {}
    if hasattr(module, 'scenes') and current_scene_id in module.scenes:
        scene = module.scenes[current_scene_id]
        scene_data = {
            "title": getattr(scene, 'title', current_scene_id),
            "description": getattr(scene, 'description', ''),
        }
    else:
        scene_data = {
            "title": current_scene_id,
            "description": "",
        }

    # Extract state summary from canonical state
    canonical_state = runtime_session.current_runtime_state.canonical_state
    state_summary = {
        "situation": canonical_state.get("situation", ""),
        "conversation_status": canonical_state.get("conversation_status", ""),
    }

    # Extract deltas
    accepted_delta_paths = [delta.target for delta in turn_result.accepted_deltas] if turn_result.accepted_deltas else []
    rejected_delta_paths = [delta.target for delta in turn_result.rejected_deltas] if turn_result.rejected_deltas else []

    return {
        "scene": scene_data,
        "state_summary": state_summary,
        "turn_result": {
            "narrative_text": turn_result.decision.narrative_text if turn_result.decision and hasattr(turn_result.decision, 'narrative_text') else "",
            "guard_outcome": turn_result.guard_outcome.value if hasattr(turn_result.guard_outcome, 'value') else str(turn_result.guard_outcome),
            "accepted_delta_paths": accepted_delta_paths,
            "rejected_delta_paths": rejected_delta_paths,
        },
        "next_scene_id": next_scene_id,
        "execution_status": turn_result.execution_status,
    }


@web_bp.route("/play/<session_id>/execute", methods=["POST"])
@require_web_login
def session_execute(session_id: str):
    """Execute a turn in the session.

    Submits operator_input to the canonical dispatch_turn() router.
    Dispatcher owns execution mode routing and decision construction.
    Updates runtime session with result, renders updated scene + feedback.
    """
    uid = session.get("user_id")
    user = db.session.get(User, int(uid)) if uid else None

    # Validate Flask session matches session_id and load RuntimeSession
    runtime_session = _resolve_runtime_session(session_id)
    if not runtime_session:
        flash("Session not found or expired.", "error")
        return redirect(url_for("web.session_start"))

    # Extract operator input from form
    operator_input = request.form.get("operator_input", "").strip()
    if not operator_input:
        flash("Please enter an action.", "error")
        return redirect(url_for("web.session_view", session_id=session_id))

    try:
        # Call CANONICAL DISPATCHER (not execute_turn directly)
        # Dispatcher owns execution mode routing and all decision construction
        # Note: asyncio.run() wraps async dispatch_turn for sync Flask route
        turn_result = asyncio.run(dispatch_turn(
            session=runtime_session.current_runtime_state,
            current_turn=runtime_session.current_runtime_state.turn_counter + 1,
            module=runtime_session.module,
            operator_input=operator_input,
        ))

        # Update RuntimeSession in store
        # Replace canonical state with result state
        updated_state = runtime_session.current_runtime_state
        updated_state.canonical_state = turn_result.updated_canonical_state
        updated_state.current_scene_id = turn_result.updated_scene_id or updated_state.current_scene_id
        updated_state.turn_counter += 1

        update_runtime_session(session_id, updated_state)

        # Reload runtime session with updated state
        runtime_session = get_runtime_session(session_id)

        # Map result to template fields
        presented_result = _present_turn_result(runtime_session, turn_result)

        # Present characters and conflict from updated state
        characters = present_all_characters(runtime_session.current_runtime_state)
        conflict = present_conflict_panel(runtime_session.current_runtime_state)
        history_panel = present_history_panel(runtime_session.current_runtime_state)

        # Render updated scene + result feedback
        return render_template(
            "session_shell.html",
            current_user=user,
            session_id=session_id,
            scene=presented_result["scene"],
            state_summary=presented_result["state_summary"],
            turn_result=presented_result["turn_result"],
            characters=characters,
            conflict=conflict,
            history_panel=history_panel,
            session_data={
                "module_id": runtime_session.current_runtime_state.module_id,
                "current_scene_id": runtime_session.current_runtime_state.current_scene_id,
                "status": runtime_session.current_runtime_state.status.value,
                "turn_counter": runtime_session.current_runtime_state.turn_counter,
            },
        )

    except Exception as e:
        # Error: preserve session state, flash error, re-render current scene
        flash(f"Turn execution failed: {str(e)}", "error")

        # Re-render current scene without state change
        module = runtime_session.module
        current_scene_id = runtime_session.current_runtime_state.current_scene_id
        canonical_state = runtime_session.current_runtime_state.canonical_state

        scene_data = {}
        if hasattr(module, 'scenes') and current_scene_id in module.scenes:
            scene = module.scenes[current_scene_id]
            scene_data = {
                "title": getattr(scene, 'title', current_scene_id),
                "description": getattr(scene, 'description', ''),
            }
        else:
            scene_data = {
                "title": current_scene_id,
                "description": "",
            }

        state_summary = {
            "situation": canonical_state.get("situation", ""),
            "conversation_status": canonical_state.get("conversation_status", ""),
        }

        # Present characters and conflict from current state (unchanged by error)
        characters = present_all_characters(runtime_session.current_runtime_state)
        conflict = present_conflict_panel(runtime_session.current_runtime_state)
        history_panel = present_history_panel(runtime_session.current_runtime_state)

        return render_template(
            "session_shell.html",
            current_user=user,
            session_id=session_id,
            scene=scene_data,
            state_summary=state_summary,
            characters=characters,
            conflict=conflict,
            history_panel=history_panel,
            session_data={
                "module_id": runtime_session.current_runtime_state.module_id,
                "current_scene_id": current_scene_id,
                "status": runtime_session.current_runtime_state.status.value,
                "turn_counter": runtime_session.current_runtime_state.turn_counter,
            },
            error="Turn execution failed.",
        ), 400
