from story_runtime_core.adapters import MockModelAdapter, OpenAIChatAdapter, build_default_model_adapters


def test_mock_adapter_returns_success():
    result = MockModelAdapter().generate("hello")
    assert result.success is True
    assert result.content.startswith("[mock]")


def test_openai_adapter_handles_missing_key():
    result = OpenAIChatAdapter().generate("hello")
    assert result.success is False
    assert result.metadata.get("error") == "missing_openai_api_key"


def test_build_default_model_adapters_registers_providers():
    adapters = build_default_model_adapters()
    assert set(adapters.keys()) == {"mock", "openai", "ollama"}
    assert adapters["mock"].generate("x").success is True
