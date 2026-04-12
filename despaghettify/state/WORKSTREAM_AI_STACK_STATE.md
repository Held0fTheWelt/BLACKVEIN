# Workstream state: AI Stack

## Current objective

Changes under `ai_stack/` follow the same pre/post rules as [`EXECUTION_GOVERNANCE.md`](EXECUTION_GOVERNANCE.md). Structure topics: [`despaghettify/despaghettification_implementation_input.md`](../despaghettification_implementation_input.md).

## Current repository status

- Typical scope: `ai_stack/`, tests under `ai_stack/tests/`.
- After the next wave: artefacts under `artifacts/workstreams/ai_stack/pre|post/`.

## Hotspot / target status

- **DS-003** closed as a multi-stage strand (2026-04-11); facade remains `rag.py`.
- **DS-009 (2026-04-12):** context-pack assembly — wave 1 `rag_context_pack_build.py` + assembler delegate; wave 2 optional submodules (`section_titles`, `result_tail`, `compact_body`, `trace_footer`); posts `session_20260412_DS-009_post.md`, `session_20260412_DS-009_optional_post.md`.
- **DS-013 (2026-04-10):** GoC semantic priority rules — `_RULE_SPEC_ROWS` + frozen `_GOC_PRIORITY_RULES`; thin `build_goc_priority_rules`; see `post/session_20260410_DS-013_*`.

## Last completed wave/session

- **2026-04-10 — DS-002 w02 (C6, GoC tests):** Shared `goc_yaml_cache_fixtures.goc_yaml_authority_cache_autoclear` + `pytest_plugins` in seven GoC test modules (evidence under `backend_runtime_services` DS-002 post bundle — primary workstream for this C6 tranche).
- **2026-04-10 — DS-026 (dramatic review package section):** `langgraph_runtime_package_output_dramatic_review` + re-export from `langgraph_runtime_package_output_sections`. Evidence: `pre/session_20260410_DS-026_w01_dramatic_review_pre.md`, `pre/session_20260410_DS-026_wave_plan.json`; `post/session_20260410_DS-026_w01_dramatic_review_post.md`, `post/session_20260410_DS-026_w01_pytest_ai_stack.exit.txt`, `post/session_20260410_DS-026_w01_ds005.exit.txt`, `post/session_20260410_DS-026_w01_spaghetti_ast_scan_post.txt`, `post/session_20260410_DS-026_w01_pre_post_comparison.json`.
- **2026-04-10 — DS-025 (capability invocation summaries):** `capabilities_invocation_summaries` (per-`wos.*` handlers + `summarize_invocation_result`) + `_summarize_invocation_result` alias in `capabilities.py`. Evidence: `pre/session_20260410_DS-025_w01_capability_summaries_pre.md`, `pre/session_20260410_DS-025_wave_plan.json`; `post/session_20260410_DS-025_w01_capability_summaries_post.md`, `post/session_20260410_DS-025_w01_pytest_ai_stack.exit.txt`, `post/session_20260410_DS-025_w01_ds005.exit.txt`, `post/session_20260410_DS-025_w01_spaghetti_ast_scan_post.txt`, `post/session_20260410_DS-025_w01_pre_post_comparison.json`.
- **2026-04-10 — DS-022 (GoC legacy keyword scene candidates):** `scene_director_goc_legacy_keyword_candidates.legacy_keyword_scene_candidates` + import alias `_legacy_keyword_scene_candidates` in `scene_director_goc`; `spaghetti_ast_scan` **5-tuple** unpack fix. Evidence: `pre/session_20260410_DS-022_w01_legacy_keyword_pre.md`, `pre/session_20260410_DS-022_wave_plan.json`; `post/session_20260410_DS-022_w01_legacy_keyword_post.md`, `post/session_20260410_DS-022_w01_pytest_ai_stack.exit.txt`, `post/session_20260410_DS-022_w01_ds005.exit.txt`, `post/session_20260410_DS-022_w01_spaghetti_ast_scan_post.txt`, `post/session_20260410_DS-022_w01_pre_post_comparison.json`.
- **2026-04-10 — DS-013 (GoC semantic priority rules):** table-driven `_RULE_SPEC_ROWS`, module-level `_GOC_PRIORITY_RULES`, `build_goc_priority_rules` **3** AST L; `pytest ai_stack/tests/` **795** passed; `ds005` **0**; AST scan — builder **not** in top-12. Evidence: `pre/session_20260410_DS-013_goc_priority_rules_pre.md`; `post/session_20260410_DS-013_goc_priority_rules_post.md`, `…/session_20260410_DS-013_pytest_ai_stack.exit.txt`, `…/session_20260410_DS-013_spaghetti_ast_scan_post.txt`, `…/session_20260410_DS-013_ds005.exit.txt`, `…/session_20260410_DS-013_pre_post_comparison.json`.
- **2026-04-13 — DS-008 (dramatic effect gate + MCP session handlers):** `dramatic_effect_gate_evaluate_tags`, `dramatic_effect_gate_evaluate_branch_outcomes`, thin `dramatic_effect_gate_evaluate_core`; `tools/mcp_server/backend_session_mcp_handler_factories` + thin `tools_registry_handlers_backend_session`. Evidence: `post/session_20260413_DS-008_dramatic_gate_mcp_post.md`, `post/session_20260413_DS-008_pre_post_comparison.json`. Tests: `ai_stack/tests/test_dramatic_effect_gate.py` **7**; MCP session/registry **29** with `PYTHONPATH` at repo root; `ds005` **0**.
- **2026-04-12 — DS-009 (optional):** submodule split; pre `session_20260412_DS-009_optional_pre.md`; post `session_20260412_DS-009_optional_post.md` + `session_20260412_DS-009_optional_verification.json`; RAG trio **73**; `ds005` **0**.
- **2026-04-12 — DS-009:** `rag_context_pack_build.py`; assembler delegates. Pre: `artifacts/workstreams/ai_stack/pre/session_20260412_DS-009_scope.md`; post: `session_20260412_DS-009_post.md`, `session_20260412_DS-009_verification.json`; `pytest` RAG trio **73** passed; `ds005` exit **0**.
- **2026-04-11 — DS-001/002/003 (follow-up):** `ds005` + `validators`; `writers_room_store.py`; test imports off `rag` where trivial. Post: `artifacts/workstreams/ai_stack/post/session_20260411_DS-003_followup_001_002_003_post.md`; ai_stack RAG trio 73; backend writers_room + improvement_routes 88 passed.
- **2026-04-11 — DS-003 (optional combined):** `rag_retrieval_dtos.py` + workflow/workstream notes; `rag.py` ~88 lines. Post: `artifacts/workstreams/ai_stack/post/session_20260411_DS-003_optional_combined_post.md`; `pytest` ai_stack RAG trio 73; `backend/tests/writers_room` 64 passed; `ds005` exit 0.
- **2026-04-11 — DS-003 (stage 11):** `rag_runtime_bootstrap.py`; `rag.py` ~163 lines. Post: `artifacts/workstreams/ai_stack/post/session_20260411_DS-003_stage11_post.md`; `pytest` ai_stack RAG trio 73 passed; backend writers_room + improvement subset 41 passed.
- **2026-04-10 — DS-003 (stage 10):** `rag_corpus.py`; `rag.py` ~175 lines. Post: `artifacts/workstreams/ai_stack/post/session_20260410_DS-003_stage10_post.md`; `pytest …/test_rag.py` + `test_retrieval_governance_summary.py` + `test_langgraph_runtime.py` 73 passed.
- **2026-04-11 — DS-003 (stage 9):** `rag_ingestion.py`; `rag.py` ~314 lines. Post: `artifacts/workstreams/ai_stack/post/session_20260411_DS-003_stage9_post.md`; `pytest …/test_rag.py` + `test_retrieval_governance_summary.py` + `test_langgraph_runtime.py` 73 passed.
- **2026-04-11 — DS-003 (stage 8):** `rag_context_retriever.py`; `rag.py` ~470 lines. Post: `artifacts/workstreams/ai_stack/post/session_20260411_DS-003_stage8_post.md`; `pytest …/test_rag.py` + `test_retrieval_governance_summary.py` 63 passed.
- **2026-04-11 — DS-003 (stage 7):** `rag_context_pack_assembler.py`, `rag_persistent_store.py`; `rag.py` ~797 lines. Post: `artifacts/workstreams/ai_stack/post/session_20260411_DS-003_stage7_post.md`; `pytest …/test_rag.py` 56 passed, `test_retrieval_governance_summary.py` 7 passed.
- **2026-04-11 — DS-003 (stage 6):** `rag_retrieval_support.py`; `rag.py` ~1000 lines. Post: `artifacts/workstreams/ai_stack/post/session_20260411_DS-003_stage6_post.md`; `pytest …/test_rag.py` 56 passed, `test_retrieval_governance_summary.py` 7 passed.
- **2026-04-11 — DS-003 (stage 5):** `rag_retrieval_policy_pool.py`; `rag.py` ~1286 lines. Post: `artifacts/workstreams/ai_stack/post/session_20260411_DS-003_stage5_post.md`; `pytest …/test_rag.py` 56 passed, `test_retrieval_governance_summary.py` 7 passed.
- **2026-04-11 — DS-003 (stage 4):** `rag_retrieval_lexical.py`; `rag.py` ~1515 lines. Post: `artifacts/workstreams/ai_stack/post/session_20260411_DS-003_stage4_post.md`; `pytest …/test_rag.py` 56 passed.
- **2026-04-11 — DS-003 (stage 3):** `rag_embedding_index.py` (dense index); `rag.py` ~1706 lines. Post: `artifacts/workstreams/ai_stack/post/session_20260411_DS-003_stage3_post.md`; `pytest …/test_rag.py` 56 passed.
- **2026-04-11 — DS-003 (stage 2):** `rag_governance.py` with `governance_view_for_chunk`; `rag.py` ~1915 lines. Post: `artifacts/workstreams/ai_stack/post/session_20260411_DS-003_stage2_post.md`; `pytest …/test_rag.py` 56 passed, `test_retrieval_governance_summary.py` 7 passed.
- **2026-04-11 — DS-003 (stage 1):** Types and RAG tuning/version constants to `rag_types.py` / `rag_constants.py`; `rag.py` ~1973 lines. Post: `artifacts/workstreams/ai_stack/post/session_20260411_DS-003_stage1_post.md`; `pytest …/test_rag.py` 56 passed, `test_retrieval_governance_summary.py` 7 passed.

## Pre-work baseline reference

- `artifacts/workstreams/ai_stack/pre/git_status_scope.txt` *(optional)*
- `artifacts/workstreams/ai_stack/pre/session_YYYYMMDD_DS-xxx_*`

## Post-work verification reference

- `artifacts/workstreams/ai_stack/post/session_YYYYMMDD_DS-xxx_*`
- Pre→post comparison as described in governance.

## Known blockers

- —

## Next recommended wave

- Run [spaghetti-check-task.md](../spaghetti-check-task.md) when triggers apply to repopulate **DS-*** from current AST hotspots; align interfaces with `backend_runtime_services` when touching RAG / LangGraph / capabilities.

## Contradictions / caveats

- Progress narrative without artefact references is not closure-ready.
