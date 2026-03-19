from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
    _config_dir = Path(__file__).resolve().parent
    _project_root = _config_dir.parent
    load_dotenv(_project_root / ".env")
except ImportError:  # pragma: no cover - optional in constrained environments
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "var"
RUN_STORE_DIR = DATA_DIR / "runs"
APP_TITLE = os.getenv("APP_TITLE", "World of Shadows Play Service Prototype")
APP_VERSION = "0.3.0"
PLAY_SERVICE_SECRET = (os.getenv("PLAY_SERVICE_SECRET") or os.getenv("PLAY_SERVICE_SHARED_SECRET") or "change-me-for-production")
PLAY_SERVICE_INTERNAL_API_KEY = os.getenv("PLAY_SERVICE_INTERNAL_API_KEY", "")
RUN_STORE_BACKEND = os.getenv("RUN_STORE_BACKEND", "json")
RUN_STORE_URL = os.getenv("RUN_STORE_URL", "")
