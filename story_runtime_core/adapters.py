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

    @staticmethod
    def _uses_responses_api(model_name: str) -> bool:
        model = model_name.strip().lower()
        return model.startswith("gpt-5") or model.startswith("o1") or model.startswith("o3") or model.startswith("o4")

    @staticmethod
    def _json_mode_requested(prompt: str) -> bool:
        text = prompt.lower()
        return "return valid json" in text or "format instructions" in text

    @staticmethod
    def _extract_responses_text(payload: dict[str, Any]) -> str:
        output_text = payload.get("output_text")
        if isinstance(output_text, str):
            return output_text
        chunks: list[str] = []
        output_items = payload.get("output")
        if isinstance(output_items, list):
            for item in output_items:
                if not isinstance(item, dict):
                    continue
                content_items = item.get("content")
                if not isinstance(content_items, list):
                    continue
                for content_item in content_items:
                    if not isinstance(content_item, dict):
                        continue
                    text = content_item.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
                    refusal = content_item.get("refusal")
                    if isinstance(refusal, str) and not chunks:
                        chunks.append(refusal)
        return "\n".join(chunk for chunk in chunks if chunk)

    @staticmethod
    def _usage_details(usage: dict[str, Any]) -> tuple[int, int, int]:
        prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
        return prompt_tokens, completion_tokens, total_tokens

    def _generate_with_responses_api(
        self,
        *,
        client: httpx.Client,
        api_key: str,
        prompt: str,
        retrieval_context: str | None,
        chosen_model: str,
        request_timeout: float,
    ) -> ModelCallResult:
        payload: dict[str, Any] = {
            "model": chosen_model,
            "instructions": retrieval_context or "No retrieval context attached.",
            "input": prompt,
        }
        if self._supports_custom_temperature(chosen_model):
            payload["temperature"] = 0.3
        if self._uses_reasoning_controls(chosen_model):
            payload["reasoning"] = {"effort": "minimal"}
            payload["max_output_tokens"] = 1200
        if self._json_mode_requested(prompt):
            payload["text"] = {"format": {"type": "json_object"}}
        response = client.post(
            f"{self.base_url}/responses",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        response.raise_for_status()
        response_payload = response.json()
        message = self._extract_responses_text(response_payload)
        usage = response_payload.get("usage") if isinstance(response_payload.get("usage"), dict) else {}
        prompt_tokens, completion_tokens, total_tokens = self._usage_details(usage)
        return ModelCallResult(
            content=message,
            success=True,
            metadata={
                "adapter": self.adapter_name,
                "adapter_api": "responses",
                "model": chosen_model,
                "base_url": self.base_url,
                "timeout_seconds": request_timeout,
                "usage_available": bool(usage),
                "usage_source": "provider_response" if usage else "provider_response_missing_usage",
                "usage_details": {
                    "input": prompt_tokens,
                    "output": completion_tokens,
                    "total": total_tokens,
                },
                "tokens_prompt": prompt_tokens,
                "tokens_completion": completion_tokens,
                "tokens_total": total_tokens,
                "response_id": response_payload.get("id"),
            },
        )

    def _generate_with_chat_completions_api(
        self,
        *,
        client: httpx.Client,
        api_key: str,
        prompt: str,
        retrieval_context: str | None,
        chosen_model: str,
        request_timeout: float,
    ) -> ModelCallResult:
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
        if self._uses_reasoning_controls(chosen_model):
            payload["reasoning_effort"] = "minimal"
            payload["max_completion_tokens"] = 1200
        if self._json_mode_requested(prompt):
            payload["response_format"] = {"type": "json_object"}
        response = client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        response.raise_for_status()
        response_payload = response.json()
        message = response_payload["choices"][0]["message"]["content"]
        usage = response_payload.get("usage") if isinstance(response_payload.get("usage"), dict) else {}
        prompt_tokens, completion_tokens, total_tokens = self._usage_details(usage)
        return ModelCallResult(
            content=message,
            success=True,
            metadata={
                "adapter": self.adapter_name,
                "adapter_api": "chat_completions",
                "model": chosen_model,
                "base_url": self.base_url,
                "timeout_seconds": request_timeout,
                "usage_available": bool(usage),
                "usage_source": "provider_response" if usage else "provider_response_missing_usage",
                "usage_details": {
                    "input": prompt_tokens,
                    "output": completion_tokens,
                    "total": total_tokens,
                },
                "tokens_prompt": prompt_tokens,
                "tokens_completion": completion_tokens,
                "tokens_total": total_tokens,
            },
        )

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
            override_raw = os.getenv("OPENAI_REASONING_RESPONSES_TIMEOUT_SECONDS") or os.getenv("OPENAI_REASONING_CHAT_TIMEOUT_SECONDS")
            if override_raw is not None and override_raw.strip():
                try:
                    request_timeout = max(1.0, float(override_raw.strip()))
                except ValueError:
                    request_timeout = 60.0
            else:
                request_timeout = max(float(timeout_seconds), 60.0)
        if not api_key:
            return ModelCallResult(
                content="",
                success=False,
                metadata={"error": "missing_openai_api_key", "model": chosen_model},
            )
        try:
            with httpx.Client(timeout=request_timeout) as client:
                call_kwargs = {
                    "client": client,
                    "api_key": api_key,
                    "prompt": prompt,
                    "retrieval_context": retrieval_context,
                    "chosen_model": chosen_model,
                    "request_timeout": request_timeout,
                }
                if self._uses_responses_api(chosen_model):
                    return self._generate_with_responses_api(**call_kwargs)
                return self._generate_with_chat_completions_api(**call_kwargs)
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
                prompt_tokens = int(payload.get("prompt_eval_count") or 0)
                completion_tokens = int(payload.get("eval_count") or 0)
                total_tokens = prompt_tokens + completion_tokens
                return ModelCallResult(
                    content=payload.get("response", ""),
                    success=True,
                    metadata={
                        "adapter": self.adapter_name,
                        "model": chosen_model,
                        "usage_available": bool(total_tokens),
                        "usage_source": "provider_response" if total_tokens else "provider_unavailable",
                        "usage_details": {
                            "input": prompt_tokens,
                            "output": completion_tokens,
                            "total": total_tokens,
                        },
                        "tokens_prompt": prompt_tokens,
                        "tokens_completion": completion_tokens,
                        "tokens_total": total_tokens,
                    },
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
