"""World Engine Langfuse integration for distributed tracing."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

print(">>> LOADING LANGFUSE ADAPTER MODULE", flush=True)
logger = logging.getLogger(__name__)
logger.info(">>> LANGFUSE ADAPTER MODULE LOADED")


class LangfuseAdapter:
    """Singleton Langfuse adapter for world-engine story execution tracing."""

    _instance: Optional[LangfuseAdapter] = None
    _langfuse_client: Any = None

    def __init__(self):
        self.is_ready = False
        self.client = None
        self.active_span = None

        # Check if Langfuse is enabled
        enabled = os.getenv("LANGFUSE_ENABLED", "").lower() == "true"
        logger.info(f"Langfuse ENABLED env var: {enabled}")
        if not enabled:
            logger.info("Langfuse not enabled")
            return

        # Fetch credentials from backend database
        try:
            logger.info("Fetching Langfuse credentials from backend...")
            credentials = self._fetch_credentials_from_backend()
            logger.info(f"Credentials result: {credentials}")
            if not credentials:
                logger.info("Langfuse credentials not configured in backend")
                return

            public_key = credentials.get("public_key", "").strip()
            secret_key = credentials.get("secret_key", "").strip()
            base_url = credentials.get("base_url", "https://cloud.langfuse.com").strip()

            logger.info(f"Langfuse config: base_url={base_url}, has_public_key={bool(public_key)}, has_secret_key={bool(secret_key)}")
            if not public_key or not secret_key:
                logger.info("Langfuse credentials incomplete")
                return

            logger.info("Importing Langfuse SDK...")
            from langfuse import Langfuse
            logger.info(f"Initializing Langfuse client with base_url={base_url}")
            self.client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                base_url=base_url,
                environment=os.getenv("LANGFUSE_ENVIRONMENT", "development"),
                release=os.getenv("LANGFUSE_RELEASE", "unknown"),
                sample_rate=float(os.getenv("LANGFUSE_SAMPLE_RATE", "1.0")),
                enabled=True,
            )
            self.is_ready = True
            logger.info("✓ Langfuse adapter initialized successfully for world-engine")
        except ImportError as e:
            logger.warning(f"Langfuse SDK not available: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse: {str(e)}", exc_info=True)

    def _fetch_credentials_from_backend(self) -> Optional[dict[str, str]]:
        """Fetch Langfuse credentials from backend database."""
        try:
            import httpx
            backend_url = os.getenv("BACKEND_INTERNAL_URL", "http://localhost:5000")
            internal_token = os.getenv("INTERNAL_RUNTIME_CONFIG_TOKEN", "")

            logger.info(f"Backend URL: {backend_url}")
            logger.info(f"Token present: {bool(internal_token)}")

            if not internal_token:
                logger.warning("INTERNAL_RUNTIME_CONFIG_TOKEN not set")
                return None

            endpoint = f"{backend_url}/api/v1/internal/observability/langfuse-credentials"
            logger.info(f"Calling: {endpoint}")

            with httpx.Client(timeout=5.0) as client:
                response = client.get(
                    endpoint,
                    headers={"X-Internal-Config-Token": internal_token},
                )
                logger.info(f"Response status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    logger.info(f"Got credentials from backend: enabled={data.get('enabled')}, has_keys={bool(data.get('secret_key'))}")
                    return {
                        "public_key": data.get("public_key", ""),
                        "secret_key": data.get("secret_key", ""),
                        "base_url": data.get("base_url", "https://cloud.langfuse.com"),
                    }
                else:
                    logger.warning(f"Unexpected response status: {response.status_code}, body: {response.text}")
        except Exception as e:
            logger.error(f"Failed to fetch credentials from backend: {str(e)}", exc_info=True)
        return None

    @classmethod
    def get_instance(cls) -> LangfuseAdapter:
        if cls._instance is None:
            cls._instance = LangfuseAdapter()
        return cls._instance

    def is_enabled(self) -> bool:
        """Check if Langfuse is ready to trace."""
        return self.is_ready and self.client is not None

    def start_trace(
        self,
        name: str,
        session_id: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[Any]:
        """Start a new trace span."""
        if not self.is_enabled():
            return None

        try:
            trace_metadata = metadata or {}
            trace_metadata.setdefault("session_id", session_id)
            span = self.client.start_observation(
                as_type="span",
                name=name,
                metadata=trace_metadata,
            )
            return span
        except Exception as e:
            logger.error(f"Failed to start trace: {str(e)}")
            return None

    def set_active_span(self, span: Any) -> None:
        """Set the currently active span for child operations."""
        self.active_span = span

    def flush(self) -> None:
        """Flush pending traces to Langfuse."""
        if self.client:
            try:
                self.client.flush()
            except Exception as e:
                logger.error(f"Failed to flush Langfuse traces: {str(e)}")
