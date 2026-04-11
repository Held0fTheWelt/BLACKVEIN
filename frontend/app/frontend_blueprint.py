"""Flask blueprint for player-facing routes (handlers live in ``routes*.py`` modules)."""

from __future__ import annotations

from flask import Blueprint

frontend_bp = Blueprint("frontend", __name__)
