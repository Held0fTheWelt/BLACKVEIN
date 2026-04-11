# Pre — DS-003 narrative commit path structure

**Date:** 2026-04-12  
**Workstream:** `backend_runtime_services`

**Baseline:** `narrative_threads_update_from_commit.py` — `update_narrative_threads_from_commit_impl` ~**225** AST lines (monolith: parsing, terminal branch, upsert closure, merge).

**Goal:** Explicit drive type (`NarrativeCommitThreadDrive`), pure path helpers module, phased apply (`build` → `maybe_terminal` → `apply_non_terminal`).

**Planned gates:** `pytest` narrative runtime bundle (`test_narrative_thread_progression`, `test_narrative_state_transfer_dto`, `test_narrative_continuity`, `test_narrative_commit`).
