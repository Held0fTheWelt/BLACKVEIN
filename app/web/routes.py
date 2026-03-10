from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.services import verify_user
from app.web.auth import require_web_login

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
        session["user_id"] = user.id
        session["username"] = user.username
        flash(f"Welcome, {user.username}.", "success")
        next_url = request.args.get("next") or url_for("web.dashboard")
        return redirect(next_url)
    flash("Invalid username or password.", "error")
    return render_template("login.html")


@web_bp.route("/logout", methods=["POST"])
def logout():
    """Clear session and redirect to home. POST only to avoid CSRF/logout-link abuse."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("web.home"))


@web_bp.route("/dashboard")
@require_web_login
def dashboard():
    """Protected page; requires logged-in session."""
    return render_template("dashboard.html")
