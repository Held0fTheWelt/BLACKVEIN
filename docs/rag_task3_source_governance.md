# Task 3: Source governance and profile policy (retrieval)

## Summary

Retrieval now applies an explicit **source governance** layer on top of Task 1 lifecycle metadata and Task 2 hybrid/rerank quality. Policy is **compact**, **deterministic**, and **inspectable** via `retrieval_policy_version`, per-hit fields, and `policy_*` ranking notes—without conflating degradation (Task 1) or ranking-quality signals (Task 2).

## Source policy model

- **`SourceEvidenceLane`**: `canonical`, `supporting`, `draft_working`, `internal_review`, `evaluative` — derived from `ContentClass`, `canonical_priority`, and **repo-relative** `source_path` (published vs `content/modules/` vs other authored paths).
- **`SourceVisibilityClass`**: `runtime_safe`, `writers_working`, `improvement_diagnostic` — describes intended visibility, not IAM.
- **`SourceGovernanceView`**: frozen dataclass returned by `governance_view_for_chunk(chunk)` for a single source of truth.

**Path note:** Ingestion stores **relative** paths (e.g. `content/published/...`). Lane detection uses substrings such as `content/published/` so published modules classify as **canonical** even when `canonical_priority` was computed from absolute paths at build time.

## Profile behavior

| Profile | Hard gate | Soft policy (additive, `policy_soft_*`) |
|--------|-----------|-------------------------------------------|
| `runtime_turn_support` | Drops **same-module** `draft_working` **authored** chunks from the rerank pool when a **published canonical** authored chunk (`canonical_priority >= 4`) for that `module_id` is already in the pool. | `CHARACTER_PROFILE` penalty when strong authored module anchor exists (rare in default ingest paths). |
| `writers_review` | No draft/published hard exclusion (broader working material). | Small boost for `draft_working` authored modules (`policy_soft_writers_draft_visibility`). |
| `improvement_eval` | None beyond domain `DOMAIN_CONTENT_ACCESS`. | Small boost for `POLICY_GUIDELINE` (`policy_soft_improvement_policy_diagnostic`). |

Task 2 rerank rules (`rerank_*`, agreement, redundancy, runtime transcript clutter penalty, etc.) are **unchanged** in intent; Task 3 adds a **separate** policy stage before rerank (hard pool filter) and **additive** `policy_soft_*` deltas merged into the same final score with a single combined delta line in reasons.

## Canonical vs supporting in outputs

- **`pack_role`**: Workflow-oriented (e.g. `canonical_evidence`, `draft_working_context` for writers, `evaluative_evidence` for improvement). Runtime **canonical** pack role requires governance lane `canonical` (typically published-tree authored), not merely `canonical_priority >= 3`.
- **`RetrievalHit`**: `source_evidence_lane`, `source_visibility_class`, `policy_note`, `profile_policy_influence`.
- **`ContextPack`**: `sources[]` includes the same governance fields; `compact_context` lines include `role=`, `lane=`, `visibility=`, plus a short `context_pack_governance=...` footer per profile.

## Observability

- **`retrieval_policy_version`**: `task3_source_governance_v1` (constant `RETRIEVAL_POLICY_VERSION` in `ai_stack/rag.py`).
- **Ranking notes**: After Task 2 quality lines, compact `policy_*` aggregates (e.g. `policy_hard_excluded_pool_count=`) and optional per-chunk hard-exclusion lines (capped).
- **Capabilities**: `wos.context_pack.build` retrieval payload includes `retrieval_policy_version`; audit summaries may include `primary_source_evidence_lane` and `primary_profile_policy_influence`.

## Optional upward extensions chosen

- Writers **`draft_working_context`** pack section and sort tier between authored and review.
- Explicit **combined score delta** label `score_delta_task2_rerank_plus_task3_policy=` for traceability.
- **Profile version** strings bumped to `*_v3_source_policy` in `PROFILE_VERSIONS` for corpus metadata visibility.

## Deferred (Task 4+)

- Broader evaluation harnesses, external policy services, IAM, MCP observability redesign.
- Reordering `_detect_content_class` so paths like `content/characters/` can surface as true `CHARACTER_PROFILE` chunks (today most paths under `content/` ingest as `AUTHORED_MODULE`).
- Richer draft/published metadata persisted on `CorpusChunk` (would require schema/corpus migration).
