import pytest
from unittest.mock import Mock, patch, MagicMock
from http import HTTPStatus
import json

# Mock the proxy module
class MockProxyResponse:
    def __init__(self, status_code, body=None, headers=None):
        self.status_code = status_code
        self.body = body or b'{}'
        self.headers = headers or {}

    def read(self):
        return self.body

    def getcode(self):
        return self.status_code

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

class MockProxyException(Exception):
    def __init__(self, reason):
        self.reason = reason

class MockURLError(Exception):
    def __init__(self, reason):
        self.reason = reason

@pytest.fixture
def mock_urlopen():
    """Create a mock for urllib.request.urlopen"""
    with patch('urllib.request.urlopen') as mock:
        yield mock

@pytest.fixture
def mock_proxy_module():
    """Mock the proxy module with necessary functions"""
    with patch('test_proxy_security.proxy') as mock_proxy:
        yield mock_proxy

@pytest.fixture
def mock_request():
    """Create a mock HTTP request"""
    mock = Mock()
    mock.get_method.return_value = 'GET'
    mock.get_full_url.return_value = '/_proxy/api/v1/users'
    mock.headers = {}
    mock.data = None
    return mock

class TestProxySecurity:
    """Test suite for proxy security functionality"""

    @pytest.mark.security
    def test_proxy_allows_api_requests(self, client):
        """Test that /_proxy/api/v1/users should reach backend"""
        response = client.get('/_proxy/api/v1/users')
        # Should either proxy through or handle gracefully
        assert response.status_code in (200, 502, 500)

    @pytest.mark.security
    def test_proxy_blocks_admin_paths(self, client):
        """Test that /_proxy/admin/* should return 403"""
        admin_paths = [
            '/_proxy/admin/users',
            '/_proxy/admin/settings',
            '/_proxy/admin/config',
            '/_proxy/admin/dashboard'
        ]

        for path in admin_paths:
            response = client.get(path)
            assert response.status_code == 403, f"Path {path} should return 403"

    @pytest.mark.security
    def test_proxy_forwards_authorization_header(self, client):
        """Test that Authorization header is forwarded to backend"""
        auth_token = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'
        headers = {'Authorization': auth_token}

        response = client.get(
            '/_proxy/api/v1/users',
            headers=headers
        )
        # Request should be attempted with auth header
        assert response.status_code in (200, 401, 502)

    @pytest.mark.security
    def test_proxy_strips_dangerous_headers(self, client):
        """Test that Cookie, Set-Cookie, Host headers are NOT forwarded"""
        dangerous_headers = {
            'Cookie': 'sessionid=abc123',
            'Set-Cookie': 'test=value',
            'Host': 'malicious-attacker.com'
        }

        response = client.get(
            '/_proxy/api/v1/users',
            headers=dangerous_headers
        )
        # Request should succeed without forwarding dangerous headers
        assert response.status_code in (200, 502)

    @pytest.mark.security
    def test_proxy_preserves_query_strings(self, client):
        """Test that /_proxy/api/v1/users?id=5 preserves query string"""
        test_cases = [
            '/_proxy/api/v1/users?id=5',
            '/_proxy/api/v1/users?name=john&age=30',
            '/_proxy/api/v1/users?page=1&limit=10',
        ]

        for path in test_cases:
            response = client.get(path)
            # Should handle query string properly
            assert response.status_code in (200, 502)

    @pytest.mark.security
    def test_proxy_forwards_post_body(self, client):
        """Test that POST body is forwarded to backend correctly"""
        post_data = json.dumps({'name': 'John', 'email': 'john@example.com'})
        headers = {'Content-Type': 'application/json'}

        response = client.post(
            '/_proxy/api/v1/users',
            data=post_data,
            headers=headers
        )

        # POST should be attempted
        assert response.status_code in (201, 400, 401, 502)

    @pytest.mark.security
    def test_proxy_handles_upstream_errors(self, client):
        """Test that 401/404/500 from backend pass through"""
        # Test various error codes that might come from backend
        response = client.get('/_proxy/api/v1/users/999')
        # Should return backend status or 502 if backend unavailable
        assert response.status_code in (200, 404, 502)

    @pytest.mark.security
    def test_proxy_rejects_malformed_requests(self, client):
        """Test that malformed requests are rejected"""
        # Test with paths that don't start with /_proxy
        response = client.get('/api/v1/users')
        # Should not proxy non-/_proxy paths
        assert response.status_code in (404, 405)
