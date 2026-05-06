from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

_log = logging.getLogger(__name__)


@dataclass(slots=True)
class ModelCallResult:
    content: str
    success: bool
    metadata: dict[str, Any]


class BaseModelAdapter:
    adapter_name: str = "base"

    def generate(
        self,
        prompt: str,
        *,
        timeout_seconds: float = 10.0,
        retrieval_context: str | None = None,
        model_name: str | None = None,
    ) -> ModelCallResult:
        raise NotImplementedError


_MOCK_NARRATIVE_JSON = (
    '{"narrative_response": "The tension in the room becomes undeniable. Voices rise and fall'
    ' in carefully measured bursts, each word weighted with unspoken consequence.'
    ' No one yields ground; everyone recalculates.",'
    ' "proposed_state_effects": [], "intent_summary": "mock_deterministic", "confidence": 0.7}'
)


class MockModelAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def generate(
        self,
        prompt: str,
        *,
        timeout_seconds: float = 10.0,
        retrieval_context: str | None = None,
        model_name: str | None = None,
    ) -> ModelCallResult:
        # Return structured JSON so the dramatic alignment validator has enough narrative mass.
        # The narrative_response is >48 chars to pass high-stakes scene function thresholds.
        # responder_actor_ids contains NPC only (veronique) — human actor protection respected.
        return ModelCallResult(
            content=_MOCK_NARRATIVE_JSON,
            success=True,
            metadata={
                "adapter": self.adapter_name,
                "timeout_seconds": timeout_seconds,
                "retrieval_context_attached": bool(retrieval_context),
            },
        )


class OpenAIChatAdapter(BaseModelAdapter):
    adapter_name = "openai"

    def __init__(
        self,
        *,
        model_name: str = "gpt-4o-mini",
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self._configured_api_key = (api_key or "").strip() or None

    @staticmethod
    def _supports_custom_temperature(model_name: str) -> bool:
        model = model_name.strip().lower()
        return not (
            model.startswith("gpt-5")
            or model.startswith("o1")
            or model.startswith("o3")
            or model.startswith("o4")
        )

    @staticmethod
    def _uses_reasoning_controls(model_name: str) -> bool:
        model = model_name.strip().lower()
        return model.startswith("gpt-5") or model.startswith("o1") or model.startswith("o3") or model.startswith("o4")

    def generate(
        self,
        prompt: str,
        *,
        timeout_seconds: float = 20.0,
        retrieval_context: str | None = None,
        model_name: str | None = None,
    ) -> ModelCallResult:
        api_key = (self._configured_api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        chosen_model = (model_name or self.model_name).strip() or self.model_name
        uses_reasoning_controls = self._uses_reasoning_controls(chosen_model)
        request_timeout = timeout_seconds
        if uses_reasoning_controls:
            cap_raw = os.getenv("OPENAI_REASONING_CHAT_TIMEOUT_SECONDS", "12").strip()
            try:
                request_timeout = min(float(timeout_seconds), max(1.0, float(cap_raw)))
            except ValueError:
                request_timeout = min(float(timeout_seconds), 12.0)
        if not api_key:
            return ModelCallResult(
                content="",
                success=False,
                metadata={"error": "missing_openai_api_key", "model": chosen_model},
            )
        try:
            with httpx.Client(timeout=request_timeout) as client:
                payload: dict[str, Any] = {
                    "model": chosen_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": retrieval_context or "No retrieval context attached.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                }
                if self._supports_custom_temperature(chosen_model):
                    payload["temperature"] = 0.3
                if uses_reasoning_controls:
                    payload["reasoning_effort"] = "minimal"
                    payload["max_completion_tokens"] = 1200
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                payload = response.json()
                message = payload["choices"][0]["message"]["content"]
                return ModelCallResult(
                    content=message,
                    success=True,
                    metadata={
                        "adapter": self.adapter_name,
                        "model": chosen_model,
                        "base_url": self.base_url,
                        "timeout_seconds": request_timeout,
                    },
                )
        except Exception as exc:
            error_str = str(exc)
            _log.error("Model adapter call failed: adapter=%s model=%s error=%s", self.adapter_name, chosen_model, error_str)
            return ModelCallResult(
                content="",
                success=False,
                metadata={
                    "adapter": self.adapter_name,
                    "model": chosen_model,
                    "base_url": self.base_url,
                    "timeout_seconds": request_timeout,
                    "error": error_str,
                },
            )


class OllamaAdapter(BaseModelAdapter):
    adapter_name = "ollama"

    def __init__(self, *, model_name: str = "llama3.2", base_url: str | None = None) -> None:
        self.model_name = model_name
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")

    def generate(
        self,
        prompt: str,
        *,
        timeout_seconds: float = 10.0,
        retrieval_context: str | None = None,
        model_name: str | None = None,
    ) -> ModelCallResult:
        chosen_model = (model_name or self.model_name).strip() or self.model_name
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": chosen_model,
                        "prompt": prompt if not retrieval_context else f"{retrieval_context}\n\n{prompt}",
                        "stream": False,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                return ModelCallResult(
                    content=payload.get("response", ""),
                    success=True,
                    metadata={"adapter": self.adapter_name, "model": chosen_model},
                )
        except Exception as exc:
            return ModelCallResult(
                content="",
                success=False,
                metadata={"adapter": self.adapter_name, "model": chosen_model, "error": str(exc)},
            )


def build_default_model_adapters() -> dict[str, BaseModelAdapter]:
    """Concrete adapter instances keyed by provider name (startup registration surface).

    Used by the World-Engine story runtime host alongside :class:`ModelRegistry` specs.
    """
    return {
        "mock": MockModelAdapter(),
        "openai": OpenAIChatAdapter(),
        "ollama": OllamaAdapter(),
    }
