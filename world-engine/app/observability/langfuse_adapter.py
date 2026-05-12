"""World Engine Langfuse integration for distributed tracing."""

from __future__ import annotations

import logging
import math
import os
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from types import SimpleNamespace
from typing import Any, Iterator, Optional

from story_runtime_core.langfuse_tracing_environment import resolve_langfuse_environment

logger = logging.getLogger(__name__)

_LANGFUSE_DEBUG_APPLIED = False
_LANGFUSE_DEBUG_HANDLER_ATTR = "_wos_langfuse_debug_handler"


def _wos_langfuse_diagnostic_env_enabled(var_name: str, *, default_when_unset: bool = True) -> bool:
    """Docker-compose uses ``${VAR:-1}``; a blank ``VAR=`` in ``.env`` can still yield an empty string in the container.

    Treat **unset** and **blank** like the compose default (on). Only explicit ``0`` / ``false`` / ``no`` / ``off``
    disables. Unknown non-empty strings fall back to ``default_when_unset``.
    """
    raw = os.getenv(var_name)
    if raw is None or str(raw).strip() == "":
        return default_when_unset
    s = str(raw).strip().lower()
    if s in {"0", "false", "no", "off"}:
        return False
    if s in {"1", "true", "yes", "on"}:
        return True
    return default_when_unset


def _langfuse_debug_handler_installed(lg: logging.Logger) -> bool:
    return any(getattr(h, _LANGFUSE_DEBUG_HANDLER_ATTR, False) for h in lg.handlers)


def _install_langfuse_sdk_debug_stream_handlers() -> None:
    """Attach DEBUG handlers so SDK `logger.debug(exception)` is visible under uvicorn (root INFO drops DEBUG)."""
    fmt = logging.Formatter("%(asctime)s %(levelname)s [langfuse-sdk] %(name)s %(message)s")
    for name in ("langfuse", "langfuse.api"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.DEBUG)
        if _langfuse_debug_handler_installed(lg):
            continue
        h = logging.StreamHandler()
        setattr(h, _LANGFUSE_DEBUG_HANDLER_ATTR, True)
        h.setLevel(logging.DEBUG)
        h.setFormatter(fmt)
        lg.addHandler(h)
        # Otherwise DEBUG records propagate to root and are filtered when root/uwicorn is INFO.
        lg.propagate = False


_LANGFUSE_INGESTION_ERROR_BRIDGE = False


def _align_langfuse_otel_resource_environment(backend_environment: str) -> bool:
    """Align process ``LANGFUSE_TRACING_ENVIRONMENT`` with live traces when backend uses ``staging``.

    The Langfuse Python SDK keeps one ``LangfuseResourceManager`` per ``public_key``; the **first**
    ``Langfuse(environment=...)`` call pins the OTEL resource attribute ``langfuse.environment`` for
    that process. Backend credentials often use ``environment=staging`` while ``resolve_langfuse_environment``
    maps ``live_ui`` + ``live`` to ``live`` for trace metadata and scores — that mismatch can yield
    ingestion 400/207 on score batches. If the operator has not set ``LANGFUSE_TRACING_ENVIRONMENT``,
    force it to ``live`` in the common staging-credentials + live-UI case.

    OTEL / SDK source: ``langfuse/_client/client.py`` (``LANGFUSE_TRACING_ENVIRONMENT``) and
    ``langfuse/_client/resource_manager.py`` (singleton ``_instances`` keyed by ``public_key``).

    Returns:
        True if this function set ``LANGFUSE_TRACING_ENVIRONMENT`` in the process environment.
    """
    if (os.getenv("LANGFUSE_TRACING_ENVIRONMENT") or "").strip():
        return False
    be = (backend_environment or "").strip().lower()
    if be != "staging":
        return False
    live_slug = resolve_langfuse_environment("live_ui", "live", default=backend_environment)
    if live_slug != "live":
        return False
    os.environ["LANGFUSE_TRACING_ENVIRONMENT"] = live_slug
    logger.warning(
        "[LANGFUSE] Backend credential environment is %r but live_ui+live maps to %r. "
        "LANGFUSE_TRACING_ENVIRONMENT was unset; set process env to %r so OTEL "
        "``langfuse.environment`` matches live session traces (Langfuse SDK singleton per public_key). "
        "To keep a different OTEL environment, set LANGFUSE_TRACING_ENVIRONMENT before starting play-service.",
        be,
        live_slug,
        live_slug,
    )
    return True


def _install_langfuse_ingestion_error_bridge() -> None:
    """Log Langfuse SDK score/API batch exceptions at WARNING with full ``APIError`` / ``APIErrors`` text.

    The SDK's ``handle_exception`` only logs generic messages at ERROR; details are on DEBUG. When
    ``WOS_LANGFUSE_INGESTION_ERROR_DETAIL`` is enabled (unset/blank defaults to on, like compose ``:-1``).

    ``score_ingestion_consumer`` does ``from ... import handle_exception`` (bound at import time), so we
    must also replace ``langfuse._task_manager.score_ingestion_consumer.handle_exception`` or the
    bridge would never run for score batches.
    """
    global _LANGFUSE_INGESTION_ERROR_BRIDGE
    if _LANGFUSE_INGESTION_ERROR_BRIDGE:
        return
    if not _wos_langfuse_diagnostic_env_enabled("WOS_LANGFUSE_INGESTION_ERROR_DETAIL", default_when_unset=True):
        return
    try:
        from langfuse._task_manager import score_ingestion_consumer as _lf_score_consumer
        from langfuse._utils import parse_error as _lf_parse_error
        from langfuse._utils.request import APIError, APIErrors

        _orig = _lf_parse_error.handle_exception

        def _wos_handle_exception(exc: BaseException) -> None:
            _orig(exc)
            if isinstance(exc, APIErrors):
                logger.warning("[LANGFUSE] SDK batch/APIErrors detail: %s", exc)
            elif isinstance(exc, APIError):
                logger.warning("[LANGFUSE] SDK APIError detail: %s", exc)

        _lf_parse_error.handle_exception = _wos_handle_exception  # type: ignore[assignment]
        _lf_score_consumer.handle_exception = _wos_handle_exception  # type: ignore[assignment]
        _LANGFUSE_INGESTION_ERROR_BRIDGE = True
        logger.info("[LANGFUSE] Ingestion error detail bridge installed (WOS_LANGFUSE_INGESTION_ERROR_DETAIL)")
    except Exception as e:
        logger.debug("[LANGFUSE] Failed to install ingestion error bridge: %s", e, exc_info=True)


def _apply_langfuse_debug_env() -> None:
    """Raise Langfuse SDK log level when WOS_LANGFUSE_DEBUG or LANGFUSE_DEBUG is truthy."""
    global _LANGFUSE_DEBUG_APPLIED
    if _LANGFUSE_DEBUG_APPLIED:
        return
    raw = (os.getenv("WOS_LANGFUSE_DEBUG") or os.getenv("LANGFUSE_DEBUG") or "").strip().lower()
    if raw not in {"1", "true", "yes", "debug"}:
        return
    _LANGFUSE_DEBUG_APPLIED = True
    _install_langfuse_sdk_debug_stream_handlers()
    logger.info(
        "[LANGFUSE] Debug logging enabled for langfuse SDK loggers "
        "(WOS_LANGFUSE_DEBUG/LANGFUSE_DEBUG); DEBUG lines include batch/API exception details"
    )


def _langfuse_sdk_exc_detail(exc: BaseException) -> str:
    parts: list[str] = [f"{type(exc).__name__}: {exc}"]
    resp = getattr(exc, "response", None)
    if resp is not None:
        try:
            body = (resp.text or "").strip()
            if body:
                parts.append(f"http_body={body[:1200]}")
        except Exception:
            parts.append("http_body=<unreadable>")
    return " | ".join(parts)[:2000]


def _langfuse_sanitize_value(
    val: Any,
    *,
    max_str: int = 12000,
    max_list: int = 80,
    max_dict: int = 80,
    depth: int = 0,
) -> Any:
    """Bound size/depth for Langfuse observation payloads (avoid 400 from oversized JSON)."""
    if depth > 8:
        return "<max_depth>"
    if val is None or isinstance(val, (bool, int, float)):
        if isinstance(val, float) and not math.isfinite(val):
            return None
        return val
    if isinstance(val, str):
        if len(val) > max_str:
            return val[:max_str] + "…"
        return val
    if isinstance(val, dict):
        out: dict[str, Any] = {}
        for i, (k, v) in enumerate(val.items()):
            if i >= max_dict:
                out["_truncated_keys"] = len(val) - max_dict
                break
            key = str(k)[:256]
            out[key] = _langfuse_sanitize_value(v, max_str=max_str, max_list=max_list, max_dict=max_dict, depth=depth + 1)
        return out
    if isinstance(val, (list, tuple)):
        seq = list(val)[:max_list]
        return [_langfuse_sanitize_value(v, max_str=max_str, max_list=max_list, max_dict=max_dict, depth=depth + 1) for v in seq]
    return str(val)[:max_str]

_active_span_context: ContextVar[Optional[Any]] = ContextVar("active_span", default=None)
_active_langfuse_client: ContextVar[Optional[Any]] = ContextVar("langfuse_client", default=None)
_active_langfuse_session_id: ContextVar[Optional[str]] = ContextVar("langfuse_session_id", default=None)
_span_context_registry: dict[int, tuple[Optional[Any], Optional[str]]] = {}


class LangfuseAdapter:
    """Singleton Langfuse adapter for world-engine story execution tracing."""

    _instance: Optional[LangfuseAdapter] = None

    def __init__(self):
        _apply_langfuse_debug_env()
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
            aligned = _align_langfuse_otel_resource_environment(str(self._config.environment))
            _install_langfuse_ingestion_error_bridge()
            if aligned:
                try:
                    # First Langfuse() for this public_key pins OTEL resource; prefer live client first.
                    self._get_client(
                        resolve_langfuse_environment("live_ui", "live", default=str(self._config.environment))
                    )
                except Exception:
                    logger.debug("[LANGFUSE] Eager Langfuse client init failed", exc_info=True)
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

            safe_sid = self._safe_session_id(session_id)

            def _create_root():
                return client.start_observation(
                    as_type="span",
                    name=name,
                    trace_context={"trace_id": trace_id} if trace_id else None,
                    input=input or {"session_id": session_id},
                    metadata=trace_metadata,
                )

            if safe_sid:
                from langfuse import propagate_attributes

                with propagate_attributes(session_id=safe_sid, trace_name=name):
                    span = _create_root()
            else:
                span = _create_root()
            _active_langfuse_client.set(client)
            _active_langfuse_session_id.set(safe_sid)
            _span_context_registry[id(span)] = (client, safe_sid)
            logger.info(f"[LANGFUSE] root span created: name={name}, session_id={session_id}, span_id={getattr(span, 'span_id', 'unknown')}, trace_id={getattr(span, 'trace_id', 'unknown')}")
            return span
        except Exception as e:
            logger.error("[LANGFUSE] Failed to start trace: %s", _langfuse_sdk_exc_detail(e), exc_info=True)
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
            safe_sid = self._safe_session_id(md.get("session_id"))

            def _create_joined():
                return client.start_observation(
                    as_type="span",
                    name=name,
                    trace_context={"trace_id": trace_id},
                    input=input or {},
                    metadata=md,
                )

            if safe_sid:
                from langfuse import propagate_attributes

                with propagate_attributes(session_id=safe_sid, trace_name=name):
                    span = _create_joined()
            else:
                span = _create_joined()
            _active_langfuse_client.set(client)
            _active_langfuse_session_id.set(safe_sid)
            _span_context_registry[id(span)] = (client, safe_sid)
            logger.info(f"[LANGFUSE] span created in trace: name={name}, trace_id={trace_id}")
            return span
        except Exception as e:
            logger.error("[LANGFUSE] Failed to create span in trace %r: %s", trace_id, _langfuse_sdk_exc_detail(e), exc_info=True)
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

        token = _active_langfuse_session_id.set(safe_session_id)
        if otel_span is not None:
            try:
                with otel_trace_api.use_span(otel_span, end_on_exit=False):
                    with propagate:
                        yield
            finally:
                _active_langfuse_session_id.reset(token)
        else:
            try:
                with propagate:
                    yield
            finally:
                _active_langfuse_session_id.reset(token)

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
            _active_langfuse_session_id.set(None)
        else:
            client, session_id = _span_context_registry.get(
                id(span),
                (_active_langfuse_client.get(), _active_langfuse_session_id.get()),
            )
            _active_langfuse_client.set(client)
            _active_langfuse_session_id.set(session_id)
        span_name = getattr(span, 'name', 'unknown') if span else None
        span_id = getattr(span, 'span_id', 'unknown') if span else None
        logger.info(f"[LANGFUSE] set_active_span: name={span_name}, span_id={span_id}")
        _active_span_context.set(span)

    def _metadata_with_active_session(self, metadata: Optional[dict[str, Any]]) -> dict[str, Any]:
        """Attach the active Langfuse session id to observation metadata when absent."""
        md = dict(metadata or {})
        active_session_id = _active_langfuse_session_id.get()
        if active_session_id:
            md.setdefault("session_id", active_session_id)
            md.setdefault("langfuse_session_id", active_session_id)
        return md

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
            safe_in = _langfuse_sanitize_value(input or {})
            safe_out = _langfuse_sanitize_value(output or {})
            child_span = parent_span.start_observation(
                as_type=as_type,
                name=name,
                input=safe_in,
                output=safe_out,
                metadata=self._metadata_with_active_session(metadata),
                level=level,  # type: ignore[arg-type]
                status_message=status_message,
            )
            _span_context_registry[id(child_span)] = (
                _active_langfuse_client.get(),
                _active_langfuse_session_id.get(),
            )
            logger.info(f"[LANGFUSE] child span created: name={name}, span_id={getattr(child_span, 'span_id', 'unknown')}, parent_span_id={getattr(parent_span, 'span_id', 'unknown')}")
            return child_span
        except Exception as e:
            logger.error("[LANGFUSE] Failed to create child span %r: %s", name, _langfuse_sdk_exc_detail(e), exc_info=True)
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
        provided_model_name: Optional[str] = None,
        prompt_name: Optional[str] = None,
        latency_ms: Optional[float] = None,
        time_to_first_token_ms: Optional[float] = None,
        tokens_per_second: Optional[float] = None,
    ) -> Optional[Any]:
        """Record a Langfuse generation observation under the active story span."""
        if not self.is_enabled():
            return None
        parent_span = _active_span_context.get()
        if not parent_span:
            logger.warning(f"[LANGFUSE] No active parent span to record generation '{name}'")
            return None
        try:
            resolved_model = (provided_model_name or model or "").strip() or model
            gen_metadata: dict[str, Any] = {
                **(metadata or {}),
                "model": resolved_model,
                "provider": provider,
                "provided_model_name": (provided_model_name or model or "").strip() or None,
            }
            gen_metadata = self._metadata_with_active_session(gen_metadata)
            if prompt_name:
                gen_metadata["langfuse_prompt_name"] = prompt_name
            if latency_ms is not None:
                gen_metadata["generation_latency_ms"] = latency_ms
            if time_to_first_token_ms is not None:
                gen_metadata["time_to_first_token_ms"] = time_to_first_token_ms
            if tokens_per_second is not None:
                gen_metadata["tokens_per_second_output"] = tokens_per_second
            safe_prompt = _langfuse_sanitize_value({"prompt": prompt} if prompt else {})
            generation = parent_span.start_observation(
                as_type="generation",
                name=name,
                model=resolved_model,
                input=safe_prompt,
                metadata=gen_metadata,
            )
            update_kwargs: dict[str, Any] = {
                "output": _langfuse_sanitize_value({"completion": completion} if completion else {}),
                "model": resolved_model,
            }
            if isinstance(usage_details, dict) and usage_details:
                # Langfuse expects int counts; keys typically input / output / total.
                ud: dict[str, int] = {}
                for k in ("input", "output", "total"):
                    if k in usage_details and usage_details[k] is not None:
                        try:
                            ud[k] = int(usage_details[k])
                        except (TypeError, ValueError):
                            pass
                if ud:
                    update_kwargs["usage_details"] = ud
            generation.update(**update_kwargs)
            generation.end()
            logger.info(f"[LANGFUSE] generation observation recorded: name={name}, model={resolved_model}")
            return generation
        except Exception as e:
            logger.error("[LANGFUSE] Failed to record generation %r: %s", name, _langfuse_sdk_exc_detail(e), exc_info=True)
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
                input=_langfuse_sanitize_value({"query": query} if query else {}),
                metadata=self._metadata_with_active_session({
                    **(metadata or {}),
                    "document_count": len(documents or []),
                }),
            )
            retrieval.update(output=_langfuse_sanitize_value({"documents": documents or []}))
            retrieval.end()
            logger.info(f"[LANGFUSE] retriever observation recorded: name={name}, documents={len(documents or [])}")
            return retrieval
        except Exception as e:
            logger.error("[LANGFUSE] Failed to record retrieval %r: %s", name, _langfuse_sdk_exc_detail(e), exc_info=True)
            return None

    @staticmethod
    def _normalize_trace_id_for_score_api(trace_id: object) -> str | None:
        """Return W3C-style 32-char lowercase hex trace id, or None if ``trace_id`` is unusable for Langfuse APIs.

        Langfuse ingestion and ``create_score`` reject arbitrary strings; invalid ids produced
        HTTP 207/400 score batches (generic Bad request at ERROR, details on DEBUG).
        """
        raw = str(trace_id or "").strip()
        if not raw:
            return None
        if len(raw) == 32 and all(c in "0123456789abcdefABCDEF" for c in raw):
            return raw.lower()
        if len(raw) == 36 and raw.count("-") == 4:
            collapsed = raw.replace("-", "").lower()
            if len(collapsed) == 32 and all(c in "0123456789abcdef" for c in collapsed):
                return collapsed
            return None
        return None

    @staticmethod
    def _coerce_score_value(value: float) -> float | None:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(v):
            return None
        return v

    @staticmethod
    def _observation_id_from_span_for_score(parent_span: object) -> str | None:
        """Return a string observation id for ``create_score``; ignore unittest mocks / non-strings."""
        oid = getattr(parent_span, "id", None)
        if oid is None:
            oid = getattr(parent_span, "observation_id", None)
        try:
            from unittest.mock import MagicMock, NonCallableMagicMock

            if isinstance(oid, (MagicMock, NonCallableMagicMock)):
                return None
        except Exception:
            pass
        if isinstance(oid, str):
            s = oid.strip()
            return s or None
        return None

    @staticmethod
    def _normalize_langfuse_create_score_scope_kwargs(
        kw: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, str]:
        """Enforce Langfuse rule: exactly one of traceId (+ optional observationId), sessionId, or datasetRunId.

        Returns ``(payload, emitted_scope)`` where ``emitted_scope`` is one of
        ``trace``, ``observation``, ``session``, ``dataset``, or ``skipped``.
        When ``skipped``, ``payload`` is ``None`` and the caller must not call ``create_score``.
        """
        base = dict(kw)
        tid = base.pop("trace_id", None)
        oid = base.pop("observation_id", None)
        sid = base.pop("session_id", None)
        drid = base.pop("dataset_run_id", None)

        def _present(x: object) -> bool:
            if x is None:
                return False
            if isinstance(x, str):
                return bool(x.strip())
            return True

        if _present(drid):
            base["dataset_run_id"] = drid
            return base, "dataset"
        if _present(tid):
            base["trace_id"] = tid
            if _present(oid):
                base["observation_id"] = oid
                return base, "observation"
            return base, "trace"
        if _present(sid):
            base["session_id"] = sid
            return base, "session"
        if _present(oid):
            return None, "skipped"
        return None, "skipped"

    @staticmethod
    def _log_wos_langfuse_score_scope_debug(
        score_name: str,
        *,
        has_trace_id: bool,
        has_observation_id: bool,
        had_session_before_norm: bool,
        emitted_scope: str,
    ) -> None:
        if not _wos_langfuse_diagnostic_env_enabled("WOS_LANGFUSE_SCORE_DEBUG", default_when_unset=True):
            return
        # Use INFO so play-service default (uvicorn/root INFO) still shows lines when this flag is on.
        logger.info(
            "[LANGFUSE] score_scope name=%r has_trace_id=%s has_observation_id=%s "
            "has_session_id_before_normalization=%s emitted_scope=%s",
            score_name,
            has_trace_id,
            has_observation_id,
            had_session_before_norm,
            emitted_scope,
        )

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
        coerced = self._coerce_score_value(value)
        if coerced is None:
            logger.warning("[LANGFUSE] Skipping score %r: non-finite or invalid value %r", name, value)
            return
        try:
            from langfuse.api import ScoreDataType
        except Exception as e:
            logger.error("[LANGFUSE] Langfuse ScoreDataType import failed: %s", e, exc_info=True)
            return
        try:
            score_metadata = self._metadata_with_active_session(metadata)
            safe_score_metadata = _langfuse_sanitize_value(
                score_metadata,
                max_str=4000,
                max_list=40,
                max_dict=40,
            )
            parent_span.score(
                name=name,
                value=coerced,
                comment=comment,
                metadata=safe_score_metadata,
                data_type=ScoreDataType.NUMERIC,
            )
        except Exception as e:
            logger.error("[LANGFUSE] Failed to add score %r: %s", name, _langfuse_sdk_exc_detail(e), exc_info=True)
            return
        # Trace-level duplicate: Langfuse UI / trace JSON export `trace.scores` list trace-level
        # scores; `span.score()` attaches to the observation only (see ADR-0033 §13.5).
        if (os.getenv("LANGFUSE_SKIP_TRACE_LEVEL_CREATE_SCORE") or "").strip().lower() in {"1", "true", "yes"}:
            return
        try:
            lf_client = _active_langfuse_client.get() or self.client
            tid = self._normalize_trace_id_for_score_api(trace_id)
            if tid and lf_client:
                meta = dict(safe_score_metadata) if isinstance(safe_score_metadata, dict) else {}
                meta.setdefault("score_attachment", "trace_duplicate")
                safe_trace_meta = _langfuse_sanitize_value(
                    meta,
                    max_str=4000,
                    max_list=40,
                    max_dict=40,
                )
                score_session_id = self._safe_session_id(meta.get("session_id"))
                obs_for_score = self._observation_id_from_span_for_score(parent_span)
                create_kw: dict[str, Any] = {
                    "name": name,
                    "value": coerced,
                    "trace_id": tid,
                    "comment": comment,
                    "metadata": safe_trace_meta,
                    "data_type": ScoreDataType.NUMERIC,
                }
                if obs_for_score:
                    create_kw["observation_id"] = obs_for_score
                # Langfuse rejects trace_id + session_id together; session stays in metadata only.
                normed, emitted_scope = self._normalize_langfuse_create_score_scope_kwargs(create_kw)
                self._log_wos_langfuse_score_scope_debug(
                    name,
                    has_trace_id=True,
                    has_observation_id=bool(obs_for_score),
                    had_session_before_norm=bool(score_session_id),
                    emitted_scope=emitted_scope,
                )
                if normed is None:
                    logger.warning(
                        "[LANGFUSE] Skipping create_score for %r after scope normalization (scope=%s)",
                        name,
                        emitted_scope,
                    )
                else:
                    lf_client.create_score(**normed)
            elif lf_client and not tid:
                logger.warning(
                    "[LANGFUSE] Skipping trace-level create_score for %r: invalid or non-W3C trace_id %r",
                    name,
                    trace_id,
                )
        except Exception as e:
            logger.warning(
                "[LANGFUSE] Trace-level create_score failed for %r: %s",
                name,
                _langfuse_sdk_exc_detail(e),
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
