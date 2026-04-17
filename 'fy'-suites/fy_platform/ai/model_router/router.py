from __future__ import annotations

from fy_platform.ai.schemas.common import ModelRouteDecision


class ModelRouter:
    TASK_POLICIES = {
        'classify': ('slm', 'local-slim-classifier', 'cheap'),
        'extract': ('slm', 'local-slim-extractor', 'cheap'),
        'cluster': ('slm', 'local-slim-cluster', 'cheap'),
        'summarize': ('slm', 'local-slim-summarizer', 'cheap'),
        'explain': ('llm', 'local-general-llm', 'moderate'),
        'triage': ('llm', 'local-general-llm', 'moderate'),
        'compare': ('llm', 'local-general-llm', 'moderate'),
        'prepare_fix': ('llm', 'local-code-llm', 'expensive'),
        'prepare_context_pack': ('slm', 'local-slim-retrieval-helper', 'cheap'),
    }

    def route(self, task_type: str) -> ModelRouteDecision:
        tier, model, budget = self.TASK_POLICIES.get(task_type, ('slm', 'local-slim-default', 'cheap'))
        fallback = ['deterministic-fallback']
        if tier == 'llm':
            fallback.insert(0, 'local-slim-default')
        return ModelRouteDecision(
            task_type=task_type,
            selected_tier=tier,
            selected_model=model,
            reason=f'policy_route:{task_type}',
            budget_class=budget,
            fallback_chain=fallback,
        )
