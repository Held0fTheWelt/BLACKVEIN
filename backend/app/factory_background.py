"""Background maintenance hooks for the Flask app (DS-042)."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone, timedelta

from flask import Flask


def schedule_token_blacklist_cleanup(app: Flask) -> None:
    """Schedule a daily cleanup task for expired JWT tokens (daemon thread)."""
    logger = logging.getLogger(__name__)

    def cleanup_worker() -> None:
        next_cleanup = None

        while True:
            try:
                now = datetime.now(timezone.utc)

                if next_cleanup is None:
                    next_cleanup = now.replace(hour=2, minute=0, second=0, microsecond=0)
                    if next_cleanup <= now:
                        next_cleanup += timedelta(days=1)

                wait_seconds = (next_cleanup - datetime.now(timezone.utc)).total_seconds()
                if wait_seconds > 0:
                    time.sleep(min(wait_seconds, 60))
                    continue

                with app.app_context():
                    from app.models.token_blacklist import TokenBlacklist

                    deleted_count = TokenBlacklist.cleanup_expired()
                    if deleted_count > 0:
                        logger.info(
                            "Token blacklist maintenance: deleted %s expired tokens at %s",
                            deleted_count,
                            datetime.now(timezone.utc).isoformat(),
                        )

                next_cleanup = next_cleanup + timedelta(days=1)

            except Exception as e:
                logger.error("Error during token blacklist cleanup: %s", e, exc_info=True)
                time.sleep(300)

    if not app.config.get("TESTING"):
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.name = "TokenBlacklistCleanup"
        cleanup_thread.start()
        logger.debug("Started token blacklist cleanup scheduler (daily at 2 AM UTC)")
