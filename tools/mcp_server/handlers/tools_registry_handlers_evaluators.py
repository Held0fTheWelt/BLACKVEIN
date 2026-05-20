"""MCP handlers for WoS Langfuse LLM-as-a-Judge evaluator catalog (read-only, no Langfuse writes)."""

from __future__ import annotations

from typing import Any, Callable

from ai_stack.langfuse.langfuse_evaluator_catalog import (
    ORDERED_CATEGORICAL_EVALUATORS,
    all_categorical_evaluator_specs,
    build_langfuse_sync_preview_payload,
    evaluator_spec_to_public_dict,
    get_categorical_evaluator_spec,
    langfuse_evaluator_filter_templates,
)


def _available_names() -> list[str]:
    return [s.name for s in all_categorical_evaluator_specs()]


def _not_found(name: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": "evaluator_not_found",
            "message": f"Unknown evaluator: {name!r}",
            "available": _available_names(),
        },
    }


def build_evaluators_mcp_handlers() -> dict[str, Callable[..., dict[str, Any]]]:
    def wos_evaluators_catalog(arguments: dict[str, Any]) -> dict[str, Any]:
        inc = arguments.get("include_prompts")
        include_prompts = bool(inc) if isinstance(inc, bool) else False
        return {
            "ok": True,
            "evaluators": [
                evaluator_spec_to_public_dict(s, include_prompts=include_prompts)
                for s in ORDERED_CATEGORICAL_EVALUATORS
            ],
            "count": len(ORDERED_CATEGORICAL_EVALUATORS),
            "langfuse_filter_templates": langfuse_evaluator_filter_templates(),
        }

    def wos_evaluators_get(arguments: dict[str, Any]) -> dict[str, Any]:
        name = str(arguments.get("name") or "").strip()
        if not name:
            return {
                "ok": False,
                "error": {
                    "code": "invalid_input",
                    "message": "name is required",
                    "available": _available_names(),
                },
            }
        spec = get_categorical_evaluator_spec(name)
        if spec is None:
            return _not_found(name)
        return {
            "ok": True,
            "evaluator": evaluator_spec_to_public_dict(spec, include_prompts=True),
        }

    def wos_evaluators_langfuse_sync_preview(arguments: dict[str, Any]) -> dict[str, Any]:
        name = str(arguments.get("name") or "").strip()
        if not name:
            return {
                "ok": False,
                "error": {
                    "code": "invalid_input",
                    "message": "name is required",
                    "available": _available_names(),
                },
            }
        payload = build_langfuse_sync_preview_payload(name)
        if payload is None:
            return _not_found(name)
        return {"ok": True, "langfuse_sync_preview": payload}

    return {
        "wos.evaluators.catalog": wos_evaluators_catalog,
        "wos.evaluators.get": wos_evaluators_get,
        "wos.evaluators.langfuse_sync_preview": wos_evaluators_langfuse_sync_preview,
    }
