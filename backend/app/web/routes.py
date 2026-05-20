"""Backend web infrastructure routes."""
from __future__ import annotations

from flask import Blueprint, current_app, redirect, send_from_directory, url_for

web_bp = Blueprint("web", __name__)


@web_bp.route("/health")
def health():
    return {"status": "ok"}, 200


@web_bp.route("/favicon.ico")
def favicon():
    return send_from_directory(current_app.static_folder, "favicon.ico", mimetype="image/vnd.microsoft.icon")


@web_bp.route("/")
def home():
    """Direct browser entry lands on the technical backend info surface, not the player frontend."""
    return redirect(url_for("info.backend_home"))
