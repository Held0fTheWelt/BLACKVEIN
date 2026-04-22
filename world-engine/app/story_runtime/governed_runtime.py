"""Governed story-runtime bridge: registry, routing, and adapters from backend-resolved config."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from story_runtime_core import ModelRegistry
from story_runtime_core.adapters import (
    BaseModelAdapter,
    MockModelAdapter,
    OllamaAdapter,
    OpenAIChatAdapter,
)
from story_runtime_core.model_registry import ModelSpec, RoutingDecision


_MODEL_NAME_ALIASES: dict[str, str] = {
    "gpt-5.4 mini": "gpt-5-mini",
    "gpt-5.4 nano": "gpt-5-nano",
    "chatgpt mini": "gpt-5-mini",
    "chatgpt nano": "gpt-5-nano",
    "gpt 5 mini": "gpt-5-mini",
    "gpt 5 nano": "gpt-5-nano",
}


def normalize_provider_model_name(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    low = raw.lower().strip()
    if low in _MODEL_NAME_ALIASES:
        return _MODEL_NAME_ALIASES[low]
    normalized = low.replace(" ", "-")
    normalized = normalized.replace(".4-", "-")
    normalized = normalized.replace(".5-", "-")
    normalized = normalized.replace("--", "-")
    return normalized


@dataclass(slots=True)
class GovernedStoryRoutingPolicy:
    registry: ModelRegistry
    routes: dict[str, dict[str, Any]]
    generation_mode: str = "mock_only"

    def choose(self, *, task_type: str) -> RoutingDecision:
        # P1-6: Enforce runtime mode semantics in routing decision
        route = self._route_for_task(task_type)
        preferred = str(route.get("preferred_model_id") or "").strip() or None
        fallback = str(route.get("fallback_model_id") or "").strip() or None
        mock_mid = str(route.get("mock_model_id") or "").strip() or None

        mode = (str(self.generation_mode or "").strip().lower() or "mock_only")
        # mode enforcement:
        # - "ai_only": use preferred/fallback, raise error if not available
        # - "mock_only": use mock only, skip preferred/fallback
        # - "hybrid": preferred → fallback → mock (original behavior)
        if mode == "ai_only":
            selected = preferred or fallback
            if not selected:
                raise ValueError(f"generation_execution_mode=ai_only but no AI model available for task_type={task_type!r}")
            fallback_chain = fallback or None
        elif mode == "mock_only":
            selected = mock_mid
            fallback_chain = None
        else:  # hybrid (default)
            selected = preferred or fallback or mock_mid
            fallback_chain = fallback or mock_mid

        if not selected:
            raise ValueError(f"No governed model configured for task_type={task_type!r}")
        spec = self.registry.get(selected)
        if spec is None:
            raise ValueError(f"Governed route selected missing model spec: {selected!r}")
        return RoutingDecision(
            selected_model=selected,
            selected_provider=spec.provider,
            route_reason="role_matrix_primary",
            fallback_model=fallback_chain,
        )

    def _route_for_task(self, task_type: str) -> dict[str, Any]:
        task = (task_type or "").strip().lower()
        if task == "classification":
            candidates = [
                "narrative_validation_semantic_global",
                "retrieval_query_expansion_global",
            ]
        else:
            candidates = [
                "narrative_live_generation_global",
                "narrative_preview_generation_global",
                "writers_room_revision_assist_global",
                "research_synthesis_global",
                "research_revision_drafting_global",
            ]
        for route_id in candidates:
            route = self.routes.get(route_id)
            if isinstance(route, dict):
                return route
        for route in self.routes.values():
            if isinstance(route, dict):
                return route
        raise ValueError("No governed routes available for story runtime")


def build_governed_model_adapters(config: dict[str, Any]) -> dict[str, BaseModelAdapter]:
    import os
    import httpx

    adapters: dict[str, BaseModelAdapter] = {"mock": MockModelAdapter()}
    providers = config.get("providers") if isinstance(config.get("providers"), list) else []

    # Backend internal API config
    backend_url = os.getenv("BACKEND_RUNTIME_CONFIG_URL", "http://backend:8000").rstrip("/")
    token = os.getenv("INTERNAL_RUNTIME_CONFIG_TOKEN", "").strip()

    for row in providers:
        if not isinstance(row, dict):
            continue
        provider_id = str(row.get("provider_id") or "").strip()
        provider_type = str(row.get("provider_type") or "").strip().lower()
        base_url = str(row.get("base_url") or "").strip() or None

        api_key = None
        credential_configured = row.get("credential_configured", False)

        # If credential is configured, fetch it via backend API
        if credential_configured and token:
            credential_endpoint = row.get("credential_endpoint")
            if credential_endpoint:
                endpoint_url = f"{backend_url}{credential_endpoint}"
                print(f"DEBUG: Fetching credential from {endpoint_url} for {provider_id}", flush=True)
                try:
                    with httpx.Client(timeout=5.0) as client:
                        response = client.get(
                            endpoint_url,
                            headers={"X-Internal-Config-Token": token},
                        )
                        if response.status_code == 200:
                            data = response.json()
                            if isinstance(data, dict) and data.get("ok"):
                                cred_data = data.get("data", {})
                                api_key = cred_data.get("api_key")
                                print(f"DEBUG: Successfully fetched credential for {provider_id}: key={api_key[:20] + '...' if api_key else 'None'}", flush=True)
                            else:
                                print(f"DEBUG: Invalid response from credential endpoint for {provider_id}: {response.status_code}", flush=True)
                        else:
                            print(f"DEBUG: Failed to fetch credential for {provider_id}: HTTP {response.status_code}", flush=True)
                except Exception as e:
                    print(f"DEBUG: Exception fetching credential for {provider_id}: {e}", flush=True)

        print(f"DEBUG: Building adapter for {provider_id} ({provider_type}): api_key={api_key[:20] + '...' if api_key else 'None'}", flush=True)
        if provider_type == "openai":
            adapters[provider_id] = OpenAIChatAdapter(base_url=base_url, api_key=api_key)
        elif provider_type == "ollama":
            adapters[provider_id] = OllamaAdapter(base_url=base_url)
        elif provider_type == "mock":
            adapters[provider_id] = MockModelAdapter()

    return adapters


def build_governed_story_runtime_components(config: dict[str, Any] | None):
    if not isinstance(config, dict):
        return None
    providers = config.get("providers") if isinstance(config.get("providers"), list) else []
    models = config.get("models") if isinstance(config.get("models"), list) else []
    routes = config.get("routes") if isinstance(config.get("routes"), list) else []
    if not providers or not models or not routes:
        return None

    provider_ids = {str(p.get("provider_id") or "").strip() for p in providers if isinstance(p, dict)}
    registry = ModelRegistry()
    for row in models:
        if not isinstance(row, dict):
            continue
        provider_id = str(row.get("provider_id") or "").strip()
        model_id = str(row.get("model_id") or "").strip()
        if not provider_id or provider_id not in provider_ids or not model_id:
            continue
        role = str(row.get("model_role") or "llm").strip().lower()
        provider_model_name = normalize_provider_model_name(str(row.get("model_name") or ""))
        registry.register(
            ModelSpec(
                model_name=model_id,
                provider=provider_id,
                llm_or_slm="llm" if role == "llm" else ("mock" if role == "mock" else "slm"),
                timeout_seconds=float(row.get("timeout_seconds") or 10.0),
                structured_output_capable=bool(row.get("structured_output_capable")),
                cost_class="governed",
                latency_class="governed",
                use_cases=(str(row.get("model_role") or role),),
                provider_model_name=provider_model_name or model_id,
            )
        )
    resolved_routes = {
        str(route.get("route_id") or "").strip(): dict(route)
        for route in routes
        if isinstance(route, dict) and str(route.get("route_id") or "").strip()
    }
    if not registry.all() or not resolved_routes:
        return None
    adapters = build_governed_model_adapters(config)
    routing = GovernedStoryRoutingPolicy(
        registry=registry,
        routes=resolved_routes,
        generation_mode=str(config.get("generation_execution_mode") or "mock_only"),
    )
    return registry, routing, adapters
