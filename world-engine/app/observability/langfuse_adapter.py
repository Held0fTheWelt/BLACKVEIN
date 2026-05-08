"""World Engine Langfuse integration for distributed tracing."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from types import SimpleNamespace
from typing import Any, Iterator, Optional

from story_runtime_core.langfuse_tracing_environment import resolve_langfuse_environment

logger = logging.getLogger(__name__)

_active_span_context: ContextVar[Optional[Any]] = ContextVar("active_span", default=None)
_active_langfuse_client: ContextVar[Optional[Any]] = ContextVar("langfuse_client", default=None)


class LangfuseAdapter:
    """Singleton Langfuse adapter for world-engine story execution tracing."""

    _instance: Optional[LangfuseAdapter] = None

    def __init__(self):
        self.is_ready = False
        self._clients: dict[str, Any] = {}
        self._public_key = ""
        self._secret_key = ""
        self._base_url = "https://cloud.langfuse.com"
        self._release = "unknown"
        self._sample_rate = 1.0
        self._config = SimpleNamespace(
            environment=os.getenv("LANGFUSE_ENVIRONMENT", "development"),
            release=os.getenv("LANGFUSE_RELEASE", "unknown"),
            sample_rate=float(os.getenv("LANGFUSE_SAMPLE_RATE", "1.0")),
        )

        # Fetch runtime observability settings from the backend database.
        try:
            credentials = self._fetch_credentials_from_backend()
            if not credentials:
                logger.info("[LANGFUSE] Credentials not configured in backend")
                return
            if not credentials.get("enabled"):
                logger.info("[LANGFUSE] Disabled in backend settings")
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

            if not public_key or not secret_key:
                logger.info("[LANGFUSE] Credentials incomplete (missing key)")
                return

            self._public_key = public_key
            self._secret_key = secret_key
            self._base_url = base_url
            self._release = release
            self._sample_rate = sample_rate
            self.is_ready = True
            logger.info("[LANGFUSE] ✓ Credentials loaded; Langfuse clients are created per trace environment")
        except ImportError as e:
            logger.warning(f"[LANGFUSE] SDK not available: {e}")
        except Exception as e:
            logger.error(f"[LANGFUSE] Failed to initialize: {str(e)}", exc_info=True)

    @property
    def client(self) -> Any | None:
        """Default-environment client (backward compatibility)."""
        if not self.is_ready:
            return None
        return self._get_client(self._config.environment)

    def _get_client(self, environment: str | None) -> Any | None:
        """Return a Langfuse SDK client for ``environment`` (cached)."""
        if not self.is_ready or not self._public_key or not self._secret_key:
            return None
        env_key = (environment or self._config.environment or "development").strip() or "development"
        if env_key not in self._clients:
            try:
                from langfuse import Langfuse

                self._clients[env_key] = Langfuse(
                    public_key=self._public_key,
                    secret_key=self._secret_key,
                    base_url=self._base_url,
                    environment=env_key,
                    release=self._release,
                    sample_rate=self._sample_rate,
                )
                logger.info(f"[LANGFUSE] Created Langfuse client for environment={env_key!r}")
            except Exception as e:
                logger.error(f"[LANGFUSE] Failed to create client for {env_key!r}: {e}", exc_info=True)
                return None
        return self._clients.get(env_key)

    def _fetch_credentials_from_backend(self) -> Optional[dict[str, str]]:
        """Fetch Langfuse credentials from backend database."""
        try:
            import httpx
            backend_url = os.getenv("BACKEND_RUNTIME_CONFIG_URL") or os.getenv("BACKEND_INTERNAL_URL", "http://localhost:8000")
            internal_token = os.getenv("INTERNAL_RUNTIME_CONFIG_TOKEN", "")
            if not internal_token:
                logger.debug("[LANGFUSE] INTERNAL_RUNTIME_CONFIG_TOKEN not set; skipping credential fetch")
                return None
            endpoint = f"{backend_url}/api/v1/internal/observability/langfuse-credentials"
            with httpx.Client(timeout=5.0) as client:
                response = client.get(endpoint, headers={"X-Internal-Config-Token": internal_token})
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    logger.info("[LANGFUSE] Credentials fetched from backend: enabled=%s", data.get("enabled"))
                    return {
                        "enabled": bool(data.get("enabled")),
                        "public_key": data.get("public_key", ""),
                        "secret_key": data.get("secret_key", ""),
                        "base_url": data.get("base_url", "https://cloud.langfuse.com"),
                        "environment": data.get("environment", "development"),
                        "release": data.get("release", "unknown"),
                        "sample_rate": data.get("sample_rate", 1.0),
                    }
                logger.warning("[LANGFUSE] Backend credential endpoint returned %s", response.status_code)
        except Exception as e:
            logger.error("[LANGFUSE] Failed to fetch credentials from backend: %s", e, exc_info=True)
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
            trace_metadata = dict(metadata or {})
            trace_metadata.setdefault("session_id", session_id)
            env = resolve_langfuse_environment(
                trace_metadata.get("trace_origin"),
                trace_metadata.get("execution_tier"),
                default=str(self._config.environment or "development"),
            )
            trace_metadata.setdefault("wos_langfuse_environment", env)
            client = self._get_client(env)
            if not client:
                logger.warning("[LANGFUSE] start_trace skipped: no client for environment %r", env)
                return None

            # Use Langfuse SDK v4.x API: start_observation with as_type="span"
            span = client.start_observation(
                as_type="span",
                name=name,
                trace_context={"trace_id": trace_id} if trace_id else None,
                input=input or {"session_id": session_id},
                metadata=trace_metadata,
            )
            _active_langfuse_client.set(client)
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
            md = dict(metadata or {})
            env = resolve_langfuse_environment(
                md.get("trace_origin"),
                md.get("execution_tier"),
                default=str(self._config.environment or "development"),
            )
            md.setdefault("wos_langfuse_environment", env)
            client = self._get_client(env)
            if not client:
                logger.warning("[LANGFUSE] start_span_in_trace skipped: no client for environment %r", env)
                return None
            span = client.start_observation(
                as_type="span",
                name=name,
                trace_context={"trace_id": trace_id},
                input=input or {},
                metadata=md,
            )
            _active_langfuse_client.set(client)
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
        if span is None:
            _active_langfuse_client.set(None)
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
            lf_client = _active_langfuse_client.get() or self.client
            if trace_id and lf_client:
                meta = dict(metadata or {})
                meta.setdefault("score_attachment", "trace_duplicate")
                lf_client.create_score(
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

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton — flush existing clients then discard instance (for testing)."""
        if cls._instance is not None:
            for _env, c in list(cls._instance._clients.items()):
                try:
                    c.flush()
                except Exception:
                    pass
            cls._instance._clients.clear()
        cls._instance = None

    def shutdown(self) -> None:
        """Gracefully shutdown — flush all environment clients."""
        self.flush()
        self._clients.clear()

    def flush(self) -> None:
        """Flush pending traces to Langfuse."""
        if not self._clients:
            logger.warning("[LANGFUSE] Flush called but no Langfuse clients exist")
            return
        logger.info("[LANGFUSE] Flushing pending traces to Langfuse (%s environments)...", len(self._clients))
        for env_key, client in list(self._clients.items()):
            try:
                client.flush()
                logger.info("[LANGFUSE] Flush completed for environment=%r", env_key)
            except Exception as e:
                logger.error("[LANGFUSE] Failed to flush Langfuse traces (%r): %s", env_key, e, exc_info=True)
