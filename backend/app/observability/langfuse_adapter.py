"""Canonical Langfuse observability adapter.

Provides unified tracing for AI/runtime behavior across backend, world-engine,
and ai_stack. Langfuse is optional and disabled by default.

Safe: no-op mode if disabled or credentials missing.
Secure: redacts secrets before sending.
Correlated: all traces linked to session/run/turn/module/scene.
"""

from __future__ import annotations

import os
from typing import Any, Optional
from functools import wraps
import logging
from datetime import datetime
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Context variable for tracking active span
_active_span_context: ContextVar[Optional[Any]] = ContextVar('active_span', default=None)

# Attempt to import Langfuse; gracefully degrade if not available
try:
    from langfuse import Langfuse
    from langfuse.openai import OpenAI as LangfuseOpenAI
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None
    LangfuseOpenAI = None


class LangfuseConfig:
    """Langfuse configuration from environment or database."""

    def __init__(self):
        env_enabled = os.getenv("LANGFUSE_ENABLED", "").lower() in ("true", "1", "yes")
        db_enabled = self._get_enabled_from_db()
        # Environment variable takes precedence; if not set, use database config
        self.enabled = env_enabled or (db_enabled if os.getenv("LANGFUSE_ENABLED") == "" else env_enabled)
        if not os.getenv("LANGFUSE_ENABLED"):
            self.enabled = db_enabled

        # Try environment variables first, then fall back to database
        self.public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "") or self._get_credential_from_db("public_key") or ""
        self.secret_key = os.getenv("LANGFUSE_SECRET_KEY", "") or self._get_credential_from_db("secret_key") or ""

        self.base_url = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
        self.environment = os.getenv("LANGFUSE_ENVIRONMENT", "development")
        self.release = os.getenv("LANGFUSE_RELEASE", "unknown")
        self.sample_rate = float(os.getenv("LANGFUSE_SAMPLE_RATE", "1.0"))
        self.capture_prompts = os.getenv("LANGFUSE_CAPTURE_PROMPTS", "true").lower() in ("true", "1")
        self.capture_outputs = os.getenv("LANGFUSE_CAPTURE_OUTPUTS", "true").lower() in ("true", "1")
        self.capture_retrieval = os.getenv("LANGFUSE_CAPTURE_RETRIEVAL", "false").lower() in ("true", "1")
        self.redaction_mode = os.getenv("LANGFUSE_REDACTION_MODE", "strict")

    @staticmethod
    def _get_enabled_from_db() -> bool:
        """Get enabled flag from database (set via admin tool)."""
        try:
            from app.models.governance_core import ObservabilityConfig
            config = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
            if config:
                return bool(config.is_enabled)
        except Exception:
            pass
        return False

    @staticmethod
    def _get_credential_from_db(secret_name: str) -> Optional[str]:
        """Get credential from database (stored via admin tool)."""
        try:
            from app.models.governance_core import ObservabilityCredential
            cred = ObservabilityCredential.query.filter_by(
                service_id="langfuse",
                secret_name=secret_name,
                is_active=True,
            ).first()
            if cred:
                try:
                    return cred.encrypted_secret.decode()
                except Exception:
                    return None
        except Exception:
            return None
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
        self._client: Optional[Langfuse] = None
        self._active_trace: Optional[Any] = None

        if self.config.is_ready:
            try:
                self._client = Langfuse(
                    public_key=self.config.public_key,
                    secret_key=self.config.secret_key,
                    base_url=self.config.base_url,
                    environment=self.config.environment,
                    release=self.config.release,
                    sample_rate=self.config.sample_rate,
                )
                logger.info(f"Langfuse initialized: {self.config.environment}@{self.config.base_url}")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse: {e}. Tracing disabled.")
                self._client = None

    @classmethod
    def get_instance(cls, config: Optional[LangfuseConfig] = None) -> "LangfuseAdapter":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (useful for testing)."""
        if cls._instance is not None and cls._instance._client:
            try:
                cls._instance._client.flush()
            except Exception:
                pass
        cls._instance = None

    def is_enabled(self) -> bool:
        """Check if tracing is enabled and ready."""
        return self._client is not None

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

    def start_trace(
        self,
        name: str,
        session_id: Optional[str] = None,
        run_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        module_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[Any]:
        """Start a new trace.

        Args:
            name: Trace name (e.g., "player_session_creation", "turn_execution")
            session_id: Player session ID for correlation
            run_id: Run/narrative ID for correlation
            turn_id: Turn ID or number for correlation
            module_id: Module ID (e.g., "god_of_carnage") for correlation
            metadata: Additional metadata to attach

        Returns:
            Trace span object if enabled, None otherwise.
        """
        if not self.is_enabled():
            return None

        try:
            trace_metadata = metadata or {}
            trace_metadata.update({
                "session_id": session_id,
                "run_id": run_id,
                "turn_id": turn_id,
                "module_id": module_id,
            })
            trace_metadata = self._sanitize_metadata({k: v for k, v in trace_metadata.items() if v is not None})

            # v4 API: start_observation returns a span object (not context manager here)
            self._active_trace = self._client.start_observation(
                as_type="span",
                name=name,
                metadata=trace_metadata,
            )
            return self._active_trace
        except Exception as e:
            logger.warning(f"Failed to start trace: {e}")
            return None

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

        target_trace = trace or self._active_trace
        if not target_trace:
            return None

        try:
            span_input = self._sanitize_metadata(input_data) if input_data and self.config.capture_prompts else None
            span_output = self._sanitize_metadata(output_data) if output_data and self.config.capture_outputs else None
            span_metadata = self._sanitize_metadata(metadata) if metadata else None

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

        target_trace = trace or self._active_trace
        if not target_trace:
            return

        try:
            gen_metadata = metadata or {}
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

        target_trace = trace or self._active_trace
        if not target_trace:
            return

        try:
            ret_metadata = metadata or {}
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

        target_trace = trace or self._active_trace
        if not target_trace:
            return

        try:
            val_metadata = metadata or {}
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

        target_trace = trace or self._active_trace
        if not target_trace:
            return

        try:
            # v4 API: use score method on the span
            target_trace.score(
                name=name,
                value=value,
                comment=comment,
                metadata=self._sanitize_metadata(metadata) if metadata else None,
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

        try:
            parent = parent_span or _active_span_context.get()
            if not parent:
                return None

            span_input = self._sanitize_metadata(input) if input and self.config.capture_prompts else None
            span_metadata = self._sanitize_metadata(metadata) if metadata else None

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
        if self._client:
            try:
                self._client.flush()
            except Exception as e:
                logger.warning(f"Failed to flush Langfuse: {e}")

    def shutdown(self) -> None:
        """Gracefully shutdown Langfuse client."""
        if self._client:
            try:
                self._client.flush()
                self._client = None
            except Exception as e:
                logger.warning(f"Failed to shutdown Langfuse: {e}")


def get_langfuse_adapter() -> LangfuseAdapter:
    """Get the global Langfuse adapter instance."""
    return LangfuseAdapter.get_instance()
