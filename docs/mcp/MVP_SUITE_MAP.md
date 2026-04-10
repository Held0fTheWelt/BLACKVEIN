# MCP suite map (operator quick reference)

**Conceptual model (tools, resources, prompts, suites, authority):** [MCP integration reference](../technical/integration/MCP.md) — read that first; this page is the **operator quick map** (tool and URI tables only).

**Roadmap cross-reference:** [ROADMAP_MVP_WOS_VSL.md](../ROADMAP_MVP_WOS_VSL.md) — suite expectations and pilot misrouting metrics are spelled out there (sections on MCP suites and review methodology).

Canonical tool names and suite membership are defined in code: `ai_stack/mcp_canonical_surface.py` (`CANONICAL_MCP_TOOL_DESCRIPTORS`). Pilot reviewers classify misrouting against the tables below.

**Runtime rule:** MCP is **control plane only**. Reads reflect backend or filesystem authority; research outputs and bundles are **review-bound**; nothing here publishes canonical module YAML or replaces live session authority.

## Suite overview

| Suite id | Responsibility |
|----------|----------------|
| `wos-admin` | Operations, health, capability catalog, operator legibility, backend session snapshot |
| `wos-author` | Draft / workspace content inspection (filesystem-backed slice material) |
| `wos-ai` | Research, evaluation, canon issue/proposal **preview** (no direct publish) |
| `wos-runtime-read` | Read-only runtime observability: diagnostics, state, event logs |
| `wos-runtime-control` | Narrow control: session shell create, guarded turn execution |

## Tools by suite

| Tool name | Suite | Notes |
|-----------|-------|-------|
| `wos.system.health` | `wos-admin` | Backend reachability |
| `wos.capabilities.catalog` | `wos-admin` | Capability registry mirror |
| `wos.mcp.operator_truth` | `wos-admin` | Surface aggregate / alignment |
| `wos.session.get` | `wos-admin` | Backend session snapshot (operator) |
| `wos.goc.list_modules` | `wos-author` | List workspace modules |
| `wos.goc.get_module` | `wos-author` | Fetch module payload |
| `wos.content.search` | `wos-author` | Repo content search |
| `wos.research.source.inspect` | `wos-ai` | Research provenance |
| `wos.research.aspect.extract` | `wos-ai` | Aspect extraction |
| `wos.research.claim.list` | `wos-ai` | Claims |
| `wos.research.run.get` | `wos-ai` | Run record |
| `wos.research.exploration.graph` | `wos-ai` | Exploration graph |
| `wos.canon.issue.inspect` | `wos-ai` | Canon issue read |
| `wos.research.explore` | `wos-ai` | Bounded exploration (review-bound) |
| `wos.research.validate` | `wos-ai` | Run validation checkpoint (see MCP doc for semantics) |
| `wos.research.bundle.build` | `wos-ai` | Review bundle |
| `wos.canon.improvement.propose` | `wos-ai` | Proposal generation (non-publish) |
| `wos.canon.improvement.preview` | `wos-ai` | Proposal preview |
| `wos.session.diag` | `wos-runtime-read` | Session diagnostics |
| `wos.session.state` | `wos-runtime-read` | Runtime/session state |
| `wos.session.logs` | `wos-runtime-read` | Session event logs |
| `wos.session.create` | `wos-runtime-control` | Create backend session shell |
| `wos.session.execute_turn` | `wos-runtime-control` | Turn execution (guarded; prefer player/runtime path) |

## MCP resources (stable reads)

Resources mirror read-only HTTP/FS paths **without** mixing read and write operations. URI scheme: `wos://…` (opaque to clients; resolved by `tools/mcp_server`). Specs: `ai_stack/mcp_static_catalog.py` (`MCP_RESOURCE_SPECS`).

| URI template | Suite | Source | Params |
|--------------|-------|--------|--------|
| `wos://system/health` | `wos-admin` | Backend health | — |
| `wos://mcp/operator_truth` | `wos-admin` | Aggregated operator truth | optional query `probe_backend=true` |
| `wos://capabilities/catalog` | `wos-admin` | Capability catalog JSON | — |
| `wos://session/{session_id}` | `wos-admin` | `GET /api/v1/sessions/{id}` | path `session_id` |
| `wos://session/{session_id}/diagnostics` | `wos-runtime-read` | Diagnostics | path |
| `wos://session/{session_id}/state` | `wos-runtime-read` | Story/runtime state | path |
| `wos://session/{session_id}/logs` | `wos-runtime-read` | Session logs | path; optional `?limit=N` |
| `wos://content/modules` | `wos-author` | Module list (FS) | — |
| `wos://content/module/{module_id}` | `wos-author` | Single module (FS) | path `module_id` |

## MCP prompts (recurring workflows)

Declared in `ai_stack/mcp_static_catalog.py` (`MCP_PROMPT_SPECS`); bodies in `tools/mcp_server/resource_prompt_support.py`.

| Prompt name | Suite | Purpose |
|-------------|-------|---------|
| `wos-admin-session-triage` | `wos-admin` | Steps to gather health + session snapshot + operator truth for a weak run |
| `wos-runtime-read-trace-review` | `wos-runtime-read` | Order: diagnostics → state → logs for a `session_id` |
| `wos-author-module-spotcheck` | `wos-author` | List modules, open one, optional content search |
| `wos-ai-research-bundle` | `wos-ai` | High-level order for exploration → validate → bundle (bounded) |

## Connection recipes (`WOS_MCP_SUITE`)

Run the same stdio server; set env before launch:

- **all suites (default):** omit `WOS_MCP_SUITE` or `WOS_MCP_SUITE=all`
- **admin only:** `WOS_MCP_SUITE=wos-admin`
- **author only:** `WOS_MCP_SUITE=wos-author`
- **AI only:** `WOS_MCP_SUITE=wos-ai`
- **runtime read only:** `WOS_MCP_SUITE=wos-runtime-read`
- **runtime control only:** `WOS_MCP_SUITE=wos-runtime-control`

See [tools/mcp_server/README.md](../../tools/mcp_server/README.md) for command examples.

## Misrouting rubric (pilot)

An interaction is **misrouted** if the suite used is not the **primary owner** in the tables above for that workflow (e.g. using `wos-ai` only to fetch session diagnostics — should be `wos-runtime-read` or `wos-admin` per intent).

Formula (manual): `misrouted_interactions / reviewed_interactions` — see roadmap MCP review section in [ROADMAP_MVP_WOS_VSL.md](../ROADMAP_MVP_WOS_VSL.md).
