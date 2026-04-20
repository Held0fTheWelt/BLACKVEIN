"""Tests for app.services.token_service."""

import pytest
from flask_jwt_extended import decode_token

from app.extensions import db
from app.models import RefreshToken
from app.services.token_service import generate_tokens, refresh_access_token, revoke_user_tokens


class TestTokenService:
    def test_generate_tokens_persists_refresh_token_and_claims(self, app, test_user):
        user, _ = test_user

        with app.app_context():
            tokens = generate_tokens(user.id)

            access_payload = decode_token(tokens["access_token"])
            refresh_payload = decode_token(tokens["refresh_token"])
            stored = RefreshToken.query.filter_by(user_id=user.id, jti=refresh_payload["jti"]).one()

            assert access_payload["sub"] == str(user.id)
            assert access_payload["type"] == "access"
            assert refresh_payload["type"] == "refresh"
            assert tokens["expires_in"] == app.config["JWT_ACCESS_TOKEN_EXPIRES"]
            assert tokens["expires_at"] == access_payload["exp"]
            assert tokens["refresh_expires_at"] == refresh_payload["exp"]
            assert stored.refresh_token == refresh_payload["jti"]

    @pytest.mark.parametrize("user_id", [0, -1, None])
    def test_generate_tokens_rejects_invalid_user_ids(self, app, user_id):
        with app.app_context():
            with pytest.raises(ValueError, match="Invalid user_id"):
                generate_tokens(user_id)

    def test_refresh_access_token_rejects_unknown_refresh_token(self, app, test_user):
        user, _ = test_user

        with app.app_context():
            with pytest.raises(ValueError, match="invalid or expired"):
                refresh_access_token(user.id, "missing-jti")

    def test_revoke_user_tokens_revokes_all_active_refresh_tokens(self, app, test_user):
        user, _ = test_user

        with app.app_context():
            first = generate_tokens(user.id)
            second = generate_tokens(user.id)
            first_jti = decode_token(first["refresh_token"])["jti"]
            second_jti = decode_token(second["refresh_token"])["jti"]

            revoked_count = revoke_user_tokens(user.id)

            db.session.expire_all()
            assert revoked_count == 2
            assert RefreshToken.is_valid(user.id, first_jti) is False
            assert RefreshToken.is_valid(user.id, second_jti) is False
