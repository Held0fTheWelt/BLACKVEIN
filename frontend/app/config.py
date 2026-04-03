"""Frontend service configuration."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
    _here = Path(__file__).resolve().parent
    _frontend_root = _here.parent
    _repo_root = _frontend_root.parent
    if _repo_root != _frontend_root:
        load_dotenv(_repo_root / ".env")
except ImportError:  # pragma: no cover
    pass


def env_bool(name: str, default: bool = False) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


class Config:
    SECRET_KEY = os.environ.get("FRONTEND_SECRET_KEY") or os.environ.get("SECRET_KEY")
    BACKEND_API_URL = (os.environ.get("BACKEND_API_URL") or "http://127.0.0.1:5000").rstrip("/")
    PLAY_SERVICE_PUBLIC_URL = (os.environ.get("PLAY_SERVICE_PUBLIC_URL") or "http://127.0.0.1:8001").rstrip("/")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_bool("PREFER_HTTPS", False)
    ENFORCE_HTTPS = env_bool("PREFER_HTTPS", False)
    TESTING = False


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "frontend-test-secret"
    BACKEND_API_URL = "http://backend.example.test"
    PLAY_SERVICE_PUBLIC_URL = "http://play.example.test"
