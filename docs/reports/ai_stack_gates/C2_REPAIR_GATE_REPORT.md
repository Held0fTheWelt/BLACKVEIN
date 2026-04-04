# C2 Repair Gate Report — MCP/Capabilities as Real Workflow Tools

Date: 2026-04-04

## 1. Scope completed

- Moved improvement experiment workflow from service-only logic to capability-backed workflow actions.
- Wired `wos.context_pack.build` and `wos.review_bundle.build` into `POST /api/v1/improvement/experiments/run`.
- Added explicit capability failure surfacing (`502 capability_workflow_failed`) with capability audit payload.
- Extended improvement route tests to assert real tool invocation outputs and audit records.
- Kept runtime and writers-room capability workflows intact and revalidated.

## 2. Files changed

- `backend/app/api/v1/improvement_routes.py`
- `backend/tests/test_improvement_routes.py`
- `docs/architecture/mcp_in_world_of_shadows.md`
- `docs/reports/ai_stack_gates/C2_REPAIR_GATE_REPORT.md`

## 3. What is truly wired

- Runtime path uses `wos.context_pack.build` in real turn execution flow and emits capability audit diagnostics.
- Writers-room review flow uses `wos.context_pack.build` and `wos.review_bundle.build` for retrieval + artifact generation.
- Improvement experiment run flow now depends on:
  - `wos.context_pack.build` (`improvement` mode) for evaluation-context retrieval,
  - `wos.review_bundle.build` (`improvement` mode) for reviewable recommendation bundle artifact,
  - capability audit return in API payload.

## 4. What remains incomplete

- No external MCP policy authority or signed immutable audit store is implemented.
- Capability layer remains process-local and in-memory for runtime audit rows.
- `wos.transcript.read` is still not a required dependency in the primary improvement run path.

## 5. Tests added/updated

- Updated `backend/tests/test_improvement_routes.py`:
  - verifies improvement run response includes capability-backed retrieval, review bundle, and audit entries,
  - verifies capability failure path returns explicit `502` with error and audit details.
- Existing capability governance tests retained:
  - `wos_ai_stack/tests/test_capabilities.py` (permission denial, validation errors, audit emission).
- Existing writers-room and runtime capability wiring tests re-run.

## 6. Exact test commands run

```powershell
python -m pytest "backend/tests/test_improvement_routes.py"
```

```powershell
python -m pytest "wos_ai_stack/tests/test_capabilities.py"
```

```powershell
python -m pytest "backend/tests/test_writers_room_routes.py"
```

```powershell
python -m pytest "world-engine/tests/test_story_runtime_rag_runtime.py"
```

## 7. Pass / Partial / Fail

Pass

## 8. Reason for the verdict

- Tools are now invoked in runtime, writers-room, and improvement workflow code, not only registered in an inventory.
- Permission/scope and audit behavior remains enforced and covered by capability tests.
- Improvement workflow now has explicit, test-covered failure behavior when capability tooling fails.
- Tests validate invocation outcomes and returned audit evidence in real route paths.

## 9. Risks introduced or remaining

- Improvement route now depends on capability stack availability; if retrieval/tooling degrades, route returns explicit failure.
- Capability registry is instantiated per improvement run call; this is simple and explicit but may be optimized later.
- Audit visibility is strong for current paths but still bounded by in-memory retention semantics.
