from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "var"
RUN_STORE_DIR = DATA_DIR / "runs"
APP_TITLE = os.getenv("APP_TITLE", "World of Shadows Play Service Prototype")
APP_VERSION = "0.1.0"
