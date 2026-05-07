"""World Engine Langfuse integration for distributed tracing."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from types import SimpleNamespace
from typing import Any, Iterator, Optional

print(">>> LOADING LANGFUSE ADAPTER MODULE", flush=True)
logger = logging.getLogger(__name__)
logger.info(">>> LANGFUSE ADAPTER MODULE LOADED")

_active_span_context: ContextVar[Optional[Any]] = ContextVar("active_span", default=None)


class LangfuseAdapter:
    """Singleton Langfuse adapter for world-engine story execution tracing."""

    _instance: Optional[LangfuseAdapter] = None
    _langfuse_client: Any = None

    def __init__(self):
        self.is_ready = False
        self.client = None
        self._config = SimpleNamespace(
            environment=os.getenv("LANGFUSE_ENVIRONMENT", "development"),
            release=os.getenv("LANGFUSE_RELEASE", "unknown"),
            sample_rate=float(os.getenv("LANGFUSE_SAMPLE_RATE", "1.0")),
        )

        # Fetch runtime observability settings from the backend database.
        try:
            logger.info("Fetching Langfuse credentials from backend...")
            credentials = self._fetch_credentials_from_backend()
            logger.info(f"Credentials result: {credentials}")
            if not credentials:
                logger.info("Langfuse credentials not configured in backend")
                return
            if not credentials.get("enabled"):
                logger.info("Langfuse disabled in backend settings")
                return

            public_key = credentials.get("public_key", "").strip()
            secret_key = credentials.get("secret_key", "").strip()
            base_url = credentials.get("base_url", "https://cloud.langfuse.com").strip()
            environment = credentials.get("environment") or os.getenv("LANGFUSE_ENVIRONMENT", "development")
            release = credentials.get("release") or os.getenv("LANGFUSE_RELEASE", "unknown")
            sample_rate = float(credentials.get("sample_rate") or os.getenv("LANGFUSE_SAMPLE_RATE", "1.0"))
            self._config.environment = environment
            self._config.release = release
            self._config.sample_rate = sample_rate

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
                environment=environment,
                release=release,
                sample_rate=sample_rate,
            )
            self.is_ready = True
            logger.info(f"[LANGFUSE] ✓ Adapter initialized successfully: is_ready=True, client={type(self.client).__name__}")
        except ImportError as e:
            logger.warning(f"[LANGFUSE] SDK not available: {e}")
        except Exception as e:
            logger.error(f"[LANGFUSE] Failed to initialize: {str(e)}", exc_info=True)

    def _fetch_credentials_from_backend(self) -> Optional[dict[str, str]]:
        """Fetch Langfuse credentials from backend database."""
        try:
            import httpx
            backend_url = os.getenv("BACKEND_RUNTIME_CONFIG_URL") or os.getenv("BACKEND_INTERNAL_URL", "http://localhost:8000")
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
                        "enabled": bool(data.get("enabled")),
                        "public_key": data.get("public_key", ""),
                        "secret_key": data.get("secret_key", ""),
                        "base_url": data.get("base_url", "https://cloud.langfuse.com"),
                        "environment": data.get("environment", "development"),
                        "release": data.get("release", "unknown"),
                        "sample_rate": data.get("sample_rate", 1.0),
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
        input: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> Optional[Any]:
        """Start a new trace root span (Langfuse SDK v4.x API)."""
        if not self.is_enabled():
            logger.info(f"[LANGFUSE] start_trace skipped: adapter not enabled")
            return None

        try:
            trace_metadata = metadata or {}
            trace_metadata.setdefault("session_id", session_id)

            # Use Langfuse SDK v4.x API: start_observation with as_type="span"
            span = self.client.start_observation(
                as_type="span",
                name=name,
                trace_context={"trace_id": trace_id} if trace_id else None,
                input=input or {"session_id": session_id},
                metadata=trace_metadata,
            )
            logger.info(f"[LANGFUSE] root span created: name={name}, session_id={session_id}, span_id={getattr(span, 'span_id', 'unknown')}, trace_id={getattr(span, 'trace_id', 'unknown')}")
            return span
        except Exception as e:
            logger.error(f"[LANGFUSE] Failed to start trace: {str(e)}", exc_info=True)
            return None

    def start_span_in_trace(
        self,
        *,
        trace_id: str,
        name: str,
        input: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[Any]:
        """Create a v4 span inside an existing Langfuse trace."""
        if not self.is_enabled():
            logger.info("[LANGFUSE] start_span_in_trace skipped: adapter not enabled")
            return None
        try:
            span = self.client.start_observation(
                as_type="span",
                name=name,
                trace_context={"trace_id": trace_id},
                input=input or {},
                metadata=metadata or {},
            )
            logger.info(f"[LANGFUSE] span created in trace: name={name}, trace_id={trace_id}")
            return span
        except Exception as e:
            logger.error(f"[LANGFUSE] Failed to create span in trace {trace_id}: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def _safe_session_id(value: str | None) -> str | None:
        session_id = str(value or "").strip()
        if not session_id:
            return None
        try:
            session_id.encode("ascii")
        except UnicodeEncodeError:
            logger.warning("[LANGFUSE] Dropping non-ASCII session_id for Langfuse session tracking")
            return None
        if len(session_id) > 200:
            logger.warning("[LANGFUSE] Dropping overlong session_id for Langfuse session tracking")
            return None
        return session_id

    @contextmanager
    def session_scope(
        self,
        *,
        root_span: Optional[Any],
        session_id: str | None,
        metadata: Optional[dict[str, str]] = None,
        trace_name: str | None = None,
        user_id: str | None = None,
    ) -> Iterator[None]:
        """Propagate Langfuse session_id and user_id to the root observation and child observations."""
        safe_session_id = self._safe_session_id(session_id)
        if not self.is_enabled() or not safe_session_id:
            with nullcontext():
                yield
            return

        try:
            from langfuse import propagate_attributes
            from opentelemetry import trace as otel_trace_api

            otel_span = getattr(root_span, "_otel_span", None)
            prop_kwargs: dict = {
                "session_id": safe_session_id,
                "metadata": metadata or {},
                "trace_name": trace_name,
            }
            if user_id:
                prop_kwargs["user_id"] = user_id
            propagate = propagate_attributes(**prop_kwargs)
        except Exception:
            logger.debug("[LANGFUSE] Failed to prepare session propagation", exc_info=True)
            with nullcontext():
                yield
            return

        if otel_span is not None:
            with otel_trace_api.use_span(otel_span, end_on_exit=False):
                with propagate:
                    yield
        else:
            with propagate:
                yield

    @property
    def config(self) -> SimpleNamespace:
        """Configuration object with environment, release, sample_rate."""
        return self._config

    def get_active_span(self) -> Optional[Any]:
        """Get the currently active span for child operations."""
        span = _active_span_context.get()
        logger.debug(f"[LANGFUSE] get_active_span: {span}")
        return span

    def set_active_span(self, span: Optional[Any]) -> None:
        """Set the currently active span for child operations (thread-safe via ContextVar)."""
        span_name = getattr(span, 'name', 'unknown') if span else None
        span_id = getattr(span, 'span_id', 'unknown') if span else None
        logger.info(f"[LANGFUSE] set_active_span: name={span_name}, span_id={span_id}")
        _active_span_context.set(span)

    def create_child_span(
        self,
        name: str,
        input: Optional[dict[str, Any]] = None,
        output: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
        level: Optional[str] = None,
        status_message: Optional[str] = None,
        as_type: str = "span",
    ) -> Optional[Any]:
        """Create a child span under the currently active parent span."""
        if not self.is_enabled():
            logger.debug(f"[LANGFUSE] create_child_span skipped: adapter not enabled")
            return None

        parent_span = _active_span_context.get()
        if not parent_span:
            logger.warning(f"[LANGFUSE] No active parent span to create child '{name}' - check if root span was set_active_span()")
            return None

        try:
            # Langfuse SDK v4: use start_observation to create child spans
            child_span = parent_span.start_observation(
                as_type=as_type,
                name=name,
                input=input or {},
                output=output or {},
                metadata=metadata or {},
                level=level,  # type: ignore[arg-type]
                status_message=status_message,
            )
            logger.info(f"[LANGFUSE] child span created: name={name}, span_id={getattr(child_span, 'span_id', 'unknown')}, parent_span_id={getattr(parent_span, 'span_id', 'unknown')}")
            return child_span
        except Exception as e:
            logger.error(f"[LANGFUSE] Failed to create child span '{name}': {str(e)}", exc_info=True)
            return None

    def record_generation(
        self,
        *,
        name: str,
        model: str,
        provider: str,
        prompt: Optional[str] = None,
        completion: Optional[str] = None,
        usage_details: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[Any]:
        """Record a Langfuse generation observation under the active story span."""
        if not self.is_enabled():
            return None
        parent_span = _active_span_context.get()
        if not parent_span:
            logger.warning(f"[LANGFUSE] No active parent span to record generation '{name}'")
            return None
        try:
            generation = parent_span.start_observation(
                as_type="generation",
                name=name,
                model=model,
                input={"prompt": prompt} if prompt else {},
                metadata={
                    **(metadata or {}),
                    "model": model,
                    "provider": provider,
                },
            )
            update_kwargs: dict[str, Any] = {
                "output": {"completion": completion} if completion else {},
            }
            if isinstance(usage_details, dict):
                update_kwargs["usage_details"] = usage_details
            generation.update(**update_kwargs)
            generation.end()
            logger.info(f"[LANGFUSE] generation observation recorded: name={name}, model={model}")
            return generation
        except Exception as e:
            logger.error(f"[LANGFUSE] Failed to record generation '{name}': {str(e)}", exc_info=True)
            return None

    def record_retrieval(
        self,
        *,
        name: str = "story.rag.retrieval",
        query: Optional[str] = None,
        documents: Optional[list[dict[str, Any]]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[Any]:
        """Record a Langfuse retriever observation under the active story span."""
        if not self.is_enabled():
            return None
        parent_span = _active_span_context.get()
        if not parent_span:
            logger.warning(f"[LANGFUSE] No active parent span to record retrieval '{name}'")
            return None
        try:
            retrieval = parent_span.start_observation(
                as_type="retriever",
                name=name,
                input={"query": query} if query else {},
                metadata={
                    **(metadata or {}),
                    "document_count": len(documents or []),
                },
            )
            retrieval.update(output={"documents": documents or []})
            retrieval.end()
            logger.info(f"[LANGFUSE] retriever observation recorded: name={name}, documents={len(documents or [])}")
            return retrieval
        except Exception as e:
            logger.error(f"[LANGFUSE] Failed to record retrieval '{name}': {str(e)}", exc_info=True)
            return None

    def add_score(
        self,
        *,
        name: str,
        value: float,
        comment: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Attach a deterministic score to the active story trace/span."""
        if not self.is_enabled():
            return
        parent_span = _active_span_context.get()
        if not parent_span:
            logger.warning(f"[LANGFUSE] No active parent span to add score '{name}'")
            return
        trace_id = getattr(parent_span, "trace_id", None)
        try:
            parent_span.score(
                name=name,
                value=value,
                comment=comment,
                metadata=metadata or {},
            )
        except Exception as e:
            logger.error(f"[LANGFUSE] Failed to add score '{name}': {str(e)}", exc_info=True)
            return
        # Trace-level duplicate: Langfuse UI / trace JSON export `trace.scores` list trace-level
        # scores; `span.score()` attaches to the observation only (see ADR-0033 §13.5).
        try:
            if trace_id and self.client:
                meta = dict(metadata or {})
                meta.setdefault("score_attachment", "trace_duplicate")
                self.client.create_score(
                    name=name,
                    value=value,
                    trace_id=str(trace_id),
                    comment=comment,
                    metadata=meta,
                )
        except Exception as e:
            logger.warning(
                f"[LANGFUSE] Trace-level create_score failed for '{name}': {str(e)}",
                exc_info=True,
            )

    def flush(self) -> None:
        """Flush pending traces to Langfuse."""
        if self.client:
            logger.info(f"[LANGFUSE] Flushing pending traces to Langfuse...")
            try:
                self.client.flush()
                logger.info(f"[LANGFUSE] Flush completed successfully")
            except Exception as e:
                logger.error(f"[LANGFUSE] Failed to flush Langfuse traces: {str(e)}", exc_info=True)
        else:
            logger.warning(f"[LANGFUSE] Flush called but client is None")
