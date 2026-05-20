"""JWT blocklist / refresh revocation — kept out of extensions to avoid model↔extensions coupling."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from flask_jwt_extended import JWTManager
    from flask_sqlalchemy import SQLAlchemy


def register_jwt_revocation_handlers(jwt: JWTManager, db: SQLAlchemy) -> None:
    """Register token_in_blocklist_loader on the given JWT manager."""

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """Check if token is blacklisted or refresh token revoked."""
        jti = jwt_payload.get("jti")
        if jti:
            blacklisted = db.session.execute(
                text("SELECT 1 FROM token_blacklist WHERE jti = :jti LIMIT 1"),
                {"jti": jti},
            ).first()
            if blacklisted is not None:
                return True

            token_type = jwt_payload.get("type")
            if token_type == "refresh":
                user_id = jwt_payload.get("sub")
                if user_id:
                    revoked = db.session.execute(
                        text(
                            "SELECT 1 FROM refresh_tokens "
                            "WHERE jti = :jti AND revoked_at IS NOT NULL LIMIT 1"
                        ),
                        {"jti": jti},
                    )
                    if revoked.first() is not None:
                        return True

        return False
