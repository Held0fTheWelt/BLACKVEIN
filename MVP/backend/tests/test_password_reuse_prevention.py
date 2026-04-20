"""
Tests for password reuse prevention feature.
Ensures users cannot reuse their last 3 passwords.
"""
import pytest
import json
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db
from app.models import User, Role
from app.services.user_service import change_password, create_user


@pytest.fixture
def password_reuse_test_user(app):
    """Create a test user for password reuse tests."""
    with app.app_context():
        user, err = create_user("passwordtestuser", "InitialPass123!", email="pwtest@example.com")
        assert err is None
        assert user is not None
        return user


def test_password_history_field_exists(app):
    """Test that password_history field exists and is nullable."""
    with app.app_context():
        user, err = create_user("testuser1", "InitialPass123!", email="test1@example.com")
        assert err is None
        assert user is not None
        assert hasattr(user, "password_history")
        assert user.password_history is None  # Initially None


def test_password_reuse_prevention_first_change(app, password_reuse_test_user):
    """Test that first password change works without history."""
    with app.app_context():
        user_from_db = User.query.get(password_reuse_test_user.id)
        # First change should work (no history)
        new_user, err = change_password(
            user_from_db.id,
            current_password="InitialPass123!",
            new_password="FirstNewPass456!",
        )
        assert err is None
        assert new_user is not None
        # Old password should be in history
        assert new_user.password_history is not None


def test_password_reuse_prevention_blocks_immediate_reuse(app, password_reuse_test_user):
    """Test that immediate password reuse is blocked."""
    with app.app_context():
        user_from_db = User.query.get(password_reuse_test_user.id)
        # First change
        new_user, err = change_password(
            user_from_db.id,
            current_password="InitialPass123!",
            new_password="FirstNewPass456!",
        )
        assert err is None

        # Refresh user from db
        user_from_db = User.query.get(password_reuse_test_user.id)

        # Try to change back to initial password immediately
        result_user, err = change_password(
            user_from_db.id,
            current_password="FirstNewPass456!",
            new_password="InitialPass123!",
        )
        assert err == "Cannot reuse one of your last 3 passwords"
        assert result_user is None


def test_password_reuse_prevention_three_password_cycle(app, password_reuse_test_user):
    """
    Test the full cycle:
    - Set password to Pass1
    - Change to Pass2
    - Change to Pass3
    - Change to Pass4
    - Try Pass1 again -> should still fail (in history)
    - Change to Pass5
    - Try Pass1 again -> should succeed (rotated out)
    """
    with app.app_context():
        user_from_db = User.query.get(password_reuse_test_user.id)

        # Start: InitialPass123! (current)
        # Password 1
        new_user, err = change_password(
            user_from_db.id,
            current_password="InitialPass123!",
            new_password="Pass1_NewPass456!",
        )
        assert err is None, f"First change failed: {err}"

        user_from_db = User.query.get(password_reuse_test_user.id)

        # Password 2
        new_user, err = change_password(
            user_from_db.id,
            current_password="Pass1_NewPass456!",
            new_password="Pass2_NewPass789!",
        )
        assert err is None, f"Second change failed: {err}"

        user_from_db = User.query.get(password_reuse_test_user.id)

        # Password 3
        new_user, err = change_password(
            user_from_db.id,
            current_password="Pass2_NewPass789!",
            new_password="Pass3_NewPass000!",
        )
        assert err is None, f"Third change failed: {err}"

        user_from_db = User.query.get(password_reuse_test_user.id)

        # Password 4 - now history is [Pass1, Pass2, Pass3] (original rotated out after 4 changes)
        new_user, err = change_password(
            user_from_db.id,
            current_password="Pass3_NewPass000!",
            new_password="Pass4_NewPass111!",
        )
        assert err is None, f"Fourth change failed: {err}"

        user_from_db = User.query.get(password_reuse_test_user.id)

        # Try to change back to Pass3 (in history) -> should fail
        result_user, err = change_password(
            user_from_db.id,
            current_password="Pass4_NewPass111!",
            new_password="Pass3_NewPass000!",
        )
        assert err == "Cannot reuse one of your last 3 passwords", f"Should reject Pass3: {err}"
        assert result_user is None

        user_from_db = User.query.get(password_reuse_test_user.id)

        # Password 5
        new_user, err = change_password(
            user_from_db.id,
            current_password="Pass4_NewPass111!",
            new_password="Pass5_NewPass222!",
        )
        assert err is None, f"Fifth change failed: {err}"

        user_from_db = User.query.get(password_reuse_test_user.id)

        # Now history is [Pass2, Pass3, Pass4] (Pass1 rotated out)
        # Try to use Pass1 again -> should succeed (rotated out)
        result_user, err = change_password(
            user_from_db.id,
            current_password="Pass5_NewPass222!",
            new_password="Pass1_NewPass456!",  # Try to reuse Pass1 (now rotated out)
        )
        assert err is None, f"Pass1 should now be allowed (rotated out): {err}"
        assert result_user is not None

        # Now InitialPass123! should definitely be rotated out since we've gone through more cycles
        # History now has: [Pass3, Pass4, Pass5]
        # Password 6 (which is Pass1 again, but we're doing another change for clarity)
        user_from_db = User.query.get(password_reuse_test_user.id)
        new_user, err = change_password(
            user_from_db.id,
            current_password="Pass1_NewPass456!",
            new_password="Pass6_NewPass333!",
        )
        assert err is None, f"Sixth change failed: {err}"

        user_from_db = User.query.get(password_reuse_test_user.id)

        # Now InitialPass123! should be rotated out
        # History should have last 3 only
        result_user, err = change_password(
            user_from_db.id,
            current_password="Pass6_NewPass333!",
            new_password="InitialPass123!",
        )
        assert err is None, f"Should allow original password now (fully rotated out): {err}"
        assert result_user is not None
        assert check_password_hash(result_user.password_hash, "InitialPass123!")


def test_password_history_json_format(app, password_reuse_test_user):
    """Test that password history is stored as valid JSON."""
    with app.app_context():
        user_from_db = User.query.get(password_reuse_test_user.id)
        new_user, err = change_password(
            user_from_db.id,
            current_password="InitialPass123!",
            new_password="FirstNewPass456!",
        )
        assert err is None
        user_from_db = User.query.get(password_reuse_test_user.id)
        assert user_from_db.password_history is not None

        history = json.loads(user_from_db.password_history)
        assert isinstance(history, list)
        assert len(history) == 1
        # Old password hash should be in history
        assert check_password_hash(history[0], "InitialPass123!")


def test_password_history_keeps_only_three(app, password_reuse_test_user):
    """Test that only the last 3 passwords are kept."""
    with app.app_context():
        user_from_db = User.query.get(password_reuse_test_user.id)

        passwords = [
            ("InitialPass123!", "Pass1_New123!"),
            ("Pass1_New123!", "Pass2_New123!"),
            ("Pass2_New123!", "Pass3_New123!"),
            ("Pass3_New123!", "Pass4_New123!"),
            ("Pass4_New123!", "Pass5_New123!"),
        ]

        for current, new in passwords:
            user_from_db = User.query.get(password_reuse_test_user.id)
            result_user, err = change_password(user_from_db.id, current_password=current, new_password=new)
            assert err is None, f"Password change failed: {err}"

        user_from_db = User.query.get(password_reuse_test_user.id)
        import json
        history = json.loads(user_from_db.password_history)

        # Should only have 4 hashes (last 3 old ones + current = 4)
        # Actually, history stores the last 3 OLD passwords
        assert len(history) == 3, f"Expected 3 hashes in history, got {len(history)}"
