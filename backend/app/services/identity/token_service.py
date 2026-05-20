"""JWT token generation and management service."""
import time
from datetime import timedelta
from uuid import uuid4

from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token, decode_token

from app.extensions import db
from app.models import RefreshToken


def generate_tokens(user_id: int) -> dict:
    """Generate both access and refresh tokens for a user.

    Args:
        user_id: The user ID to generate tokens for

    Returns:
        dict: Contains 'access_token', 'refresh_token', 'expires_at', 'expires_in',
              and 'refresh_expires_at' with expiration timestamp information

    Raises:
        ValueError: If user_id is invalid
    """
    if not user_id or user_id <= 0:
        raise ValueError("Invalid user_id")

    # Generate unique JWT IDs for both tokens
    access_jti = str(uuid4())
    refresh_jti = str(uuid4())

    # Get configured token lifetimes
    access_expires = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", 3600)  # 1 hour default
    refresh_expires = current_app.config.get("JWT_REFRESH_TOKEN_EXPIRES", 604800)  # 7 days default

    # Create access token (short-lived, 1 hour)
    access_token = create_access_token(
        identity=str(user_id),
        additional_claims={"type": "access", "jti": access_jti},
        expires_delta=timedelta(seconds=access_expires),
    )

    # Create refresh token (long-lived, 7 days)
    refresh_token = create_refresh_token(
        identity=str(user_id),
        additional_claims={"type": "refresh", "jti": refresh_jti},
        expires_delta=timedelta(seconds=refresh_expires),
    )

    # Decode tokens to extract 'exp' claim (Unix timestamp)
    access_payload = decode_token(access_token)
    refresh_payload = decode_token(refresh_token)

    access_expires_at = access_payload.get("exp")
    refresh_expires_at = refresh_payload.get("exp")

    # Store refresh token in database with the JTI as the unique identifier
    # The token_hash field stores a portion of the actual token for audit purposes
    # Use the refresh_jti as the hash to ensure uniqueness
    RefreshToken.create(
        user_id=user_id,
        jti=refresh_jti,
        token_hash=refresh_jti,  # Use JTI as unique hash identifier
        expires_in_seconds=refresh_expires,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": access_expires_at,  # Unix timestamp when access token expires
        "expires_in": access_expires,      # Seconds from now until expiration
        "refresh_expires_at": refresh_expires_at,  # Unix timestamp when refresh token expires
    }


def refresh_access_token(user_id: int, refresh_jti: str) -> dict:
    """Generate a new access token using a valid refresh token.

    Args:
        user_id: The user ID from the refresh token
        refresh_jti: The JTI of the refresh token being used

    Returns:
        dict: Contains new 'access_token' and 'refresh_token'

    Raises:
        ValueError: If refresh token is invalid or revoked
    """
    # Verify refresh token is valid
    if not RefreshToken.is_valid(user_id, refresh_jti):
        raise ValueError("Refresh token is invalid or expired")

    # Generate new tokens (access and optionally new refresh via rotation)
    new_tokens = generate_tokens(user_id)

    # Optionally: revoke old refresh token (token rotation)
    # This enforces single-use refresh tokens for enhanced security
    # Uncomment to enable token rotation:
    # RefreshToken.revoke(user_id, refresh_jti)

    return new_tokens


def revoke_user_tokens(user_id: int) -> int:
    """Revoke all refresh tokens for a user (e.g., during logout).

    Args:
        user_id: The user ID

    Returns:
        int: Number of tokens revoked
    """
    return RefreshToken.revoke_all_user_tokens(user_id)
