from unittest.mock import Mock, patch

from story_runtime_core.adapters import MockModelAdapter, OpenAIChatAdapter, build_default_model_adapters


def test_mock_adapter_returns_success():
    result = MockModelAdapter().generate("hello")
    assert result.success is True
    import json
    parsed = json.loads(result.content)
    assert "narrative_response" in parsed


def test_openai_adapter_handles_missing_key():
    result = OpenAIChatAdapter().generate("hello")
    assert result.success is False
    assert result.metadata.get("error") == "missing_openai_api_key"


def test_openai_adapter_omits_temperature_for_gpt5_models():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
    }
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    client.post.return_value = response

    with patch("story_runtime_core.adapters.httpx.Client", return_value=client):
        result = OpenAIChatAdapter(api_key="sk-test").generate("Return valid JSON.", model_name="gpt-5-mini")

    assert result.success is True
    assert result.metadata["usage_available"] is True
    assert result.metadata["usage_source"] == "provider_response"
    assert result.metadata["usage_details"] == {"input": 11, "output": 7, "total": 18}
    assert client.post.call_args is not None
    assert result.metadata["timeout_seconds"] == 60.0
    payload = client.post.call_args.kwargs["json"]
    assert payload["model"] == "gpt-5-mini"
    assert "temperature" not in payload
    assert payload["reasoning_effort"] == "minimal"
    assert payload["max_completion_tokens"] == 1200
    assert payload["response_format"] == {"type": "json_object"}


def test_openai_adapter_caps_reasoning_model_timeout(monkeypatch):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    client.post.return_value = response
    monkeypatch.setenv("OPENAI_REASONING_CHAT_TIMEOUT_SECONDS", "7")

    with patch("story_runtime_core.adapters.httpx.Client", return_value=client) as client_cls:
        result = OpenAIChatAdapter(api_key="sk-test").generate(
            "hello",
            model_name="gpt-5-mini",
            timeout_seconds=30,
        )

    assert result.success is True
    assert result.metadata["timeout_seconds"] == 7.0
    assert client_cls.call_args.kwargs["timeout"] == 7.0


def test_openai_adapter_keeps_temperature_for_non_reasoning_chat_models():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    client.post.return_value = response

    with patch("story_runtime_core.adapters.httpx.Client", return_value=client):
        result = OpenAIChatAdapter(api_key="sk-test").generate("hello", model_name="gpt-4o-mini")

    assert result.success is True
    payload = client.post.call_args.kwargs["json"]
    assert payload["model"] == "gpt-4o-mini"
    assert payload["temperature"] == 0.3
    assert "reasoning_effort" not in payload
    assert "max_completion_tokens" not in payload


def test_build_default_model_adapters_registers_providers():
    adapters = build_default_model_adapters()
    assert set(adapters.keys()) == {"mock", "openai", "ollama"}
    assert adapters["mock"].generate("x").success is True
