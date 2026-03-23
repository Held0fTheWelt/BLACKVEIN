import pytest
import unittest.mock
import json
from unittest.mock import patch

# Assuming your application is in a directory named 'app'
# and your client is in a directory named 'client'
# from app.task_executor import TaskExecutor, OllamaUnavailableError, ClaudeUnavailableError
# from client import OllamaClient  # Or whatever your client import statement is

# Mock fixtures (replace with your actual fixture implementations)
def test_user():
    return {"id": 123, "name": "Test User"}

def test_admin_headers():
    return {
        "Authorization": "Bearer AdminToken",
        "X-API-Key": "AdminKey"
    }
from app.task_executor import TaskExecutor, OllamaUnavailableError, ClaudeUnavailableError, TaskExecutionResult

# Fixture for the app client
@pytest.fixture
def app_client():
    """Fixture to create the app client."""
    # Replace with your actual client instantiation
    client = OllamaClient()
    return client

# Fixture for the test user
@pytest.fixture
def test_user():
    return {"id": 123, "name": "Test User"}


# Fixture for admin headers
@pytest.fixture
def admin_headers():
    return {
        "Authorization": "Bearer AdminToken",
        "X-API-Key": "AdminKey"
    }


# Test file for TaskExecutor fallback behavior
def test_ollama_available_routes_to_ollama(app_client):
    """Test that Ollama is available and targets 'ollama' with cost 0.0"""
    ollama_client_mock = unittest.mock.MagicMock()
    ollama_client_mock.get_ollama_routes.return_value = [{"worker": "ollama"}]
    ollama_client_mock.execute.return_value = TaskExecutionResult(
        id="ollama_task_1",
        status="success",
        result="ollama_result"
    )

    # Mock the client object
    with patch("app.task_executor.OllamaClient") as mock_ollama_client:
        mock_ollama_client.return_value = ollama_client_mock
        result = TaskExecutor(app_client, "some_task").execute(
            "test_task", test_user(), admin_headers
        )

    assert result.target_worker == "ollama"
    assert result.cost == 0.0


def test_ollama_unavailable_falls_back_to_claude(app_client):
    """Test that Ollama unavailable throws an error and Claude is called."""
    claude_client_mock = unittest.mock.MagicMock()
    claude_client_mock.get_claude_routes.return_value = [{"worker": "claude_api"}]
    claude_client_mock.execute.return_value = TaskExecutionResult(
        id="claude_task_1",
        status="success",
        result="claude_result"
    )

    # Mock the client object
    with patch("app.task_executor.OllamaClient") as mock_ollama_client:
        mock_ollama_client.return_value = ollama_client_mock
        mock_ollama_client.side_effect = OllamaUnavailableError()

        result = TaskExecutor(app_client, "some_task").execute(
            "test_task", test_user(), admin_headers
        )

    assert result.target_worker == "claude_api"
    assert result.cost > 0.0 #Claude has cost


def test_force_ollama_fails_when_unavailable(app_client):
    """Test that forcing Ollama fails when it's unavailable."""
    ollama_client_mock = unittest.mock.MagicMock()
    ollama_client_mock.get_ollama_routes.return_value = [{"worker": "ollama"}]
    ollama_client_mock.execute.return_value = TaskExecutionResult(
        id="ollama_task_1",
        status="success",
        result="ollama_result"
    )

    # Mock the client object
    with patch("app.task_executor.OllamaClient") as mock_ollama_client:
        mock_ollama_client.return_value = ollama_client_mock
        mock_ollama_client.side_effect = OllamaUnavailableError()
        result = TaskExecutor(app_client, "some_task").execute(
            "test_task", test_user(), admin_headers, force_ollama=True
        )

    assert result.success is False
    assert result.target_worker == "stop_ask_user"


def test_both_unavailable_returns_error(app_client):
    """Test that both Ollama and Claude are unavailable."""
    with patch("app.task_executor.OllamaClient") as mock_ollama_client:
        mock_ollama_client.side_effect = OllamaUnavailableError()

    with patch("app.task_executor.AnthropicClient") as mock_anthropic_client:
        mock_anthropic_client.side_effect = ClaudeUnavailableError()

        result = TaskExecutor(app_client, "some_task").execute(
            "test_task", test_user(), admin_headers
        )

    assert result.success is False
    assert result.error_message is not None
    # Check for a relevant error message (customize based on your error handling)


def test_cost_tracking_ollama_zero_cost(app_client):
    """Test that Ollama execution records cost == 0.0"""
    ollama_client_mock = unittest.mock.MagicMock()
    ollama_client_mock.execute.return_value = TaskExecutionResult(
        id="ollama_task_1",
        status="success",
        result="ollama_result",
        cost=0.0
    )

    # Mock the client object
    with patch("app.task_executor.OllamaClient") as mock_ollama_client:
        mock_ollama_client.return_value = ollama_client_mock
        result = TaskExecutor(app_client, "some_task").execute(
            "test_task", test_user(), admin_headers
        )

    assert result.cost == 0.0


def test_cost_tracking_claude_has_nonzero_cost(app_client):
    """Test that Claude fallback records cost > 0.0"""
    claude_client_mock = unittest.mock.MagicMock()
    claude_client_mock.execute.return_value = TaskExecutionResult(
        id="claude_task_1",
        status="success",
        result="claude_result",
        cost=1.23
    )

    # Mock the client object
    with patch("app.task_executor.OllamaClient") as mock_ollama_client:
        mock_ollama_client.side_effect = OllamaUnavailableError()
        mock_ollama_client.return_value = ollama_client_mock
        result = TaskExecutor(app_client, "some_task").execute(
            "test_task", test_user(), admin_headers, force_ollama=False
        )

    assert result.cost > 0.0

def test_l5_escalation_stops_and_asks_user(app_client):
    """Test that L5 escalation stops and asks user."""
    escalation_client_mock = unittest.mock.MagicMock()
    escalation_client_mock.stop_and_ask_user.return_value = TaskExecutionResult(
        id="escalation_task_1",
        status="stopped_asked",
        result="escalation_result"
    )

    # Mock the client object
    with patch("app.task_executor.OllamaClient") as mock_ollama_client:
        mock_ollama_client.side_effect = OllamaUnavailableError()
        mock_ollama_client.return_value = escalation_client_mock
        result = TaskExecutor(app_client, "some_task").execute(
            "test_task", test_user(), admin_headers, escalation_level=5
        )

    assert result.target_worker == "stop_ask_user"
    assert result.success is False

def test_api_endpoint_task_execution(app_client):
    """Integration test hitting POST /api/v1/tasks via test client"""
    data = {"task_name": "test_task"}
    response = app_client.post("/api/v1/tasks", json=data, headers=admin_headers)
    assert response.status_code == 200  # Adjust based on your API response
    # Optionally, assert the response body
    assert "id" in response.json()