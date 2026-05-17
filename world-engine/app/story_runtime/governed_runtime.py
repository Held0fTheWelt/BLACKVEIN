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
    "chatgpt mini": "gpt-5.4-mini",
    "chatgpt nano": "gpt-5.4-nano",
    "gpt 5 mini": "gpt-5.4-mini",
    "gpt 5 nano": "gpt-5.4-nano",
}

_PROVIDER_MODEL_UNDERSCORE_ALIASES: dict[str, str] = {
    "gpt_5_4": "gpt-5.4",
    "gpt_5_4_mini": "gpt-5.4-mini",
    "gpt_5_4_nano": "gpt-5.4-nano",
    "gpt_5_5": "gpt-5.5",
    "gpt_5_5_mini": "gpt-5.5-mini",
}


def normalize_provider_model_name(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    normalized = " ".join(raw.split()).lower()
    if normalized in _MODEL_NAME_ALIASES:
        return _MODEL_NAME_ALIASES[normalized]
    normalized = normalized.replace(" ", "-")
    while "--" in normalized:
        normalized = normalized.replace("--", "-")
    if normalized in _PROVIDER_MODEL_UNDERSCORE_ALIASES:
        return _PROVIDER_MODEL_UNDERSCORE_ALIASES[normalized]
    return normalized


ROUTE_FAMILY_LIVE_STORY = "narrative_live_generation"
ROUTE_FAMILY_PREVIEW = "narrative_preview_generation"
ROUTE_FAMILY_WRITERS_ROOM = "writers_room_revision_assist"
ROUTE_FAMILY_RESEARCH = "research"
ROUTE_FAMILY_VALIDATION = "narrative_validation_semantic"
ROUTE_FAMILY_RETRIEVAL_QUERY = "retrieval_query_expansion"

# Maps a route id to the family it belongs to for truth-surface reporting.
_ROUTE_ID_TO_FAMILY: dict[str, str] = {
    "narrative_live_generation_global": ROUTE_FAMILY_LIVE_STORY,
    "narrative_preview_generation_global": ROUTE_FAMILY_PREVIEW,
    "writers_room_revision_assist_global": ROUTE_FAMILY_WRITERS_ROOM,
    "research_synthesis_global": ROUTE_FAMILY_RESEARCH,
    "research_revision_drafting_global": ROUTE_FAMILY_RESEARCH,
    "narrative_validation_semantic_global": ROUTE_FAMILY_VALIDATION,
    "retrieval_query_expansion_global": ROUTE_FAMILY_RETRIEVAL_QUERY,
}


class LiveStoryRoutingError(RuntimeError):
    """Raised when the governed routing policy cannot fulfill a live story request truthfully.

    Raised instead of silently substituting a preview/writers-room/research route for a
    live player story turn. Operator action: publish the missing route in Administration
    Center and call POST /api/internal/story/runtime/reload-config.
    """


@dataclass(slots=True)
class GovernedStoryRoutingPolicy:
    registry: ModelRegistry
    routes: dict[str, dict[str, Any]]
    generation_mode: str = "mock_only"
    # Ephemeral metadata describing the most recent routing choice. Readers
    # (the graph executor's ``_route_model`` node) use this to publish
    # truthful route-family information onto the per-turn state without
    # changing the shared ``RoutingDecision`` dataclass in
    # ``story_runtime_core``.
    _last_choice_meta: dict[str, Any] | None = None

    def choose(
        self,
        *,
        task_type: str,
        dramatic_requirements: dict[str, Any] | None = None,
    ) -> RoutingDecision:
        resolved = self._resolve_route_for_task(task_type)
        route = resolved["route"]
        route_id = resolved["route_id"]
        route_family = resolved["route_family"]
        expected_family = resolved["expected_family"]
        substitution_occurred = resolved["substitution_occurred"]

        preferred = str(route.get("preferred_model_id") or "").strip() or None
        fallback = str(route.get("fallback_model_id") or "").strip() or None
        mock_mid = str(route.get("mock_model_id") or "").strip() or None

        def _is_non_mock_model(model_id: str | None) -> bool:
            if not model_id:
                return False
            spec = self.registry.get(model_id)
            return spec is not None and str(spec.provider or "").strip().lower() != "mock"

        preferred_ai = preferred if _is_non_mock_model(preferred) else None
        fallback_ai = fallback if _is_non_mock_model(fallback) else None

        req = dramatic_requirements if isinstance(dramatic_requirements, dict) else {}
        complexity = str(req.get("dialogue_complexity") or "").strip().lower()
        scene_pressure = str(req.get("scene_pressure") or "").strip().lower()
        escalation_density = str(req.get("escalation_density") or "").strip().lower()
        actor_count_raw = req.get("actor_count")
        try:
            actor_count = int(actor_count_raw) if actor_count_raw is not None else 1
        except (TypeError, ValueError):
            actor_count = 1
        high_complexity = (
            complexity == "high"
            or scene_pressure in {"high_blame", "thread_pressure_high"}
            or escalation_density == "high"
            or actor_count >= 2
        )
        drama_profile = "high_complexity" if high_complexity else "standard_complexity"

        mode = (str(self.generation_mode or "").strip().lower() or "mock_only")
        if mode == "ai_only":
            if high_complexity:
                selected = preferred_ai or fallback_ai
                fallback_chain = fallback_ai or None
            else:
                selected = fallback_ai or preferred_ai
                fallback_chain = preferred_ai or None
            if not selected:
                raise ValueError(
                    f"generation_execution_mode=ai_only but no AI model available for task_type={task_type!r}"
                )
            mock_fallback_blocked = True
        elif mode == "mock_only":
            selected = mock_mid
            fallback_chain = None
            mock_fallback_blocked = False
        else:  # hybrid (default)
            if high_complexity:
                selected = preferred_ai or fallback_ai or mock_mid
                fallback_chain = fallback_ai or mock_mid
            else:
                selected = fallback_ai or preferred_ai or mock_mid
                fallback_chain = preferred_ai or mock_mid
            mock_fallback_blocked = False

        if not selected:
            raise ValueError(f"No governed model configured for task_type={task_type!r}")
        spec = self.registry.get(selected)
        if spec is None:
            raise ValueError(f"Governed route selected missing model spec: {selected!r}")

        # Produce a route_reason that tells operators whether the chosen
        # route family is the expected one. Earlier behavior labeled every
        # decision ``role_matrix_primary`` regardless of which family ended
        # up servicing the turn.
        if substitution_occurred:
            route_reason = f"governed_route_substituted:{expected_family}->{route_family}"
        else:
            route_reason = f"governed_route_primary:{route_family}"

        self._last_choice_meta = {
            "route_id": route_id,
            "route_family": route_family,
            "route_family_expected": expected_family,
            "route_substitution_occurred": substitution_occurred,
            "generation_execution_mode": mode,
            "mock_fallback_blocked": mock_fallback_blocked,
            "drama_aware_profile": drama_profile,
            "drama_aware_requirements": req or None,
        }
        return RoutingDecision(
            selected_model=selected,
            selected_provider=spec.provider,
            route_reason=route_reason,
            fallback_model=fallback_chain,
        )

    def _resolve_route_for_task(self, task_type: str) -> dict[str, Any]:
        """Pick a route for a task_type with no silent cross-family substitution.

        - narrative_formulation (live story turns): only ``narrative_live_generation_global``.
          If missing, raise ``LiveStoryRoutingError`` rather than leak into preview /
          writers-room / research families.
        - classification (validation / query expansion): accept the validation or
          retrieval-query-expansion route; fail explicitly if neither is published.
        - Any other task_type: fail explicitly. No catch-all fallback over
          ``self.routes.values()``.
        """
        task = (task_type or "").strip().lower()
        if task == "classification":
            expected_family = ROUTE_FAMILY_VALIDATION
            # Classification tasks (scope / legality checks, query expansion)
            # may degrade to the live narrative route if no dedicated
            # validation route is published. The substitution is labeled
            # truthfully so operators can see it in
            # ``runtime_governance_surface.primary_route_selection``.
            ordered = [
                "narrative_validation_semantic_global",
                "retrieval_query_expansion_global",
                "narrative_live_generation_global",
            ]
        elif task in {"narrative_formulation", "narrative_generation", "narrative"}:
            expected_family = ROUTE_FAMILY_LIVE_STORY
            # Live narrative turns have no cross-family fallback: if the live
            # route is missing, the runtime fails explicitly rather than leak
            # player turns into preview / writers-room / research families.
            ordered = ["narrative_live_generation_global"]
        else:
            raise LiveStoryRoutingError(
                f"LIVE_STORY_RUNTIME_BLOCKED: no governed route family is registered for "
                f"task_type={task_type!r}. Route families must be declared explicitly; "
                f"the governed policy refuses to substitute an unrelated route."
            )

        for route_id in ordered:
            route = self.routes.get(route_id)
            if isinstance(route, dict):
                family = _ROUTE_ID_TO_FAMILY.get(route_id, expected_family)
                return {
                    "route": route,
                    "route_id": route_id,
                    "route_family": family,
                    "expected_family": expected_family,
                    "substitution_occurred": family != expected_family,
                }

        available = sorted(self.routes.keys())
        raise LiveStoryRoutingError(
            f"LIVE_STORY_RUNTIME_BLOCKED: expected route family {expected_family!r} "
            f"(route_ids={ordered}) is not published in governed runtime config. "
            f"Refusing to silently substitute from available route_ids={available}. "
            f"Publish the missing route in Administration Center and reload."
        )


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
                                print(f"DEBUG: Credential fetch ok for {provider_id}: present={bool(api_key)}", flush=True)
                            else:
                                print(f"DEBUG: Invalid response from credential endpoint for {provider_id}: {response.status_code}", flush=True)
                        else:
                            print(f"DEBUG: Failed to fetch credential for {provider_id}: HTTP {response.status_code}", flush=True)
                except Exception as e:
                    print(f"DEBUG: Exception fetching credential for {provider_id}: {type(e).__name__}", flush=True)

        print(f"DEBUG: Building adapter for {provider_id} ({provider_type}): api_key_present={bool(api_key)}", flush=True)
        if provider_type in {"openai", "openrouter"}:
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
        if role in {"embedding", "embeddings", "embedding_role", "text_embedding", "text_embeddings"}:
            continue
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
