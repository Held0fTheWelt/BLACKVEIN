"""Loader for the small Langfuse verify handler slices."""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Any

_FRAGMENT_MODULES: tuple[str, ...] = (
    "01_imports_and_score_helpers",
    "02_judge_score_metadata",
    "03_trace_blocks_and_opening_detection",
    "04_normalized_evidence_core",
    "05_normalized_evidence_scores",
    "06_adr0041_runtime_evidence",
    "07_runtime_matrix_columns_core",
    "08_runtime_matrix_columns_narrative",
    "09_runtime_matrix_helpers",
    "10_runtime_matrix_context",
    "11_runtime_matrix_failure_selection",
    "12_runtime_matrix_base_fields",
    "13_runtime_matrix_energy_and_pacing",
    "14_runtime_matrix_time_sensory_genre",
    "15_runtime_matrix_symbolic_improv_pressure",
    "16_runtime_matrix_relationship_disclosure_variation",
    "17_runtime_matrix_momentum_irony_callbacks",
    "18_runtime_matrix_authority_agency_capabilities",
    "19_runtime_matrix_narrative_voice_tone_memory",
    "20_runtime_matrix_query_client",
    "21_assertion_contract_modes",
    "22_handler_projection_tests",
    "23_handler_trace_fetch_and_query",
    "24_handler_opening_contract",
    "25_handler_live_opening_matrix",
    "26_handler_trace_scores",
    "27_handler_opening_judge_scores",
    "28_handler_opening_quality_context",
    "29_runtime_matrix_filtering",
    "30_runtime_matrix_public_client",
    "31_langfuse_trace_query",
    "32_langfuse_query_filters_and_assertions",
    "33_handler_builder_projection_start",
    "34_handler_projection_preflight",
    "35_handler_trace_fetch_and_query",
    "36_handler_opening_contract_assertions",
    "37_handler_live_matrix_and_score_start",
    "38_handler_trace_score_payload",
    "39_handler_judge_score_summary_start",
    "40_handler_judge_matrix_rows",
    "41_handler_quality_context_start",
    "42_handler_quality_context_finish",
    "43_handler_runtime_summary_views",
)


def load_into(namespace: dict[str, Any]) -> None:
    """Execute the ordered source slices in the package namespace."""
    package = str(namespace.get("__name__") or "")
    source_parts: list[str] = []
    for module_name in _FRAGMENT_MODULES:
        module: ModuleType = importlib.import_module(f"{package}.{module_name}")
        source_parts.append(str(module.SOURCE))
    compiled = compile("\n".join(source_parts), f"{package}.__generated__", "exec")
    exec(compiled, namespace)
