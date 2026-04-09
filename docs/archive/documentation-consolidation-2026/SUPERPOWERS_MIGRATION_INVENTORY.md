# Superpowers migration inventory

**Scope:** Former `docs/superpowers/plans/` and `docs/superpowers/specs/` (now `docs/archive/superpowers-legacy-execution-2026/{plans,specs}/`).  
**Inventory date:** 2026-04-10. **Validation:** Cross-checked against tracked `backend/`, `frontend/`, and canonical `docs/technical/` files.

**Classification legend**

- **DT** — durable technical truth (behavior, contracts, file roles)
- **DE** — durable explanatory/documentary (design rationale still worth preserving in archive)
- **HP** — historical process only (checkbox TDD steps, wave IDs)
- **OB** — obsolete or contradicted by current architecture (e.g. backend web shell paths superseded by `frontend/` play shell for player UX)
- **DC** — duplicate of content already present in canonical active docs before this pass

---

## Plans (`docs/archive/superpowers-legacy-execution-2026/plans/`)

| Source path | Class | Summary | Still-useful material? | Disposition |
|-------------|-------|---------|------------------------|-------------|
| `.../plans/2026-03-28-w2-2-2-mutation-policy.md` | DT, HP | TDD plan for `mutation_policy.py` + validator integration | DT absorbed into active doc | Migrated + archived |
| `.../plans/2026-03-28-w2-2-3-reference-policy.md` | DT, HP | TDD plan for `reference_policy.py` | DT absorbed | Migrated + archived |
| `.../plans/2026-03-28-w2-4-2-adapter-role-integration.md` | DT, HP | Adapter + `AIRoleContract` wiring | DT absorbed | Migrated + archived |
| `.../plans/2026-03-28-w2-4-3-role-parsing.md` | DT, HP | `parse_role_contract` / `role_structured_decision.py` | DT absorbed | Migrated + archived |
| `.../plans/2026-03-29-w2-4-4-role-diagnostics.md` | DT, HP | Diagnostics surfacing for role sections | DC (`llm-slm-role-stratification.md`, presenters) | Migrated + archived |
| `.../plans/2026-03-29-w2-4-5-responder-only-gating.md` | DT, HP | Responder-only execution boundary | DT absorbed | Migrated + archived |
| `.../plans/2026-03-29-w3-1-session-api-foundation.md` | HP, OB | Flask session CRUD plan; predates world-engine–first stance | Partially OB; API stance in `backend-runtime-classification.md` | Migrated + archived |
| `.../plans/2026-03-29-w3-3-implementation-plan.md` | HP, OB | Playable scene / shell work | Player path in `a1_free_input_primary_runtime_path.md` | Migrated + archived |
| `.../plans/2026-03-29-w3-4-1-presenter-implementation.md` | HP, OB | Presenter wiring to templates | OB (no `backend/.../session_shell.html` today) | Migrated + archived |
| `.../plans/2026-03-29-w3-4-2-character-panel-implementation.md` | HP, OB | Character panel UI | Presenters exist; UI target differs | Migrated + archived |
| `.../plans/2026-03-29-w3-4-3-conflict-panel-implementation.md` | HP, OB | Conflict panel UI | Same | Migrated + archived |
| `.../plans/2026-03-29-w3-4-4-panel-update-verification.md` | HP | Regression-test plan for panels | Tests may exist; no exclusive truth | Migrated + archived |
| `.../plans/2026-03-29-w3-5-1-history-debug-presenter.md` | DT, HP | `history_presenter` / `debug_presenter` | DC (`backend-runtime-classification.md` lists modules) | Migrated + archived |
| `.../plans/2026-03-30-w2w3-closure.md` | HP, DT | Meta-closure bundling helpers + session API + diagnostics | DT fragments absorbed | Migrated + archived |
| `.../plans/2026-03-30-w3-5-2-history-panel-ui.md` | HP, OB | History panel HTML | OB for player shell | Migrated + archived |
| `.../plans/2026-03-30-w3-5-3-debug-panel-ui.md` | HP, OB | Debug panel HTML | OB for player shell | Migrated + archived |
| `.../plans/2026-03-30-w3-5-4-synchronization-regression.md` | HP | Regression plan | No exclusive active claim | Migrated + archived |
| `.../plans/2026-03-30-w3-6-smoke-implementation.md` | HP, DC | Smoke test expansion | `docs/technical/reference/test-strategy-and-suite-layout.md` | Migrated + archived |
| `.../plans/2026-03-30-w4-implementation.md` | HP, OB | W4 sequential gates implementation | Superseded by roadmap/process docs; not promoted | Migrated + archived |
| `.../plans/2026-03-31-mcp-a1-2-tools-v0.md` | HP, DC | MCP tool v0 plan | `mcp-server-developer-guide.md`, `tools/mcp_server/README.md` | Migrated + archived |
| `.../plans/2026-03-31-mcp-a1-3-bridge-endpoints.md` | DT, HP | Service-token session JSON routes | DT absorbed | Migrated + archived |
| `.../plans/2026-03-31-mcp-a2-observability.md` | HP, DC | Trace + audit plan | `observability-and-governance.md` | Migrated + archived |
| `.../plans/2026-04-04-a1-refocus-natural-input-dominance.md` | HP, DT | Rename `operator_input` → `player_input` | Implemented; `a1_free_input_primary_runtime_path.md` | Migrated + archived |

---

## Specs (`docs/archive/superpowers-legacy-execution-2026/specs/`)

| Source path | Class | Summary | Still-useful material? | Disposition |
|-------------|-------|---------|------------------------|-------------|
| `.../specs/2026-03-28-w2-2-2-mutation-policy-design.md` | DT, DE | Deny-by-default whitelist domains | DT absorbed | Migrated + archived |
| `.../specs/2026-03-28-w2-4-1-role-contract-design.md` | DT, DE | Interpreter / director / responder contract | DT absorbed + `llm-slm-role-stratification.md` already distinguishes | Migrated + archived |
| `.../specs/2026-03-28-w2-4-3-role-parsing-integration.md` | DT, DE | Parsing integration narrative | DT absorbed | Migrated + archived |
| `.../specs/2026-03-29-w2-4-4-role-diagnostics.md` | DE, DC | Diagnostics shape | DC | Migrated + archived |
| `.../specs/2026-03-29-w3-3-playable-scene-interaction-design.md` | DE, DC | Playable scene UX | User/runtime docs | Migrated + archived |
| `.../specs/2026-03-29-w3-4-1-presenter-design.md` | DE, OB | Presenter design | Archive only | Migrated + archived |
| `.../specs/2026-03-29-w3-4-2-character-panel-design.md` | DE, OB | Character panel | Archive only | Migrated + archived |
| `.../specs/2026-03-29-w3-5-1-history-debug-presenter-design.md` | DE, DC | Presenter outputs | Code + classification doc | Migrated + archived |
| `.../specs/2026-03-29-w3-5-2-history-panel-ui-design.md` | DE, OB | History UI | Archive only | Migrated + archived |
| `.../specs/2026-03-30-w3-5-3-debug-panel-ui.md` | DE, OB | Debug UI | Archive only | Migrated + archived |
| `.../specs/2026-03-30-w3-5-4-synchronization-regression.md` | HP, DE | Regression spec | Archive only | Migrated + archived |
| `.../specs/2026-03-30-w3-6-smoke-coverage-design.md` | HP, DC | Smoke design | Test strategy doc | Migrated + archived |
| `.../specs/2026-03-30-w4-design.md` | HP, DE | W4 gate model | Roadmap / process; not promoted as technical truth | Migrated + archived |
| `.../specs/2026-03-31-mcp-a1-3-bridge-endpoints.md` | DT, DE | Bridge endpoint JSON + auth | DT absorbed | Migrated + archived |

**Count:** 23 plans + 14 specs = **37** source files.

---

## Revalidation note (audit baselines)

Baseline audit files that predate this move may still mention the historical `docs/superpowers/*` path in narrative. **Current tree:** sources live under `docs/archive/superpowers-legacy-execution-2026/`. Rows in `TASK_1A`, `TASK_1B`, `TASK_2_*`, and admin/dev README exclusions were updated during this pass where they still acted as navigation targets.
