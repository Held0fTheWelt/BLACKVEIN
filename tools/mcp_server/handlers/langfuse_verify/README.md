# Langfuse Verify Handlers

This package owns the read-only MCP tools that verify Langfuse evidence for
World of Shadows runtime traces.

The former single handler file was split into named slices so handler logic,
tests, and governance references no longer depend on one 3000-line module. The
package exports the same public builder and helper functions:

- `build_langfuse_verify_mcp_handlers`
- `_extract_scores_split`
- `_extract_metadata`
- `_extract_path_summary_from_trace`
- `_extract_runtime_aspect_ledger_from_trace`
- `_get_observations`
- `_langfuse_get_trace`
- `_langfuse_query_traces`
- `_runtime_aspect_matrix_row`
- `_runtime_aspect_recommended_repair`

The slices are loaded in numeric order by `loader.py`. Keep new behavior in a
clearly named slice and keep every file below 100 lines.

All tools remain read-only. Local pytest or local Langfuse evidence must stay
marked as local-only evidence and must not be promoted to live or staging proof.
