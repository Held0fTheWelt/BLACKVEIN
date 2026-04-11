# MVP WOS_VSL — MCP control-plane surface

**Authority:** World-engine remains the only committed runtime; MCP does not store or override narrative truth.

## Where it lives

| Piece | Location |
|-------|----------|
| Canonical tool descriptors + `mcp_suite` | `ai_stack/mcp_canonical_surface.py` |
| Suite ↔ tool ↔ resource map (human + pilot rubric) | `docs/mcp/MVP_SUITE_MAP.md` |
| Stdio JSON-RPC server (tools, resources, prompts) | `tools/mcp_server/server.py` |
| `wos://` resource handlers | `tools/mcp_server/resource_prompt_support.py` |
| Pilot metrics helpers | `ai_stack/wos_vsl_mcp_metrics.py` |

## Environment

- `WOS_MCP_SUITE` — filter exposed tools/resources/prompts to one of the five MVP suites (see `tools/mcp_server/README.md`).
- `WOS_MCP_OPERATING_PROFILE` — gate `write_capable` tools (`healthy` vs review-safe modes).
- `BACKEND_BEARER_TOKEN` — required for backend `GET /api/v1/sessions/...` used by session tools and resources.

## Validation

- Closure-style tests: `ai_stack/tests/test_wos_vsl_mvp_closure.py`, `ai_stack/tests/test_mcp_suite_map_complete.py`
- MCP server: `tools/mcp_server/tests/test_mcp_resources_prompts_and_filter.py`
