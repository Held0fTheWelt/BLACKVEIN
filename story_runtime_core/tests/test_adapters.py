import httpx
import pytest
from unittest.mock import Mock, patch

from story_runtime_core.adapters import MockModelAdapter, OpenAIChatAdapter, build_default_model_adapters, openai_http_error_excerpt


def test_openai_http_error_excerpt_parses_error_message():
    resp = Mock()
    resp.json.return_value = {"error": {"type": "invalid_request_error", "message": "bad param"}}
    assert "invalid_request_error" in openai_http_error_excerpt(resp)
    assert "bad param" in openai_http_error_excerpt(resp)


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
        "id": "resp_test",
        "output_text": "ok",
        "usage": {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18},
    }
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    client.post.return_value = response

    with patch("story_runtime_core.adapters.httpx.Client", return_value=client):
        result = OpenAIChatAdapter(api_key="sk-test").generate("Return valid JSON.", model_name="gpt-5.4-mini")

    assert result.success is True
    assert result.metadata["adapter_api"] == "responses"
    assert result.metadata["usage_available"] is True
    assert result.metadata["usage_source"] == "provider_response"
    assert result.metadata["usage_details"] == {"input": 11, "output": 7, "total": 18}
    assert client.post.call_args is not None
    assert result.metadata["timeout_seconds"] == 60.0
    assert client.post.call_args.args[0].endswith("/responses")
    payload = client.post.call_args.kwargs["json"]
    assert payload["model"] == "gpt-5.4-mini"
    assert payload["input"] == "Return valid JSON."
    assert "instructions" not in payload
    assert "temperature" not in payload
    assert "reasoning" not in payload
    assert payload["max_output_tokens"] == 4096
    assert payload["text"] == {"format": {"type": "json_object"}}


def test_openai_adapter_caps_reasoning_model_timeout(monkeypatch):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"output_text": "ok"}
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    client.post.return_value = response
    monkeypatch.setenv("OPENAI_REASONING_CHAT_TIMEOUT_SECONDS", "7")

    with patch("story_runtime_core.adapters.httpx.Client", return_value=client) as client_cls:
        result = OpenAIChatAdapter(api_key="sk-test").generate(
            "hello",
            model_name="gpt-5.5",
            timeout_seconds=30,
        )

    assert result.success is True
    assert result.metadata["timeout_seconds"] == 7.0
    assert client_cls.call_args.kwargs["timeout"] == 7.0
    assert client.post.call_args.kwargs["json"]["model"] == "gpt-5.5"


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


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"output_text": "  hi  "}, "hi"),
        ({"output_text": ["a", "", "b"]}, "a\nb"),
        (
            {
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "Hello"}],
                    }
                ]
            },
            "Hello",
        ),
        (
            {
                "output": [
                    {"type": "message", "role": "assistant", "content": "Plain string body"},
                ]
            },
            "Plain string body",
        ),
        (
            {
                "output": [
                    {"type": "output_text", "text": "standalone"},
                ]
            },
            "standalone",
        ),
        (
            {
                "output": [
                    {
                        "type": "reasoning",
                        "summary": [{"type": "summary_text", "text": "thought"}],
                    },
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "answer"}],
                    },
                ]
            },
            "thought\nanswer",
        ),
        ({"output": [{"type": "message", "content": [{"refusal": "no"}]}]}, "no"),
    ],
)
def test_openai_extract_responses_text_handles_documented_shapes(payload, expected):
    assert OpenAIChatAdapter._extract_responses_text(payload) == expected


def test_openai_adapter_non_json_gpt5_includes_reasoning_on_responses():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"output_text": "ok"}
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    client.post.return_value = response

    with patch("story_runtime_core.adapters.httpx.Client", return_value=client):
        OpenAIChatAdapter(api_key="sk-test").generate("plain hello", model_name="gpt-5.5")

    payload = client.post.call_args.kwargs["json"]
    assert payload["input"] == "plain hello"
    assert payload["reasoning"] == {"effort": "minimal"}
    assert payload["max_output_tokens"] == 1200


def test_openai_adapter_allows_env_override_for_reasoning_json_output_budget(monkeypatch):
    monkeypatch.setenv("OPENAI_REASONING_JSON_MAX_OUTPUT_TOKENS", "8192")
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"output_text": "{\"ok\": true}"}
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    client.post.return_value = response

    with patch("story_runtime_core.adapters.httpx.Client", return_value=client):
        result = OpenAIChatAdapter(api_key="sk-test").generate(
            "Return valid JSON.",
            model_name="gpt-5.4-mini",
        )

    assert result.success is True
    payload = client.post.call_args.kwargs["json"]
    assert payload["max_output_tokens"] == 8192


def test_openai_adapter_responses_incomplete_returns_failure():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "id": "resp_cut",
        "status": "incomplete",
        "incomplete_details": {"reason": "max_output_tokens"},
        "output_text": "{\"partial\":",
        "usage": {"input_tokens": 11, "output_tokens": 4096, "total_tokens": 4107},
    }
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    client.post.return_value = response

    with patch("story_runtime_core.adapters.httpx.Client", return_value=client):
        result = OpenAIChatAdapter(api_key="sk-test").generate(
            "Return valid JSON.",
            model_name="gpt-5.4-mini",
        )

    assert result.success is False
    assert result.content == "{\"partial\":"
    assert result.metadata["error"] == "openai_response_incomplete:max_output_tokens"
    assert result.metadata["response_status"] == "incomplete"
    assert result.metadata["incomplete_reason"] == "max_output_tokens"
    assert result.metadata["tokens_completion"] == 4096


def test_openai_adapter_http_400_returns_provider_error_excerpt():
    err_resp = Mock()
    err_resp.status_code = 400
    err_resp.json.return_value = {"error": {"type": "invalid_request_error", "message": "Unknown model xyz"}}
    err_resp.text = '{"error":{"message":"Unknown model xyz"}}'

    exc = httpx.HTTPStatusError("bad", request=Mock(), response=err_resp)

    def _raise(*_a, **_k):
        raise exc

    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    client.post = Mock(side_effect=_raise)

    with patch("story_runtime_core.adapters.httpx.Client", return_value=client):
        result = OpenAIChatAdapter(api_key="sk-test").generate("hi", model_name="gpt-5.4-mini")

    assert result.success is False
    assert result.metadata.get("http_status") == 400
    assert "Unknown model xyz" in (result.metadata.get("provider_error_excerpt") or "")
    assert result.metadata.get("adapter_api") == "responses"


def test_openai_adapter_force_chat_completions_env(monkeypatch):
    monkeypatch.setenv("OPENAI_GPT5_USE_CHAT_COMPLETIONS", "1")
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    client.post.return_value = response

    with patch("story_runtime_core.adapters.httpx.Client", return_value=client):
        result = OpenAIChatAdapter(api_key="sk-test").generate("hello", model_name="gpt-5.4-mini")

    assert result.success is True
    assert result.metadata["adapter_api"] == "chat_completions"
    assert client.post.call_args.args[0].endswith("/chat/completions")


def test_openai_adapter_chat_length_finish_returns_failure():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "choices": [{"message": {"content": "{\"partial\":"}, "finish_reason": "length"}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 1200, "total_tokens": 1203},
    }
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    client.post.return_value = response

    with patch("story_runtime_core.adapters.httpx.Client", return_value=client):
        result = OpenAIChatAdapter(api_key="sk-test").generate("hello", model_name="gpt-4o-mini")

    assert result.success is False
    assert result.metadata["error"] == "openai_chat_completion_incomplete:length"
    assert result.metadata["finish_reason"] == "length"
    assert result.metadata["tokens_completion"] == 1200


def test_openai_responses_request_includes_instructions_when_retrieval_present():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"output_text": "ok"}
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    client.post.return_value = response

    with patch("story_runtime_core.adapters.httpx.Client", return_value=client):
        OpenAIChatAdapter(api_key="sk-test").generate(
            "hello",
            model_name="gpt-5.4-nano",
            retrieval_context="System context here.",
        )

    payload = client.post.call_args.kwargs["json"]
    assert payload["instructions"] == "System context here."
    assert payload["input"] == "hello"
