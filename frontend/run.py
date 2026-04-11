"""Frontend service entry point."""
from __future__ import annotations

import os

from app import create_app
from app.config import Config

app = create_app(Config)


if __name__ == "__main__":
    port = int(os.environ.get("FRONTEND_PORT", os.environ.get("PORT", "5002")))
    debug = (os.environ.get("FLASK_DEBUG") or "").strip().lower() in ("1", "true", "yes", "on")
    app.run(host="0.0.0.0", port=port, debug=debug)
