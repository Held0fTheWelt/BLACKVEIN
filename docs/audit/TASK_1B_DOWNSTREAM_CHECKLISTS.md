# Task 1B — Downstream execution checklists

**Purpose:** Operational artifacts referenced by the Task 1B plan todos. **Normative baseline** remains [TASK_1B_CROSS_STACK_COHESION_BASELINE.md](TASK_1B_CROSS_STACK_COHESION_BASELINE.md).

**Rules:** Do not claim GoC normalization complete or cohesion closed using **tests alone**—see Task 1B §8. If Task 1B baseline is **stale** (§9), refresh or replace it before using these checklists as control input.

---

## A. GoC relocation and renamespace gate (P0)

**Blocker:** No directory rename under `content/modules/`, no `module_id` change, no writers-room registry ID renamespace for God of Carnage until this section is satisfied.

**Authority:** Task 1B §6 and §5.1 (P0 dependency classes).

| P0 class (§5.1) | Closed list of tracked references (or tool inventory + sign-off) | Owner | Date |
|-----------------|-------------------------------------------------------------------|-------|------|
| ID_literal | [ ] | | |
| Path_filesystem | [ ] | | |
| Registry_prompt | [ ] | | |
| Schema_contract | [ ] | | |
| RAG_lane | [ ] | | |
| Runtime_graph | [ ] | | |
| MCP_tool | [ ] | | |
| Normative_doc | [ ] | | |
| Fixture_frozen | [ ] | | |

**Sign-off (required to lift the gate):** Name: _______________  Date: _______________

---

## B. P0 workflow seam audit worklist

**Authority:** Task 1B §5.5 (material seams). Inspect **producer and consumer** surfaces; record paths and dates. **Not** satisfied by green CI only.

| # | Workflow (from §5.5) | Declared surface | Actual / apparent surface | Producer surfaces inspected (paths) | Consumer surfaces inspected (paths) | Cohesion finding | Inspector | Date |
|---|----------------------|------------------|---------------------------|--------------------------------------|-------------------------------------|------------------|-----------|------|
| 1 | Live play session | `docs/architecture/runtime_authority_decision.md` | `docker-compose.yml` + `world-engine/app/story_runtime/manager.py` | | | | | |
| 2 | Module load for governance | Backend content services | `backend/app/content/module_loader.py` | | | | | |
| 3 | Retrieval for turns | RAG governance docs | `ai_stack/rag.py` + world-engine retriever wiring | | | | | |

**Optional P1 follow-through (same columns):** Authoring assistance (writers-room vs YAML), MCP-assisted editing (`tools/mcp_server/fs_tools.py`), external evaluator mirror (`outgoing/` vs `docs/g9_evaluator_b_external_package/`).
