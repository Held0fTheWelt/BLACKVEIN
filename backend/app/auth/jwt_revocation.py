"""JWT blocklist / refresh revocation — kept out of extensions to avoid model↔extensions coupling."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
            from app.models.token_blacklist import TokenBlacklist
            from app.models.refresh_token import RefreshToken

            if TokenBlacklist.is_blacklisted(jti):
                return True

            token_type = jwt_payload.get("type")
            if token_type == "refresh":
                user_id = jwt_payload.get("sub")
                if user_id:
                    token_obj = (
                        db.session.query(RefreshToken)
                        .filter(RefreshToken.jti == jti)
                        .first()
                    )
                    if token_obj and token_obj.revoked_at is not None:
                        return True

        return False
