# ai_stack/tests/test_operational_profile.py
from __future__ import annotations

from ai_stack.operational_profile import (
    prompt_length_bucket,
    build_operational_cost_hints_for_runtime_graph,
    build_operational_cost_hints_from_retrieval,
)


def test_prompt_length_bucket_small() -> None:
    assert prompt_length_bucket(0) == "small"
    assert prompt_length_bucket(1000) == "small"
    assert prompt_length_bucket(3999) == "small"


def test_prompt_length_bucket_medium() -> None:
    assert prompt_length_bucket(4000) == "medium"
    assert prompt_length_bucket(8000) == "medium"
    assert prompt_length_bucket(15999) == "medium"


def test_prompt_length_bucket_large() -> None:
    assert prompt_length_bucket(16000) == "large"
    assert prompt_length_bucket(50000) == "large"


def test_prompt_length_bucket_negative_becomes_zero() -> None:
    assert prompt_length_bucket(-100) == "small"
    assert prompt_length_bucket(-1) == "small"


def test_build_operational_cost_hints_for_runtime_graph_all_none() -> None:
    result = build_operational_cost_hints_for_runtime_graph(
        retrieval=None,
        generation=None,
        graph_execution_health="ok",
        model_prompt=None,
        fallback_path_taken=False,
    )
    assert result["disclaimer"] == "coarse_operational_signals_not_financial_estimates"
    assert result["retrieval_route"] == ""
    assert result["retrieval_status"] == ""
    assert result["prompt_length_bucket"] == "small"
    assert result["prompt_length_chars"] == 0
    assert result["model_fallback_used"] is False


def test_build_operational_cost_hints_for_runtime_graph_with_retrieval() -> None:
    retrieval = {
        "retrieval_route": "hybrid",
        "status": "ok",
        "embedding_model_id": "text-embedding-3-large",
        "hit_count": 3,
    }
    generation = {
        "fallback_used": False,
        "attempted": True,
        "success": True,
        "metadata": {
            "adapter_invocation_mode": "forward_pass",
        },
    }
    result = build_operational_cost_hints_for_runtime_graph(
        retrieval=retrieval,
        generation=generation,
        graph_execution_health="ok",
        model_prompt="This is a test prompt",
        fallback_path_taken=False,
    )
    assert result["retrieval_route"] == "hybrid"
    assert result["retrieval_status"] == "ok"
    assert result["retrieval_hit_count"] == 3
    assert result["adapter_invocation_mode"] == "forward_pass"
    assert result["primary_generation_success"] is True
    assert result["prompt_length_bucket"] == "small"


def test_build_operational_cost_hints_for_runtime_graph_with_fallback() -> None:
    generation = {
        "fallback_used": True,
        "attempted": True,
        "success": False,
    }
    result = build_operational_cost_hints_for_runtime_graph(
        retrieval=None,
        generation=generation,
        graph_execution_health="degraded",
        model_prompt=None,
        fallback_path_taken=True,
    )
    assert result["model_fallback_used"] is True
    assert result["fallback_path_taken"] is True
    assert result["graph_execution_health"] == "degraded"


def test_build_operational_cost_hints_for_runtime_graph_large_prompt() -> None:
    large_prompt = "x" * 20000
    result = build_operational_cost_hints_for_runtime_graph(
        retrieval=None,
        generation=None,
        graph_execution_health="ok",
        model_prompt=large_prompt,
        fallback_path_taken=False,
    )
    assert result["prompt_length_chars"] == 20000
    assert result["prompt_length_bucket"] == "large"


def test_build_operational_cost_hints_from_retrieval_all_none() -> None:
    result = build_operational_cost_hints_from_retrieval(None)
    assert result["disclaimer"] == "coarse_operational_signals_not_financial_estimates"
    assert result["retrieval_route"] == ""
    assert result["retrieval_status"] == ""
    assert result["retrieval_hit_count"] is None


def test_build_operational_cost_hints_from_retrieval_with_data() -> None:
    retrieval = {
        "retrieval_route": "sparse_fallback",
        "status": "degraded",
        "embedding_model_id": "sparse-bm25",
        "hit_count": 2,
    }
    result = build_operational_cost_hints_from_retrieval(retrieval)
    assert result["retrieval_route"] == "sparse_fallback"
    assert result["retrieval_status"] == "degraded"
    assert result["retrieval_hit_count"] == 2
    assert result["embedding_model_id"] == "sparse-bm25"
    assert "retrieval_trace_schema_version" in result


def test_build_operational_cost_hints_from_retrieval_invalid_type() -> None:
    result = build_operational_cost_hints_from_retrieval("not a dict")  # type: ignore
    assert result["retrieval_route"] == ""
    assert result["retrieval_status"] == ""
