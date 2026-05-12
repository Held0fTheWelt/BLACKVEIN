"""Static MCP tool descriptions and JSON input schemas for the default registry."""

from typing import Any

MCP_DEFAULT_TOOL_DESCRIPTIONS: dict[str, str] = {
    "wos.system.health": "Check backend system health status",
    "wos.session.create": "Create a new session for a module (authority-respecting backend flow only)",
    "wos.goc.list_modules": "List available modules",
    "wos.goc.get_module": "Get module metadata and file list",
    "wos.content.search": "Search content with regex pattern",
    "wos.capabilities.catalog": "Canonical capability surface with governance metadata (read-only mirror)",
    "wos.mcp.operator_truth": "Compact MCP operator truth (profile, route, policy, no-eligible discipline)",
    "wos.session.get": "Session snapshot (read-only, authority-respecting backend mirror)",
    "wos.session.execute_turn": "Execute turn via backend → world-engine (POST /turns; pass player_input or prompt)",
    "wos.session.logs": "Session event logs (read-only, authority-respecting audit surfaces)",
    "wos.session.state": "Session state snapshot (read-only, authority-respecting runtime state machine)",
    "wos.session.diag": "Session diagnostics (read-only, authority-respecting backend mirror)",
    "wos.research.source.inspect": "Inspect normalized research source with anchors and aspects",
    "wos.research.aspect.extract": "Read extracted aspect records for a source",
    "wos.research.claim.list": "List structured research claims",
    "wos.research.run.get": "Get one research run with deterministic outputs",
    "wos.research.exploration.graph": "Get exploration graph for one run",
    "wos.canon.issue.inspect": "Inspect structured canon issues",
    "wos.research.explore": "Run bounded research exploration with mandatory budget",
    "wos.research.validate": "Validate research run claims in review-bound mode",
    "wos.research.bundle.build": "Build review-safe research bundle from run output",
    "wos.canon.improvement.propose": "Generate taxonomy-bound canon improvement proposals",
    "wos.canon.improvement.preview": "Preview generated canon improvement proposals",
    "run_projection_tests": "Run projection pytest suite and return structured pass/fail",
    "fetch_langfuse_trace": "Fetch one Langfuse trace and normalize metadata/scores",
    "query_langfuse_traces": "Query recent Langfuse traces with optional filters",
    "assert_langfuse_opening_contract": "Assert live/test opening contract fields on a Langfuse trace",
    "summarize_live_opening_matrix": "Summarize live opening matrix across recent Langfuse traces",
    "fetch_langfuse_trace_scores": "Fetch deterministic gates and LLM-as-a-Judge scores for a live trace (filters non-live by default)",
    "summarize_opening_judge_scores": "Matrix of deterministic + categorical judge categories for recent live traces (opening + turn judges), filterable by role and trace.name",
    "build_opening_quality_context": "Build AI-readable quality context for a live opening trace: gates, judge scores, recommended repair card",
    "summarize_runtime_aspect_matrix": "Summarize backend-owned RuntimeAspectLedger evidence across Langfuse turn traces (backend.turn.execute UI roots plus world-engine.turn.execute legacy/runtime traces)",
    "summarize_beat_realization_failures": "Summarize traces where a selected beat was missing, degraded, or lost in projection",
    "summarize_narrator_npc_authority": "Summarize narrator/NPC authority contracts and violations from runtime aspect evidence",
    "summarize_capability_realization": "Summarize selected, realized, missing, and forbidden dramatic runtime capabilities",
    "summarize_visible_projection_origin_loss": "Summarize visible block origin metadata loss from backend runtime aspects",
}

MCP_DEFAULT_TOOL_INPUT_SCHEMAS: dict[str, dict[str, Any]] = {
    "wos.system.health": {"type": "object", "properties": {}, "required": []},
    "wos.session.create": {
        "type": "object",
        "properties": {
            "module_id": {"type": "string"},
            "module_version": {"type": "string"},
        },
        "required": ["module_id"],
    },
    "wos.goc.list_modules": {"type": "object", "properties": {}, "required": []},
    "wos.goc.get_module": {
        "type": "object",
        "properties": {"module_id": {"type": "string"}},
        "required": ["module_id"],
    },
    "wos.content.search": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "case_sensitive": {"type": "boolean"},
        },
        "required": ["pattern"],
    },
    "wos.capabilities.catalog": {"type": "object", "properties": {}, "required": []},
    "wos.mcp.operator_truth": {
        "type": "object",
        "properties": {"probe_backend": {"type": "boolean"}},
        "required": [],
    },
    "wos.session.diag": {
        "type": "object",
        "properties": {"session_id": {"type": "string"}},
        "required": ["session_id"],
    },
    "wos.session.get": {
        "type": "object",
        "properties": {"session_id": {"type": "string"}},
        "required": ["session_id"],
    },
    "wos.session.logs": {
        "type": "object",
        "properties": {
            "session_id": {"type": "string"},
            "limit": {"type": "integer"},
        },
        "required": ["session_id"],
    },
    "wos.session.state": {
        "type": "object",
        "properties": {"session_id": {"type": "string"}},
        "required": ["session_id"],
    },
    "wos.session.execute_turn": {
        "type": "object",
        "properties": {
            "session_id": {"type": "string"},
            "player_input": {"type": "string"},
            "prompt": {"type": "string"},
            "input": {"type": "string"},
        },
        "required": ["session_id"],
    },
    "wos.research.source.inspect": {
        "type": "object",
        "properties": {"source_id": {"type": "string"}},
        "required": ["source_id"],
    },
    "wos.research.aspect.extract": {
        "type": "object",
        "properties": {"source_id": {"type": "string"}},
        "required": ["source_id"],
    },
    "wos.research.claim.list": {
        "type": "object",
        "properties": {"work_id": {"type": "string"}},
        "required": [],
    },
    "wos.research.run.get": {
        "type": "object",
        "properties": {"run_id": {"type": "string"}},
        "required": ["run_id"],
    },
    "wos.research.exploration.graph": {
        "type": "object",
        "properties": {"run_id": {"type": "string"}},
        "required": ["run_id"],
    },
    "wos.canon.issue.inspect": {
        "type": "object",
        "properties": {"module_id": {"type": "string"}},
        "required": [],
    },
    "wos.research.explore": {
        "type": "object",
        "properties": {
            "work_id": {"type": "string"},
            "module_id": {"type": "string"},
            "seed_question": {"type": "string"},
            "source_inputs": {"type": "array"},
            "budget": {"type": "object"},
        },
        "required": ["work_id", "module_id", "source_inputs", "budget"],
    },
    "wos.research.validate": {
        "type": "object",
        "properties": {"run_id": {"type": "string"}},
        "required": ["run_id"],
    },
    "wos.research.bundle.build": {
        "type": "object",
        "properties": {"run_id": {"type": "string"}},
        "required": ["run_id"],
    },
    "wos.canon.improvement.propose": {
        "type": "object",
        "properties": {"module_id": {"type": "string"}},
        "required": ["module_id"],
    },
    "wos.canon.improvement.preview": {
        "type": "object",
        "properties": {"module_id": {"type": "string"}},
        "required": ["module_id"],
    },
    "run_projection_tests": {
        "type": "object",
        "properties": {
            "extra_pytest_args": {
                "type": "array",
                "items": {"type": "string"},
            }
        },
        "required": [],
    },
    "fetch_langfuse_trace": {
        "type": "object",
        "properties": {"langfuse_trace_id": {"type": "string"}},
        "required": ["langfuse_trace_id"],
    },
    "query_langfuse_traces": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer"},
            "trace_origin": {"type": "string"},
            "canonical_player_flow": {"type": "boolean"},
            "execution_tier": {"type": "string"},
            "trace_name": {"type": "string"},
        },
        "required": [],
    },
    "assert_langfuse_opening_contract": {
        "type": "object",
        "properties": {
            "mode": {"type": "string"},
            "langfuse_trace_id": {"type": "string"},
            "limit": {"type": "integer"},
        },
        "required": [],
    },
    "summarize_live_opening_matrix": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer"},
            "execution_tier": {"type": "string"},
            "trace_name": {"type": "string"},
        },
        "required": [],
    },
    "fetch_langfuse_trace_scores": {
        "type": "object",
        "properties": {
            "trace_id": {"type": "string"},
            "allow_non_live": {"type": "boolean"},
        },
        "required": ["trace_id"],
    },
    "summarize_opening_judge_scores": {
        "type": "object",
        "properties": {
            "trace_origin": {"type": "string"},
            "execution_tier": {"type": "string"},
            "canonical_player_flow": {"type": "boolean"},
            "trace_name": {"type": "string"},
            "roles": {"type": "array", "items": {"type": "string"}},
            "limit_per_role": {"type": "integer"},
        },
        "required": [],
    },
    "build_opening_quality_context": {
        "type": "object",
        "properties": {
            "trace_id": {"type": "string"},
            "include_raw_reasoning": {"type": "boolean"},
        },
        "required": ["trace_id"],
    },
    "summarize_runtime_aspect_matrix": {
        "type": "object",
        "properties": {
            "trace_id": {"type": "string"},
            "limit": {"type": "integer"},
            "trace_origin": {"type": "string"},
            "execution_tier": {"type": "string"},
            "canonical_player_flow": {"type": "boolean"},
            "trace_name": {"type": "string"},
        },
        "required": [],
    },
    "summarize_beat_realization_failures": {
        "type": "object",
        "properties": {
            "trace_id": {"type": "string"},
            "limit": {"type": "integer"},
            "trace_origin": {"type": "string"},
            "execution_tier": {"type": "string"},
            "canonical_player_flow": {"type": "boolean"},
            "trace_name": {"type": "string"},
        },
        "required": [],
    },
    "summarize_narrator_npc_authority": {
        "type": "object",
        "properties": {
            "trace_id": {"type": "string"},
            "limit": {"type": "integer"},
            "trace_origin": {"type": "string"},
            "execution_tier": {"type": "string"},
            "canonical_player_flow": {"type": "boolean"},
            "trace_name": {"type": "string"},
        },
        "required": [],
    },
    "summarize_capability_realization": {
        "type": "object",
        "properties": {
            "trace_id": {"type": "string"},
            "limit": {"type": "integer"},
            "trace_origin": {"type": "string"},
            "execution_tier": {"type": "string"},
            "canonical_player_flow": {"type": "boolean"},
            "trace_name": {"type": "string"},
        },
        "required": [],
    },
    "summarize_visible_projection_origin_loss": {
        "type": "object",
        "properties": {
            "trace_id": {"type": "string"},
            "limit": {"type": "integer"},
            "trace_origin": {"type": "string"},
            "execution_tier": {"type": "string"},
            "canonical_player_flow": {"type": "boolean"},
            "trace_name": {"type": "string"},
        },
        "required": [],
    },
}
