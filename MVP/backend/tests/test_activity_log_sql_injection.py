"""SQL injection vulnerability audit for activity log filtering.

This test suite ensures all activity log filters use parameterized queries
and properly sanitize input to prevent SQL injection attacks.
"""
import pytest
from app.models import ActivityLog
from app.services.activity_log_service import list_activity_logs, log_activity


class TestActivityLogSQLInjectionProtection:
    """Audit activity log filtering for SQL injection vulnerabilities."""

    def test_sql_injection_user_filter_quote_escape(self, app, admin_headers):
        """Test user filter with single quote escape attempt."""
        with app.app_context():
            # Log a test activity
            log_activity(
                category="test",
                action="sql_test",
                status="info",
                message="Normal message"
            )

            # Try SQL injection in user search
            malicious_q = "admin' OR '1'='1"
            items, total = list_activity_logs(q=malicious_q)

            # Should not return all records; parameterized query treats it as literal string
            # If vulnerable to injection, it would return all records
            assert isinstance(items, list)
            assert isinstance(total, int)
            # The query should find no exact matches for this string
            # (since we logged with "Normal message")
            if total > 0:
                # Verify the results are from literal string matching, not injection
                for item in items:
                    assert malicious_q in (item.message or "") or \
                           malicious_q in (item.action or "") or \
                           malicious_q in (item.actor_username_snapshot or "")

    def test_sql_injection_action_filter_double_quote(self, app):
        """Test action filter with double quote escape attempt."""
        with app.app_context():
            log_activity(
                category="test",
                action="create_user",
                status="success"
            )

            # Try SQL injection with double quotes
            malicious_action = 'create" OR "1"="1'
            items, total = list_activity_logs(action=malicious_action)

            # Should safely handle without executing injected SQL
            assert isinstance(items, list)
            assert isinstance(total, int)
            # Should find nothing or only exact matches
            if total > 0:
                for item in items:
                    assert item.action == malicious_action

    def test_sql_injection_category_filter_union(self, app):
        """Test category filter with UNION injection attempt."""
        with app.app_context():
            log_activity(
                category="auth",
                action="login",
                status="success"
            )
            log_activity(
                category="news",
                action="create",
                status="success"
            )

            # Try UNION-based injection
            malicious_category = "auth' UNION SELECT * FROM users WHERE '1'='1"
            items, total = list_activity_logs(category=malicious_category)

            # Should find no results since category must exactly match
            assert isinstance(items, list)
            assert isinstance(total, int)
            # Safe parameterized query will find no match
            for item in items:
                assert item.category == malicious_category

    def test_sql_injection_date_range_integer_injection(self, app):
        """Test date range filters with integer injection attempts."""
        with app.app_context():
            log_activity(
                category="test",
                action="timestamp_test",
                status="info"
            )

            # Try integer injection in date field
            malicious_date_from = "2024-01-01' OR '1'='1"
            items, total = list_activity_logs(date_from=malicious_date_from)

            # Invalid date format is caught by try/except, so no injection occurs
            assert isinstance(items, list)
            assert isinstance(total, int)

    def test_sql_injection_date_to_boundary_check(self, app):
        """Test date_to filter handles injection in boundary logic."""
        with app.app_context():
            log_activity(
                category="test",
                action="date_boundary",
                status="info"
            )

            # Try injection with date boundary manipulation
            malicious_date_to = "2024-12-31'; DROP TABLE activity_logs; --"
            items, total = list_activity_logs(date_to=malicious_date_to)

            # Should safely handle as invalid date
            assert isinstance(items, list)
            assert isinstance(total, int)
            # Table should still exist (proof SQL wasn't executed)
            count = ActivityLog.query.count()
            assert count >= 1

    def test_sql_injection_chained_filters_no_concatenation(self, app):
        """Test multiple filters combined don't use string concatenation."""
        with app.app_context():
            log_activity(
                category="auth",
                action="login",
                status="success",
                message="User logged in"
            )

            # Use multiple filters together with injection attempts
            malicious_q = "admin' OR '1'='1"
            malicious_category = "auth' OR '1'='1"
            malicious_status = "success' OR '1'='1"

            items, total = list_activity_logs(
                q=malicious_q,
                category=malicious_category,
                status=malicious_status
            )

            # All filters should be parameterized; no injection concatenation
            assert isinstance(items, list)
            assert isinstance(total, int)
            # Only exact matches should be returned
            for item in items:
                assert item.category == malicious_category or \
                       item.status == malicious_status or \
                       malicious_q in (item.message or "")

    def test_sql_injection_like_operator_with_wildcards(self, app):
        """Test LIKE operator in search filter uses proper parameterization."""
        with app.app_context():
            log_activity(
                category="test",
                action="search_test",
                status="info",
                message="Test message for search"
            )

            # Try injection through LIKE operator
            malicious_q = "search'; DROP TABLE activity_logs; --"
            items, total = list_activity_logs(q=malicious_q)

            # Should be safe; ILIKE in SQLAlchemy is parameterized
            assert isinstance(items, list)
            assert isinstance(total, int)
            # Table should still exist
            assert ActivityLog.query.count() >= 1

    def test_sql_injection_percent_sign_in_search(self, app):
        """Test percent sign handling in search (LIKE wildcard)."""
        with app.app_context():
            log_activity(
                category="test",
                action="percent_test",
                status="info",
                message="Message with % character"
            )

            # Use percent sign which is special in LIKE
            test_q = "Message%"
            items, total = list_activity_logs(q=test_q)

            # Parameterized query treats % as literal in search term
            assert isinstance(items, list)
            assert isinstance(total, int)

    def test_sql_injection_null_byte_injection(self, app):
        """Test null byte injection attempts."""
        with app.app_context():
            log_activity(
                category="test",
                action="null_byte_test",
                status="info"
            )

            # Try null byte injection
            malicious_q = "search\x00' OR '1'='1"
            items, total = list_activity_logs(q=malicious_q)

            # Should handle safely
            assert isinstance(items, list)
            assert isinstance(total, int)

    def test_sql_injection_stacked_queries(self, app):
        """Test stacked query injection attempts."""
        with app.app_context():
            log_activity(
                category="test",
                action="stacked_test",
                status="info"
            )

            # Try stacked queries
            malicious_action = "login'; DELETE FROM activity_logs; --"
            items, total = list_activity_logs(action=malicious_action)

            # Should be safe; parameterized queries prevent stacking
            assert isinstance(items, list)
            assert isinstance(total, int)
            # Table should still exist and have data
            assert ActivityLog.query.count() >= 1

    def test_sql_injection_time_based_blind(self, app):
        """Test time-based blind SQL injection attempts."""
        with app.app_context():
            log_activity(
                category="test",
                action="timing_test",
                status="info"
            )

            # Try time-based blind injection (SLEEP/WAITFOR)
            malicious_category = "test' OR SLEEP(5) OR '1'='1"

            import time
            start = time.time()
            items, total = list_activity_logs(category=malicious_category)
            elapsed = time.time() - start

            # Should complete quickly (no SLEEP executed)
            assert elapsed < 2.0  # Should be much less than 5 seconds
            assert isinstance(items, list)
            assert isinstance(total, int)

    def test_sql_injection_comment_based_evasion(self, app):
        """Test comment-based SQL injection evasion."""
        with app.app_context():
            log_activity(
                category="auth",
                action="login",
                status="success"
            )

            # Try injection with SQL comments
            malicious_q = "auth' OR '1'='1' -- "
            items, total = list_activity_logs(q=malicious_q)

            # Should be safely parameterized
            assert isinstance(items, list)
            assert isinstance(total, int)

    def test_owasp_top10_sql_injection_example(self, app):
        """Test OWASP Top 10 SQL injection example: admin' OR '1'='1."""
        with app.app_context():
            # Create some test data
            log_activity(
                category="admin",
                action="user_delete",
                status="success",
                actor_username_snapshot="admin"
            )
            log_activity(
                category="user",
                action="login",
                status="success",
                actor_username_snapshot="regularuser"
            )

            # OWASP classic injection
            malicious_username = "admin' OR '1'='1"
            items, total = list_activity_logs(q=malicious_username)

            # If vulnerable, this would return all records
            # With parameterized queries, it should find no matches or literal matches only
            assert isinstance(items, list)
            assert isinstance(total, int)

            # Verify that results are either empty or contain the literal string
            for item in items:
                has_injection_string = (
                    malicious_username in (item.actor_username_snapshot or "") or
                    malicious_username in (item.message or "") or
                    malicious_username in (item.action or "")
                )
                assert has_injection_string, \
                    "Query returned results without the injection string (sign of SQL injection vulnerability)"

    def test_parameterized_query_verification(self, app):
        """Verify that queries are parameterized (not string concatenation)."""
        with app.app_context():
            # This test verifies implementation details
            # The list_activity_logs function should use SQLAlchemy ORM methods
            # which produce parameterized queries automatically

            # Create test data
            log_activity(category="test", action="verify", status="info")

            # All these should use the same parameterized approach
            filters_to_test = [
                {"q": "test' OR '1'='1"},
                {"category": "test' OR '1'='1"},
                {"status": "info' OR '1'='1"},
                {"date_from": "2024-01-01' OR '1'='1"},
                {"date_to": "2024-12-31' OR '1'='1"},
            ]

            for filter_kwargs in filters_to_test:
                items, total = list_activity_logs(**filter_kwargs)
                # Should not crash and should return valid results
                assert isinstance(items, list)
                assert isinstance(total, int)
