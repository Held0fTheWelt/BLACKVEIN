# MCP suite map (operator quick reference)

**Conceptual model (tools, resources, prompts, suites, authority):** [MCP integration reference](../technical/integration/MCP.md) — read that first; this page is the **operator quick map** (tool and URI tables only).

**Roadmap cross-reference:** [ROADMAP_MVP_WOS_VSL.md](../MVPs/MVP_WoS_VSL/ROADMAP_MVP_WOS_VSL.md) — suite expectations and pilot misrouting metrics are spelled out there (sections on MCP suites and review methodology).

Canonical tool names and suite membership are defined in code: `ai_stack/mcp/mcp_canonical_surface.py` (`CANONICAL_MCP_TOOL_DESCRIPTORS`). Pilot reviewers classify misrouting against the tables below.

**Runtime rule:** MCP is **control plane only**. Reads reflect backend or filesystem authority; research outputs and bundles are **review-bound**; nothing here publishes canonical module YAML or replaces live session authority.

## Suite overview

| Suite id | Responsibility |
|----------|----------------|
| `wos-admin` | Operations, health, capability catalog, operator legibility, player-session snapshot |
| `wos-author` | Draft / workspace content inspection (filesystem-backed slice material) |
| `wos-ai` | Research, evaluation, canon issue/proposal **preview** (no direct publish) |
| `wos-runtime-read` | Read-only runtime observability: story-session evidence, state, story entries |
| `wos-runtime-control` | Narrow control: player-session create/resume, guarded turn execution |

## Tools by suite

| Tool name | Suite | Notes |
|-----------|-------|-------|
| `wos.system.health` | `wos-admin` | Backend reachability |
| `wos.capabilities.catalog` | `wos-admin` | Capability registry mirror |
| `wos.mcp.operator_truth` | `wos-admin` | Surface aggregate / alignment |
| `wos.session.get` | `wos-admin` | Canonical player-session snapshot by run id |
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
| `wos.session.diag` | `wos-runtime-read` | World-Engine story-session evidence |
| `wos.session.state` | `wos-runtime-read` | Player-session shell state by run id |
| `wos.session.logs` | `wos-runtime-read` | Player-session story entries by run id |
| `wos.session.create` | `wos-runtime-control` | Create or resume canonical player session |
| `wos.session.execute_turn` | `wos-runtime-control` | Turn execution through `/api/v1/game/player-sessions/<run_id>/turns` |

## MCP resources (stable reads)

Resources mirror read-only HTTP/FS paths **without** mixing read and write operations. URI scheme: `wos://…` (opaque to clients; resolved by `tools/mcp_server`). Specs: `ai_stack/mcp/mcp_static_catalog.py` (`MCP_RESOURCE_SPECS`).

| URI template | Suite | Source | Params |
|--------------|-------|--------|--------|
| `wos://system/health` | `wos-admin` | Backend health | — |
| `wos://mcp/operator_truth` | `wos-admin` | Aggregated operator truth | optional query `probe_backend=true` |
| `wos://capabilities/catalog` | `wos-admin` | Capability catalog JSON | — |
| `wos://session/{run_id}` | `wos-admin` | `GET /api/v1/game/player-sessions/{run_id}` | path `run_id` |
| `wos://session/{story_session_id}/diagnostics` | `wos-runtime-read` | `GET /api/v1/admin/ai-stack/session-evidence/{story_session_id}` | path |
| `wos://session/{run_id}/state` | `wos-runtime-read` | Player-session shell state | path |
| `wos://session/{run_id}/logs` | `wos-runtime-read` | Player-session story entries | path; optional `?limit=N` |
| `wos://content/modules` | `wos-author` | Module list (FS) | — |
| `wos://content/module/{module_id}` | `wos-author` | Single module (FS) | path `module_id` |

## MCP prompts (recurring workflows)

Declared in `ai_stack/mcp/mcp_static_catalog.py` (`MCP_PROMPT_SPECS`); bodies in `tools/mcp_server/resource_prompt_support.py`.

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

Formula (manual): `misrouted_interactions / reviewed_interactions` — see roadmap MCP review section in [ROADMAP_MVP_WOS_VSL.md](../MVPs/MVP_WoS_VSL/ROADMAP_MVP_WOS_VSL.md).
