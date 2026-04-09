# Task 4 — GoC Dependency Sufficiency Record

## Scope and decision

- Scope: dependency sufficiency gate for GoC namespace movement, relocation, and renamespace actions.
- Decision model: hard blocker from Task 1B; no movement before P0 dependency classes are mapped with producer/consumer evidence.
- Gate outcome in this pass: **NOT LIFTED** for physical movement/renamespace. Control artifacts are complete; execution movement remains blocked pending deeper per-reference closure.

## Baseline revalidation (Task 1A/1B/2/3)

Revalidation trigger check against current tracked surface:

1. GoC-related paths/loaders/registries are still present and active (`content/modules`, `ai_stack`, `backend/app/content`, `tools/mcp_server`, `writers-room`).
2. Task 2 and Task 3 introduced/updated tracked cleanup control surfaces (`docs/audit/TASK_2_*`, `docs/audit/TASK_3_*`) after Task 1A/1B publication.
3. Documentation and test cleanup changed tracked surfaces relevant to Task 4 closure evidence.

Result:

- Task 1A sections on path ambiguity and hygiene: **revalidated and still applicable**.
- Task 1B P0 dependency class model: **revalidated and still applicable**.
- Task 2 curated docs/link repair constraints: **revalidated and still applicable**.
- Task 3 sidecar/test consistency constraints: **revalidated and still applicable**.

## P0 dependency sufficiency matrix

| P0 class | Producer surfaces verified | Consumer surfaces verified | Break mode if moved without repair | Status |
|---|---|---|---|---|
| ID literals | `ai_stack/goc_frozen_vocab.py`, `world-engine/app/content/builtins.py`, tests | `ai_stack`, `world-engine`, `backend`, `tools/mcp_server`, `frontend` tests | silent mismatch across module/template selection and assertions | mapped, not fully closed |
| Filesystem paths | `backend/app/content/module_loader.py`, `ai_stack/goc_yaml_authority.py`, `tools/mcp_server/fs_tools.py` | backend runtime/content APIs, MCP tools, RAG ingestion | loaders/discovery fail or partial discovery | mapped, not fully closed |
| Loader/discovery logic | `backend/app/content/module_service.py`, `module_loader.py`, MCP handlers | backend APIs, MCP clients/tests | missing module or stale metadata views | mapped, not fully closed |
| Registry/prompt IDs | `writers-room/app/models/markdown/_registry/prompt_registry.yaml` | writers-room presets/implementations | broken authoring references or stale alias chains | mapped, not fully closed |
| Schema/model contracts | `schemas/content_module.schema.json` | backend validators/tests/docs | contract mismatch between docs/schema/runtime | mapped, not fully closed |
| RAG lane rules | `ai_stack/rag.py` (`content/modules` vs `content/published`) | runtime retrieval path and RAG tests | lane misclassification without obvious hard failure | mapped, not fully closed |
| Runtime graph/orchestration | `world-engine/app/story_runtime/manager.py`, `ai_stack/langgraph_runtime.py` | live turn orchestration | seam drift between runtime and ai_stack semantics | mapped, not fully closed |
| MCP/tooling assumptions | `tools/mcp_server/config.py`, `fs_tools.py`, `tools_registry.py` | MCP tests and tool callers | divergent filesystem/API truth | mapped, not fully closed |
| Normative docs/gates | `docs/CANONICAL_TURN_CONTRACT_GOC.md`, `docs/VERTICAL_SLICE_CONTRACT_GOC.md`, `docs/audit/gate_summary_matrix.md` | implementers/operators/audits | false closure claims and wrong authority assumptions | mapped, not fully closed |
| Fixtures/frozen evidence | `tests/goc_gates/fixtures/*`, `docs/goc_evidence_templates/*`, `outgoing/**` | gates, evaluator package flow, scripts | broken evaluation flow or stale evidence references | mapped, not fully closed |

## Coverage evidence notes

- Literal-ID and path assumptions remain broad across tracked tests and docs.
- Path-sensitive behavior is confirmed in `ai_stack/rag.py` and module loaders.
- Mirror and evidence-policy surfaces remain active and require coordinated handling with residue and reference repair.

## Mandatory refusal rule (applied)

Because P0 classes are mapped but not fully closed at per-reference granularity, this pass refuses to:

- move GoC module directories,
- rename `module_id`,
- renamespace writers-room IDs,
- claim movement-based completion.

This pass completes control artifacts and closure governance only.

