# World of Shadows MCP Server - Phase A1.2 Operator Tool Set

## Overview

Model Context Protocol (MCP) server implementing Phase A1.2: operator/developer tooling via stdio transport, with mutating tools gated by operating profile.

**Features:**
- Canonical descriptor-derived tool registry (`ai_stack/mcp_canonical_surface.py`) with per-tool **`mcp_suite`** (WOS_VSL five-suite map)
- **`resources/list`** + **`resources/read`** for stable reads (`wos://…` URIs — see `docs/mcp/MVP_SUITE_MAP.md`)
- **`prompts/list`** + **`prompts/get`** for recurring operator/author/AI workflows
- Explicit tool classes: `read_only`, `review_bound`, `write_capable` + operating profile gating
- Stable per-token/local rate limiting; trace IDs are not used as quota keys
- HTTP client with 5-second timeout and automatic retry; optional bearer token for backend session routes
- Langfuse/runtime evidence normalization for `turn_aspect_ledger`, beat, capability, narrator/NPC authority, visible-origin, commit, and hierarchical-memory proof
- Read-only Quality Lab diagnostics (`wos.quality_lab.*`) for judge, trace, MCP exchange, pattern, investigation, repair-wave, judge-set, and content-revision analysis
- **`WOS_MCP_SUITE`** env to expose only one suite’s tools/resources/prompts (default: all)

## Environment Configuration

**Bootstrap:** Starting the server via `python -m tools.mcp_server.server` (including Cursor’s stdio MCP config) loads **repository-root `.env`** first (`override=False`). Use the same **`INTERNAL_RUNTIME_CONFIG_TOKEN`** as Docker / world-engine / play-service — generated once by `docker-up.py` and stored in `.env` (ADR-0030). No separate MCP-specific token is required for Langfuse credential fetch or internal observability routes.

| Variable | Default | Purpose |
|----------|---------|---------|
| `INTERNAL_RUNTIME_CONFIG_TOKEN` | from `.env` (see above) | Same internal runtime trust token as backend internal APIs (`X-Internal-Config-Token`); optional if unset |
| `BACKEND_BASE_URL` | `http://localhost:8000` | Backend API endpoint (override for your deploy) |
| `BACKEND_BEARER_TOKEN` | (empty) | Bearer for MCP-protected session routes (`/api/v1/sessions/...`) |
| `LANGFUSE_MCP_BASE_URL` | `http://localhost:3000` for local stdio MCP | Host-side MCP Langfuse API URL. Use this when backend/world-engine use Docker DNS (`http://langfuse-web:3000`) but MCP runs outside Docker. |
| `REPO_ROOT` | (auto-detected) | Repository root directory containing `content/` |
| `WOS_MCP_OPERATING_PROFILE` | `healthy` | `healthy` allows `write_capable` tools; `review_safe` / `test_isolated` deny them |
| `WOS_MCP_SUITE` | `all` | `wos-admin` \| `wos-author` \| `wos-ai` \| `wos-runtime-read` \| `wos-runtime-control` \| `all` |
| `WOS_MCP_TELEMETRY_INGEST_URL` | (empty) | If set with `MCP_SERVICE_TOKEN`, each JSON-RPC dispatch POSTs captured log lines to `POST /api/v1/operator/mcp-telemetry/ingest` on the backend (best-effort; failures only go to stderr) |
| `MCP_SERVICE_TOKEN` | (empty) | Same token the backend expects for operator routes; required for telemetry ingest |

## Tools Available (M1 Canonical Surface)

### P0: Backend Integration

| Tool | Input | Purpose |
|------|-------|---------|
| `wos.system.health` | (none) | Check backend health status |
| `wos.session.create` | `module_id`, `module_version?` | Create new game session |

### P1: Filesystem Utilities

| Tool | Input | Purpose |
|------|-------|---------|
| `wos.goc.list_modules` | (none) | List available modules |
| `wos.goc.get_module` | `module_id` | Get module metadata and file list |
| `wos.content.search` | `pattern`, `case_sensitive?` | Search content with regex |

Session observability and research tools are implemented; see `tools_registry.py` and `docs/mcp/MVP_SUITE_MAP.md`.

### Runtime aspect verification (`wos-runtime-read`)

Langfuse verification tools normalize deterministic runtime evidence from
backend/world-engine ledgers and trace scores. Operators can query:

- `turn_aspect_ledger_present`
- `beat_selected`
- `beat_realized`
- `narrator_required_when_expected`
- `npc_takeover_absent`
- `capability_selection_present`
- `selected_capabilities_realized`
- `visible_block_origin_present`
- `required_visible_origin_preserved`
- `hierarchical_memory_present`
- `hierarchical_memory_contract_pass`

These fields are evidence reads only. MCP must not infer correctness from
visible prose, must not treat fallback/mock/degraded generation as healthy, and
must not mutate runtime state while inspecting aspect data.

### Quality Lab diagnostics (`wos-runtime-read`)

All Quality Lab tools are read-only, registered in the canonical MCP surface,
and governed by ADR-0040. They interpret evidence and propose next steps; they
do not mutate runtime state, Langfuse evaluator definitions, prompts, content,
or source code.

| Tool | Input | Purpose |
|------|-------|---------|
| `wos.quality_lab.review_judgments` | `scores` or `trace_scores_payload` | Interpret categorical LLM-as-a-Judge scores using `docs/llm-as-a-judge/` severity buckets and repair areas |
| `wos.quality_lab.review_trace` | `trace_payload` or `raw_trace` | Analyze trace metadata coverage, runtime aspect ledger, beat/capability realization, authority/origin signals, and span anomalies |
| `wos.quality_lab.review_mcp_exchange` | `request`, `response`, `focus?` | Analyze an MCP request/response pair for missing context, stale assumptions, weak analysis, and follow-up queries |
| `wos.quality_lab.find_patterns` | `trace_summaries`, `judge_results`, `cluster_by?` | Find recurring quality problems across trace and judge summaries |
| `wos.quality_lab.suggest_investigation` | `problem_cluster`, `available_context?` | Convert a problem cluster into hypotheses, evidence needs, and follow-up MCP tools |
| `wos.quality_lab.plan_repair_wave` | `improvement_candidates`, `constraints?` | Turn improvement candidates into a safe, ordered repair plan |
| `wos.quality_lab.refine_judge_set` | `judge_names`, `observed_failures`, `examples?` | Propose judge maintenance work without editing evaluator definitions |
| `wos.quality_lab.plan_content_revision` | `content_module?`, `quality_findings`, `scene_or_context?` | Connect quality findings to governed content-revision tasks |

### Wire format vs canonical name

Some MCP hosts (notably Cursor) constrain tool names to `^[A-Za-z0-9_]+$`. The
canonical descriptor identity stays dotted (`wos.system.health`) for governance
parity with [`docs/mcp/MVP_SUITE_MAP.md`](../../docs/mcp/MVP_SUITE_MAP.md),
[`docs/mcp/04_M0_contract_v0.md`](../../docs/mcp/04_M0_contract_v0.md), and
the M1 ADRs. The `tools/list` wire format emitted by this server uses the
underscored form so every host accepts every tool:

```json
{
  "name": "wos_system_health",
  "canonical_name": "wos.system.health",
  ...
}
```

`tools/call` accepts BOTH forms — dotted callers continue to work, underscored
callers (Cursor) work for the first time. The mapping is a pure `.`→`_`
substitution implemented in `cursor_safe_name()` in
[`tools_registry.py`](tools_registry.py); bijection over the canonical
descriptor set is asserted by
[`tests/test_tools_registry_aliases.py`](tests/test_tools_registry_aliases.py).

## Suite connection recipes (same binary, different env)

```bash
# Admin / operations only
set WOS_MCP_SUITE=wos-admin
python -m tools.mcp_server.server

# Authoring / draft content only
set WOS_MCP_SUITE=wos-author
python -m tools.mcp_server.server

# Research & evaluation only
set WOS_MCP_SUITE=wos-ai
python -m tools.mcp_server.server

# Read-only runtime observability
set WOS_MCP_SUITE=wos-runtime-read
python -m tools.mcp_server.server

# Narrow control (session create + guarded turn)
set WOS_MCP_SUITE=wos-runtime-control
python -m tools.mcp_server.server
```

On Unix: `export WOS_MCP_SUITE=wos-admin` then start the server.

## Running the Server

### Prerequisites

```bash
python -m pip install requests
```

### Start Server

```bash
python -m tools.mcp_server.server
```

The server reads JSON-RPC requests from stdin and writes responses to stdout.

## Example Calls

### tools/list

**Request:**
```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
```

**Response:** Shows all canonical M1 tools (descriptor-derived; no shadow list)

### tools/call: System Health

**Request:**
```json
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "wos.system.health", "arguments": {}}}
```

**Response:** Successful ``tools/call`` returns MCP ``CallToolResult``: inner payload is JSON in ``result.content[0].text``. Use ``tools.mcp_server.call_tool_result.unwrap_call_tool_result`` in tests.

```json
{"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": "{\"status\": \"healthy\", \"backend\": {\"status\": \"ok\"}}"}]}}
```

The examples below show the **inner** JSON only (after unwrap) for readability.

### tools/call: Create Session

**Request:**
```json
{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "wos.session.create", "arguments": {"module_id": "god_of_carnage"}}}
```

**Response:**
```json
{"jsonrpc": "2.0", "id": 3, "result": {"session_id": "sess-12345", "module_id": "god_of_carnage"}}
```

### tools/call: List Modules

**Request:**
```json
{"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "wos.goc.list_modules", "arguments": {}}}
```

**Response:**
```json
{"jsonrpc": "2.0", "id": 4, "result": {"modules": ["god_of_carnage"]}}
```

### tools/call: Search Content

**Request:**
```json
{"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "wos.content.search", "arguments": {"pattern": "god of carnage"}}}
```

**Response:**
```json
{"jsonrpc": "2.0", "id": 5, "result": {"pattern": "god of carnage", "hits": 2, "results": [...]}}
```

## Architecture

```
config.py              → Environment configuration + repo root detection
backend_client.py      → HTTP client (5s timeout, auto-retry)
fs_tools.py            → Filesystem utilities (list, get, search)
tools_registry.py      → Tool definitions + handlers
server.py              → JSON-RPC main loop (tools + resources + prompts)
resource_prompt_support.py → `wos://` resource catalog and prompt bodies
logging_utils.py       → Structured logging
rate_limiter.py        → Token bucket rate limiting
errors.py              → Error codes + JSON-RPC envelope
```

## Testing

```bash
pytest tools/mcp_server/tests/ -v
```

**Results:** run the MCP suites from repo root (`PYTHONPATH` = repository root):
- `python -m pytest ai_stack/tests/test_mcp_canonical_surface.py tools/mcp_server/tests/test_mcp_operational_parity_and_registry.py tools/mcp_server/tests/test_rpc.py -q --tb=short --no-cov`
- `python -m pytest backend/tests/runtime/test_mcp_enrichment.py -q --tb=short --no-cov` (from `backend/` or with equivalent pytest config)
- Full MCP tree: `python -m pytest tools/mcp_server/tests -q --tb=short --no-cov` (233 tests at ADR-0040 completion)
- 8 backend client tests
- 7 config tests
- 7 filesystem tests
- Quality Lab handler coverage for all ADR-0040 tools
- Registry and wire-alias tests for canonical dotted names and Cursor-safe names
- 5 RPC tests
- 3 rate limit tests
- 1 validation test

## Notes

- Legacy `permission` is compatibility metadata only; policy enforcement is class/profile-based
- `write_capable` tools are denied unless `WOS_MCP_OPERATING_PROFILE=healthy`
- Player/prompt request bodies sent to MCP Langfuse tracing are hashed, not stored verbatim
- HTTP timeout: 5 seconds with automatic 1x retry
- Search limits: 10MB per file, 100 hits per query
- Configuration from environment variables with defaults
- Repo root auto-detected by finding content/ folder
