"""Canonical Langfuse observability adapter.

Provides unified tracing for AI/runtime behavior across backend, world-engine,
and ai_stack. Langfuse is optional and disabled by default.

Safe: no-op mode if disabled or credentials missing.
Secure: redacts secrets before sending.
Correlated: all traces linked to session/run/turn/module/scene.
"""

from __future__ import annotations

import os
import hashlib
from typing import Any, Optional
from functools import wraps
import logging
from datetime import datetime
from contextvars import ContextVar

from story_runtime_core.langfuse_tracing_environment import (
    local_langfuse_evidence_metadata,
    resolve_runtime_langfuse_base_url,
    resolve_langfuse_environment,
)
from story_runtime_core.observability_tree_policy import (
    normalize_enabled_observation_trees,
    should_emit_observation,
)

logger = logging.getLogger(__name__)

# Context variable for tracking active span
_active_span_context: ContextVar[Optional[Any]] = ContextVar('active_span', default=None)

# Attempt to import Langfuse; gracefully degrade if not available
try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None

# Optional: OpenAI integration (requires openai package)
try:
    from langfuse.openai import OpenAI as LangfuseOpenAI
except ImportError:
    LangfuseOpenAI = None


class LangfuseConfig:
    """Langfuse configuration from environment or database."""

    def __init__(self):
        db_config = self._get_config_from_db()
        self.enabled = bool(db_config.get("is_enabled"))
        self.public_key = self._get_credential_from_db("public_key") or ""
        self.secret_key = self._get_credential_from_db("secret_key") or ""

        self.base_url, self.base_url_source = resolve_runtime_langfuse_base_url(
            str(db_config.get("base_url") or "https://cloud.langfuse.com")
        )
        self.environment = str(db_config.get("environment") or "development")
        self.release = str(db_config.get("release") or "unknown")
        self.sample_rate = float(db_config.get("sample_rate") or 1.0)
        self.capture_prompts = bool(db_config.get("capture_prompts", True))
        self.capture_outputs = bool(db_config.get("capture_outputs", True))
        self.capture_retrieval = bool(db_config.get("capture_retrieval", False))
        self.redaction_mode = str(db_config.get("redaction_mode") or "strict")
        self.enabled_observation_trees = normalize_enabled_observation_trees(
            db_config.get("enabled_observation_trees")
        )

    @staticmethod
    def _get_config_from_db() -> dict[str, Any]:
        """Get Langfuse configuration from the governed runtime database."""
        try:
            from app.models.governance_core import ObservabilityConfig
            config = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
            if config:
                return {
                    "is_enabled": bool(config.is_enabled),
                    "base_url": config.base_url,
                    "environment": config.environment,
                    "release": config.release,
                    "sample_rate": config.sample_rate,
                    "capture_prompts": config.capture_prompts,
                    "capture_outputs": config.capture_outputs,
                    "capture_retrieval": config.capture_retrieval,
                    "redaction_mode": config.redaction_mode,
                    "enabled_observation_trees": getattr(config, "enabled_observation_trees", None),
                }
        except Exception:
            pass
        return {"is_enabled": False}

    @staticmethod
    def _get_credential_from_db(secret_name: str) -> Optional[str]:
        """Get credential from database (stored via admin tool)."""
        try:
            from app.services.observability_governance_service import get_observability_credential_for_runtime
            return get_observability_credential_for_runtime(secret_name)
        except Exception:
            return None

    @property
    def is_valid(self) -> bool:
        """Check if config is valid for enabled mode."""
        if not self.enabled:
            return True
        return bool(self.public_key and self.secret_key)

    @property
    def is_ready(self) -> bool:
        """Check if Langfuse is ready to use."""
        return self.enabled and self.is_valid and LANGFUSE_AVAILABLE


class LangfuseAdapter:
    """Canonical Langfuse tracing adapter.

    Provides safe, optional, correlated tracing for AI/runtime behavior.
    No-op if disabled or credentials missing.
    """

    _instance: Optional[LangfuseAdapter] = None

    def __init__(self, config: Optional[LangfuseConfig] = None):
        self.config = config or LangfuseConfig()
        self._clients: dict[str, Any] = {}
        self._active_trace: Optional[Any] = None
        self.is_ready: bool = bool(self.config.is_ready)

        if self.is_ready:
            logger.info(
                "Langfuse adapter ready (lazy clients per trace environment); default=%s @ %s",
                self.config.environment,
                self.config.base_url,
            )
        else:
            logger.info("Langfuse adapter not ready (disabled, invalid config, or SDK missing)")

    @classmethod
    def get_instance(cls, config: Optional[LangfuseConfig] = None) -> "LangfuseAdapter":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (useful for testing)."""
        if cls._instance is not None:
            for _env, client in list(cls._instance._clients.items()):
                try:
                    client.flush()
                except Exception:
                    pass
            cls._instance._clients.clear()
        cls._instance = None

    def is_enabled(self) -> bool:
        """Check if tracing is enabled and client is ready."""
        return self.is_ready

    def _get_client(self, environment: str | None) -> Optional[Any]:
        """Return a Langfuse SDK client for ``environment`` (cached)."""
        if not self.is_ready or not LANGFUSE_AVAILABLE or Langfuse is None:
            return None
        env_key = (environment or self.config.environment or "development").strip() or "development"
        if env_key not in self._clients:
            try:
                self._clients[env_key] = Langfuse(
                    public_key=self.config.public_key,
                    secret_key=self.config.secret_key,
                    base_url=self.config.base_url,
                    environment=env_key,
                    release=self.config.release,
                    sample_rate=self.config.sample_rate,
                )
                logger.info("Langfuse client created for environment=%r", env_key)
            except Exception as e:
                logger.exception("Failed to create Langfuse client for %r: %s", env_key, e)
                return None
        return self._clients.get(env_key)

    @property
    def client(self) -> Optional[Any]:
        """Default-environment client (backward compatibility)."""
        return self._get_client(self.config.environment)

    def _redact_value(self, value: Any, key: str = "") -> Any:
        """Redact sensitive values based on key patterns."""
        if not isinstance(value, str):
            return value

        key_lower = key.lower()
        sensitive_patterns = [
            "password", "token", "secret", "key", "auth",
            "credential", "apikey", "api_key", "bearer",
            "cookie", "session", "jwt", "oauth"
        ]

        if any(pattern in key_lower for pattern in sensitive_patterns):
            if len(value) > 4:
                return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
            return "***"

        return value

    def _sanitize_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Sanitize metadata to remove/redact sensitive values."""
        if not metadata or self.config.redaction_mode == "none":
            return metadata

        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, dict):
                sanitized[key] = self._sanitize_metadata(value)
            elif isinstance(value, (list, tuple)):
                sanitized[key] = type(value)(
                    self._sanitize_metadata({"v": v}).get("v", v) if isinstance(v, dict) else
                    self._redact_value(v, key)
                    for v in value
                )
            else:
                sanitized[key] = self._redact_value(value, key)

        return sanitized

    def is_observation_enabled(
        self,
        name: str,
        *,
        as_type: str | None = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Return whether an optional child observation is enabled by policy."""
        if not hasattr(self.config, "enabled_observation_trees"):
            return True
        return should_emit_observation(
            getattr(self.config, "enabled_observation_trees", None),
            name,
            as_type=as_type,
            metadata=metadata,
        )

    @staticmethod
    def _with_local_evidence_metadata(metadata: Optional[dict[str, Any]]) -> dict[str, Any]:
        """Attach opt-in local-only Langfuse evidence metadata."""
        md = dict(metadata or {})
        local_meta = local_langfuse_evidence_metadata()
        if local_meta:
            md.update(local_meta)
        return md

    def start_trace(
        self,
        name: str,
        session_id: Optional[str] = None,
        run_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        module_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[Any]:
        """Start a new trace.

        Args:
            name: Trace name (e.g., "player_session_creation", "turn_execution")
            session_id: Player session ID for correlation
            run_id: Run/narrative ID for correlation
            turn_id: Turn ID or number for correlation
            module_id: Module ID (e.g., "god_of_carnage") for correlation
            metadata: Additional metadata to attach
            trace_id: Optional Langfuse v4 trace ID for distributed tracing

        Returns:
            Trace span object if enabled, None otherwise.
        """
        if not self.is_enabled():
            return None

        try:
            trace_metadata = self._with_local_evidence_metadata(metadata)
            trace_metadata.update({
                "session_id": session_id,
                "run_id": run_id,
                "turn_id": turn_id,
                "module_id": module_id,
            })
            env = resolve_langfuse_environment(
                trace_metadata.get("trace_origin"),
                trace_metadata.get("execution_tier"),
                default=str(self.config.environment or "development"),
            )
            trace_metadata.setdefault("wos_langfuse_environment", env)
            trace_metadata = self._sanitize_metadata({k: v for k, v in trace_metadata.items() if v is not None})
            client = self._get_client(env)
            if not client:
                return None

            # v4 API: start_observation returns a span object (not context manager here)
            trace_context = {"trace_id": trace_id} if trace_id else None

            def _create():
                return client.start_observation(
                    as_type="span",
                    name=name,
                    trace_context=trace_context,
                    metadata=trace_metadata,
                )

            # First-class Langfuse sessionId / userId come from OTEL propagation, not metadata alone.
            prop_kwargs: dict[str, Any] = {}
            if session_id:
                prop_kwargs["session_id"] = session_id
            if user_id:
                prop_kwargs["user_id"] = user_id
            if prop_kwargs:
                from langfuse import propagate_attributes

                with propagate_attributes(**prop_kwargs):
                    self._active_trace = _create()
            else:
                self._active_trace = _create()
            return self._active_trace
        except Exception as e:
            logger.warning(f"Failed to start trace: {e}")
            return None

    def create_trace_id(self, seed: Optional[str] = None) -> str:
        """Create a Langfuse-compatible 32-char hex trace ID."""
        c = self.client
        if c:
            return c.create_trace_id(seed=seed)
        if LANGFUSE_AVAILABLE and Langfuse:
            return Langfuse.create_trace_id(seed=seed)
        if seed:
            return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]
        return os.urandom(16).hex()

    def end_trace(self, trace: Optional[Any] = None) -> None:
        """End the current or specified trace."""
        if not self.is_enabled():
            return

        target = trace or self._active_trace
        if target:
            try:
                # v4 API: call end() on the span
                target.end()
                if self._active_trace == target:
                    self._active_trace = None
            except Exception as e:
                logger.warning(f"Failed to end trace: {e}")

    def add_span(
        self,
        name: str,
        input_data: Optional[dict[str, Any]] = None,
        output_data: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
        trace: Optional[Any] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Optional[Any]:
        """Add a span to a trace.

        Args:
            name: Span name
            input_data: Input to the span
            output_data: Output from the span
            metadata: Additional metadata
            trace: Target trace (defaults to active trace)
            start_time: Span start time
            end_time: Span end time

        Returns:
            Span object if enabled, None otherwise.
        """
        if not self.is_enabled():
            return None
        if not self.is_observation_enabled(name, as_type="span", metadata=metadata):
            return None

        target_trace = trace or self._active_trace
        if not target_trace:
            return None

        try:
            span_input = self._sanitize_metadata(input_data) if input_data and self.config.capture_prompts else None
            span_output = self._sanitize_metadata(output_data) if output_data and self.config.capture_outputs else None
            span_metadata_raw = self._with_local_evidence_metadata(metadata)
            span_metadata = self._sanitize_metadata(span_metadata_raw) if span_metadata_raw else None

            # v4 API: create nested span
            span = target_trace.start_observation(
                as_type="span",
                name=name,
                input=span_input,
                metadata=span_metadata,
            )
            if span:
                span.update(output=span_output)
                span.end()
            return span
        except Exception as e:
            logger.warning(f"Failed to add span: {e}")
            return None

    def record_generation(
        self,
        name: str,
        model: str,
        provider: str,
        prompt: Optional[str] = None,
        completion: Optional[str] = None,
        tokens_prompt: Optional[int] = None,
        tokens_completion: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        trace: Optional[Any] = None,
    ) -> None:
        """Record an AI generation (LLM call).

        Args:
            name: Generation name
            model: Model name
            provider: Provider name
            prompt: Prompt sent (if capture enabled)
            completion: Completion received (if capture enabled)
            tokens_prompt: Prompt token count
            tokens_completion: Completion token count
            metadata: Additional metadata
            trace: Target trace (defaults to active trace)
        """
        if not self.is_enabled():
            return
        if not self.is_observation_enabled(name, as_type="generation", metadata=metadata):
            return

        target_trace = trace or self._active_trace
        if not target_trace:
            return

        try:
            gen_metadata = self._with_local_evidence_metadata(metadata)
            gen_metadata.update({
                "model": model,
                "provider": provider,
                "tokens_prompt": tokens_prompt,
                "tokens_completion": tokens_completion,
            })

            prompt_text = (self._sanitize_metadata({"p": prompt}).get("p") if prompt and self.config.capture_prompts else None)
            completion_text = (self._sanitize_metadata({"c": completion}).get("c") if completion and self.config.capture_outputs else None)

            # v4 API: create generation as a nested observation
            generation = target_trace.start_observation(
                as_type="generation",
                name=name,
                model=model,
                input={"prompt": prompt_text} if prompt_text else None,
                metadata=self._sanitize_metadata(gen_metadata),
            )

            # Record output and token usage
            if generation:
                generation.update(
                    output={"completion": completion_text} if completion_text else None,
                    usage_details={
                        "input": tokens_prompt or 0,
                        "output": tokens_completion or 0,
                        "total": (tokens_prompt or 0) + (tokens_completion or 0),
                    } if (tokens_prompt or tokens_completion) else None,
                )
                generation.end()
        except Exception as e:
            logger.warning(f"Failed to record generation: {e}")

    def record_retrieval(
        self,
        query: Optional[str] = None,
        retrieved_documents: Optional[list[dict[str, Any]]] = None,
        metadata: Optional[dict[str, Any]] = None,
        trace: Optional[Any] = None,
    ) -> None:
        """Record a retrieval operation.

        Args:
            query: Search query (if capture enabled)
            retrieved_documents: Retrieved items (if capture enabled)
            metadata: Additional metadata
            trace: Target trace (defaults to active trace)
        """
        if not self.is_enabled():
            return
        if not self.is_observation_enabled("retrieval", as_type="retriever", metadata=metadata):
            return

        target_trace = trace or self._active_trace
        if not target_trace:
            return

        try:
            ret_metadata = self._with_local_evidence_metadata(metadata)
            ret_metadata["document_count"] = len(retrieved_documents) if retrieved_documents else 0

            input_data = None
            output_data = None

            if self.config.capture_retrieval:
                if query:
                    input_data = {"query": query}
                if retrieved_documents:
                    output_data = {"documents": retrieved_documents[:5]}  # Limit to first 5

            # v4 API: use retriever observation type
            retrieval = target_trace.start_observation(
                as_type="retriever",
                name="retrieval",
                input=input_data,
                metadata=self._sanitize_metadata(ret_metadata),
            )
            if retrieval:
                retrieval.update(output=output_data)
                retrieval.end()
        except Exception as e:
            logger.warning(f"Failed to record retrieval: {e}")

    def record_validation(
        self,
        name: str,
        status: str,
        input_data: Optional[dict[str, Any]] = None,
        output_data: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
        trace: Optional[Any] = None,
    ) -> None:
        """Record a validation/guard operation.

        Args:
            name: Validation name
            status: "approved", "rejected", or "degraded"
            input_data: Input to validation
            output_data: Validation output
            metadata: Additional metadata
            trace: Target trace (defaults to active trace)
        """
        if not self.is_enabled():
            return
        if not self.is_observation_enabled(f"validation_{name}", as_type="guardrail", metadata=metadata):
            return

        target_trace = trace or self._active_trace
        if not target_trace:
            return

        try:
            val_metadata = self._with_local_evidence_metadata(metadata)
            val_metadata["status"] = status

            # v4 API: use guardrail observation type
            validation = target_trace.start_observation(
                as_type="guardrail",
                name=f"validation_{name}",
                input=self._sanitize_metadata(input_data) if input_data else None,
                metadata=self._sanitize_metadata(val_metadata),
            )
            if validation:
                validation.update(output=self._sanitize_metadata(output_data) if output_data else None)
                validation.end()
        except Exception as e:
            logger.warning(f"Failed to record validation: {e}")

    def add_score(
        self,
        name: str,
        value: float,
        comment: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        trace: Optional[Any] = None,
    ) -> None:
        """Add a score/evaluation to a trace.

        Args:
            name: Score name
            value: Score value (0.0-1.0)
            comment: Human-readable comment
            metadata: Additional metadata
            trace: Target trace (defaults to active trace)
        """
        if not self.is_enabled():
            return
        if not self.is_observation_enabled(name, as_type="score", metadata=metadata):
            return

        target_trace = trace or self._active_trace
        if not target_trace:
            return

        try:
            from langfuse.api import ScoreDataType

            # v4 API: use score method on the span (explicit NUMERIC for strict Langfuse servers)
            target_trace.score(
                name=name,
                value=value,
                comment=comment,
                metadata=self._sanitize_metadata(self._with_local_evidence_metadata(metadata)),
                data_type=ScoreDataType.NUMERIC,
            )
        except Exception as e:
            logger.warning(f"Failed to add score: {e}")

    def create_child_span(
        self,
        name: str,
        input: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
        parent_span: Optional[Any] = None,
    ) -> Optional[Any]:
        """Create a child span of the current active span.

        Args:
            name: Child span name
            input: Input to the span
            metadata: Additional metadata
            parent_span: Parent span (defaults to active span context)

        Returns:
            Child span object if enabled, None otherwise.
        """
        if not self.is_enabled():
            return None
        if not self.is_observation_enabled(name, as_type="span", metadata=metadata):
            return None

        try:
            parent = parent_span or _active_span_context.get()
            if not parent:
                return None

            span_input = self._sanitize_metadata(input) if input and self.config.capture_prompts else None
            span_metadata_raw = self._with_local_evidence_metadata(metadata)
            span_metadata = self._sanitize_metadata(span_metadata_raw) if span_metadata_raw else None

            child_span = parent.start_observation(
                as_type="span",
                name=name,
                input=span_input,
                metadata=span_metadata,
            )
            return child_span
        except Exception as e:
            logger.warning(f"Failed to create child span: {e}")
            return None

    def set_active_span(self, span: Optional[Any]) -> Optional[Any]:
        """Set the active span in context."""
        return _active_span_context.set(span)

    def get_active_span(self) -> Optional[Any]:
        """Get the current active span from context."""
        return _active_span_context.get()

    @property
    def active_root_trace(self) -> Optional[Any]:
        """Root observation started via ``start_trace`` (may be None in nested-only contexts)."""
        return self._active_trace

    def resolve_parent_observation_for_nested_span(self) -> Optional[Any]:
        """Prefer the innermost active span, else the root trace, for nested observations."""
        return self.get_active_span() or self._active_trace

    def record_wos_nested_span_observation(
        self,
        *,
        name: str,
        metadata: Optional[dict[str, Any]] = None,
        input_data: Optional[dict[str, Any]] = None,
        output_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Emit a nested Langfuse span under the active parent; returns diagnostics (never raises)."""
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
            span_metadata_raw = self._with_local_evidence_metadata(metadata)
            span_metadata = self._sanitize_metadata(span_metadata_raw) if span_metadata_raw else None
            span_input = (
                self._sanitize_metadata(input_data)
                if input_data and self.config.capture_prompts
                else None
            )
            span_output = (
                self._sanitize_metadata(output_data)
                if output_data and self.config.capture_outputs
                else None
            )
            child = parent.start_observation(
                as_type="span",
                name=name,
                metadata=span_metadata,
                input=span_input,
            )
            if not child:
                out["reason"] = "langfuse_child_observation_not_created"
                return out
            if span_output:
                child.update(output=span_output)
            child.end()
            trace_id = (
                getattr(child, "trace_id", None)
                or getattr(child, "traceId", None)
                or getattr(parent, "trace_id", None)
                or getattr(parent, "traceId", None)
            )
            obs_id = getattr(child, "id", None) or getattr(child, "observation_id", None)
            out["emitted"] = True
            if trace_id is not None:
                out["langfuse_trace_id"] = str(trace_id)
            if obs_id is not None:
                out["langfuse_observation_id"] = str(obs_id)
            return out
        except Exception as e:
            logger.warning("Failed to record WoS nested span %r: %s", name, e)
            out["reason"] = f"langfuse_error:{e}"
            return out

    def record_adr0041_langfuse_scores(
        self,
        *,
        scores: list[tuple[str, float]],
        comment: str,
    ) -> dict[str, Any]:
        """Attach ADR-0041 numeric scores to the active root trace (best-effort)."""
        out: dict[str, Any] = {"emitted": False, "scores_attempted": len(scores)}
        if not self.is_enabled() or not self._active_trace:
            out["reason"] = "no_active_root_trace_for_scoring"
            return out
        if not self.is_observation_enabled("adr0041_langfuse_scores", as_type="score"):
            out["reason"] = "observation_tree_disabled"
            return out
        meta_base = {
            "score_origin": "adr0041_runtime_intelligence",
            "proof_level": "local_only",
        }
        try:
            for s_name, s_val in scores:
                self.add_score(
                    s_name,
                    float(s_val),
                    comment=comment,
                    metadata=meta_base,
                    trace=self._active_trace,
                )
            out["emitted"] = True
            return out
        except Exception as e:
            logger.warning("Failed to record ADR-0041 Langfuse scores: %s", e)
            out["reason"] = f"langfuse_error:{e}"
            return out

    def calculate_token_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost for a given model and token counts.

        Args:
            model: Model name (e.g., 'claude-3-sonnet', 'gpt-4')
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD (or 0.0 if model not recognized)
        """
        # Token pricing (as of April 2026 - update as needed)
        pricing = {
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},  # per 1k tokens
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        }

        model_lower = model.lower()
        for model_key, rates in pricing.items():
            if model_key in model_lower:
                input_cost = (input_tokens / 1000) * rates["input"]
                output_cost = (output_tokens / 1000) * rates["output"]
                return round(input_cost + output_cost, 6)

        # Default: assume similar to gpt-3.5 if model not recognized
        return 0.0

    def flush(self) -> None:
        """Flush pending traces."""
        for env_key, client in list(self._clients.items()):
            try:
                client.flush()
            except Exception as e:
                logger.warning("Failed to flush Langfuse (%r): %s", env_key, e)

    def shutdown(self) -> None:
        """Gracefully shutdown Langfuse client."""
        self.flush()
        self._clients.clear()


def get_langfuse_adapter() -> LangfuseAdapter:
    """Get the global Langfuse adapter instance."""
    return LangfuseAdapter.get_instance()
