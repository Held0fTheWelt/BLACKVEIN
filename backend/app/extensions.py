"""Flask extensions; init_app(app) called from create_app."""
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_migrate import Migrate
from flask_mail import Mail

db = SQLAlchemy()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=[])
migrate = Migrate()
mail = Mail()


def init_app(app):
    """Bind extensions to app. CORS uses configurable origins from config."""
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)
    if not app.config.get("TESTING"):
        migrate.init_app(app, db)
    origins = app.config.get("CORS_ORIGINS")
    if origins:
        CORS(
            app,
            origins=origins,
            allow_headers=["Content-Type", "Authorization"],
            expose_headers=["Content-Type"],
            methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            supports_credentials=False,
        )

    # Register JWT callback for token revocation checking
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """Check if token is blacklisted (logout/revocation) or refresh token is revoked."""
        jti = jwt_payload.get("jti")
        if jti:
            from app.models.token_blacklist import TokenBlacklist
            from app.models.refresh_token import RefreshToken

            # Check access token blacklist
            if TokenBlacklist.is_blacklisted(jti):
                return True

            # For refresh tokens, check if explicitly revoked
            token_type = jwt_payload.get("type")
            if token_type == "refresh":
                user_id = jwt_payload.get("sub")
                if user_id:
                    # Check if token was explicitly revoked
                    # Only reject if token exists in DB and is marked as revoked
                    token_obj = (
                        db.session.query(RefreshToken)
                        .filter(RefreshToken.jti == jti)
                        .first()
                    )
                    if token_obj and token_obj.revoked_at is not None:
                        # Token is revoked
                        return True

        return False

    # Register JWT callback for real-time ban enforcement
    @jwt.token_verification_loader
    def verify_jwt_token(jwt_header, jwt_data):
        """
        Verify JWT token before allowing access to protected endpoints.
        Checks if the user is banned in real-time, rejecting valid non-expired tokens
        when the user is banned.
        This ensures bans are enforced immediately.

        Returns True if token is valid, False if it should be rejected with 401.
        """
        try:
            # Extract user_id from jwt_data (the 'sub' claim contains user ID as string)
            user_id = jwt_data.get("sub")
            if not user_id:
                return True  # No identity to check; allow other handlers to validate

            # Convert string ID to int
            user_id = int(user_id)

            # Check if user exists and is banned
            from app.models.user import User
            user = User.query.get(user_id)

            # Reject token if user is banned
            if user and getattr(user, "is_banned", False):
                return False

            return True

        except (ValueError, TypeError):
            return True  # Let other handlers process non-integer IDs
        except Exception:
            # Silently allow on DB errors; let other mechanisms handle real issues
            return True

    # Handle token verification failure (when banned user tries to use token)
    @jwt.token_verification_failed_loader
    def token_verification_failed(_jwt_header, _jwt_data):
        """
        Callback when token verification fails (e.g., user is banned).
        Returns 401 Unauthorized response.
        """
        return {"error": "Token verification failed"}, 401
