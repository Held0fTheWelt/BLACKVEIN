"""Langfuse verify source segment: imports_and_score_helpers.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
"""MCP handlers for projection-test orchestration and Langfuse trace verification."""

from __future__ import annotations

import json
import os
import re
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests

from ai_stack.langfuse.langfuse_evaluator_catalog import (
    BACKEND_TURN_ROOT_TRACE_NAME,
    JUDGE_DISPLAY_SHORT as _JUDGE_DISPLAY_SHORT,
    JUDGE_TO_REPAIR_CARD as _JUDGE_TO_REPAIR_CARD,
    LANGFUSE_OPENING_GENERATION_FILTER_BUNDLE,
    LANGFUSE_TURN_GENERATION_FILTER_BUNDLE,
    JUDGE_ISSUE_ALIAS_TOKENS,
    LLM_AS_A_JUDGE_DOC_RELATIVE_PATH,
    MATRIX_JUDGE_COLUMN_KEYS as _MATRIX_JUDGE_COLUMN_KEYS,
    OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
    TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
    WORLD_ENGINE_TURN_TRACE_NAME,
    WOS_CATEGORICAL_JUDGES_ORDER,
    WOS_JUDGE_ISSUE_CATEGORIES as _WOS_JUDGE_ISSUE_CATEGORIES,
    build_llm_judge_interpretation as _build_llm_judge_interpretation,
    category_severity as _category_severity,
    get_categorical_evaluator_spec as _get_categorical_evaluator_spec,
    judge_names_for_scope as _judge_names_for_scope,
    normalize_judge_category_label as _normalize_judge_category_label,
)
from ai_stack.langfuse.langfuse_evidence import (
    ADR0041_LANGFUSE_SCORE_PARENT_PRESENT,
    ADR0041_LANGFUSE_SCORE_PLAN_ENFORCED,
    ADR0041_LANGFUSE_SCORE_READINESS_AGG,
    ADR0041_LANGFUSE_SCORE_READINESS_PREVIEW,
    WOS_ADR0041_RUNTIME_INTELLIGENCE_OBSERVATION_NAME,
)
from ai_stack.story_runtime.npc_agency.npc_agency_claim_readiness import assess_npc_agency_claim_readiness
from tools.mcp_server.config import Config
from tools.mcp_server.langfuse_tracing import McpLangfuseTracer


def _to_plain(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    if hasattr(value, "model_dump"):
        try:
            return _to_plain(value.model_dump())
        except Exception:
            pass
    if hasattr(value, "to_dict"):
        try:
            return _to_plain(value.to_dict())
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        try:
            return _to_plain(vars(value))
        except Exception:
            pass
    return str(value)


'''
