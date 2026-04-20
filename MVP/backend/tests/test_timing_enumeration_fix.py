"""Tests for constant-time timing attack mitigation on email enumeration endpoints."""
import time
import pytest

from app.extensions import db
from app.models import User
from werkzeug.security import generate_password_hash


@pytest.fixture
def unverified_user(app):
    """Create a test user with unverified email."""
    with app.app_context():
        from app.models import Role
        role = Role.query.filter_by(name="user").first()
        if not role:
            role = Role(name="user", default_role_level=0)
            db.session.add(role)
            db.session.commit()

        user = User(
            username="unverified_user",
            email="unverified@example.com",
            password_hash=generate_password_hash("SecurePassword123!"),
            role_id=role.id,
            email_verified_at=None,  # Not verified
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        yield user
        # Cleanup handled by test database teardown


def test_resend_verification_constant_time_existing_email(client, unverified_user):
    """
    Test that /auth/resend-verification endpoint takes constant time
    regardless of whether email exists or not.
    """
    # Measure time for existing email
    start = time.time()
    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "unverified@example.com"},
        content_type="application/json",
    )
    elapsed_existing = time.time() - start

    assert response.status_code == 200

    print(f"Time for existing email: {elapsed_existing:.4f}s")


def test_resend_verification_constant_time_nonexistent_email(client):
    """Test that /auth/resend-verification takes constant time for non-existent email."""
    # Measure time for non-existent email
    start = time.time()
    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "nonexistent@example.com"},
        content_type="application/json",
    )
    elapsed_nonexisting = time.time() - start

    assert response.status_code == 200
    assert "if the email exists" in response.get_json().get("message", "").lower()

    print(f"Time for non-existent email: {elapsed_nonexisting:.4f}s")


def test_resend_verification_timing_variance(client, unverified_user):
    """
    Test that timing variance between existing and non-existing emails
    is within acceptable bounds (both should take ~0.2s).
    """
    # Collect multiple samples for statistical significance
    times_existing = []
    times_nonexisting = []

    for _ in range(3):
        # Test existing email
        start = time.time()
        response = client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "unverified@example.com"},
            content_type="application/json",
        )
        elapsed = time.time() - start
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        times_existing.append(elapsed)

        time.sleep(13)  # Space out requests to avoid 5 per minute rate limit

        # Test non-existent email
        start = time.time()
        response = client.post(
            "/api/v1/auth/resend-verification",
            json={"email": f"nonexistent{_}@example.com"},
            content_type="application/json",
        )
        elapsed = time.time() - start
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        times_nonexisting.append(elapsed)

        time.sleep(13)  # Space out requests to avoid 5 per minute rate limit

    avg_existing = sum(times_existing) / len(times_existing)
    avg_nonexisting = sum(times_nonexisting) / len(times_nonexisting)

    print(f"\nResend Verification Timing Analysis:")
    print(f"  Avg time (existing email): {avg_existing:.4f}s")
    print(f"  Avg time (non-existent email): {avg_nonexisting:.4f}s")
    print(f"  Variance: {abs(avg_existing - avg_nonexisting):.4f}s")

    # Both should take at least ~200ms (0.2s) due to constant-time delay
    # Allow 100ms variance for system jitter
    assert avg_existing >= 0.15, f"Existing email time too fast: {avg_existing}s (should be ~0.2s)"
    assert avg_nonexisting >= 0.15, f"Non-existent email time too fast: {avg_nonexisting}s (should be ~0.2s)"

    # Times should be reasonably close (within 100ms)
    timing_diff = abs(avg_existing - avg_nonexisting)
    assert timing_diff < 0.1, \
        f"Timing variance too high: {timing_diff:.4f}s (should be <0.1s to prevent enumeration)"


def test_forgot_password_constant_time_existing_email(client, unverified_user):
    """Test that /auth/forgot-password endpoint takes constant time for existing email."""
    start = time.time()
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "unverified@example.com"},
        content_type="application/json",
    )
    elapsed_existing = time.time() - start

    assert response.status_code == 200
    assert "if the email exists" in response.get_json().get("message", "").lower()

    print(f"Time for forgot-password (existing email): {elapsed_existing:.4f}s")


def test_forgot_password_constant_time_nonexistent_email(client):
    """Test that /auth/forgot-password takes constant time for non-existent email."""
    start = time.time()
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nonexistent@example.com"},
        content_type="application/json",
    )
    elapsed_nonexisting = time.time() - start

    assert response.status_code == 200
    assert "if the email exists" in response.get_json().get("message", "").lower()

    print(f"Time for forgot-password (non-existent email): {elapsed_nonexisting:.4f}s")


def test_forgot_password_timing_variance(client, unverified_user):
    """
    Test that timing variance between existing and non-existing emails
    in forgot-password endpoint is within acceptable bounds.
    """
    times_existing = []
    times_nonexisting = []

    for _ in range(3):
        # Test existing email
        start = time.time()
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "unverified@example.com"},
            content_type="application/json",
        )
        elapsed = time.time() - start
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        times_existing.append(elapsed)

        time.sleep(0.3)  # Space out requests to avoid 5 per hour rate limit per email

        # Test non-existent email (using different email each iteration to avoid rate limit)
        start = time.time()
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": f"nonexistent{_}@example.com"},
            content_type="application/json",
        )
        elapsed = time.time() - start
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        times_nonexisting.append(elapsed)

        time.sleep(0.3)  # Space out requests to avoid 5 per hour rate limit per email

    avg_existing = sum(times_existing) / len(times_existing)
    avg_nonexisting = sum(times_nonexisting) / len(times_nonexisting)

    print(f"\nForgot Password Timing Analysis:")
    print(f"  Avg time (existing email): {avg_existing:.4f}s")
    print(f"  Avg time (non-existent email): {avg_nonexisting:.4f}s")
    print(f"  Variance: {abs(avg_existing - avg_nonexisting):.4f}s")

    # Both should take at least ~200ms (0.2s) due to constant-time delay
    assert avg_existing >= 0.15, f"Existing email time too fast: {avg_existing}s (should be ~0.2s)"
    assert avg_nonexisting >= 0.15, f"Non-existent email time too fast: {avg_nonexisting}s (should be ~0.2s)"

    # Times should be reasonably close (within 100ms)
    timing_diff = abs(avg_existing - avg_nonexisting)
    assert timing_diff < 0.1, \
        f"Timing variance too high: {timing_diff:.4f}s (should be <0.1s to prevent enumeration)"


def test_resend_verification_empty_email_returns_400(client):
    """Test that empty email is rejected (no timing attack possible)."""
    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": ""},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "required" in response.get_json().get("error", "").lower()


def test_forgot_password_empty_email_returns_400(client):
    """Test that empty email is rejected (no timing attack possible)."""
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": ""},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "required" in response.get_json().get("error", "").lower()
