import pytest
from unittest.mock import patch, MagicMock
from tools.mcp_server.backend_client import BackendClient
from tools.mcp_server.errors import JsonRpcError

@pytest.fixture
def client():
    return BackendClient(base_url="http://localhost:8000", bearer_token=None)

def test_health_returns_dict_on_success(client):
    with patch("tools.mcp_server.backend_client.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"status": "ok"}
        result = client.health(trace_id="test-123")
        assert result == {"status": "ok"}

def test_health_raises_mcp_error_on_timeout(client):
    with patch("tools.mcp_server.backend_client.requests.get") as mock_get:
        mock_get.side_effect = TimeoutError()
        with pytest.raises(JsonRpcError):
            client.health(trace_id="test-123")

def test_health_raises_mcp_error_on_connection_error(client):
    with patch("tools.mcp_server.backend_client.requests.get") as mock_get:
        mock_get.side_effect = ConnectionError()
        with pytest.raises(JsonRpcError):
            client.health(trace_id="test-123")

def test_health_retries_on_network_error(client):
    with patch("tools.mcp_server.backend_client.requests.get") as mock_get:
        mock_get.side_effect = [ConnectionError(), MagicMock(status_code=200, json=lambda: {"status": "ok"})]
        result = client.health(trace_id="test-123")
        assert result == {"status": "ok"}
        assert mock_get.call_count == 2

def test_create_session_sends_post_request(client):
    with patch("tools.mcp_server.backend_client.requests.post") as mock_post:
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"session_id": "s123"}
        result = client.create_session(module_id="god_of_carnage", trace_id="test-456")
        assert result == {"session_id": "s123"}

def test_request_includes_trace_id_header(client):
    with patch("tools.mcp_server.backend_client.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"status": "ok"}
        client.health(trace_id="my-trace-456")
        call_args = mock_get.call_args
        assert call_args[1]["headers"]["X-Trace-ID"] == "my-trace-456"

def test_request_includes_bearer_token_when_set():
    client = BackendClient(base_url="http://localhost:8000", bearer_token="token123")
    with patch("tools.mcp_server.backend_client.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"status": "ok"}
        client.health(trace_id="test-789")
        call_args = mock_get.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer token123"

def test_http_error_raises_mcp_error(client):
    with patch("tools.mcp_server.backend_client.requests.get") as mock_get:
        mock_get.return_value.status_code = 500
        mock_get.return_value.text = "Internal Server Error"
        with pytest.raises(JsonRpcError):
            client.health(trace_id="test-999")
