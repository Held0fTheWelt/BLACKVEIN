from pathlib import Path

import markdown
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, Response, session, url_for

from app.extensions import db, limiter
from app.models import User
from app.services import create_user, log_activity, verify_user
from app.services.user_service import create_email_verification_token
from app.services.mail_service import send_verification_email
from app.web.auth import is_safe_redirect, require_web_login, require_web_admin

web_bp = Blueprint("web", __name__)


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
        if user.email and user.email_verified_at is None:
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


def _get_wiki_html():
    """Load wiki Markdown from content/wiki.md and return rendered HTML, or None if missing."""
    app_root = Path(current_app.root_path)
    wiki_path = app_root.parent / "content" / "wiki.md"
    if not wiki_path.is_file():
        return None
    try:
        text = wiki_path.read_text(encoding="utf-8")
        return markdown.markdown(text, extensions=["extra"])
    except Exception:
        return None


@web_bp.route("/wiki")
def wiki():
    """Wiki view: render Markdown from Backend/content/wiki.md."""
    wiki_html = _get_wiki_html()
    return render_template("wiki.html", wiki_html=wiki_html)


@web_bp.route("/community")
def community():
    """Community page (placeholder)."""
    return render_template("community.html")


@web_bp.route("/game-menu")
@require_web_login
def game_menu():
    """Game menu (placeholder); requires logged-in session."""
    return render_template("game_menu.html")


@web_bp.route("/dashboard")
@require_web_login
def dashboard():
    """Protected page; requires logged-in session. Admin section only visible to admins."""
    uid = session.get("user_id")
    user = db.session.get(User, int(uid)) if uid else None
    return render_template("dashboard.html", is_admin=user.is_admin if user else False)


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

    def csv_escape(s):
        if s is None:
            return ""
        s = str(s)
        if "\n" in s or "," in s or '"' in s:
            return '"' + s.replace('"', '""') + '"'
        return s

    import json
    lines = [
        "id,created_at,actor_user_id,actor_username_snapshot,actor_role_snapshot,category,action,status,message,route,method,tags,meta,target_type,target_id"
    ]
    for e in items:
        tags_str = ";".join(e.tags or [])
        meta_str = json.dumps(e.meta) if e.meta else ""
        row = [
            e.id,
            e.created_at.isoformat() if e.created_at else "",
            e.actor_user_id or "",
            e.actor_username_snapshot or "",
            e.actor_role_snapshot or "",
            e.category,
            e.action,
            e.status,
            (e.message or "").replace("\n", " "),
            e.route or "",
            e.method or "",
            tags_str,
            meta_str,
            e.target_type or "",
            e.target_id or "",
        ]
        lines.append(",".join(csv_escape(x) for x in row))

    return Response(
        "\n".join(lines),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=wos-activity-logs.csv"},
    )
