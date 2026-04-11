# F — Full System Release Gate Report

Date: 2026-04-04 (full re-verification run)

## 1. Scope completed

Full-system release gate (F.1–F.10): environment and dependencies, layers **A1–A2, B1–B2, C1–C2, D1–D2, E1, H, G**, cross-layer consistency, and a final verdict. No new subsystems and no parallel stacks. This document reflects a **complete fresh verification** after correction of previously failing live integration tests.

## 2. Files changed (this documentation update)

| File | Change |
|------|--------|
| `docs/reports/ai_stack_gates/F_FULL_RELEASE_GATE_REPORT.md` | Regenerated from a full re-run of the scoped test matrix. |
| `docs/reports/AI_STACK_FULL_RELEASE_CLOSURE.md` | Aligned with the updated verdict and evidence. |

**Implementation note (already in tree before this report refresh):** Live backend↔World-Engine integration stability in `backend/tests/test_backend_playservice_integration.py` — isolated subprocess `env` (test Flask mode, shared secret, `RUN_STORE_BACKEND=json`, proxy vars stripped), **45s** readiness window, readiness probe on **`GET /api/health`** (not `/api/templates`). That repair is what removed the prior gate errors; this F run **confirms** it under the commands below.

## 3. Exact verification commands run

Host: **Windows**, **PowerShell**. Repository root: `c:\Users\YvesT\PycharmProjects\WorldOfShadows` unless noted.

### 3.1 AI stack (LangGraph, LangChain, RAG, capabilities, semantic embedding)

```text
Set-Location "c:\Users\YvesT\PycharmProjects\WorldOfShadows"
$env:PYTHONPATH = "c:\Users\YvesT\PycharmProjects\WorldOfShadows"
python -m pytest ai_stack/tests/test_langgraph_runtime.py ai_stack/tests/test_langchain_integration.py ai_stack/tests/test_rag.py ai_stack/tests/test_capabilities.py ai_stack/tests/test_semantic_embedding.py -q --tb=short --no-cov
```

**Result:** `53 passed` (3× UserWarning from Hugging Face hub: symlink cache limitation on Windows temp dirs — environment note, not failures).

### 3.2 World-Engine (story runtime, progression, RAG wiring)

```text
Set-Location "c:\Users\YvesT\PycharmProjects\WorldOfShadows\world-engine"
python -m pytest tests/test_story_runtime_api.py tests/test_story_progression_merge.py tests/test_canonical_runtime_contract.py tests/test_story_runtime_rag_runtime.py -q --tb=short --no-cov
```

**Result:** `18 passed`

### 3.3 Story runtime core (repo root on `PYTHONPATH`)

```text
Set-Location "c:\Users\YvesT\PycharmProjects\WorldOfShadows"
$env:PYTHONPATH = "c:\Users\YvesT\PycharmProjects\WorldOfShadows"
python -m pytest story_runtime_core/tests -q --tb=short --no-cov
```

**Result:** `21 passed`

**Setup truth:** Running these tests with `cwd` = `story_runtime_core/` and without repo root on `PYTHONPATH` yields `ModuleNotFoundError: No module named 'story_runtime_core'`.

### 3.4 Frontend (A1 — natural input / play shell)

```text
Set-Location "c:\Users\YvesT\PycharmProjects\WorldOfShadows\frontend"
python -m pytest tests/test_routes_extended.py -q --tb=short --no-cov
```

**Result:** `37 passed`

### 3.5 Administration-tool (manage game / AI governance, proxy contracts)

```text
Set-Location "c:\Users\YvesT\PycharmProjects\WorldOfShadows\administration-tool"
python -m pytest tests/test_manage_game_routes.py tests/test_proxy_contract.py tests/test_proxy_integration_contract.py -q --tb=short --no-cov
```

**Result:** `105 passed`

### 3.6 Backend (E1, H, D1, D2, C2 enrichment, observability, **live playservice**)

```text
Set-Location "c:\Users\YvesT\PycharmProjects\WorldOfShadows\backend"
python -m pytest tests/test_m11_ai_stack_observability.py tests/test_observability.py tests/test_game_routes.py tests/test_game_admin_routes.py tests/test_game_content_service.py tests/test_writers_room_routes.py tests/test_improvement_routes.py tests/runtime/test_mcp_enrichment.py tests/test_backend_playservice_integration.py -q --tb=short --no-cov
```

**Result:** **`142 passed`** in **324.33s** (includes two live World-Engine subprocess tests in `test_backend_playservice_integration.py`).

### 3.7 Writers-Room standalone package

```text
Set-Location "c:\Users\YvesT\PycharmProjects\WorldOfShadows\writers-room"
python -m pytest tests -q --tb=short --no-cov
```

**Result:** `3 passed`

### 3.8 MCP server (repo-root `PYTHONPATH`)

```text
Set-Location "c:\Users\YvesT\PycharmProjects\WorldOfShadows"
$env:PYTHONPATH = "c:\Users\YvesT\PycharmProjects\WorldOfShadows"
python -m pytest tools/mcp_server/tests -q --tb=short --no-cov
```

**Result:** `44 passed`

## 4. Environment and dependency notes

### 4.1 Declared dependencies (summary)

| Component | Source | Notable AI/RAG-related deps |
|-----------|--------|------------------------------|
| Backend | `backend/requirements.txt` | `langchain`, `langgraph`, `fastembed`, `numpy`, … |
| World-Engine | `world-engine/requirements.txt` | `langchain`, `langgraph`, `fastembed`, `fastapi`, `uvicorn`, … |
| Administration-tool | `administration-tool/requirements.txt` | Flask proxy/UI (no LangChain in this file) |
| Story runtime core | `story_runtime_core/pyproject.toml` | `pydantic`, `httpx` |

LangChain/LangGraph/FastEmbed are **required** in backend and world-engine requirements files (not documented as optional extras there). Dense/hybrid embedding behavior remains **environment-sensitive** (model download, cache layout, Windows symlink support).

### 4.2 Environment vs design blockers

| Topic | Classification |
|-------|----------------|
| `PYTHONPATH` for `story_runtime_core` / `tools/mcp_server` tests | **Invocation setup** |
| HF hub symlink warnings on Windows | **Environment** (degraded cache; tests passed) |
| Live playservice tests (~5+ min for full backend batch) | **Expected cost** of subprocess + sync; **not** a failure in this run |

## 5. Per-block verdicts

Scale: **Pass** / **Partial** / **Fail**.

| Block | Focus | Verdict | Basis |
|-------|-------|---------|--------|
| **A1** | Natural input → real turn; backend↔World-Engine bridge | **Pass** | `test_routes_extended.py` **37/37**; `test_backend_playservice_integration.py` **2/2** inside **142/142** backend batch. |
| **A2** | Authoritative commit vs diagnostics | **Pass** | World-Engine focused suite **18/18**; aligns with `world_engine_authoritative_narrative_commit.md`. |
| **B1** | LangChain where claimed | **Pass** | Part of **53** ai_stack tests (`test_langchain_integration.py`). |
| **B2** | LangGraph runtime turn path | **Pass** | `test_langgraph_runtime.py` + world-engine story tests. |
| **C1** | RAG on active paths | **Pass** | `test_rag.py`, `test_semantic_embedding.py`, `test_story_runtime_rag_runtime.py` in scoped runs. |
| **C2** | Capabilities / MCP-style surface | **Pass** | `test_capabilities.py`, `test_mcp_enrichment.py`, **44** MCP server tests. |
| **D1** | Writers-Room structured workflow | **Pass** | `test_writers_room_routes.py` in backend batch. |
| **D2** | Improvement loop | **Pass** | `test_improvement_routes.py` in backend batch. |
| **E1** | Evidence, governance, honest release-readiness | **Pass** | `test_m11_ai_stack_observability.py` + `test_observability.py` all green; aggregate readiness remains **honestly partial** when artifacts/tiers are weak — verified, not hidden. |
| **H** | Content lifecycle / publishing | **Pass** | Game routes, admin routes, content service tests in batch. |
| **G** | Operational hints / reduced waste (G scope) | **Pass** | Same ai_stack + D-route coverage as G-gate; operational signals tested in graph/integration/improvement/writers-room paths. |

## 6. Cross-layer consistency (F.9)

1. **A2 vs E1** — `ai_stack_evidence_service` separates committed narrative surface from diagnostic envelopes; `test_m11_ai_stack_observability.py` binds World-Engine diagnostics to session evidence. **Consistent.**

2. **B2 vs E1** — `graph_diagnostics` / `execution_health` / `repro_metadata` appear in evidence tests; release-readiness documents non-substitution of session bundles. **Consistent.**

3. **C vs D** — Writers-Room and improvement tests tie retrieval traces and evidence tiers to review artifacts. **Consistent.**

4. **D vs H** — Publish lifecycle tests enforce gating; review/governance surfaces are not equated with published feed content in tested contracts. **Consistent.**

5. **G vs E1** — Operational hints do not force a false “ready”; weak retrieval still yields partial readiness in tests. **Consistent.**

6. **Admin vs backend** — Manage routes and proxy tests reference governance API paths correctly. **Consistent.**

**No cross-layer contradictions** identified in code/tests reviewed for this gate.

## 7. What was verified as-is

All scoped suites in §3, totaling **383** test items in the listed invocations (53+18+21+37+105+142+3+44), **all passed** in this run.

## 8. What was repaired before this re-run (codebase, not this doc-only refresh)

- **`test_backend_playservice_integration`:** Subprocess environment isolation, **45s** readiness deadline, **`/api/health`** probe, and stricter test-mode env for the spawned World-Engine — eliminates prior false failures from slow startup, inherited CI env, or proxy settings.

- **Earlier gate cycle:** `tools/mcp_server/tests/test_rpc.py` expected `tools/list` count aligned with registry (**10** tools).

## 9. What remains partial (by design or maturity, not by test failure)

- **Aggregate** `GET /admin/ai-stack/release-readiness` can still return `overall_status: partial` when local artifacts or retrieval tiers are weak — **correct behavior**.

- **Writers-Room LangGraph** seed graph remains **shallower** than the runtime turn graph (explicit in release-readiness areas and docs).

## 10. What remains intentionally lightweight / local / environment-sensitive

- Local JSON RAG corpus, process-lifetime caches, optional dense sidecar; corpus refresh may require process restart.

- Writers-Room / improvement artifacts under **`var/`** JSON layouts.

- Windows HF hub cache symlink warnings during embedding tests.

- Documented **`PYTHONPATH`** requirements for some test trees.

## 11. Final verdict

**PASS**

## 12. Precise reason for final verdict

Major **A–E, H, G** claims **survived explicit verification** in this full re-run: all listed tests **passed**, including the **live** backend↔World-Engine integration tests. **Cross-layer** semantics in evidence and governance code are **aligned** with tests. **Environment-sensitive** behavior is **bounded and documented**; it does **not** invalidate the judgment that the repository is **honestly ready for a broader stabilization/release phase** (without claiming final production maturity). Governance and release-readiness **do not overstate** readiness when evidence is weak.

## 13. Remaining risk

- **Runtime cost:** Full backend batch including live subprocess tests is **slow** (~5+ minutes); CI should allocate time accordingly.

- **Operational:** Local persistence and RAG are still **not** a substitute for hardened production storage, cross-process cache coherence, or financial SLAs — `operational_cost_hints` remain non-financial, coarse signals.
