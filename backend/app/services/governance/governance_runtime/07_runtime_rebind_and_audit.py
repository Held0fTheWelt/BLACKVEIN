"""Governance runtime source segment: runtime_rebind_and_audit.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
                    "operator_message": "Embedding model responded successfully.",
                }

            if provider_type == "openai" and OpenAIChatAdapter._uses_responses_api(model_name):
                endpoint = f"{base_url}/responses"
                # Minimal connectivity probe: plain-string input matches Responses API docs and
                # avoids 400s from strict message-item validation on some gateways. Omit ``reasoning``
                # here so the probe stays a shallow reachability check (full turns use the adapter).
                payload: dict[str, object] = {
                    "model": model_name,
                    "input": "Reply with OK.",
                    "max_output_tokens": 64,
                }
                response = client.post(endpoint, headers=headers, json=payload)
                metadata.update(
                    {
                        "probe_kind": "text_generation",
                        "adapter_api": "responses",
                        "probe_endpoint": "/responses",
                        "http_status": response.status_code,
                    }
                )
                response.raise_for_status()
                response_payload = response.json()
                content = OpenAIChatAdapter._extract_responses_text(response_payload if isinstance(response_payload, dict) else {})
                metadata["response_id"] = response_payload.get("id") if isinstance(response_payload, dict) else None
                if not content and not (isinstance(response_payload, dict) and response_payload.get("output")):
                    return {
                        "success": False,
                        "content": "",
                        "metadata": metadata,
                        "error_code": "responses_response_missing_output",
                        "operator_message": "Responses probe completed but returned no output.",
                    }
                return {
                    "success": True,
                    "content": content or "ok",
                    "metadata": metadata,
                    "error_code": None,
                    "operator_message": "Model responded successfully.",
                }

            endpoint = f"{base_url}/chat/completions"
            payload: dict[str, object] = {
                "model": model_name,
                "messages": [{"role": "user", "content": "Reply with OK."}],
                "max_tokens": 8,
            }
            if OpenAIChatAdapter._supports_custom_temperature(model_name):
                payload["temperature"] = 0
            response = client.post(endpoint, headers=headers, json=payload)
            metadata.update(
                {
                    "probe_kind": "text_generation",
                    "adapter_api": "chat_completions",
                    "probe_endpoint": "/chat/completions",
                    "http_status": response.status_code,
                }
            )
            response.raise_for_status()
            response_payload = response.json()
            choices = response_payload.get("choices") if isinstance(response_payload, dict) else None
            first_choice = choices[0] if isinstance(choices, list) and choices else {}
            message = first_choice.get("message") if isinstance(first_choice, dict) else {}
            content = str(message.get("content") or "").strip() if isinstance(message, dict) else ""
            if not content:
                return {
                    "success": False,
                    "content": "",
                    "metadata": metadata,
                    "error_code": "chat_completion_response_missing_content",
                    "operator_message": "Chat completion probe completed but returned no message content.",
'''
