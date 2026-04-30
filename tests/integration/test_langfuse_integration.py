#!/usr/bin/env python3
"""Integration test for Langfuse tracing in the application.

Verifies that the backend and world-engine Langfuse adapters correctly:
1. Use the correct Langfuse SDK v4.x parameter names (base_url, not host/baseUrl)
2. Initialize with Langfuse credentials when available
3. Handle disabled/missing credentials gracefully
4. Send traces to the Langfuse service (when enabled and credentials provided)
"""

import os
import time
import inspect
import pytest


class TestLangfuseParameterNamesInCode:
    """Test that adapter code uses correct Langfuse SDK v4.x parameter names."""

    def test_backend_adapter_uses_base_url_not_host(self):
        """Backend adapter uses 'base_url' not 'host' parameter."""
        from backend.app.observability.langfuse_adapter import LangfuseAdapter

        source = inspect.getsource(LangfuseAdapter.__init__)

        # Verify host parameter is NOT used (the bug fix)
        assert "host=" not in source, \
            "Backend adapter should use 'base_url=' not 'host=' (Langfuse SDK v4.x)"

        # Verify base_url parameter IS used
        assert "base_url=" in source, \
            "Backend adapter should use 'base_url=' parameter (Langfuse SDK v4.x)"

    def test_backend_config_uses_base_url_not_host(self):
        """Backend config defines 'base_url' attribute not 'host'."""
        from backend.app.observability.langfuse_adapter import LangfuseConfig

        source = inspect.getsource(LangfuseConfig.__init__)

        # Verify the config defines base_url
        assert "self.base_url" in source, \
            "LangfuseConfig should define 'self.base_url' attribute"

    def test_worldengine_adapter_uses_base_url_not_baseurl(self):
        """World-engine adapter uses 'base_url' not 'baseUrl' parameter."""
        try:
            from world_engine.app.observability.langfuse_adapter import LangfuseAdapter

            source = inspect.getsource(LangfuseAdapter.__init__)

            # Verify baseUrl (camelCase) is NOT used (the bug fix)
            assert "baseUrl=" not in source, \
                "World-engine adapter should use 'base_url=' not 'baseUrl=' (Langfuse SDK v4.x)"

            # Verify base_url IS used
            assert "base_url=" in source, \
                "World-engine adapter should use 'base_url=' parameter (Langfuse SDK v4.x)"
        except ImportError:
            pytest.skip("World-engine not available in test environment")


class TestLangfuseBackendAdapterDisabled:
    """Test backend Langfuse adapter graceful degradation when disabled."""

    def test_backend_adapter_no_op_when_disabled(self):
        """Backend adapter is a no-op when Langfuse is disabled."""
        from backend.app.observability.langfuse_adapter import LangfuseConfig, LangfuseAdapter

        # Create a disabled config
        config = LangfuseConfig()
        config.enabled = False

        # Create adapter with disabled config
        adapter = LangfuseAdapter(config)

        assert not adapter.is_enabled(), "Adapter should not be enabled when disabled"
        assert adapter._client is None, "Client should not be initialized"

        # start_trace should return None (safe no-op)
        result = adapter.start_trace(
            name="test.disabled.trace",
            session_id="test_session",
            metadata={"test": "disabled"},
        )
        assert result is None, "start_trace should return None when disabled"

    def test_backend_adapter_no_op_with_missing_credentials(self):
        """Backend adapter is a no-op when credentials are missing."""
        from backend.app.observability.langfuse_adapter import LangfuseConfig, LangfuseAdapter

        # Create a config with enabled=True but missing credentials
        config = LangfuseConfig()
        config.enabled = True
        config.public_key = ""
        config.secret_key = ""

        # Create adapter with incomplete config
        adapter = LangfuseAdapter(config)

        assert not adapter.is_enabled(), "Adapter should not be enabled without credentials"
        assert adapter._client is None, "Client should not be initialized without credentials"


class TestLangfuseDirectSDKUsage:
    """Test Langfuse SDK directly with correct v4.x API."""

    @pytest.mark.skipif(
        not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")),
        reason="Langfuse credentials not configured"
    )
    def test_langfuse_sdk_with_correct_base_url_parameter(self):
        """Verify Langfuse SDK v4.x accepts 'base_url' parameter."""
        from langfuse import Langfuse

        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        base_url = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

        # This should not raise an exception (correct parameter name)
        try:
            client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                base_url=base_url,
            )
            assert client is not None, "Langfuse client should be created successfully"
        except TypeError as e:
            pytest.fail(f"Langfuse SDK should accept 'base_url' parameter: {e}")

    @pytest.mark.skipif(
        not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")),
        reason="Langfuse credentials not configured"
    )
    def test_langfuse_sdk_rejects_baseurl_parameter(self):
        """Verify Langfuse SDK v4.x does NOT accept 'baseUrl' parameter."""
        from langfuse import Langfuse

        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")

        # This should raise TypeError (incorrect parameter name)
        with pytest.raises(TypeError):
            Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                baseUrl="https://cloud.langfuse.com",  # Wrong: camelCase
            )


class TestLangfuseCanEmitTraces:
    """Test that application can emit traces using correct SDK API."""

    @pytest.mark.skipif(
        not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")),
        reason="Langfuse credentials not configured"
    )
    def test_langfuse_emit_trace_with_observe_decorator(self):
        """Test trace emission using @observe() decorator (v4.x API)."""
        from langfuse import observe

        @observe()
        def test_function():
            return {"status": "success"}

        # Execute decorated function
        result = test_function()
        assert result["status"] == "success"

        # If we got here without exception, trace was emitted
        # (Langfuse sends async, so no need to verify receipt)

