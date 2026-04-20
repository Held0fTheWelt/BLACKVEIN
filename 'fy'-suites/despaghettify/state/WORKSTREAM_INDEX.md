# Workstream index

This document is the canonical index for state-changing workstreams under governance.

## Status overview

| Workstream | State document | Pre artefacts | Post artefacts | Governance status |
| --- | --- | --- | --- | --- |
| Backend Runtime and Services | `WORKSTREAM_BACKEND_RUNTIME_AND_SERVICES_STATE.md` | `artifacts/workstreams/backend_runtime_services/pre/` | `artifacts/workstreams/backend_runtime_services/post/` | Governed |
| AI Stack | `WORKSTREAM_AI_STACK_STATE.md` | `artifacts/workstreams/ai_stack/pre/` | `artifacts/workstreams/ai_stack/post/` | Governed |
| Administration Tool | `WORKSTREAM_ADMIN_TOOL_STATE.md` | `artifacts/workstreams/administration_tool/pre/` | `artifacts/workstreams/administration_tool/post/` | Governed |
| Documentation | `WORKSTREAM_DOCUMENTATION_STATE.md` | `artifacts/workstreams/documentation/pre/` | `artifacts/workstreams/documentation/post/` | Governed |
| World Engine | `WORKSTREAM_WORLD_ENGINE_STATE.md` | `artifacts/workstreams/world_engine/pre/` | `artifacts/workstreams/world_engine/post/` | Governed |

**Pre/post directories** are target paths for future waves; they may exist in the working tree **without files** when older session artefacts were intentionally removed.

## Repository-wide rollout evidence

- Pre: `artifacts/repo_governance_rollout/pre/`
- Post: `artifacts/repo_governance_rollout/post/`

## Bootstrap decisions

- Existing governance / audit material under `docs/audit/`, `docs/audits/`, and `audits/` remains in place.
- `despaghettify/state/` is the canonical restart anchor for ongoing execution governance (Despaghettify hub).
- Historical claims without linked evidence do not count as closure proof.

## Structural code work (despaghettification)

Refactors against spaghetti / module boundaries use the **same** pre/post paths as the workstreams above (per affected `artifacts/workstreams/<slug>/pre|post/`). Canonical working template (input list, **DS-ID → workstream** table, implementation order, work log — currently prepared as templates): [`despaghettify/despaghettification_implementation_input.md`](../despaghettification_implementation_input.md).
