#!/usr/bin/env python
"""
Demonstration of timing attack mitigation for email enumeration.

This script shows that the endpoints respond with constant time
regardless of whether the email exists in the database or not.
"""
import time
import sys
import os

# Set up Flask app
os.environ["FLASK_ENV"] = "testing"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import User, Role
from app.models.role import ensure_roles_seeded
from werkzeug.security import generate_password_hash

def run_timing_test():
    """Run timing tests on email enumeration endpoints."""
    print("=" * 70)
    print("TIMING ATTACK MITIGATION TEST")
    print("=" * 70)
    print()

    app = create_app(TestingConfig)

    with app.app_context():
        db.create_all()
        ensure_roles_seeded()

        # Get default role
        default_role = Role.query.filter_by(name=Role.NAME_USER).first()

        # Create test user with unverified email
        user = User(
            username="testuser",
            email="existing@example.com",
            password_hash=generate_password_hash("SecurePassword123!"),
            email_verified_at=None,
            role_id=default_role.id,
        )
        db.session.add(user)
        db.session.commit()

        client = app.test_client()

        # Test 1: Resend Verification - Existing Email
        print("\nTest 1: Resend Verification Endpoint")
        print("-" * 70)

        times_existing = []
        times_nonexistent = []

        for i in range(2):  # Reduced from 3 to avoid rate limiting (5 per minute)
            print(f"\nRound {i + 1}:")

            # Test existing email
            start = time.time()
            response = client.post(
                "/api/v1/auth/resend-verification",
                json={"email": "existing@example.com"},
                content_type="application/json",
            )
            elapsed = time.time() - start
            times_existing.append(elapsed)
            print(f"  Existing email:     {elapsed:.4f}s (status: {response.status_code})")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            # Test non-existent email
            start = time.time()
            response = client.post(
                "/api/v1/auth/resend-verification",
                json={"email": f"nonexistent{i}@example.com"},
                content_type="application/json",
            )
            elapsed = time.time() - start
            times_nonexistent.append(elapsed)
            print(f"  Non-existent email: {elapsed:.4f}s (status: {response.status_code})")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        avg_existing = sum(times_existing) / len(times_existing)
        avg_nonexistent = sum(times_nonexistent) / len(times_nonexistent)
        variance = abs(avg_existing - avg_nonexistent)

        print(f"\nSummary:")
        print(f"  Avg time (existing):     {avg_existing:.4f}s")
        print(f"  Avg time (non-existent): {avg_nonexistent:.4f}s")
        print(f"  Timing variance:         {variance:.4f}s")
        print(f"  Constant-time delay:     0.2000s (configured)")

        if variance < 0.1:
            print(f"  Result: PASS - Timing is constant (variance < 100ms)")
        else:
            print(f"  Result: FAIL - Timing variance too high (variance >= 100ms)")

        # Test 2: Forgot Password
        print("\n" + "=" * 70)
        print("\nTest 2: Forgot Password Endpoint")
        print("-" * 70)

        times_existing = []
        times_nonexistent = []

        for i in range(2):  # Reduced from 3 to avoid rate limiting (5 per minute)
            print(f"\nRound {i + 1}:")

            # Test existing email
            start = time.time()
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "existing@example.com"},
                content_type="application/json",
            )
            elapsed = time.time() - start
            times_existing.append(elapsed)
            print(f"  Existing email:     {elapsed:.4f}s (status: {response.status_code})")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            # Test non-existent email
            start = time.time()
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": f"nonexistent{i}@example.com"},
                content_type="application/json",
            )
            elapsed = time.time() - start
            times_nonexistent.append(elapsed)
            print(f"  Non-existent email: {elapsed:.4f}s (status: {response.status_code})")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        avg_existing = sum(times_existing) / len(times_existing)
        avg_nonexistent = sum(times_nonexistent) / len(times_nonexistent)
        variance = abs(avg_existing - avg_nonexistent)

        print(f"\nSummary:")
        print(f"  Avg time (existing):     {avg_existing:.4f}s")
        print(f"  Avg time (non-existent): {avg_nonexistent:.4f}s")
        print(f"  Timing variance:         {variance:.4f}s")
        print(f"  Constant-time delay:     0.2000s (configured)")

        if variance < 0.1:
            print(f"  Result: PASS - Timing is constant (variance < 100ms)")
        else:
            print(f"  Result: FAIL - Timing variance too high (variance >= 100ms)")

        # Test 3: Verify both endpoints return same message
        print("\n" + "=" * 70)
        print("\nTest 3: Response Message Consistency")
        print("-" * 70)

        # Test resend verification
        response1 = client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "existing@example.com"},
            content_type="application/json",
        )
        msg1 = response1.get_json().get("message", "")

        response2 = client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "nonexistent@example.com"},
            content_type="application/json",
        )
        msg2 = response2.get_json().get("message", "")

        print(f"\nResend Verification:")
        print(f"  Existing email:     '{msg1}'")
        print(f"  Non-existent email: '{msg2}'")

        # Same message for both = no info leak
        if msg1 == msg2:
            print(f"  Result: PASS - Same message for both (no info leak)")
        else:
            print(f"  Result: PARTIAL - Different messages (may leak info)")

        # Test forgot password
        response1 = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "existing@example.com"},
            content_type="application/json",
        )
        msg1 = response1.get_json().get("message", "")

        response2 = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
            content_type="application/json",
        )
        msg2 = response2.get_json().get("message", "")

        print(f"\nForgot Password:")
        print(f"  Existing email:     '{msg1}'")
        print(f"  Non-existent email: '{msg2}'")

        # Same message for both = no info leak
        if msg1 == msg2:
            print(f"  Result: PASS - Same message for both (no info leak)")
        else:
            print(f"  Result: PARTIAL - Different messages (may leak info)")

        # Cleanup
        db.drop_all()

        print("\n" + "=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)

if __name__ == "__main__":
    run_timing_test()
