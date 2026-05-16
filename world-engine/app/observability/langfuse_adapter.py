"""World Engine Langfuse integration for distributed tracing."""

from __future__ import annotations

import json
import logging
import math
import os
import time
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from types import SimpleNamespace
from typing import Any, Iterator, Optional

from story_runtime_core.langfuse_tracing_environment import (
    local_langfuse_evidence_metadata,
    resolve_langfuse_environment,
)
from story_runtime_core.observability_tree_policy import (
    classify_observation_tree,
    normalize_enabled_observation_trees,
    should_emit_observation,
)

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
    """If ``LANGFUSE_TRACING_ENVIRONMENT`` is unset, pin OTEL to backend observability ``environment``.

    The Langfuse Python SDK keeps one ``LangfuseResourceManager`` per ``public_key``; the **first**
    ``Langfuse(environment=...)`` call pins the OTEL resource attribute ``langfuse.environment`` for
    that process. We align the process env with the same string the backend stores for observability
    so ingestion and the SDK stay consistent.

    Returns:
        True if this function set ``LANGFUSE_TRACING_ENVIRONMENT`` in the process environment.
    """
    if (os.getenv("LANGFUSE_TRACING_ENVIRONMENT") or "").strip():
        return False
    be = (backend_environment or "").strip()
    if not be:
        return False
    os.environ["LANGFUSE_TRACING_ENVIRONMENT"] = be
    logger.info(
        "[LANGFUSE] LANGFUSE_TRACING_ENVIRONMENT was unset; set to backend observability environment %r "
        "so OTEL ``langfuse.environment`` matches the Langfuse client (SDK singleton per public_key). "
        "Override anytime by setting LANGFUSE_TRACING_ENVIRONMENT before starting play-service.",
        be,
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

# Langfuse Python SDK v4 often does not populate public ``span_id`` on in-memory observation handles
# until after flush; ``id`` / ``observation_id`` may also be absent pre-export. Logs must not imply failure.
_LANGFUSE_ID_UNAVAILABLE = "unavailable_from_sdk_object"


def _lf_sdk_public_observation_id(span: object) -> Optional[str]:
    """Return a non-empty Langfuse observation id string when exposed by the SDK object."""
    for attr in ("id", "observation_id", "span_id"):
        val = getattr(span, attr, None)
        if val is None:
            continue
        try:
            from unittest.mock import MagicMock, NonCallableMagicMock

            if isinstance(val, (MagicMock, NonCallableMagicMock)):
                continue
        except Exception:
            pass
        if isinstance(val, str):
            s = val.strip()
            if s:
                return s
    return None


def _lf_trace_ref_for_log(span: Optional[object]) -> str:
    tid = getattr(span, "trace_id", None) if span is not None else None
    if isinstance(tid, str) and tid.strip():
        return tid.strip()
    return _LANGFUSE_ID_UNAVAILABLE


def _lf_json_log_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, default=str, separators=(",", ":"))


class LangfuseAdapter:
    """Singleton Langfuse adapter for world-engine story execution tracing."""

    _instance: Optional[LangfuseAdapter] = None
    _OBSERVATION_TREE_POLICY_VERSION = "observability_tree_policy.v1"

    def __init__(self):
        _apply_langfuse_debug_env()
        self.is_ready = False
        self._clients: dict[str, Any] = {}
        self._public_key = ""
        self._secret_key = ""
        self._base_url = "https://cloud.langfuse.com"
        self._release = "unknown"
        self._sample_rate = 1.0
        self._enabled_observation_trees = normalize_enabled_observation_trees(None)
        self._config = SimpleNamespace(
            environment=os.getenv("LANGFUSE_ENVIRONMENT", "development"),
            release=os.getenv("LANGFUSE_RELEASE", "unknown"),
            sample_rate=float(os.getenv("LANGFUSE_SAMPLE_RATE", "1.0")),
            enabled_observation_trees=list(self._enabled_observation_trees),
        )
        self._last_backend_config_refresh_monotonic = 0.0
        self._backend_config_refresh_interval_s = self._read_backend_config_refresh_interval()

        # Fetch runtime observability settings from the backend database.
        try:
            self.refresh_backend_config(force=True)
        except ImportError as e:
            logger.warning(f"[LANGFUSE] SDK not available: {e}")
        except Exception as e:
            logger.error(f"[LANGFUSE] Failed to initialize: {str(e)}", exc_info=True)

    @property
    def client(self) -> Any | None:
        """Default-environment client (backward compatibility)."""
        if hasattr(self, "_last_backend_config_refresh_monotonic"):
            self.refresh_backend_config()
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

    def _fetch_credentials_from_backend(self) -> Optional[dict[str, Any]]:
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
                        "enabled_observation_trees": data.get("enabled_observation_trees"),
                    }
                logger.warning("[LANGFUSE] Backend credential endpoint returned %s", response.status_code)
        except Exception as e:
            logger.error("[LANGFUSE] Failed to fetch credentials from backend: %s", e, exc_info=True)
        return None

    @staticmethod
    def _read_backend_config_refresh_interval() -> float:
        raw = os.getenv("WOS_LANGFUSE_CONFIG_REFRESH_SECONDS", "30")
        try:
            return max(0.0, float(raw))
        except (TypeError, ValueError):
            logger.warning("[LANGFUSE] Invalid WOS_LANGFUSE_CONFIG_REFRESH_SECONDS=%r; using 30 seconds", raw)
            return 30.0

    @staticmethod
    def _coerce_sample_rate(value: Any) -> float:
        fallback = os.getenv("LANGFUSE_SAMPLE_RATE", "1.0")
        try:
            return float(value if value is not None and value != "" else fallback)
        except (TypeError, ValueError):
            logger.warning("[LANGFUSE] Invalid sample_rate=%r; using %r", value, fallback)
            try:
                return float(fallback)
            except (TypeError, ValueError):
                return 1.0

    def _flush_and_clear_clients(self) -> None:
        for env_key, client in list(getattr(self, "_clients", {}).items()):
            try:
                client.flush()
            except Exception:
                logger.debug("[LANGFUSE] Failed to flush client before config refresh (%r)", env_key, exc_info=True)
        self._clients.clear()

    def _mark_not_ready(self, reason: str) -> None:
        if getattr(self, "is_ready", False) or getattr(self, "_clients", None):
            self._flush_and_clear_clients()
        self.is_ready = False
        logger.info("[LANGFUSE] Adapter not ready: %s", reason)

    def _apply_backend_credentials(self, credentials: dict[str, Any]) -> None:
        enabled_observation_trees = normalize_enabled_observation_trees(
            credentials.get("enabled_observation_trees")
        )
        previous_trees = list(getattr(self, "_enabled_observation_trees", []))
        tree_config_changed = list(enabled_observation_trees) != previous_trees
        self._enabled_observation_trees = list(enabled_observation_trees)
        self._config.enabled_observation_trees = list(enabled_observation_trees)

        if not credentials.get("enabled"):
            self._mark_not_ready("disabled in backend settings")
            return

        public_key = str(credentials.get("public_key") or "").strip()
        secret_key = str(credentials.get("secret_key") or "").strip()
        base_url = str(credentials.get("base_url") or "https://cloud.langfuse.com").strip()
        environment = credentials.get("environment") or os.getenv("LANGFUSE_ENVIRONMENT", "development")
        release = credentials.get("release") or os.getenv("LANGFUSE_RELEASE", "unknown")
        sample_rate = self._coerce_sample_rate(credentials.get("sample_rate"))

        self._config.environment = environment
        self._config.release = release
        self._config.sample_rate = sample_rate

        if not public_key or not secret_key:
            self._mark_not_ready("credentials incomplete (missing key)")
            return

        client_config_changed = (
            public_key != self._public_key
            or secret_key != self._secret_key
            or base_url != self._base_url
            or release != self._release
            or sample_rate != self._sample_rate
        )
        was_ready = bool(getattr(self, "is_ready", False))
        if client_config_changed and self._clients:
            self._flush_and_clear_clients()

        self._public_key = public_key
        self._secret_key = secret_key
        self._base_url = base_url
        self._release = str(release)
        self._sample_rate = sample_rate
        self.is_ready = True

        if not was_ready or client_config_changed or tree_config_changed:
            logger.info(
                "[LANGFUSE] Credentials loaded/refreshed; environment=%r, trees=%s",
                str(self._config.environment),
                ",".join(self._enabled_observation_trees),
            )
        _align_langfuse_otel_resource_environment(str(self._config.environment))
        _install_langfuse_ingestion_error_bridge()
        try:
            # First Langfuse() for this public_key pins OTEL resource; use backend observability env only.
            self._get_client(str(self._config.environment).strip() or "development")
        except Exception:
            logger.debug("[LANGFUSE] Eager Langfuse client init failed", exc_info=True)

    def refresh_backend_config(self, *, force: bool = False) -> None:
        """Refresh backend-driven Langfuse settings so the long-lived engine process does not stay stale."""
        now = time.monotonic()
        last = float(getattr(self, "_last_backend_config_refresh_monotonic", 0.0) or 0.0)
        interval = float(getattr(self, "_backend_config_refresh_interval_s", 30.0) or 0.0)
        if not force and last > 0.0 and (now - last) < interval:
            return

        self._last_backend_config_refresh_monotonic = now
        credentials = self._fetch_credentials_from_backend()
        if not credentials:
            logger.info("[LANGFUSE] Credentials not configured in backend")
            return
        self._apply_backend_credentials(credentials)

    @classmethod
    def get_instance(cls) -> LangfuseAdapter:
        if cls._instance is None:
            cls._instance = LangfuseAdapter()
        elif hasattr(cls._instance, "_last_backend_config_refresh_monotonic"):
            cls._instance.refresh_backend_config()
        return cls._instance

    def is_enabled(self) -> bool:
        """Check if Langfuse is ready to trace."""
        if hasattr(self, "_last_backend_config_refresh_monotonic"):
            self.refresh_backend_config(force=not bool(getattr(self, "is_ready", False)))
        if not self.is_ready:
            return False
        return self._get_client(self._config.environment) is not None

    def _effective_observation_trees(self) -> list[str]:
        return normalize_enabled_observation_trees(
            getattr(
                self,
                "_enabled_observation_trees",
                getattr(getattr(self, "_config", None), "enabled_observation_trees", None),
            )
        )

    def _with_observation_policy_metadata(
        self,
        metadata: Optional[dict[str, Any]],
        *,
        observation_name: str | None = None,
        as_type: str | None = None,
    ) -> dict[str, Any]:
        md = dict(metadata or {})
        enabled_trees = self._effective_observation_trees()
        md.setdefault("enabled_observation_trees", list(enabled_trees))
        md.setdefault("observation_tree_policy_version", self._OBSERVATION_TREE_POLICY_VERSION)
        if observation_name:
            md.setdefault(
                "observation_tree_id",
                classify_observation_tree(observation_name, as_type=as_type, metadata=md),
            )
        local_meta = local_langfuse_evidence_metadata()
        if local_meta:
            md.update(local_meta)
        return md

    def is_observation_enabled(
        self,
        name: str,
        *,
        as_type: str | None = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Return whether an optional child observation is enabled by policy."""
        missing = object()
        configured = getattr(self, "_enabled_observation_trees", missing)
        if configured is missing:
            configured = getattr(getattr(self, "_config", None), "enabled_observation_trees", missing)
        if configured is missing:
            return True
        return should_emit_observation(configured, name, as_type=as_type, metadata=metadata)

    def start_trace(
        self,
        name: str,
        session_id: str,
        input: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> Optional[Any]:
        """Start a new trace root span (Langfuse SDK v4.x API)."""
        if hasattr(self, "_last_backend_config_refresh_monotonic"):
            self.refresh_backend_config(force=True)
        if not self.is_enabled():
            logger.info(f"[LANGFUSE] start_trace skipped: adapter not enabled")
            return None

        try:
            trace_metadata = self._with_observation_policy_metadata(metadata)
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
        if hasattr(self, "_last_backend_config_refresh_monotonic"):
            self.refresh_backend_config(force=True)
        if not self.is_enabled():
            logger.info("[LANGFUSE] start_span_in_trace skipped: adapter not enabled")
            return None
        try:
            md = self._with_observation_policy_metadata(metadata)
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

    def resolve_parent_observation_for_nested_span(self) -> Optional[Any]:
        """Return the active Langfuse observation for best-effort nested spans.

        Shared ai_stack helpers call this method from both backend and
        world-engine contexts. World-engine keeps only the active observation in
        a ContextVar, so there is no separate root-trace fallback here.
        """
        return self.get_active_span()

    def record_wos_nested_span_observation(
        self,
        *,
        name: str,
        metadata: Optional[dict[str, Any]] = None,
        input_data: Optional[dict[str, Any]] = None,
        output_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Emit a nested local-only evidence span without affecting turn flow."""
        out: dict[str, Any] = {
            "emitted": False,
            "observation_name": name,
            "proof_level": "local_only",
            "live_or_staging_evidence": False,
            "langfuse_trace_id": None,
            "langfuse_observation_id": None,
        }
        if not self.is_enabled():
            out["reason"] = "langfuse_disabled_or_not_ready"
            return out
        if not self.is_observation_enabled(name, as_type="span", metadata=metadata):
            out["reason"] = "observation_tree_disabled"
            return out

        parent = self.resolve_parent_observation_for_nested_span()
        if parent is None:
            out["reason"] = "no_active_langfuse_parent_observation"
            return out

        try:
            child = parent.start_observation(
                as_type="span",
                name=name,
                input=_langfuse_sanitize_value(input_data or {}),
                output=_langfuse_sanitize_value(output_data or {}),
                metadata=self._metadata_with_active_session(
                    self._with_observation_policy_metadata(
                        metadata,
                        observation_name=name,
                        as_type="span",
                    )
                ),
            )
            _span_context_registry[id(child)] = (
                _active_langfuse_client.get(),
                _active_langfuse_session_id.get(),
            )
            child.end()

            trace_id = (
                getattr(child, "trace_id", None)
                or getattr(child, "traceId", None)
                or getattr(parent, "trace_id", None)
                or getattr(parent, "traceId", None)
            )
            observation_id = _lf_sdk_public_observation_id(child)
            out["emitted"] = True
            if trace_id is not None:
                out["langfuse_trace_id"] = str(trace_id)
            if observation_id is not None:
                out["langfuse_observation_id"] = observation_id
            return out
        except Exception as exc:
            logger.warning(
                "[LANGFUSE] Failed to record nested evidence span %r: %s",
                name,
                _langfuse_sdk_exc_detail(exc),
                exc_info=True,
            )
            out["reason"] = f"langfuse_error:{type(exc).__name__}"
            return out

    def record_adr0041_langfuse_scores(
        self,
        *,
        scores: list[tuple[str, float]],
        comment: str,
    ) -> dict[str, Any]:
        """Attach ADR-0041 local-only diagnostic scores to the active span."""
        out: dict[str, Any] = {"emitted": False, "scores_attempted": len(scores)}
        if not self.is_enabled():
            out["reason"] = "langfuse_disabled_or_not_ready"
            return out
        if not self.is_observation_enabled("adr0041_langfuse_scores", as_type="score"):
            out["reason"] = "observation_tree_disabled"
            return out
        if self.resolve_parent_observation_for_nested_span() is None:
            out["reason"] = "no_active_langfuse_parent_observation"
            return out

        emitted = 0
        for score_name, score_value in scores:
            try:
                self.add_score(
                    name=score_name,
                    value=float(score_value),
                    comment=comment,
                    metadata={
                        "score_origin": "adr0041_runtime_intelligence",
                        "proof_level": "local_only",
                        "live_or_staging_evidence": False,
                    },
                )
                emitted += 1
            except Exception as exc:
                logger.warning(
                    "[LANGFUSE] Failed to record ADR-0041 score %r: %s",
                    score_name,
                    _langfuse_sdk_exc_detail(exc),
                    exc_info=True,
                )
        out["emitted"] = emitted == len(scores)
        out["scores_emitted"] = emitted
        if emitted != len(scores):
            out["reason"] = "score_emission_incomplete"
        return out

    def set_active_span(self, span: Optional[Any]) -> None:
        """Set the currently active span for child operations (thread-safe via ContextVar)."""
        if span is None:
            prev_span = _active_span_context.get()
            prev_sid = _active_langfuse_session_id.get()
            clear_payload = {
                "event": "langfuse_set_active_span",
                "cleared_active_span": True,
                "previous_local_span_ref": (f"active:py{id(prev_span):x}" if prev_span is not None else None),
                "previous_langfuse_span_id": (
                    _lf_sdk_public_observation_id(prev_span) if prev_span is not None else _LANGFUSE_ID_UNAVAILABLE
                ),
                "previous_trace_ref": _lf_trace_ref_for_log(prev_span),
                "previous_story_session_id": (prev_sid if prev_sid else _LANGFUSE_ID_UNAVAILABLE),
                "note": (
                    "active_span_cleared; langfuse_client_and_session_contextvars_also_cleared "
                    "(SDK observation ids may still be unavailable_from_sdk_object before flush)"
                ),
            }
            _active_langfuse_client.set(None)
            _active_langfuse_session_id.set(None)
            logger.info("[LANGFUSE] %s", _lf_json_log_line(clear_payload))
            _active_span_context.set(span)
            return

        client, session_id = _span_context_registry.get(
            id(span),
            (_active_langfuse_client.get(), _active_langfuse_session_id.get()),
        )
        _active_langfuse_client.set(client)
        _active_langfuse_session_id.set(session_id)
        lf_sid = _lf_sdk_public_observation_id(span)
        activate_payload = {
            "event": "langfuse_set_active_span",
            "cleared_active_span": False,
            "name": getattr(span, "name", None),
            "local_span_ref": f"active:py{id(span):x}",
            "langfuse_span_id": lf_sid or _LANGFUSE_ID_UNAVAILABLE,
            "langfuse_parent_span_id": (
                _lf_sdk_public_observation_id(getattr(span, "parent", None))
                or _LANGFUSE_ID_UNAVAILABLE
            ),
            "trace_ref": _lf_trace_ref_for_log(span),
            "story_session_id": (_active_langfuse_session_id.get() or _LANGFUSE_ID_UNAVAILABLE),
            "span_successfully_activated": True,
        }
        logger.info("[LANGFUSE] %s", _lf_json_log_line(activate_payload))
        _active_span_context.set(span)

    def _metadata_with_active_session(self, metadata: Optional[dict[str, Any]]) -> dict[str, Any]:
        """Attach the active Langfuse session id to observation metadata when absent."""
        md = dict(metadata or {})
        active_session_id = _active_langfuse_session_id.get()
        if active_session_id:
            md.setdefault("session_id", active_session_id)
            md.setdefault("langfuse_session_id", active_session_id)
        local_meta = local_langfuse_evidence_metadata()
        if local_meta:
            md.update(local_meta)
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
        if not self.is_observation_enabled(name, as_type=as_type, metadata=metadata):
            logger.debug("[LANGFUSE] create_child_span skipped by observation tree policy: %s", name)
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
                metadata=self._metadata_with_active_session(
                    self._with_observation_policy_metadata(
                        metadata,
                        observation_name=name,
                        as_type=as_type,
                    )
                ),
                level=level,  # type: ignore[arg-type]
                status_message=status_message,
            )
            _span_context_registry[id(child_span)] = (
                _active_langfuse_client.get(),
                _active_langfuse_session_id.get(),
            )
            md = metadata or {}
            child_lf = _lf_sdk_public_observation_id(child_span)
            parent_lf = _lf_sdk_public_observation_id(parent_span)
            created_payload = {
                "event": "langfuse_child_span_created",
                "name": name,
                "local_span_ref": f"{name}:py{id(child_span):x}",
                "parent_local_span_ref": f"parent:py{id(parent_span):x}",
                "langfuse_span_id": child_lf or _LANGFUSE_ID_UNAVAILABLE,
                "langfuse_parent_span_id": parent_lf or _LANGFUSE_ID_UNAVAILABLE,
                "trace_ref": _lf_trace_ref_for_log(parent_span),
                "story_session_id": (_active_langfuse_session_id.get() or _LANGFUSE_ID_UNAVAILABLE),
                "canonical_turn_id": md.get("canonical_turn_id"),
                "span_successfully_created": True,
            }
            logger.info("[LANGFUSE] %s", _lf_json_log_line(created_payload))
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
        if not self.is_observation_enabled(name, as_type="generation", metadata=metadata):
            logger.debug("[LANGFUSE] generation skipped by observation tree policy: %s", name)
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
            gen_metadata = self._with_observation_policy_metadata(
                gen_metadata,
                observation_name=name,
                as_type="generation",
            )
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
        if not self.is_observation_enabled(name, as_type="retriever", metadata=metadata):
            logger.debug("[LANGFUSE] retrieval skipped by observation tree policy: %s", name)
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
                metadata=self._metadata_with_active_session(
                    self._with_observation_policy_metadata(
                        {
                            **(metadata or {}),
                            "document_count": len(documents or []),
                        },
                        observation_name=name,
                        as_type="retriever",
                    )
                ),
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

    @staticmethod
    def _extract_trace_metadata_from_payload(payload: Any) -> dict[str, Any]:
        """Best-effort extraction of trace metadata from SDK/API payload objects."""
        if isinstance(payload, dict):
            md = payload.get("metadata")
            return dict(md) if isinstance(md, dict) else {}
        md = getattr(payload, "metadata", None)
        if isinstance(md, dict):
            return dict(md)
        return {}

    @staticmethod
    def _supports_trace_metadata_backfill_client(client: Any) -> bool:
        """Return whether ``client`` exposes any known trace update surface."""
        if callable(getattr(client, "update_trace", None)):
            return True
        if callable(getattr(client, "trace", None)):
            return True
        api = getattr(client, "api", None)
        trace_api = getattr(api, "trace", None) if api is not None else None
        if trace_api is not None and callable(getattr(trace_api, "update", None)):
            return True
        return False

    def _fetch_existing_trace_metadata(self, client: Any, trace_id: str) -> dict[str, Any]:
        """Read current trace metadata when the SDK/API exposes a getter."""
        # Prefer first-class client helpers if available.
        get_trace = getattr(client, "get_trace", None)
        if callable(get_trace):
            for kwargs in ({"trace_id": trace_id}, {"id": trace_id}):
                try:
                    payload = get_trace(**kwargs)
                    return self._extract_trace_metadata_from_payload(payload)
                except TypeError:
                    continue
                except Exception:
                    break
            try:
                payload = get_trace(trace_id)
                return self._extract_trace_metadata_from_payload(payload)
            except Exception:
                pass

        # Fallback: Langfuse generated API client.
        api = getattr(client, "api", None)
        trace_api = getattr(api, "trace", None) if api is not None else None
        get_fn = getattr(trace_api, "get", None) if trace_api is not None else None
        if callable(get_fn):
            for kwargs in ({"trace_id": trace_id}, {"id": trace_id}):
                try:
                    payload = get_fn(**kwargs)
                    return self._extract_trace_metadata_from_payload(payload)
                except TypeError:
                    continue
                except Exception:
                    break
            try:
                payload = get_fn(trace_id)
                return self._extract_trace_metadata_from_payload(payload)
            except Exception:
                pass
        return {}

    def backfill_trace_metadata(
        self,
        trace_id: str,
        metadata: dict[str, Any],
        *,
        environment: str | None = None,
    ) -> bool:
        """Best-effort trace metadata merge/update by ``trace_id``.

        Returns ``False`` when update surfaces are unavailable or an SDK call fails.
        This method is intentionally non-raising for runtime safety.
        """
        if not self.is_enabled():
            return False
        tid = self._normalize_trace_id_for_score_api(trace_id)
        if not tid:
            logger.info("[LANGFUSE] Trace metadata backfill skipped: invalid trace_id %r", trace_id)
            return False
        client = self._get_client(environment or self._config.environment) or self.client
        if client is None:
            logger.info("[LANGFUSE] Trace metadata backfill skipped: no client for environment %r", environment)
            return False
        if not self._supports_trace_metadata_backfill_client(client):
            return False

        safe_patch = _langfuse_sanitize_value(metadata, max_str=4000, max_list=40, max_dict=40)
        if not isinstance(safe_patch, dict):
            safe_patch = {}

        try:
            existing = self._fetch_existing_trace_metadata(client, tid)
            merged = {**existing, **safe_patch}

            update_trace = getattr(client, "update_trace", None)
            if callable(update_trace):
                for kwargs in ({"trace_id": tid, "metadata": merged}, {"id": tid, "metadata": merged}):
                    try:
                        update_trace(**kwargs)
                        return True
                    except TypeError:
                        continue
                update_trace(tid, merged)
                return True

            trace_accessor = getattr(client, "trace", None)
            if callable(trace_accessor):
                try:
                    trace_obj = trace_accessor(id=tid)
                except TypeError:
                    trace_obj = trace_accessor(tid)
                update_fn = getattr(trace_obj, "update", None)
                if callable(update_fn):
                    update_fn(metadata=merged)
                    return True

            api = getattr(client, "api", None)
            trace_api = getattr(api, "trace", None) if api is not None else None
            trace_update = getattr(trace_api, "update", None) if trace_api is not None else None
            if callable(trace_update):
                for kwargs in ({"trace_id": tid, "metadata": merged}, {"id": tid, "metadata": merged}):
                    try:
                        trace_update(**kwargs)
                        return True
                    except TypeError:
                        continue
                trace_update(tid, metadata=merged)
                return True
        except Exception as e:
            logger.warning(
                "[LANGFUSE] Trace metadata backfill failed for trace_id=%r: %s",
                tid,
                _langfuse_sdk_exc_detail(e),
                exc_info=True,
            )
            return False
        return False

    def backfill_trace_metadata_after_commit(
        self,
        *,
        trace_id: str | None,
        canonical_turn_id: str | None,
        story_session_id: str | None,
        turn_number: int | None,
        environment: str | None,
    ) -> dict[str, Any]:
        """Attempt post-commit trace metadata backfill with explicit diagnostics."""
        diag: dict[str, Any] = {
            "attempted": True,
            "supported": False,
            "success": False,
            "trace_id": str(trace_id or "").strip() or None,
            "metadata_keys": [],
            "reason": None,
        }
        if not self.is_enabled():
            diag["reason"] = "adapter_not_enabled"
            return diag
        tid = self._normalize_trace_id_for_score_api(trace_id)
        if not tid:
            diag["reason"] = "missing_or_invalid_trace_id"
            return diag
        if not canonical_turn_id:
            diag["reason"] = "missing_canonical_turn_id"
            return diag

        metadata: dict[str, Any] = {
            "canonical_turn_id": str(canonical_turn_id),
            "story_session_id": str(story_session_id or ""),
            "turn_number": int(turn_number) if turn_number is not None else None,
        }
        if environment:
            metadata["environment"] = str(environment)
        metadata = {k: v for k, v in metadata.items() if v is not None and str(v).strip() != ""}
        diag["metadata_keys"] = sorted(metadata.keys())

        client = self._get_client(environment or self._config.environment) or self.client
        if client is None:
            diag["reason"] = "client_unavailable"
            return diag
        if not self._supports_trace_metadata_backfill_client(client):
            diag["reason"] = "sdk_method_unavailable"
            return diag

        diag["supported"] = True
        ok = self.backfill_trace_metadata(tid, metadata, environment=environment)
        diag["success"] = bool(ok)
        diag["trace_id"] = tid
        if not ok:
            diag["reason"] = "backfill_failed"
        return diag

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
        if not self.is_observation_enabled(name, as_type="score", metadata=metadata):
            logger.debug("[LANGFUSE] score skipped by observation tree policy: %s", name)
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
