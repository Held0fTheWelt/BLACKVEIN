"""Governance runtime source segment: provider_probe_adapters.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
        return base_url
    if contract.get("provider_type") == "ollama" and base_url.endswith("/api") and path.startswith("/api/"):
        return base_url + path[len("/api") :]
    return base_url + path


def _provider_headers(contract: dict, secret: str | None) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    for k, v in (contract.get("static_headers") or {}).items():
        if v:
            headers[str(k)] = str(v)
    auth_mode = contract.get("auth_mode")
    if auth_mode == "bearer_api_key" and secret:
        headers["Authorization"] = f"Bearer {secret}"
    elif auth_mode == "x_api_key" and secret:
        headers["x-api-key"] = secret
    return headers


def _minimal_openai_probe(
    *,
    base_url: str,
    contract: dict,
    secret: str | None,
    model: AIModelConfig,
    timeout_seconds: float,
    provider_type: str,
) -> dict:
    headers = _provider_headers(contract, secret)
    headers["Content-Type"] = "application/json"
    model_name = (model.model_name or "").strip()
    metadata: dict[str, object] = {
        "concrete_probe_executed": True,
        "minimal_request_executed": True,
        "provider_type": provider_type,
        "model_role": _normalize_model_role(model.model_role, model_name=model.model_name),
        "request_model_name": model_name,
    }
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            if _is_embedding_model(model):
                endpoint = f"{base_url}/embeddings"
                payload = {"model": model_name, "input": "ping"}
                response = client.post(endpoint, headers=headers, json=payload)
                metadata.update(
                    {
                        "probe_kind": "embedding",
                        "adapter_api": "embeddings",
                        "probe_endpoint": "/embeddings",
                        "http_status": response.status_code,
                    }
                )
                response.raise_for_status()
                response_payload = response.json()
                data = response_payload.get("data") if isinstance(response_payload, dict) else None
                first = data[0] if isinstance(data, list) and data else {}
                embedding = first.get("embedding") if isinstance(first, dict) else None
                dimensions = len(embedding) if isinstance(embedding, list) else 0
                metadata["embedding_dimensions"] = dimensions
                if dimensions <= 0:
                    return {
                        "success": False,
                        "content": "",
                        "metadata": metadata,
                        "error_code": "embedding_response_missing_vector",
                        "operator_message": "Embedding probe completed but returned no embedding vector.",
                    }
                return {
                    "success": True,
                    "content": f"embedding_dimensions={dimensions}",
                    "metadata": metadata,
                    "error_code": None,
'''
