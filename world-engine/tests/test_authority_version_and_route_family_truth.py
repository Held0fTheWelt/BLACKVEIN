"""Tests for authority rebinding and route-family truthfulness.

Authority rebinding:

- ``reload_runtime_config`` bumps ``authority_version`` so committed turns
  run under a provable, reload-sensitive authority identity rather than
  stale registry / routing components.
- The runtime truth surface and the per-turn governance surface expose the
  same authority version so operators can audit that a reload actually
  reached the live path.

Route-family truthfulness:

- ``GovernedStoryRoutingPolicy.choose`` populates ``_last_choice_meta`` with
  ``route_id``, ``route_family``, and ``route_family_expected`` so diagnostics
  can tell operators which family serviced a turn and whether a
  substitution occurred.
- Live narrative turns refuse to silently fall into preview, writers-room,
  or research families when the live route is missing: the policy raises
  ``LiveStoryRoutingError`` rather than leaking the turn.
- Classification tasks may degrade to the live route when no validation
  route is published; the substitution is labeled truthfully.
"""

from __future__ import annotations

import pytest

from app.story_runtime.governed_runtime import (
    GovernedStoryRoutingPolicy,
    LiveStoryRoutingError,
    build_governed_story_runtime_components,
    normalize_provider_model_name,
)
from app.story_runtime.manager import StoryRuntimeManager
from story_runtime_core import ModelRegistry
from story_runtime_core.model_registry import ModelSpec


def _governed_config(include_live_route: bool = True) -> dict:
    routes = []
    if include_live_route:
        routes.append(
            {
                "route_id": "narrative_live_generation_global",
                "preferred_model_id": "mock_llm",
                "mock_model_id": "mock_mock",
            }
        )
    else:
        # Only a writers_room route exists — no live route family published.
        routes.append(
            {
                "route_id": "writers_room_revision_assist_global",
                "preferred_model_id": "mock_llm",
                "mock_model_id": "mock_mock",
            }
        )
    return {
        "config_version": "v-test-1",
        "generation_execution_mode": "mock_only",
        "providers": [{"provider_id": "mock_provider", "provider_type": "mock"}],
        "models": [
            {
                "provider_id": "mock_provider",
                "model_id": "mock_llm",
                "model_role": "llm",
                "model_name": "mock-llm",
                "structured_output_capable": True,
            },
            {
                "provider_id": "mock_provider",
                "model_id": "mock_mock",
                "model_role": "mock",
                "model_name": "mock-mock",
            },
        ],
        "routes": routes,
    }


# ----- Authority version rebinding -----


def test_authority_version_bumps_on_initial_apply_and_reload() -> None:
    mgr = StoryRuntimeManager(governed_runtime_config=_governed_config())
    s0 = mgr.runtime_config_status()
    v0 = s0.get("authority_version")
    assert isinstance(v0, int)
    assert v0 >= 1
    assert s0.get("authority_applied_at_iso")

    cfg2 = _governed_config()
    cfg2["config_version"] = "v-test-2"
    mgr.reload_runtime_config(cfg2)
    s1 = mgr.runtime_config_status()
    v1 = s1.get("authority_version")
    assert v1 > v0

    # Reload with blocked (invalid) config still bumps — operator can see that
    # a reload attempt reached the live path, and authority_source reports the
    # blocked state truthfully.
    mgr.reload_runtime_config(None)
    s2 = mgr.runtime_config_status()
    v2 = s2.get("authority_version")
    assert v2 > v1
    ts = s2.get("runtime_truth_surface") or {}
    assert ts.get("authority_source") == "blocked_no_authoritative_config"
    assert ts.get("authority_version") == v2


def test_authority_version_mirrored_in_runtime_truth_surface() -> None:
    mgr = StoryRuntimeManager(governed_runtime_config=_governed_config())
    status = mgr.runtime_config_status()
    ts = status.get("runtime_truth_surface") or {}
    assert ts.get("authority_version") == status.get("authority_version")
    assert ts.get("authority_applied_at_iso") == status.get("authority_applied_at_iso")


# ----- Route-family truth and no silent cross-family substitution -----


def _policy_with_live_route() -> GovernedStoryRoutingPolicy:
    reg = ModelRegistry()
    reg.register(
        ModelSpec(
            model_name="mock_mock",
            provider="mock_provider",
            llm_or_slm="mock",
            timeout_seconds=10.0,
            structured_output_capable=False,
            cost_class="governed",
            latency_class="governed",
            use_cases=("mock",),
            provider_model_name="mock-mock",
        )
    )
    reg.register(
        ModelSpec(
            model_name="mock_llm",
            provider="mock_provider",
            llm_or_slm="llm",
            timeout_seconds=10.0,
            structured_output_capable=True,
            cost_class="governed",
            latency_class="governed",
            use_cases=("narrative",),
            provider_model_name="mock-llm",
        )
    )
    return GovernedStoryRoutingPolicy(
        registry=reg,
        routes={
            "narrative_live_generation_global": {
                "route_id": "narrative_live_generation_global",
                "preferred_model_id": "mock_llm",
                "mock_model_id": "mock_mock",
            }
        },
        generation_mode="mock_only",
    )


def _policy_with_live_route_and_ai_fallback() -> GovernedStoryRoutingPolicy:
    reg = ModelRegistry()
    reg.register(
        ModelSpec(
            model_name="mock_mock",
            provider="mock_provider",
            llm_or_slm="mock",
            timeout_seconds=10.0,
            structured_output_capable=False,
            cost_class="governed",
            latency_class="governed",
            use_cases=("mock",),
            provider_model_name="mock-mock",
        )
    )
    reg.register(
        ModelSpec(
            model_name="fast_llm",
            provider="mock_provider",
            llm_or_slm="llm",
            timeout_seconds=10.0,
            structured_output_capable=True,
            cost_class="governed",
            latency_class="governed",
            use_cases=("narrative",),
            provider_model_name="fast-llm",
        )
    )
    reg.register(
        ModelSpec(
            model_name="rich_llm",
            provider="mock_provider",
            llm_or_slm="llm",
            timeout_seconds=20.0,
            structured_output_capable=True,
            cost_class="governed",
            latency_class="governed",
            use_cases=("narrative",),
            provider_model_name="rich-llm",
        )
    )
    return GovernedStoryRoutingPolicy(
        registry=reg,
        routes={
            "narrative_live_generation_global": {
                "route_id": "narrative_live_generation_global",
                "preferred_model_id": "rich_llm",
                "fallback_model_id": "fast_llm",
                "mock_model_id": "mock_mock",
            }
        },
        generation_mode="hybrid",
    )


def test_narrative_task_reports_route_family_truth() -> None:
    policy = _policy_with_live_route()
    decision = policy.choose(task_type="narrative_formulation")
    meta = policy._last_choice_meta or {}
    assert meta["route_id"] == "narrative_live_generation_global"
    assert meta["route_family"] == "narrative_live_generation"
    assert meta["route_family_expected"] == "narrative_live_generation"
    assert meta["route_substitution_occurred"] is False
    assert decision.route_reason.startswith("governed_route_primary:")


def test_classification_task_with_only_live_route_labels_substitution() -> None:
    policy = _policy_with_live_route()
    policy.choose(task_type="classification")
    meta = policy._last_choice_meta or {}
    # No validation route is published, so the classifier degrades to the live
    # route. The substitution must be surfaced truthfully — not hidden.
    assert meta["route_family"] == "narrative_live_generation"
    assert meta["route_family_expected"] == "narrative_validation_semantic"
    assert meta["route_substitution_occurred"] is True


def test_narrative_task_without_live_route_fails_explicitly() -> None:
    reg = ModelRegistry()
    reg.register(
        ModelSpec(
            model_name="mock_mock",
            provider="mock_provider",
            llm_or_slm="mock",
            timeout_seconds=10.0,
            structured_output_capable=False,
            cost_class="governed",
            latency_class="governed",
            use_cases=("mock",),
            provider_model_name="mock-mock",
        )
    )
    # Only writers_room route is published — no live route.
    policy = GovernedStoryRoutingPolicy(
        registry=reg,
        routes={
            "writers_room_revision_assist_global": {
                "route_id": "writers_room_revision_assist_global",
                "preferred_model_id": "mock_mock",
                "mock_model_id": "mock_mock",
            }
        },
        generation_mode="mock_only",
    )
    with pytest.raises(LiveStoryRoutingError) as err:
        policy.choose(task_type="narrative_formulation")
    msg = str(err.value)
    assert "narrative_live_generation" in msg
    # The error must name both what was expected and what substitution was
    # refused, so operators don't have to guess.
    assert "writers_room_revision_assist_global" in msg
    assert "Refusing to silently substitute" in msg


def test_build_governed_components_uses_new_policy() -> None:
    cfg = _governed_config()
    components = build_governed_story_runtime_components(cfg)
    assert components is not None
    _, routing, _ = components
    assert isinstance(routing, GovernedStoryRoutingPolicy)
    routing.choose(task_type="narrative_formulation")
    meta = routing._last_choice_meta or {}
    assert meta["route_family"] == "narrative_live_generation"


def test_provider_model_name_preserves_current_openai_api_ids() -> None:
    assert normalize_provider_model_name("gpt-5.4") == "gpt-5.4"
    assert normalize_provider_model_name("gpt-5.4-mini") == "gpt-5.4-mini"
    assert normalize_provider_model_name("gpt-5.4-nano") == "gpt-5.4-nano"
    assert normalize_provider_model_name("gpt-5.5") == "gpt-5.5"


def test_build_governed_components_skips_embedding_role_models() -> None:
    cfg = _governed_config()
    cfg["models"].extend(
        [
            {
                "provider_id": "mock_provider",
                "model_id": "embed_model",
                "model_role": "embedding_role",
                "model_name": "text-embedding-3-small",
            },
            {
                "provider_id": "mock_provider",
                "model_id": "text_embed_alias_model",
                "model_role": "text_embedding",
                "model_name": "text-embedding-3-large",
            },
        ]
    )
    components = build_governed_story_runtime_components(cfg)
    assert components is not None
    registry, _, _ = components
    assert registry.get("embed_model") is None
    assert registry.get("text_embed_alias_model") is None


def test_governed_routing_prefers_rich_model_for_high_complexity_turns() -> None:
    policy = _policy_with_live_route_and_ai_fallback()
    decision = policy.choose(
        task_type="narrative_formulation",
        dramatic_requirements={
            "dialogue_complexity": "high",
            "scene_pressure": "high_blame",
            "actor_count": 3,
            "escalation_density": "high",
        },
    )
    assert decision.selected_model == "rich_llm"
    meta = policy._last_choice_meta or {}
    assert meta.get("drama_aware_profile") == "high_complexity"


def test_governed_routing_can_pick_fast_model_for_standard_complexity_turns() -> None:
    policy = _policy_with_live_route_and_ai_fallback()
    decision = policy.choose(
        task_type="narrative_formulation",
        dramatic_requirements={
            "dialogue_complexity": "low",
            "scene_pressure": "moderate_tension",
            "actor_count": 1,
            "escalation_density": "low",
        },
    )
    assert decision.selected_model == "fast_llm"
    meta = policy._last_choice_meta or {}
    assert meta.get("drama_aware_profile") == "standard_complexity"
