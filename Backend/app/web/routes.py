from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.extensions import limiter
from app.services import create_user, verify_user
from app.web.auth import is_safe_redirect, require_web_login

web_bp = Blueprint("web", __name__)


@web_bp.route("/health")
def health():
    """Web health check; returns JSON status."""
    return {"status": "ok"}, 200


@web_bp.route("/")
def home():
    """Home page."""
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
    flash("Invalid username or password.", "error")
    return render_template("login.html")


@web_bp.route("/logout", methods=["POST"])
def logout():
    """Clear session and redirect to home. POST only to avoid CSRF/logout-link abuse."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("web.home"))


@web_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def register():
    """Registration form. Redirects to login on success."""
    if session.get("user_id"):
        return redirect(url_for("web.dashboard"))
    if request.method == "GET":
        return render_template("register.html")
    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""
    if not email:
        flash("Email is required.", "error")
        return render_template("register.html", username=username, email="")
    if password != password_confirm:
        flash("Passwords do not match.", "error")
        return render_template("register.html", username=username, email=email)
    user, err = create_user(username, password, email)
    if err:
        flash(err, "error")
        return render_template("register.html", username=username, email=email)
    flash("Account created. Please log in.", "success")
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
    flash("Password updated. Please log in with your new password.", "success")
    return redirect(url_for("web.login"))


@web_bp.route("/news")
def news():
    """News page (placeholder)."""
    return render_template("news.html")


@web_bp.route("/wiki")
def wiki():
    """Wiki page (placeholder)."""
    return render_template("wiki.html")


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
    """Protected page; requires logged-in session."""
    return render_template("dashboard.html")
