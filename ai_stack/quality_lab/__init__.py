"""Quality Lab — read-only MCP diagnostics for World of Shadows.

See [ADR-0040](../../docs/ADR/adr-0040-quality-lab-mcp-runtime-diagnostics.md).

Phase 1 exposes evaluator catalog loading and judgment interpretation; later
phases add trace analysis, problem clustering, repair planning, and content
revision planning. All surfaces are analysis-only; deterministic runtime
gates from ADR-0033 remain authoritative.
"""

from ai_stack.quality_lab.evaluator_catalog import (
    EvaluatorView,
    category_severity_bucket,
    evaluator_view,
    evaluator_views_for_scope,
    list_evaluator_views,
)
from ai_stack.quality_lab.judgment_interpreter import interpret_judgments
from ai_stack.quality_lab.mcp_exchange_interpreter import (
    CANONICAL_TRACE_NAMES,
    MCP_EXCHANGE_FOCUS_AREAS,
    REQUIRED_REQUEST_CONTEXT_FIELDS,
    interpret_mcp_exchange,
)
from ai_stack.quality_lab.pattern_interpreter import (
    PATTERN_CLUSTER_FIELDS,
    QUALITY_LAB_PATTERN_TOOL_NAMES,
    find_patterns,
    suggest_investigation,
)
from ai_stack.quality_lab.planning_interpreter import (
    DEFAULT_REPAIR_CONSTRAINTS,
    QUALITY_LAB_PLANNING_TOOL_NAMES,
    plan_content_revision,
    plan_repair_wave,
    refine_judge_set,
)
from ai_stack.quality_lab.schemas import (
    SEVERITY_BUCKETS,
    SOURCE_KINDS,
    user_decision_prompt,
)
from ai_stack.quality_lab.trace_interpreter import (
    ASPECT_NAMES,
    EXPECTED_LIVE_METADATA_FIELDS,
    classify_trace_kind,
    interpret_trace,
)

__all__ = [
    "ASPECT_NAMES",
    "CANONICAL_TRACE_NAMES",
    "DEFAULT_REPAIR_CONSTRAINTS",
    "EXPECTED_LIVE_METADATA_FIELDS",
    "EvaluatorView",
    "MCP_EXCHANGE_FOCUS_AREAS",
    "PATTERN_CLUSTER_FIELDS",
    "QUALITY_LAB_PATTERN_TOOL_NAMES",
    "QUALITY_LAB_PLANNING_TOOL_NAMES",
    "REQUIRED_REQUEST_CONTEXT_FIELDS",
    "SEVERITY_BUCKETS",
    "SOURCE_KINDS",
    "category_severity_bucket",
    "classify_trace_kind",
    "evaluator_view",
    "evaluator_views_for_scope",
    "find_patterns",
    "interpret_judgments",
    "interpret_mcp_exchange",
    "interpret_trace",
    "list_evaluator_views",
    "plan_content_revision",
    "plan_repair_wave",
    "refine_judge_set",
    "suggest_investigation",
    "user_decision_prompt",
]
