from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

_log = logging.getLogger(__name__)

_OPENAI_ERROR_BODY_MAX = 2000


def openai_http_error_excerpt(response: httpx.Response | None, *, limit: int = _OPENAI_ERROR_BODY_MAX) -> str:
    """Return a short snippet from an OpenAI-compatible JSON error body (no secrets)."""
    if response is None:
        return ""
    try:
        data = response.json()
        if isinstance(data, dict):
            err = data.get("error")
            if isinstance(err, dict) and err.get("message"):
                msg = str(err.get("message", "")).strip()
                et = str(err.get("type", "") or "").strip()
                if et:
                    return f"{et}: {msg}"[:limit]
                return msg[:limit]
            if isinstance(err, str):
                return err.strip()[:limit]
    except Exception:
        pass
    try:
        text = (response.text or "").strip()
    except Exception:
        return ""
    return text[:limit] if text else ""

_DEBUG_LOG_ENV = "WOS_DEBUG_OPENAI_ADAPTER"
_DEBUG_SESSION_ID = "a4ace1"


def _debug_openai_adapter_ndjson(payload: dict[str, Any]) -> None:
    if os.environ.get(_DEBUG_LOG_ENV) != "1":
        return
    line = json.dumps({"sessionId": _DEBUG_SESSION_ID, "timestamp": int(time.time() * 1000), **payload}, ensure_ascii=False)
    try:
        log_path = Path(__file__).resolve().parents[1] / "debug-a4ace1.log"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        return


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
        # responder_actor_ids contains NPC only; human actor protection is respected.
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
        allow_env_api_key: bool = False,
    ) -> None:
        self.model_name = model_name
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self._configured_api_key = (api_key or "").strip() or None
        self._allow_env_api_key = bool(allow_env_api_key)

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
        """Collect visible model text from a Responses API JSON body.

        The HTTP JSON body does not always include the SDK-only ``output_text`` helper; it
        often only has ``output`` items (message, output_text, reasoning summaries, …).
        """

        def _append_non_empty(acc: list[str], value: str) -> None:
            stripped = value.strip()
            if stripped:
                acc.append(stripped)

        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()
        if isinstance(output_text, list):
            parts = [p.strip() for p in output_text if isinstance(p, str) and p.strip()]
            if parts:
                return "\n".join(parts)

        chunks: list[str] = []
        output_items = payload.get("output")
        if not isinstance(output_items, list):
            return ""

        for item in output_items:
            if not isinstance(item, dict):
                continue
            itype = str(item.get("type") or "")

            if itype == "output_text":
                text = item.get("text")
                if isinstance(text, str):
                    _append_non_empty(chunks, text)
                continue

            if itype == "reasoning":
                summaries = item.get("summary")
                if isinstance(summaries, list):
                    for sm in summaries:
                        if isinstance(sm, dict):
                            st = sm.get("text")
                            if isinstance(st, str):
                                _append_non_empty(chunks, st)
                continue

            content_items = item.get("content")
            if isinstance(content_items, str):
                _append_non_empty(chunks, content_items)
                continue
            if not isinstance(content_items, list):
                continue

            for content_item in content_items:
                if not isinstance(content_item, dict):
                    continue
                text = content_item.get("text")
                if isinstance(text, str):
                    _append_non_empty(chunks, text)
                refusal = content_item.get("refusal")
                if isinstance(refusal, str):
                    _append_non_empty(chunks, refusal)

        if chunks:
            return "\n".join(chunks)

        for item in output_items:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    _append_non_empty(chunks, text)
        return "\n".join(chunks)

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
        # Plain-string ``input`` matches OpenAI Responses migration examples and avoids
        # strict message-item validation issues on some gateways (see governance probe).
        payload: dict[str, Any] = {
            "model": chosen_model,
            "input": prompt,
        }
        if retrieval_context and retrieval_context.strip():
            payload["instructions"] = retrieval_context.strip()
        if self._supports_custom_temperature(chosen_model):
            payload["temperature"] = 0.3
        json_mode = self._json_mode_requested(prompt)
        reasoning_model = self._uses_reasoning_controls(chosen_model)
        # Some Responses deployments reject ``reasoning`` together with ``text.format``;
        # JSON mode still works without explicit reasoning controls for the probe path.
        if reasoning_model and not json_mode:
            payload["reasoning"] = {"effort": "minimal"}
            payload["max_output_tokens"] = 1200
        elif reasoning_model and json_mode:
            payload["max_output_tokens"] = 1200
        if json_mode:
            payload["text"] = {"format": {"type": "json_object"}}
        response = client.post(
            f"{self.base_url}/responses",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        response.raise_for_status()
        response_payload = response.json()
        message = self._extract_responses_text(response_payload)
        # #region agent log
        if isinstance(response_payload, dict):
            out = response_payload.get("output")
            out_types: list[str] = []
            if isinstance(out, list):
                for el in out:
                    if isinstance(el, dict) and isinstance(el.get("type"), str):
                        out_types.append(str(el["type"]))
            _debug_openai_adapter_ndjson(
                {
                    "hypothesisId": "H1-H5",
                    "location": "adapters.py:_generate_with_responses_api",
                    "message": "responses_parse",
                    "data": {
                        "model": chosen_model,
                        "top_keys": sorted(response_payload.keys()),
                        "output_item_types": out_types,
                        "extracted_len": len(message),
                        "has_output_text_key": "output_text" in response_payload,
                    },
                    "runId": "pre-fix",
                }
            )
        # #endregion
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
        api_key = (self._configured_api_key or "").strip()
        if not api_key and self._allow_env_api_key:
            api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
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
        force_chat = (os.getenv("OPENAI_GPT5_USE_CHAT_COMPLETIONS") or "").strip().lower() in {"1", "true", "yes"}
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
                use_responses = self._uses_responses_api(chosen_model) and not force_chat
                if use_responses:
                    return self._generate_with_responses_api(**call_kwargs)
                return self._generate_with_chat_completions_api(**call_kwargs)
        except httpx.HTTPStatusError as exc:
            resp = exc.response
            status = getattr(resp, "status_code", None)
            excerpt = openai_http_error_excerpt(resp)
            adapter_api = "responses" if self._uses_responses_api(chosen_model) and not force_chat else "chat_completions"
            _log.error(
                "OpenAI HTTP error: adapter=%s model=%s status=%s excerpt=%s",
                self.adapter_name,
                chosen_model,
                status,
                excerpt[:800] if excerpt else str(exc),
            )
            meta: dict[str, Any] = {
                "adapter": self.adapter_name,
                "model": chosen_model,
                "base_url": self.base_url,
                "timeout_seconds": request_timeout,
                "error": str(exc),
                "http_status": status,
                "adapter_api": adapter_api,
            }
            if excerpt:
                meta["provider_error_excerpt"] = excerpt
            return ModelCallResult(content="", success=False, metadata=meta)
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
