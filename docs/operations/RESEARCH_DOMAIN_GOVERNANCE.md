# Research domain governance (strategic visibility)

This document describes the **layered research architecture** implemented for World of Shadows: what the administration-tool shows today, what remains on deeper MCP/workbench clients, and how **canonical truth** stays separate from **candidate findings**.

## Layers

1. **Strategic visibility / governance (administration-tool)**  
   Routes under `/manage/research/*` and APIs under `GET /api/v1/admin/research-domain/*`.  
   Purpose: ownership, posture, blockers/warnings, drill-downs, and honest “deferred execution” notes.  
   This is **not** a full freeform research IDE.

2. **MCP / workbench-adjacent execution**  
   Examples: `tools/mcp_server/` (including research handler factories), MCP Operations in admin, Inspector Suite for AI stack work.  
   Purpose: active tool use, richer experiments, script-backed workflows.  
   **Does not** silently become the canonical truth source.

3. **Canonical truth (governed promotion)**  
   Represented today by **narrative package** rows (`narrative_packages`): one **active promoted package** per `module_id`.  
   **Narrative revision candidates** and conflicts are **pre-promotion** research/governance objects — many may exist; they are not canonical until promoted through the existing narrative governance path.

## Principles (encoded in API payloads)

- Many **candidate findings** / revision candidates may coexist.  
- Many **experiments** (improvement store JSON) may coexist.  
- **One promoted canonical operational package** per governed narrative module at a time (`NarrativePackage` uniqueness on `module_id`).  
- `governance_principles` in API responses restates these rules for operators and tests.

## APIs

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/admin/research-domain/overview` | All layers + drill-down list + rollup `operational_state`. |
| `GET /api/v1/admin/research-domain/layer/<layer_id>` | One of: `source_intake`, `extraction_tuning`, `findings_candidates`, `canonical_truth`, `mcp_workbench`. |

**Feature gate:** `manage.research_governance` (admin tier).

## What is intentionally deferred

- Running arbitrary research scripts from these pages.  
- Replacing narrative promotion/review with a single “research blob”.  
- Auto-promoting MCP or RAG output into `narrative_packages` without governance.

## Related surfaces

- Narrative governance UI: `/manage/narrative/*`  
- MCP Operations: `/manage/mcp-operations`  
- Improvement / experiment APIs: existing improvement routes and on-disk `backend/var/improvement/` store  

Keep this document aligned with `backend/app/services/research_domain_governance_service.py` — that module is the source of truth for aggregated fields.
