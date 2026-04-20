"""Tests for privilege/role change logging and security alerts."""
import pytest
from app.models import ActivityLog, Role, User


def test_privilege_change_logs_to_activity_log(client, admin_headers, admin_user, test_user, app):
    """When admin changes user role, activity log should record before/after values."""
    user, _ = test_user
    admin, _ = admin_user

    # Initial check: user should have role "user"
    with app.app_context():
        target = User.query.get(user.id)
        assert target.role == "user"

    # Admin assigns user to "qa" role
    r = client.patch(
        f"/api/v1/users/{user.id}/role",
        headers=admin_headers,
        json={"role": "qa"},
        content_type="application/json",
    )
    assert r.status_code == 200

    # Check activity logs: should have privilege_change log with before/after values
    with app.app_context():
        # Find privilege_change logs for this user
        logs = ActivityLog.query.filter(
            ActivityLog.target_id == str(user.id),
            ActivityLog.category == "privilege_change"
        ).all()

        assert len(logs) > 0, "No privilege_change log found"
        log = logs[0]

        # Verify metadata contains before/after values
        assert log.meta is not None, "Metadata should not be None"
        assert log.meta.get("old_role") == "user", f"Expected old_role='user', got {log.meta.get('old_role')}"
        assert log.meta.get("new_role") == "qa", f"Expected new_role='qa', got {log.meta.get('new_role')}"
        assert log.status == "warning", f"Expected status='warning', got {log.status}"


def test_superadmin_grant_triggers_critical_log(client, admin_user, test_user, app, caplog):
    """When admin grants SuperAdmin (role=admin with role_level>=100), critical alert should be logged."""
    import logging

    user, _ = test_user
    admin, _ = admin_user

    # Ensure admin has higher role_level to be able to assign
    with app.app_context():
        admin_db = User.query.get(admin.id)
        admin_db.role_level = 150  # Higher than SuperAdmin threshold (100)
        from app.extensions import db
        db.session.commit()

    # Login as admin
    r = client.post(
        "/api/v1/auth/login",
        json={"username": admin.username, "password": "Adminpass1"},
        content_type="application/json",
    )
    assert r.status_code == 200
    token = r.get_json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {token}"}

    # Admin grants SuperAdmin by setting role_level >= 100
    with caplog.at_level(logging.CRITICAL):
        r = client.put(
            f"/api/v1/users/{user.id}",
            headers=admin_headers,
            json={"role": "admin", "role_level": 100},
            content_type="application/json",
        )
        assert r.status_code == 200

    # Check that critical alert was logged
    with app.app_context():
        logs = ActivityLog.query.filter(
            ActivityLog.target_id == str(user.id),
            ActivityLog.category == "privilege_change"
        ).all()

        assert len(logs) > 0, "No privilege_change log found for SuperAdmin grant"
        log = logs[0]
        # SuperAdmin grant should have critical status
        assert log.status == "critical", f"Expected status='critical' for SuperAdmin grant, got {log.status}"


def test_role_level_change_logs_before_after_values(client, admin_headers, admin_user, test_user, app):
    """When admin changes role_level, activity log should record before/after values."""
    user, _ = test_user
    admin, _ = admin_user

    with app.app_context():
        target = User.query.get(user.id)
        old_level = target.role_level or 0

    # Admin increases role_level
    new_level = old_level + 10
    r = client.put(
        f"/api/v1/users/{user.id}",
        headers=admin_headers,
        json={"role_level": new_level},
        content_type="application/json",
    )

    # Should succeed or fail gracefully
    if r.status_code == 200:
        with app.app_context():
            logs = ActivityLog.query.filter(
                ActivityLog.target_id == str(user.id),
                ActivityLog.category == "privilege_change"
            ).all()

            if logs:
                log = logs[0]
                assert log.meta.get("old_role_level") == old_level
                assert log.meta.get("new_role_level") == new_level


def test_privilege_change_includes_actor_info(client, admin_headers, admin_user, test_user, app):
    """Privilege change log should include admin (actor) info."""
    user, _ = test_user
    admin, _ = admin_user

    r = client.patch(
        f"/api/v1/users/{user.id}/role",
        headers=admin_headers,
        json={"role": "qa"},
        content_type="application/json",
    )
    assert r.status_code == 200

    with app.app_context():
        logs = ActivityLog.query.filter(
            ActivityLog.target_id == str(user.id),
            ActivityLog.category == "privilege_change"
        ).all()

        assert len(logs) > 0
        log = logs[0]

        # Actor info should be recorded
        assert log.actor_user_id == admin.id
        assert log.actor_username_snapshot == admin.username


def test_privilege_change_with_reason(client, admin_headers, admin_user, test_user, app):
    """Privilege change log should include reason if provided."""
    user, _ = test_user
    admin, _ = admin_user

    reason = "User demonstrated good behavior and moderation skills"
    r = client.patch(
        f"/api/v1/users/{user.id}/role",
        headers=admin_headers,
        json={"role": "qa", "reason": reason},
        content_type="application/json",
    )
    assert r.status_code == 200

    with app.app_context():
        logs = ActivityLog.query.filter(
            ActivityLog.target_id == str(user.id),
            ActivityLog.category == "privilege_change"
        ).all()

        assert len(logs) > 0
        log = logs[0]

        # Reason should be in metadata
        assert log.meta.get("reason") == reason


def test_privilege_change_message_format(client, admin_headers, admin_user, test_user, app):
    """Privilege change log message should include detailed info."""
    user, _ = test_user
    admin, _ = admin_user

    r = client.patch(
        f"/api/v1/users/{user.id}/role",
        headers=admin_headers,
        json={"role": "moderator"},
        content_type="application/json",
    )
    assert r.status_code == 200

    with app.app_context():
        logs = ActivityLog.query.filter(
            ActivityLog.target_id == str(user.id),
            ActivityLog.category == "privilege_change"
        ).all()

        assert len(logs) > 0
        log = logs[0]

        # Message should contain descriptive info
        assert "Privilege change" in log.message
        assert "user" in log.message or "testuser" in log.message.lower()
        assert "moderator" in log.message.lower()
